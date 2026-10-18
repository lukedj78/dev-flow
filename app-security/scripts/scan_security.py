#!/usr/bin/env python3
"""scan_security.py — the fifth pre-deploy gate's first pass: can this app's code be attacked?

    python3 scan_security.py <project-root> [--json]

Two halves. The external tools, used when they are installed: OSV-Scanner (or pnpm/npm audit) for vulnerable
dependencies, gitleaks for secrets in the working tree and in git history, Semgrep with rules fetched at run time.
And our own checks for what Next.js makes easy to get wrong: every exported Server Action is a public POST
endpoint, so authentication and authorization belong inside each one — a page, layout or proxy check does not
cover it (Next.js Data Security guide).

Everything here is a SIGNAL, not a verdict: the agent reads each flagged file before reporting it
(`references/review.md`). A tool that is missing, offline or failing reads "not checked" — never "ok".
Stdlib only. Never installs anything, never runs an exploit.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

OK, FOUND, NOT_CHECKED = "ok", "found", "not checked"

CODE_CHECKS = ("server-action-unauthenticated", "route-handler-unauthenticated", "query-by-id-unscoped",
               "action-returns-row", "public-env-secret", "server-only-missing", "raw-sql",
               "security-headers-missing")
DEFAULT_SESSION_CALLS = ("getSession", "getCurrentUserId", "getCurrentTenantId", "requireUser", "verifySession", "auth(")
PUBLIC_BY_NATURE = ("ANON_KEY", "PUBLISHABLE", "POSTHOG_KEY", "SITE_KEY", "_URL", "REVENUECAT", "MAPS_API_KEY")
SECRET_WORDS = re.compile(r"SECRET|PRIVATE|TOKEN|PASSWORD|API_KEY|SERVICE_ROLE|_KEY$")
SKIP_ANYWHERE = {"node_modules"}   # plus every hidden directory (.next, .eve, .output…)
SKIP_TOP = {"dist", "build", "out", "coverage", "ios", "android"}   # only right under a source root: app/build/ is a route
CODE_SUFFIXES = (".ts", ".tsx", ".js", ".jsx", ".mjs")
# an owner filter: a column naming the user or the tenant, or the id compared with the caller's own id
SCOPE_WORDS = r"(?:user|tenant|owner|org|organization|workspace|team|account|member)"
SCOPE_COLUMN = rf"eq\(\s*\w+\.\w*{SCOPE_WORDS}(?:Id|_id)\b"
# what makes a module dangerous in a client bundle: a server-side env var, or a database client
HOLDS_SECRET = (r"process\.env\.(?!NEXT_PUBLIC_)\w|\b(?:drizzle|neon|postgres|createClient)\s*\(|new\s+Pool\s*\(|"
                r"from\s+['\"](?:pg|postgres|@neondatabase/serverless|drizzle-orm/(?:neon-http|neon-serverless|postgres-js|node-postgres|vercel-postgres))['\"]")
HEURISTIC = " (heuristic — read the code before reporting)"


@dataclass
class Finding:
    check: str
    status: str
    detail: str
    where: list[str] = field(default_factory=list)
    routed_to: str | None = None


def source_roots(root: Path) -> list[Path]:
    """The project root, plus every app and package in a monorepo."""
    out = [root]
    for group in ("apps", "packages"):
        if (root / group).is_dir():
            out += sorted(p for p in (root / group).iterdir() if p.is_dir())
    return out


def code_files(root: Path):
    roots = source_roots(root)
    for base in roots:
        nested = [r for r in roots if base in r.parents]   # each app and package is walked from its own root
        for p in base.rglob("*"):
            if not p.is_file() or p.suffix not in CODE_SUFFIXES or any(n in p.parents for n in nested):
                continue
            parts = p.relative_to(base).parts[:-1]
            if (parts and parts[0] in SKIP_TOP) or any(x in SKIP_ANYWHERE or x.startswith(".") for x in parts):
                continue
            yield p


def read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def rel(root: Path, p: Path) -> str:
    return p.relative_to(root).as_posix()


def session_calls(root: Path) -> list[str]:
    """The default session helpers, plus the project's own (`meta.json#stack_config.security_session_calls`)."""
    extra: list[str] = []
    try:
        meta = json.loads((root / ".workflow" / "meta.json").read_text(encoding="utf-8"))
        extra = [str(x) for x in ((meta.get("stack_config") or {}).get("security_session_calls") or [])]
    except (OSError, ValueError, AttributeError):
        pass
    return list(DEFAULT_SESSION_CALLS) + extra


