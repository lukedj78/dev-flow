# Module: db — `postgres-drizzle` (standard driver, tenant isolation by row-level security)

`meta.json#stack.db = "postgres-drizzle"`: Drizzle on the standard Postgres driver (`pg`), so the
same code runs on Neon, a managed Postgres or one you host. The tenant boundary is the **database's**
— row-level security on every table that carries `workspace_id` — not a `where` clause each query
has to remember. For the Neon-only setup use `module-db.md` (`neon-drizzle`).

Every block below ran against Postgres 18 with pgvector on 2026-11-24 (drizzle-orm 0.45, pg 8.23,
PGlite 0.6). Measured: connected as the application role, workspace A sees only its rows, a query
outside `withTenant` returns zero rows, and inserting a row for workspace B while `app.workspace` is
A is refused by Postgres itself.

## Where it goes

- **Monorepo with `boundaries.json`** (topology `web-agent-inapp`): everything in **`packages/db`** —
  `src/schema/`, `src/repositories/`, `src/client.ts`, `migrations/`, `test/`. `db` depends on
  `config` only; nothing outside `packages/db` imports `pg` or `drizzle-orm/node-postgres`.
- Single app: the same files under `lib/db/` and `migrations/` at the app root.

## Install (current versions, exact)

```bash
pnpm --filter @<slug>/db add --save-exact drizzle-orm pg
pnpm --filter @<slug>/db add -D --save-exact drizzle-kit @types/pg @electric-sql/pglite @electric-sql/pglite-pgvector
```

**Never** `@neondatabase/serverless`, `drizzle-orm/neon-http` or `neon-serverless` in shared code:
they only speak to Neon. `scripts/check_rls.py --root` fails if it finds them.

## Two roles, and why

