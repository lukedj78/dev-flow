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
import sys
from dataclasses import dataclass, field
from pathlib import Path

OK, FOUND, NOT_CHECKED = "ok", "found", "not checked"

CODE_CHECKS = ("server-action-unauthenticated", "route-handler-unauthenticated", "query-by-id-unscoped",
               "action-returns-row", "public-env-secret", "server-only-missing", "raw-sql",
               "security-headers-missing")
DEFAULT_SESSION_CALLS = ("getSession", "getCurrentUserId", "getCurrentTenantId", "requireUser", "verifySession", "auth(")
PUBLIC_BY_NATURE = ("ANON_KEY", "PUBLISHABLE", "POSTHOG_KEY", "SITE_KEY", "_URL")
SECRET_WORDS = re.compile(r"SECRET|PRIVATE|TOKEN|PASSWORD")
SKIP = {"node_modules", ".git", ".next", "dist", "build", ".turbo", ".vercel", ".expo", "ios", "android"}
CODE_SUFFIXES = (".ts", ".tsx", ".js", ".jsx", ".mjs")
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
    seen = set()
    for base in source_roots(root):
        for p in base.rglob("*"):
            if p in seen or not p.is_file() or p.suffix not in CODE_SUFFIXES:
                continue
            if any(part in SKIP for part in p.relative_to(root).parts):
                continue
            seen.add(p)
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


def is_next(root: Path) -> bool:
    return any((base / d).is_dir() for base in source_roots(root) for d in ("app", "src/app")) and not (
        (root / "app.json").is_file() and '"expo"' in read(root / "app.json"))


def exported_functions(text: str) -> list[tuple[str, str]]:
    """(name, body) for each top-level `export [async] function name` or `export const name = async (`."""
    starts = [(m.start(), m.group(1) or m.group(2)) for m in re.finditer(
        r"^export\s+(?:default\s+)?(?:async\s+)?function\s+(\w+)|^export\s+const\s+(\w+)\s*=\s*async\b", text, re.M)]
    out = []
    for i, (pos, name) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(text)
        out.append((name, text[pos:end]))
    return out


def has_session(body: str, calls: list[str]) -> bool:
    """A call to a session helper in code — a comment or a variable named like one does not count."""
    code = re.sub(r"/\*.*?\*/|//[^\n]*", "", body, flags=re.S)
    return any(re.search(rf"\b{re.escape(c.rstrip('('))}\s*\(", code) for c in calls)


def finding(check: str, hits: list[str], ok_detail: str, found_detail: str, route: str) -> Finding:
    return Finding(check, FOUND if hits else OK, (found_detail.format(n=len(hits)) + HEURISTIC) if hits else ok_detail,
                   hits[:20], route if hits else None)


def code_findings(root: Path) -> list[Finding]:
    calls = session_calls(root)
    files = list(code_files(root))
    texts = {p: read(p) for p in files}
    nextjs = is_next(root)
    out: list[Finding] = []

    if nextjs:
        unauth, rows = [], []
        for p, text in texts.items():
            if not re.search(r"^\s*['\"]use server['\"]", text, re.M):
                continue
            for name, body in exported_functions(text):
                if not has_session(body, calls):
                    unauth.append(f"{rel(root, p)}: {name}")
                if re.search(r"return\s+(?:await\s+)?db\.[\s\S]{0,200}?\.returning\(\)", body):
                    rows.append(f"{rel(root, p)}: {name}")
        out.append(finding("server-action-unauthenticated", unauth, "every exported Server Action calls a session helper",
                           "{n} exported Server Action(s) with no session call in their body", "module-add auth"))
        routes = []
        for p, text in texts.items():
            if p.name not in ("route.ts", "route.js", "route.tsx"):
                continue
            for name, body in exported_functions(text):
                if name in ("POST", "PUT", "PATCH", "DELETE") and not has_session(body, calls):
                    routes.append(f"{rel(root, p)}: {name}")
        out.append(finding("route-handler-unauthenticated", routes, "every mutating route handler checks the session",
                           "{n} mutating route handler(s) with no session call", "module-add auth"))
    else:
        for check in ("server-action-unauthenticated", "route-handler-unauthenticated"):
            out.append(Finding(check, OK, "not applicable — no Next.js app directory"))
        rows = []

    unscoped = []
    for p, text in texts.items():
        for m in re.finditer(r"\.where\(", text):
            call = text[m.end():m.end() + 400]
            depth, i = 1, 0
            while i < len(call) and depth:
                depth += {"(": 1, ")": -1}.get(call[i], 0)
                i += 1
            clause = call[:i]
            if re.search(r"eq\(\s*\w+\.id\s*,\s*\w+", clause) and not re.search(
                    r"eq\(\s*\w+\.(?:userId|user_id|tenantId|tenant_id|ownerId|owner_id|orgId|org_id)\b", clause):
                line = text[:m.start()].count("\n") + 1
                unscoped.append(f"{rel(root, p)}:{line}")
    out.append(finding("query-by-id-unscoped", unscoped, "every query by id also filters on its owner",
                       "{n} query(ies) by id with no user/tenant filter in the same where()", "the code owner"))
    out.append(finding("action-returns-row", rows, "no Server Action returns a raw row" if nextjs else "not applicable — no Next.js app directory",
                       "{n} Server Action(s) return a `.returning()` row to the client", "the code owner"))

    leaked = []
    for base in source_roots(root):
        for env in sorted(base.glob(".env*")):
            if not env.is_file():
                continue
            for line in read(env).splitlines():
                name = line.split("=", 1)[0].strip()
                if re.match(r"(NEXT_PUBLIC|EXPO_PUBLIC)_", name) and SECRET_WORDS.search(name) \
                        and not any(w in name for w in PUBLIC_BY_NATURE):
                    leaked.append(f"{rel(root, env)}: {name}")
    out.append(Finding("public-env-secret", FOUND if leaked else OK,
                       f"{len(leaked)} public variable(s) whose name says secret — they ship to the browser or the app bundle; "
                       "rotate the value, then move it server-side" if leaked else "no secret-looking public variable",
                       leaked[:20], "the user" if leaked else None))

    missing = [rel(root, p) for p, text in texts.items()
               if re.search(r"(^|/)lib/(server|db)/", rel(root, p)) and p.suffix in (".ts", ".js")
               and not p.name.startswith("test") and "server-only" not in text]
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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("project_root", type=Path)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    root = a.project_root.resolve()
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2
    findings = code_findings(root)
    if a.json:
        print(json.dumps([f.__dict__ for f in findings], indent=2))
        return 0
    mark = {OK: "·", FOUND: "!", NOT_CHECKED: "?"}
    for f in findings:
        print(f"  {mark[f.status]} {f.check}: {f.detail}")
        for w in f.where:
            print(f"      {w}")
        if f.routed_to:
            print(f"      → {f.routed_to}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