def dependencies(base: Path) -> set[str]:
    try:
        pkg = json.loads(read(base / "package.json") or "{}")
    except ValueError:
        return set()
    return set(pkg.get("dependencies") or {}) | set(pkg.get("devDependencies") or {}) if isinstance(pkg, dict) else set()


def is_expo(base: Path) -> bool:
    """Expo Router has an app/ directory too: app.json, app.config.*, or expo without next in package.json."""
    deps = dependencies(base)
    if "next" in deps:
        return False
    return ("expo" in deps or any(base.glob("app.config.*"))
            or ((base / "app.json").is_file() and '"expo"' in read(base / "app.json")))


def is_next(root: Path) -> bool:
    return any(any((base / d).is_dir() for d in ("app", "src/app")) and not is_expo(base) for base in source_roots(root))


TOP_DECL = re.compile(r"^(?:export\s+(?:default\s+)?)?(?:async\s+)?(?:function\b|const\b|let\b|var\b|class\b|type\b|interface\b|enum\b)"
                      r"|^export\s*\{", re.M)
DECL_NAME = re.compile(r"(export\s+(?:default\s+)?)?(?:async\s+)?(?:function\s*\*?\s*(\w+)|(?:const|let|var)\s+(\w+)\s*=)")


def blocks(text: str) -> list[tuple[int, int]]:
    """Each top-level declaration runs to the next one, of any kind — not to the next export."""
    starts = [m.start() for m in TOP_DECL.finditer(text)]
    return [(st, starts[i + 1] if i + 1 < len(starts) else len(text)) for i, st in enumerate(starts)]


def declarations(text: str) -> list[tuple[str, str, bool]]:
    """(name, body, exported) for each top-level function or variable."""
    out = []
    for st, end in blocks(text):
        m = DECL_NAME.match(text, st)
        if m and (m.group(2) or m.group(3)):
            out.append((m.group(2) or m.group(3), text[st:end], bool(m.group(1))))
    return out


def exported_bindings(text: str) -> list[tuple[str, str]]:
    """Every exported binding with its body: `export function`, `export const x = <anything>` (next-safe-action's
    `actionClient.action(…)`, a `withAuth(…)` wrapper), and `export { a, b as c }` resolved to the local declaration."""
    decls = declarations(text)
    local = {n: b for n, b, _ in decls}
    out = [(n, b) for n, b, exported in decls if exported]
    for m in re.finditer(r"^export\s*\{([^}]*)\}", text, re.M):
        for item in filter(None, (x.strip() for x in m.group(1).split(","))):
            src, _, alias = item.partition(" as ")
            out.append((alias.strip() or src.strip(), local.get(src.strip(), "")))
    return out


def has_directive(text: str, which: str) -> bool:
    """`"use server"` / `"use client"` as the file's first statement — not one inside a function."""
    return re.match(rf"(?:\s|//[^\n]*\n|/\*[\s\S]*?\*/)*['\"]use {which}['\"]", text) is not None


INLINE_ACTION = re.compile(r"(?:async\s+function\s+(\w+)\s*\([^)]*\)|(?:const|let)\s+(\w+)\s*=\s*async\s*(?:\([^)]*\)|\w+)\s*=>)"
                           r"[^{]*?\{\s*['\"]use server['\"]")


def inline_actions(text: str) -> list[tuple[str, str]]:
    """(name, body) of each function whose own body starts with "use server", wherever it is defined."""
    out = []
    for m in INLINE_ACTION.finditer(text):
        i, depth = text.index("{", m.start()) + 1, 1
        while i < len(text) and depth:
            depth += {"{": 1, "}": -1}.get(text[i], 0)
            i += 1
        out.append((m.group(1) or m.group(2), text[m.start():i]))
    return out


HTTP_METHODS = {"GET", "HEAD", "OPTIONS", "POST", "PUT", "PATCH", "DELETE"}