| Role | Who uses it | Rights |
|---|---|---|
| owner (the database's) | migrations only | creates tables, policies, roles |
| `app_rls` (group, NOLOGIN) | — | `NOSUPERUSER NOBYPASSRLS`, DML on the tables |
| `app_user` (login, member of `app_rls`) | the application's `DATABASE_URL` | inherits `app_rls` and nothing else |

A superuser or a `BYPASSRLS` role **ignores row-level security entirely**, and so does a role that is
a member of one. The application must never connect as the owner. The login role's password is a
secret, so it is created outside the repository:

```sql title="scripts/create-app-login.sql — run as the owner, once per environment and on every rotation"
-- The password comes from the environment (\getenv), never from the command line: a `-v pw=…`
-- argument is visible to every process on the host, and a literal in a file ends up in history.
SET log_statement = 'none';   -- keep it out of the server log; superuser only — drop the line on managed Postgres and check the provider's statement logging
\getenv pw APP_DB_PASSWORD
\if :{?pw}
SELECT format('CREATE ROLE app_user LOGIN IN ROLE app_rls PASSWORD %L', :'pw')
  WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_user') \gexec
SELECT format('ALTER ROLE app_user PASSWORD %L', :'pw') \gexec
\else
\echo 'APP_DB_PASSWORD is not set'
\quit
\endif
```

```bash
# APP_DB_PASSWORD from your secret store (never typed into chat); psql ≥ 15 for \getenv.
APP_DB_PASSWORD=… psql -X "$OWNER_DATABASE_URL" -v ON_ERROR_STOP=1 -f scripts/create-app-login.sql
```

Re-running it **rotates** the password (the `ALTER ROLE`). Measured in a Postgres 18 container: role
created from the environment, login as it with `rolsuper=f rolbypassrls=f`.

⚠️ **Managed Postgres:** the roles a provider's console creates may carry `BYPASSRLS` or belong to a
role that does (`[VERIFY]` on Neon: console-created roles are members of `neon_superuser`). Create
`app_user` with SQL as above, then let `check_rls.py` prove it.

## Migrations

Hand-written SQL in `migrations/`, applied in order by the owner (drizzle-kit can generate the
`CREATE TABLE` part with `drizzle-kit generate`; the RLS block is always written by hand, in the same
migration as the table, so a table never exists without it).

```sql title="migrations/0000_roles_and_extensions.sql"
-- Run as the database OWNER. Creates the group role the application logs in through.
-- The login role itself (with its password) is created outside the repository: see the module reference.
CREATE EXTENSION IF NOT EXISTS vector;
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_rls') THEN
    CREATE ROLE app_rls NOLOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;
  END IF;
END $$;
GRANT USAGE ON SCHEMA public TO app_rls;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_rls;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO app_rls;
```

**The RLS block every table with `workspace_id` gets** — `FORCE` makes it apply to the table owner too:

```sql title="migrations/0001_projects.sql"
CREATE TABLE IF NOT EXISTS projects (
  id text PRIMARY KEY,
  organization_id text NOT NULL,
  workspace_id text NOT NULL,
  name text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS projects_workspace_idx ON projects (workspace_id);
GRANT SELECT, INSERT, UPDATE, DELETE ON projects TO app_rls;

-- The RLS block every table with workspace_id gets. FORCE makes it apply to the table owner too.
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON projects;
CREATE POLICY tenant_isolation ON projects
  USING (workspace_id = current_setting('app.workspace', true))
  WITH CHECK (workspace_id = current_setting('app.workspace', true));
```

⚠️ `ALTER DEFAULT PRIVILEGES` covers tables created **by the role that ran it**. Every migration that
creates a table still grants it to `app_rls` explicitly, as `0001` does, so a table created by another
role is never silently out of reach — and `check_rls.py` lists any table the app can touch.

## Schema, client, repositories

```ts title="src/schema/projects.ts"
import { index, pgTable, text, timestamp } from "drizzle-orm/pg-core";

// Every domain table carries the tenant on the row. RLS (the migration that creates the table) filters on workspace_id.
export const projects = pgTable(
  "projects",
  {
    id: text("id").primaryKey(),
    organizationId: text("organization_id").notNull(),
    workspaceId: text("workspace_id").notNull(),
    name: text("name").notNull(),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (t) => [index("projects_workspace_idx").on(t.workspaceId)],
);
```

```ts title="src/client.ts"
import { sql } from "drizzle-orm";
import { drizzle, type NodePgDatabase } from "drizzle-orm/node-postgres";
import pg from "pg";
import * as schema from "./schema/index.ts";

export type Db = NodePgDatabase<typeof schema>;
export type Tx = Parameters<Parameters<Db["transaction"]>[0]>[0];

/** One pool per process, connected as the APPLICATION role (NOSUPERUSER NOBYPASSRLS) — never the owner. */
export function createDb(url = process.env.DATABASE_URL): Db {
  if (!url) throw new Error("DATABASE_URL is not set");
  return drizzle(new pg.Pool({ connectionString: url }), { schema });
}

export type TenantContext = { workspaceId: string; containerId?: string };

/**
 * Every query on domain data goes through here. It opens a transaction and sets the tenant with
 * set_config(..., true) — local to THIS transaction — so a pooled connection never carries one
 * request's workspace into the next. Outside withTenant, RLS returns zero domain rows.
 */
export async function withTenant<T>(db: Db, ctx: TenantContext, fn: (tx: Tx) => Promise<T>): Promise<T> {
  if (!ctx.workspaceId) throw new Error("withTenant: workspaceId is required");
  return db.transaction(async (tx) => {
    await tx.execute(sql`select set_config('app.workspace', ${ctx.workspaceId}, true)`);
    if (ctx.containerId) await tx.execute(sql`select set_config('app.container', ${ctx.containerId}, true)`);
    return fn(tx);
  });
}
```

- **`set_config(…, true)` is transaction-local.** With a pool, a session-level `SET` would leak one
  request's workspace into the next request that gets the same connection. `withTenant` opens the
  transaction, so the setting dies with it.
- `app.container` is for a second axis (a knowledge container, a project) when a policy needs it.

```ts title="src/repositories/projects.ts"
import { type Db, type TenantContext, withTenant } from "../client.ts";
import { projects } from "../schema/projects.ts";

// Repositories take the tenant context and never a raw workspace filter from the caller:
// the row filter is the database's (RLS), the context is the request's.
export const projectRepository = {
  list: (db: Db, ctx: TenantContext) => withTenant(db, ctx, (tx) => tx.select().from(projects)),
  create: (db: Db, ctx: TenantContext & { organizationId: string }, p: { id: string; name: string }) =>
    withTenant(db, ctx, (tx) =>
      tx
        .insert(projects)
        .values({ ...p, organizationId: ctx.organizationId, workspaceId: ctx.workspaceId })
        .returning(),
    ),
};
```

## Tests

**Local, no Docker:** PGlite (in-process Postgres) with pgvector. PGlite runs as a superuser, which
ignores RLS — the test switches to the application role first, or it proves nothing.

```ts title="test/rls.test.ts"
// Fast local check of the migrations' RLS on PGlite (in-process Postgres, with pgvector).
// PGlite runs as a superuser, which ignores RLS — so the test switches to the application role.
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { PGlite } from "@electric-sql/pglite";
import { vector } from "@electric-sql/pglite-pgvector";
import { describe, expect, it } from "vitest";

const migrations = join(import.meta.dirname, "..", "migrations");

async function database() {
  const pg = new PGlite({ extensions: { vector } });
  for (const f of readdirSync(migrations)
    .filter((f) => f.endsWith(".sql"))
    .sort()) {
    await pg.exec(readFileSync(join(migrations, f), "utf8"));
  }
  await pg.exec(`insert into projects values ('p1','o1','ws-a','A'), ('p2','o2','ws-b','B secret');`);
  await pg.exec("set role app_rls");
  return pg;
}

describe("row-level security", () => {
  it("returns nothing without app.workspace", async () => {
    const pg = await database();
    expect((await pg.query("select * from projects")).rows).toHaveLength(0);
  });

  it("returns only the workspace in app.workspace", async () => {
    const pg = await database();
    const rows = await pg.transaction(async (tx) => {
      await tx.query("select set_config('app.workspace', 'ws-a', true)");
      return (await tx.query<{ name: string }>("select name from projects")).rows;
    });
    expect(rows.map((r) => r.name)).toEqual(["A"]);
  });

  it("cannot update or delete another workspace's rows, nor move a row to it", async () => {
    const pg = await database();
    const result = await pg.transaction(async (tx) => {
      await tx.query("select set_config('app.workspace', 'ws-a', true)");
      const updated = await tx.query("update projects set name = 'x' where id = 'p2'");
      const deleted = await tx.query("delete from projects where id = 'p2'");
      return { updated: updated.affectedRows, deleted: deleted.affectedRows };
    });
    expect(result).toEqual({ updated: 0, deleted: 0 });
    await expect(
      pg.transaction(async (tx) => {
        await tx.query("select set_config('app.workspace', 'ws-a', true)");
        await tx.query("update projects set workspace_id = 'ws-b' where id = 'p1'");
      }),
    ).rejects.toThrow(/row-level security/);
  });

  it("refuses a row for another workspace", async () => {
    const pg = await database();
    await expect(
      pg.transaction(async (tx) => {
        await tx.query("select set_config('app.workspace', 'ws-a', true)");
        await tx.query("insert into projects values ('x','o2','ws-b','forged')");
      }),
    ).rejects.toThrow(/row-level security/);
  });
});
```

**Against a real Postgres** (container or the dev database), as the application role:

```bash
python3 <skills>/module-add/scripts/check_rls.py --url "$DATABASE_URL" --root . \
    --allow user,session,account,verification,organization,member,invitation,team,team_member
# psql only inside a container (the password travels in PGPASSWORD, never on the command line):
python3 <skills>/module-add/scripts/check_rls.py --url "postgres://app_user:…@localhost:5432/app" \
    --psql-cmd "docker exec -i -e PGPASSWORD <container> psql" --root .
```

It checks that the role (and every role it inherits) is neither SUPERUSER nor BYPASSRLS; that every
table the app role can touch either carries `workspace_id` or is in `--allow` (auth tables keyed by
organization, the migrations journal — say why in the command that CI runs); that every tenant table
has `relrowsecurity`, `relforcerowsecurity` and policies, **all** of which filter on `app.workspace`
in USING and WITH CHECK (one permissive `USING (true)` beside a good policy opens the table); that
each returns zero rows with no `app.workspace`; and that no Neon serverless driver is imported. It
runs psql with `-X` and without `PGOPTIONS`, so a local `~/.psqlrc` cannot `SET ROLE` behind its back.
Measured: green as `app_user`; red as the owner, on a table without `FORCE`, with a `USING (true)`
policy added, and on a readable table that is neither isolated nor allowed.

## Done when

- `pnpm --filter @<slug>/db test` green (the PGlite RLS test);
- `check_rls.py` prints `rls: clean` against a real Postgres, connected as `app_user`;
- `meta.json#stack.db = "postgres-drizzle"`, history `{ "skill": "module-add", "action": "add-db" }`.
