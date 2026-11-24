#!/usr/bin/env python3
"""check_rls.py — prove a Postgres database is isolated by tenant, connected AS THE APPLICATION ROLE.

Usage:
    python3 check_rls.py [--url <app-role URL>] [--psql-cmd "<command that runs psql>"]
                         [--allow <table,...>] [--root <repo>]

    --url        the URL the APP uses (the NOSUPERUSER NOBYPASSRLS login role), not the owner's. Default:
                 $DATABASE_URL. The password is taken OUT of the URL and handed to psql in PGPASSWORD, so it
                 never appears in the process list. With --psql-cmd "docker exec …", pass it on with
                 `docker exec -e PGPASSWORD …` (the variable is set for the command).
    --psql-cmd   how to run psql; default "psql". Always run with -X (no ~/.psqlrc) and no PGOPTIONS, so
                 nothing local can SET ROLE or set app.workspace behind the check's back.
    --allow      tables the app may read WITHOUT tenant isolation, by design (comma-separated, `schema.table`
                 or `table`): auth tables keyed by organization, the migrations journal. Everything else the
                 app role can touch must be isolated.
    --root       also scan this repository's source for the Neon serverless driver (forbidden in shared
                 code: the same code must run on Neon and on any Postgres).

Checks (each one line, PASS or FAIL; exit 1 on any FAIL, 2 when the database cannot be reached):
  1. role      — the current role, and every role it is a member of, is neither SUPERUSER nor BYPASSRLS;
  2. coverage  — every table the app role has privileges on either carries `workspace_id` or is in --allow;
  3. flags     — every table with `workspace_id` has relrowsecurity AND relforcerowsecurity, at least one
                 policy, and EVERY policy that applies to the app role filters on app.workspace in USING and
                 in WITH CHECK (a single permissive `USING (true)` beside a good policy opens the table);
  4. empty     — with no app.workspace set, each of those tables returns zero rows;
  5. driver    — with --root: no `@neondatabase/serverless` or Neon drizzle driver outside node_modules.
Pure standard library; the SQL runs through psql.
"""
from __future__ import annotations

import argparse
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit, urlunsplit

SKIP_DIRS = {"node_modules", ".next", ".turbo", "dist", "build", ".output", ".eve", ".git"}
NEON = re.compile(r"""["'](@neondatabase/serverless|drizzle-orm/neon-http|drizzle-orm/neon-serverless)["']""")
DEFAULT_ALLOW = {"__drizzle_migrations", "drizzle.__drizzle_migrations"}


class Unreachable(Exception):
    pass


def split_password(url: str) -> tuple[str, str | None]:
    """postgres://u:pw@h/db → (postgres://u@h/db, pw)."""
    parts = urlsplit(url)
    if parts.password is None:
        return url, None
    netloc = (parts.username or "") + "@" + parts.hostname + (f":{parts.port}" if parts.port else "")
    return urlunsplit(parts._replace(netloc=netloc)), unquote(parts.password)


def make_runner(psql: list[str], url: str):
    bare, password = split_password(url)
    env = {k: v for k, v in os.environ.items() if k not in ("PGOPTIONS", "PSQLRC")}
    if password is not None:
        env["PGPASSWORD"] = password

    def run_sql(sql: str) -> list[list[str]]:
        r = subprocess.run([*psql, "-X", bare, "-At", "-F", "\t", "-v", "ON_ERROR_STOP=1", "-c", sql],
                           capture_output=True, text=True, timeout=60, env=env)
        if r.returncode != 0:
            raise Unreachable((r.stderr or r.stdout).strip()[:500])
        return [line.split("\t") for line in r.stdout.splitlines() if line]

    return run_sql


def ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def filters_tenant(expr: str | None) -> bool:
    return bool(expr) and "app.workspace" in expr