def helper_candidates(functions: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Only plain functions can be helpers: not a component (PascalCase) and not a route handler."""
    return [(n, b) for n, b in functions if n not in HTTP_METHODS and not n[:1].isupper()]


def plain_module(path: Path, text: str) -> bool:
    """Not a Server Action file, a client component or a route — a call into one of those is not a session check."""
    return path.stem != "route" and not has_directive(text, "server") and not has_directive(text, "client")


def imported_names(text: str) -> dict[str, str]:
    """{exported name: local name} for every named import — `{ a, b as c }` gives {a: a, b: c}."""
    out = {}
    for m in re.finditer(r"import\s+(?:type\s+)?(?:\w+\s*,\s*)?\{([^}]*)\}\s*from\s*['\"]", text):
        for item in filter(None, (x.strip() for x in m.group(1).split(","))):
            src, _, alias = item.partition(" as ")
            out[src.strip()] = alias.strip() or src.strip()
    return out


def file_session_calls(text: str, base: list[str], derived: list[str]) -> list[str]:
    """The session calls valid in one file: the defaults and the declared ones; a project helper only when this file
    imports it (by its local name); then this file's own non-exported helpers. A local declaration shadows a
    project helper of the same name."""
    decls = declarations(text)
    names = {n for n, _, _ in decls}
    imported = imported_names(text)
    calls = list(base) + [imported[d] for d in derived if d in imported and imported[d] not in names]
    return session_helpers(helper_candidates([(n, b) for n, b, exported in decls if not exported]), calls, tuple(base))


def session_helpers(functions: list[tuple[str, str]], calls: list[str], trusted: tuple = DEFAULT_SESSION_CALLS) -> list[str]:
    """Functions whose body calls a session helper become session helpers too, until nothing changes —
    `run(input, schema, (who, p) => …)` that calls `reviewer()` that calls `getSession()` is a session check."""
    known = list(calls)
    changed = True
    while changed:
        changed = False
        for name, body in functions:
            if name not in known and has_session(body, known, trusted):
                known.append(name)
                changed = True
    return known


def has_session(body: str, calls: list[str], trusted: tuple = DEFAULT_SESSION_CALLS) -> bool:
    """A call to a session helper in code — a comment or a variable named like one does not count. A trusted name
    (the defaults and the project's declared ones) may be a method — `auth.api.getSession(` is better-auth's own
    call; a helper deduced from the project's code must be a bare call — `db.update(` is not a helper `update`."""
    code = re.sub(r"/\*.*?\*/|//[^\n]*", "", body, flags=re.S)
    method, bare = r"(?<![\w$])", r"(?<![\w.$])"
    return any(re.search((method if c in trusted else bare) + re.escape(c.rstrip("(")) + r"\s*\(", code) for c in calls)


def session_vars(body: str, calls: list[str], trusted: tuple = DEFAULT_SESSION_CALLS) -> set[str]:
    """Names bound from a session call in this body: `const userId = await getCurrentUserId()`, `const { id } = …`."""
    names = "|".join((r"(?:[\w.]+\.)?" if c in trusted else "") + re.escape(c.rstrip("(")) for c in calls)
    out: set[str] = set()
    for m in re.finditer(rf"(?:const|let|var)\s+(\{{[^}}]*\}}|\w+)\s*=\s*(?:await\s+)?(?<![\w.$])(?:{names})\s*\(", body):
        out |= set(re.findall(r"\w+", m.group(1).split(":")[-1] if ":" in m.group(1) else m.group(1)))
    return out


def finding(check: str, hits: list[str], ok_detail: str, found_detail: str, route: str) -> Finding:
    return Finding(check, FOUND if hits else OK, (found_detail.format(n=len(hits)) + HEURISTIC) if hits else ok_detail,
                   hits[:20], route if hits else None)


def code_findings(root: Path) -> list[Finding]:
    calls = session_calls(root)
    files = list(code_files(root))
    texts = {p: read(p) for p in files}
    nextjs = is_next(root)
    out: list[Finding] = []

    # a plain module's exported helper that takes the session; usable only where it is imported
    base_calls = calls
    trusted = tuple(calls)
    derived = [c for c in session_helpers(helper_candidates([(n, b) for p, t in texts.items() if plain_module(p, t)
                                                             for n, b, exported in declarations(t) if exported]), calls, trusted)
               if c not in calls]
    per_file = {p: file_session_calls(t, base_calls, derived) for p, t in texts.items()}

    if nextjs:
        unauth, rows = [], []
        for p, text in texts.items():
            local = per_file[p]
            if has_directive(text, "server"):   # every export of an action file is a public endpoint
                for name, body in exported_bindings(text):
                    if not has_session(body, local, trusted):
                        unauth.append(f"{rel(root, p)}: {name}")
                    if re.search(r"return\s+(?:await\s+)?db\.[\s\S]{0,200}?\.returning\(\)", body):
                        rows.append(f"{rel(root, p)}: {name}")
            else:   # an inline action is judged by its own body: the page's session check does not cover it
                for name, body in inline_actions(text):
                    if not has_session(body, local, trusted):
                        unauth.append(f"{rel(root, p)}: {name} (inline)")
        out.append(finding("server-action-unauthenticated", unauth, "every Server Action calls a session helper",
                           "{n} Server Action(s) with no session call in their body", "module-add auth"))
        routes = []
        for p, text in texts.items():
            if p.name not in ("route.ts", "route.js", "route.tsx"):
                continue
            for name, body in exported_bindings(text):
                if name in ("POST", "PUT", "PATCH", "DELETE") and not has_session(body, per_file[p], trusted):
                    routes.append(f"{rel(root, p)}: {name}")
        out.append(finding("route-handler-unauthenticated", routes, "every mutating route handler checks the session",
                           "{n} mutating route handler(s) with no session call", "module-add auth"))
    else:
        for check in ("server-action-unauthenticated", "route-handler-unauthenticated"):
            out.append(Finding(check, OK, "not applicable — no Next.js app directory"))
        rows = []

    unscoped = []
    for p, text in texts.items():
        spans = blocks(text)
        for m in re.finditer(r"\.where\(", text):
            call = text[m.end():m.end() + 400]
            depth, i = 1, 0
            while i < len(call) and depth:
                depth += {"(": 1, ")": -1}.get(call[i], 0)
                i += 1
            by_id = re.search(r"eq\(\s*(\w+)\.id\s*,\s*([\w.]+)", call[:i])
            if not by_id:
                continue
            table, value = by_id.groups()
            st, end = next(((a, b) for a, b in spans if a <= m.start() < b), (0, len(text)))
            fn = text[st:end]
            starts = [x.start() for x in re.finditer(r"\b(?:db|tx|trx)\s*\.", text[st:m.start()])]
            chain = text[st + (starts[-1] if starts else 0):m.end() + i]
            scoped = (re.search(SCOPE_COLUMN, chain, re.I)   # an owner filter in this query, its joins included
                      or re.search(rf"eq\(\s*{table}\.\w*{SCOPE_WORDS}(?:Id|_id)\b", fn, re.I)   # this table, earlier
                      or value.split(".")[0] in session_vars(fn, per_file[p], trusted)   # the caller's own id, from the session
                      or value == "session.user.id")
            if not scoped:
                unscoped.append(f"{rel(root, p)}:{text[:m.start()].count(chr(10)) + 1}")
    out.append(finding("query-by-id-unscoped", unscoped, "every query by id also filters on its owner",
                       "{n} query(ies) by id with no owner filter on that table, and no id taken from the session",
                       "the code owner"))
    out.append(finding("action-returns-row", rows, "no Server Action returns a raw row" if nextjs else "not applicable — no Next.js app directory",
                       "{n} Server Action(s) return a `.returning()` row to the client", "the code owner"))

    leaked = []
    for base in source_roots(root):
        for env in sorted(base.glob(".env*")):
            if not env.is_file():
                continue
            for line in read(env).splitlines():
                name = re.sub(r"^export\s+", "", line.split("=", 1)[0].strip())
                if re.match(r"(NEXT_PUBLIC|EXPO_PUBLIC)_", name) and SECRET_WORDS.search(name) \
                        and not any(w in name for w in PUBLIC_BY_NATURE):
                    leaked.append(f"{rel(root, env)}: {name}")
    out.append(Finding("public-env-secret", FOUND if leaked else OK,
                       f"{len(leaked)} public variable(s) whose name says secret — they ship to the browser or the app bundle; "
                       "rotate the value, then move it server-side" if leaked else "no secret-looking public variable",
                       leaked[:20], "the user" if leaked else None))

    missing = [rel(root, p) for p, text in texts.items()
               if re.search(r"(^|/)lib/(server|db)/", rel(root, p)) and p.suffix in (".ts", ".js")
               and not re.search(r"(^test|\.(?:test|spec)\.)", p.name) and "__tests__" not in p.parts
               and "server-only" not in text
               and not has_directive(text, "server")   # Next keeps an action module on the server
               and re.search(HOLDS_SECRET, text)]
    out.append(finding("server-only-missing", missing, "server modules import \"server-only\"",
                       "{n} server module(s) without `import \"server-only\"`", "the code owner"))

    raw = [rel(root, p) for p, text in texts.items()
           if re.search(r"sql\.raw\(\s*`[^`]*\$\{", text) or re.search(r"(execute|query)\(\s*['\"`][^'\"`]*['\"`]\s*\+", text)]
    out.append(finding("raw-sql", raw, "no SQL built from strings", "{n} file(s) build SQL from strings", "the code owner"))

    if nextjs:
        configs = [p for base in source_roots(root) for p in base.glob("next.config.*")]
        everywhere = "".join(texts.values()) + "".join(read(p) for p in configs)
        headers = re.search(r"Content-Security-Policy", everywhere, re.I) is not None
        out.append(Finding("security-headers-missing", OK if headers else FOUND,
                           "a Content-Security-Policy is set" if headers
                           else "no Content-Security-Policy header found (next.config headers() or the proxy)" + HEURISTIC,
                           [], None if headers else "vercel-deploy"))
    else:
        out.append(Finding("security-headers-missing", OK, "not applicable — no Next.js app directory"))
    return out


# --- the external tools ------------------------------------------------------------------------------------------
# Each one is used only when installed; anything that is not a clean, parseable answer is NOT_CHECKED.

INSTALL = {"osv-scanner": "brew install osv-scanner", "gitleaks": "brew install gitleaks", "semgrep": "pipx install semgrep"}


def _run(run, argv: list[str], cwd: Path | None = None):
    try:
        return run(argv, capture_output=True, text=True, timeout=600, cwd=cwd)
    except (OSError, subprocess.TimeoutExpired):
        return None


def _json(text: str):
    try:
        return json.loads(text or "")
    except ValueError:
        return None


def dependency_finding(root: Path, run, which) -> Finding:
    if which("osv-scanner"):
        r = _run(run, ["osv-scanner", "scan", "source", "-r", str(root), "--format", "json"])
        data = _json(r.stdout) if r else None
        if r and r.returncode in (0, 1) and isinstance(data, dict):
            hits = [f"{p['package']['name']}@{p['package'].get('version', '?')}: "
                    + ", ".join(v.get("id", "?") for v in p.get("vulnerabilities") or [])
                    for res in data.get("results") or [] for p in res.get("packages") or [] if p.get("vulnerabilities")]
            return Finding("dependencies", FOUND if hits else OK,
                           f"OSV-Scanner: {len(hits)} vulnerable package(s)" if hits else "OSV-Scanner: no known vulnerability",
                           hits[:20], "the user — upgrade, or record why not" if hits else None)
        return Finding("dependencies", NOT_CHECKED, f"OSV-Scanner did not answer (exit {r.returncode if r else 'none'})")
    pnpm = (root / "pnpm-lock.yaml").is_file() and which("pnpm")
    tool = ["pnpm", "audit", "--json", "--prod"] if pnpm else (["npm", "audit", "--json", "--omit=dev"] if which("npm") else None)
    if not tool:
        return Finding("dependencies", NOT_CHECKED, f"no dependency scanner — {INSTALL['osv-scanner']} (asks first)")
    r = _run(run, tool, cwd=root)   # npm and pnpm audit the lockfile of the directory they run in
    data = _json(r.stdout) if r else None
    # a failure is JSON too ({"error": {"code": "ENOLOCK"}}, ECONNREFUSED offline): only a report counts
    if not isinstance(data, dict) or "error" in data or not ({"advisories", "vulnerabilities"} & set(data)):
        why = (data.get("error") or {}).get("code") if isinstance(data, dict) and isinstance(data.get("error"), dict) else None
        return Finding("dependencies", NOT_CHECKED,
                       f"`{' '.join(tool[:2])}` gave no report" + (f" ({why})" if why else "") + " — it needs a lockfile and the network")
    if "advisories" in data:
        hits = [f"{a.get('module_name')}: {a.get('severity')} — {a.get('title')}" for a in data["advisories"].values()]
    else:
        hits = [f"{name}: {v.get('severity')}" for name, v in (data.get("vulnerabilities") or {}).items()]
    return Finding("dependencies", FOUND if hits else OK,
                   f"{tool[0]} audit: {len(hits)} vulnerable package(s)" if hits else f"{tool[0]} audit: no known vulnerability",
                   hits[:20], "the user — upgrade, or record why not" if hits else None)


def secrets_findings(root: Path, run, which) -> list[Finding]:
    out = []
    for mode, check in (("dir", "secrets-working-tree"), ("git", "secrets-history")):
        if not which("gitleaks"):
            out.append(Finding(check, NOT_CHECKED, f"gitleaks not installed — {INSTALL['gitleaks']} (asks first)"))
            continue
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "gitleaks.json"
            r = _run(run, ["gitleaks", mode, str(root), "--redact", "--report-format", "json", "--report-path", str(report)])
            data = _json(report.read_text(encoding="utf-8")) if report.is_file() else None
        if not r or r.returncode not in (0, 1) or not isinstance(data, list):
            out.append(Finding(check, NOT_CHECKED, f"gitleaks {mode} did not answer (exit {r.returncode if r else 'none'})"))
            continue
        hits = [f"{d.get('File')}:{d.get('StartLine')} {d.get('RuleID')}" + (f" (commit {d.get('Commit')})" if mode == "git" else "")
                for d in data]
        where = "in git history — rotate it: deleting the file does not remove it from history" if mode == "git" \
            else "in the working tree — rotate it, then move it to the environment"
        out.append(Finding(check, FOUND if hits else OK, f"{len(hits)} secret(s) {where}" if hits else f"gitleaks {mode}: none",
                           hits[:20], "the user" if hits else None))
    return out


def static_finding(root: Path, run, which) -> Finding:
    if not which("semgrep"):
        return Finding("static-analysis", NOT_CHECKED, f"Semgrep not installed — {INSTALL['semgrep']} (asks first)")
    r = _run(run, ["semgrep", "scan", "--config", "p/nextjs", "--config", "p/typescript", "--metrics", "off", "--json", str(root)])
    data = _json(r.stdout) if r else None
    failed = not r or r.returncode not in (0, 1) or not isinstance(data, dict) or "results" not in data \
        or any(isinstance(e, dict) and e.get("level") == "error" for e in data.get("errors") or [])
    if failed:
        return Finding("static-analysis", NOT_CHECKED, "Semgrep gave no report (the rules are fetched at run time, so it needs the network)")
    hits = [f"{x.get('path')}:{(x.get('start') or {}).get('line')} {x.get('check_id')}" for x in data["results"]]
    return Finding("static-analysis", FOUND if hits else OK,
                   f"Semgrep: {len(hits)} result(s)" + HEURISTIC if hits else "Semgrep: no result",
                   hits[:20], "the code owner" if hits else None)


def tool_findings(root: Path, run=subprocess.run, which=shutil.which) -> list[Finding]:
    return [dependency_finding(root, run, which), *secrets_findings(root, run, which), static_finding(root, run, which)]


def scan(root: Path, run=subprocess.run, which=shutil.which) -> list[Finding]:
    return tool_findings(root, run, which) + code_findings(root)


def print_report(root: Path, findings: list[Finding]) -> None:
    order = sorted(findings, key=lambda f: (f.check != "secrets-history" or f.status != FOUND))
    mark = {OK: "·", FOUND: "!", NOT_CHECKED: "?"}
    print(f"app-security signals for {root}\n")
    for f in order:
        print(f"  {mark[f.status]} {f.check}: {f.detail}")
        for w in f.where:
            print(f"      {w}")
        if f.routed_to:
            print(f"      → {f.routed_to}")
    found = sum(f.status == FOUND for f in findings)
    unchecked = sum(f.status == NOT_CHECKED for f in findings)
    print(f"\n{found} to look at, {unchecked} not checked. Signals, not verdicts: read the code before reporting "
          "(references/review.md). 'not checked' means nothing looked there.")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("project_root", type=Path)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    root = a.project_root.resolve()
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2
    findings = scan(root)
    if a.json:
        print(json.dumps([f.__dict__ for f in findings], indent=2))
        return 0
    print_report(root, findings)
    return 0


if __name__ == "__main__":
    sys.exit(main())