def main() -> int:
    ap = argparse.ArgumentParser(description="Check tenant isolation (RLS) as the application role.")
    ap.add_argument("--url", default=os.environ.get("DATABASE_URL"))
    ap.add_argument("--psql-cmd", default="psql")
    ap.add_argument("--allow", default="")
    ap.add_argument("--root")
    a = ap.parse_args()
    if not a.url:
        print("error: pass --url or set DATABASE_URL (the application role's URL)")
        return 2
    run_sql = make_runner(shlex.split(a.psql_cmd), a.url)
    allow = DEFAULT_ALLOW | {t.strip() for t in a.allow.split(",") if t.strip()}
    fails = 0

    def report(ok: bool, line: str) -> None:
        nonlocal fails
        fails += 0 if ok else 1
        print(f"{'PASS' if ok else 'FAIL'}  {line}")

    try:
        user, sup, byp = run_sql("select current_user, rolsuper, rolbypassrls from pg_roles where rolname = current_user")[0]
        inherited = run_sql("select r.rolname from pg_roles r where (r.rolsuper or r.rolbypassrls) "
                            "and pg_has_role(current_user, r.oid, 'member')")
        report(sup == "f" and byp == "f" and not inherited,
               f"role: {user} rolsuper={sup} rolbypassrls={byp}"
               + (f", inherits from {', '.join(x[0] for x in inherited)}" if inherited else ""))
        member_of = {r[0] for r in run_sql("select r.rolname from pg_roles r where pg_has_role(current_user, r.oid, 'member')")}
        tables = run_sql(
            "select n.nspname, c.relname, c.relrowsecurity, c.relforcerowsecurity, "
            "exists (select 1 from pg_attribute a where a.attrelid = c.oid and a.attname = 'workspace_id' and not a.attisdropped) "
            "from pg_class c join pg_namespace n on n.oid = c.relnamespace "
            "where c.relkind in ('r', 'p') and not c.relispartition "
            "and n.nspname not in ('pg_catalog', 'information_schema') and n.nspname not like 'pg_toast%' "
            "and has_table_privilege(current_user, c.oid, 'SELECT, INSERT, UPDATE, DELETE') order by 1, 2")
    except Unreachable as exc:
        print(f"error: cannot query the database: {exc}")
        return 2
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"error: cannot run psql ({a.psql_cmd}): {exc}")
        return 2

    tenant = []
    for schema, table, rls, force, has_ws in tables:
        name = f"{schema}.{table}"
        if has_ws != "t":
            report(name in allow or table in allow,
                   f"coverage: {name} is reachable by {user} " + ("(allowed: not tenant data)" if name in allow or table in allow
                                                                   else "with no workspace_id and no RLS — isolate it, or --allow it with a reason"))
            continue
        tenant.append((schema, table))
        try:
            policies = run_sql(f"select policyname, roles::text, qual, with_check from pg_policies "
                               f"where schemaname = '{schema}' and tablename = '{table}'")
        except Unreachable as exc:
            report(False, f"flags: {name} policies unreadable: {exc}")
            continue
        applicable = [p for p in policies
                      if "public" in p[1].strip("{}").split(",") or member_of & set(p[1].strip("{}").split(","))]
        weak = [p[0] for p in applicable if not filters_tenant(p[2]) or (p[3] and not filters_tenant(p[3]))]
        ok = rls == "t" and force == "t" and bool(applicable) and not weak
        report(ok, f"flags: {name} relrowsecurity={rls} relforcerowsecurity={force} policies={len(applicable)}"
                   + (f", not filtering on app.workspace: {', '.join(weak)}" if weak else ""))
    if not tenant:
        report(False, "flags: no table has a workspace_id column — nothing is tenant-scoped yet")
    for schema, table in tenant:
        try:
            n = run_sql(f"select count(*) from {ident(schema)}.{ident(table)}")[0][0]
            report(n == "0", f"empty: {schema}.{table} returns {n} row(s) with no app.workspace set")
        except Unreachable as exc:
            report(False, f"empty: {schema}.{table} cannot be read by {user}: {exc}")

    if a.root:
        hits = []
        for here, dirs, files in os.walk(a.root):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for f in files:
                if f.endswith((".ts", ".tsx", ".js", ".mjs", ".cjs", ".mts")):
                    p = Path(here) / f
                    try:
                        m = NEON.search(p.read_text(encoding="utf-8", errors="replace"))
                    except OSError:
                        continue
                    if m:
                        hits.append(f"{p.relative_to(a.root)} ({m.group(1)})")
        report(not hits, "driver: no Neon serverless driver in the code" if not hits else f"driver: found in {', '.join(hits)}")

    print("rls: clean" if not fails else f"rls: {fails} check(s) failed")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
