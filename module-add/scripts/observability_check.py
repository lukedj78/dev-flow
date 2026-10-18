#!/usr/bin/env python3
"""observability_check.py — is a web app's observability really wired? One verdict per piece, per level.

    python3 observability_check.py <project-root> [--all] [--json]

Levels come from `meta.json#stack.observability` (errors, logs, uptime), or all three with `--all`:

- errors — `instrumentation.ts` exports `onRequestError`; `instrumentation-client.ts` initialises the SDK;
  `global-error.tsx` and `error.tsx` (or `app/[locale]/error.tsx`) report what they catch; events carry a `release`;
  `sendDefaultPii` is not on; no Replay; `withSentryConfig` comes from `@sentry/nextjs/config`; a CSP `connect-src`
  that lists hosts lets the DSN host through (or a tunnel); the DSN's region matches `stack.data_residency` (`.ingest.de.sentry.io` for eu / eu-sovereign, or the
  project's GlitchTip host when `stack.observability_provider.errors` is "glitchtip").
- logs — `lib/log.ts`, and an `x-request-id` set somewhere (the proxy) so a report leads to a log line.
- uptime — `app/api/health/route.ts`.

Statuses: ok, found (missing or wrong — exit 1), not checked (it cannot see the answer: a DSN read from an env var
with no value in the env files, a privacy option behind a spread), not applicable (not a web surface: an Expo app
is `rn-module-add observability`'s). Uses the vendored `surfaces.py`. Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import surfaces as sf  # noqa: E402 — vendored copy of dev-flow/scripts/surfaces.py; lint_skills.py keeps it identical

LEVELS = ("errors", "logs", "uptime")
CODE = (".ts", ".tsx", ".js", ".jsx", ".mjs")
SKIP = {"node_modules", ".next", ".git", "dist", "build", "out", ".verification",
        ".eve", ".output", ".vercel", ".turbo", ".data",   # generated code and runtime data, not source
        "__tests__", "__mocks__", "e2e", "tests", "test", "fixtures"}   # tests may name what the app must not do
TEST_FILE = re.compile(r"\.(test|spec|stories)\.[a-z]+$")
LOOPBACK = re.compile(r"^(localhost|127\.0\.0\.1|\[?::1\]?)$")
ENV_FILES = (".env.example", ".env.local", ".env.production", ".env.production.local", ".env")


@dataclass
class Finding:
    level: str
    status: str   # ok | found | not checked | not applicable
    detail: str


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _files(base: Path) -> dict[Path, str]:
    """The app's own code: skipped folders are pruned, not walked (node_modules is large), and tests are left out."""
    out = {}
    for d, dirs, names in os.walk(base):
        dirs[:] = sorted(x for x in dirs if x not in SKIP)
        for n in sorted(names):
            p = Path(d) / n
            if p.suffix in CODE and not TEST_FILE.search(n):
                out[p] = _read(p)
    return out


def _first(base: Path, *names: str) -> Path | None:
    for n in names:
        for prefix in ("", "src/"):
            p = base / f"{prefix}{n}"
            if p.is_file():
                return p
    return None


def _root_error(base: Path) -> Path | None:
    """`app/error.tsx`, or the one under a top-level dynamic segment (`app/[locale]/error.tsx`) when i18n owns the root."""
    hit = _first(base, "app/error.tsx")
    if hit:
        return hit
    for app in (base / "app", base / "src" / "app"):
        if app.is_dir():
            for seg in sorted(app.iterdir()):
                if seg.is_dir() and seg.name.startswith("[") and (seg / "error.tsx").is_file():
                    return seg / "error.tsx"
    return None


def _csp_sources(text: str) -> list[tuple[list[str], bool]]:
    """The source list of every `connect-src` directive written in the code, and whether part of it is interpolated
    (a template literal's `${…}` is code, not sources: what follows it cannot be read)."""
    out = []
    for m in re.finditer(r"connect-src\s+([^;\"`\n]*)", text):
        static, _, rest = m.group(1).partition("${")
        out.append((static.split(), bool(_ or rest)))
    return out


def _allows(sources: list[str], host: str) -> bool:
    for src in sources:
        bare = re.sub(r"^\w+://", "", src).split("/")[0].split(":")[0].lower()
        if src in ("*", "https:") or bare == host or (bare.startswith("*.") and host.endswith(bare[1:])):
            return True
    return False


# a string (kept whole) or a comment (dropped). A quote or double-quote string must close on its line, so one
# unmatched quote (an apostrophe in JSX text) is read as a plain character and cannot swallow the rest of a file; a
# template literal may span lines; a block comment never closed runs to the end of the file, as it does for the parser.
_TOKENS = re.compile(r"""("(?:\\.|[^"\\\n])*"|'(?:\\.|[^'\\\n])*'|`(?:\\.|[^`\\])*`)|//[^\n]*|/\*.*?(?:\*/|\Z)""", re.S)


def _code(text: str) -> str:
    """The text without comments. Strings are skipped whole, so `https://*.ingest…` opens no comment."""
    return _TOKENS.sub(lambda m: m.group(1) or "", text)


def _dsn_hosts(base: Path, root: Path, code: str) -> tuple[list[tuple[str, str]], list[str]]:
    """Every DSN host the code and env files show, each with where it came from, and why any DSN cannot be seen.
    Every value counts, so a placeholder in .env.example cannot hide the real one; loopback hosts are the fake
    ingest's proof, not a region."""
    hosts: list[tuple[str, str]] = []
    unknown: list[str] = []
    for m in re.finditer(r"\bdsn\s*:\s*(['\"`])([^'\"`]+)\1", code):
        hosts.append((_host(m.group(2)), "a literal"))
    for v in dict.fromkeys(re.findall(r"\bdsn\s*:\s*process\.env\.(\w+)", code)):
        seen = False
        for d in dict.fromkeys((base, root)):
            for name in ENV_FILES:
                for hit in re.finditer(rf"^\s*{v}\s*=\s*['\"]?([^'\"\s#]+)", _read(d / name), re.M):
                    if "://" in hit.group(1):
                        seen = True
                        hosts.append((_host(hit.group(1)), f"{v} in {name}"))
        if not seen:
            unknown.append(f"the DSN is read from {v}, which has no value in the env files")
    if not hosts and not unknown:
        unknown.append("no `dsn:` found")
    real = [(h, o) for h, o in hosts if not LOOPBACK.match(h)]
    if hosts and not real and not unknown:
        unknown.append("the only DSN is a loopback one (the fake ingest)")
    return real, unknown


def _host(dsn: str) -> str:
    m = re.match(r"\w+://(?:[^@/]+@)?([^/:]+)", dsn)
    return (m.group(1) if m else dsn).lower()


def _errors(base: Path, root: Path, meta: dict, texts: dict[Path, str]) -> list[Finding]:
    found: list[Finding] = []
    def miss(detail: str) -> None:
        found.append(Finding("errors", "found", detail))
    all_code = "\n".join(_code(t) for t in texts.values())
    inst = _first(base, "instrumentation.ts", "instrumentation.js")
    if not inst or "onRequestError" not in _code(_read(inst)):
        miss("instrumentation.ts does not export onRequestError — server errors (Server Actions, RSC, routes) are lost")
    client = _first(base, "instrumentation-client.ts", "instrumentation-client.js")
    if not client or not re.search(r"\binit\s*\(", _code(_read(client))):
        miss("instrumentation-client.ts does not initialise the SDK — browser errors are lost")
    for p, what in ((_first(base, "app/global-error.tsx"), "global-error.tsx (root-layout errors)"), (_root_error(base), "error.tsx")):
        if not p:
            miss(f"{what} is missing")
        elif "captureException" not in _code(_read(p)):
            miss(f"{what} does not report what it catches (captureException) — the user's error stays in their browser")
    if not re.search(r"\brelease\s*:", all_code):
        miss("no `release` — an error cannot be tied to the deploy that introduced it (VERCEL_GIT_COMMIT_SHA)")
    pii = [v.strip() for v in re.findall(r"\bsendDefaultPii\s*:\s*([^,}\n]+)", all_code)]
    if "true" in pii:
        miss("sendDefaultPii is true — IP addresses, cookies and user data go to the tracker")
    for v in dict.fromkeys(x for x in pii if x not in ("true", "false")):
        found.append(Finding("errors", "not checked", f"sendDefaultPii is set from `{v}` — read what it is"))
    if re.search(r"replayIntegration|\bReplay\s*\(", all_code):
        miss("Session Replay is on — the module keeps it off by default (privacy)")
    if re.search(r"\bwithSentryConfig\b[^}]*\}\s*(from\s*|=\s*require\(\s*)['\"]@sentry/nextjs['\"]", all_code):
        miss("withSentryConfig is imported from \"@sentry/nextjs\" — version 11 exports it from \"@sentry/nextjs/config\" "
             "only, and the build fails")
    residency = ((meta.get("stack") or {}).get("data_residency")) or ""
    provider = (((meta.get("stack") or {}).get("observability_provider")) or {}).get("errors", "sentry")
    hosts, unknown = _dsn_hosts(base, root, all_code)
    # a Content-Security-Policy that lists hosts must let the browser reach the ingest, unless a tunnel keeps it 'self'
    if not re.search(r"\btunnel(Route)?\s*:", all_code):
        for sources, interpolated in _csp_sources(all_code):
            if "*" in sources or "https:" in sources:
                continue
            blocked = [h for h, _ in hosts if not _allows(sources, h)]
            if not hosts:
                found.append(Finding("errors", "not checked", f"connect-src lists hosts and the DSN host is not visible ({unknown[0]})"))
            elif blocked and interpolated:
                found.append(Finding("errors", "not checked", f"connect-src is partly interpolated — check it allows {blocked[0]}"))
            elif blocked:
                miss(f"the Content-Security-Policy's connect-src does not allow {blocked[0]} — the browser's events are "
                     "blocked (add the host, or tunnelRoute)")
    if residency in ("eu", "eu-sovereign"):
        for why in unknown:
            found.append(Finding("errors", "not checked", f"region not checked: {why}"))
        for host, origin in dict.fromkeys(hosts):
            if not (host.endswith(".ingest.de.sentry.io") or (provider == "glitchtip" and not host.endswith("sentry.io"))):
                miss(f"DSN host {host} ({origin}) is outside the EU region `stack.data_residency = {residency}` asks "
                     "for — use the Frankfurt org (*.ingest.de.sentry.io) or GlitchTip")
    return found


def _pii_visibility(texts: dict[Path, str]) -> Finding | None:
    code = "\n".join(_code(t) for t in texts.values())
    if "sendDefaultPii" in code:
        return None
    options_spread = re.search(r"\.\.\.\s*\w+", code) and re.search(r"\binit\s*\(", code)
    return Finding("errors", "not checked", "sendDefaultPii is not visible (options come through a spread) — read it") \
        if options_spread else None


def check(root: Path, meta: dict | None = None, all_levels: bool = False) -> list[Finding]:
    root = root.resolve()
    if meta is None:
        try:
            meta = json.loads(_read(root / ".workflow" / "meta.json") or "{}")
        except ValueError:
            meta = {}
    levels = list(LEVELS) if all_levels else [l for l in ((meta.get("stack") or {}).get("observability") or []) if l in LEVELS]
    found = sf.surfaces(root, meta)
    webs = [s for s in found if s.kind == "web"]
    if not webs:
        why = ("an Expo app: crash reporting is rn-module-add observability's" if any(s.kind == "mobile" for s in found)
               else "no web surface")
        return [Finding(l, "not applicable", why) for l in levels]
    out: list[Finding] = []
    for web in webs:
        base = root / web.path
        texts = _files(base)
        tag = "" if len(webs) == 1 else f"[{web.path}] "
        for level in levels:
            if level == "errors":
                fs = _errors(base, root, meta, texts)
                vis = _pii_visibility(texts)   # no literal sendDefaultPii, options through a spread: a human reads it
                fs += [vis] if vis else []
            elif level == "logs":
                fs = []
                if not _first(base, "lib/log.ts", "lib/log.js", "lib/logger.ts"):
                    fs.append(Finding("logs", "found", "lib/log.ts is missing — no structured log to tie a report to"))
                if not any("x-request-id" in t.lower() for t in texts.values()):
                    fs.append(Finding("logs", "found", "no x-request-id is set (proxy.ts) — a user's report cannot be traced to a log line"))
            else:
                health = _first(base, "app/api/health/route.ts", "app/api/health/route.js")
                conf = _code(_read(_first(base, "next.config.ts", "next.config.mjs", "next.config.js") or base / "-"))
                if not health:
                    fs = [Finding("uptime", "found", "app/api/health/route.ts is missing — nothing for an uptime monitor to call")]
                elif re.search(r"\bcacheComponents\s*:\s*true", conf) and re.search(r"export\s+const\s+dynamic\b", _code(_read(health))):
                    fs = [Finding("uptime", "found", "the health route exports `dynamic` and cacheComponents is on — the build "
                                  "fails; drop the line (a GET handler is not cached there)")]
                else:
                    fs = []
            fs = fs or [Finding(level, "ok", f"{level} wired")]
            out += [Finding(f.level, f.status, tag + f.detail) for f in fs]
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("project_root", type=Path)
    ap.add_argument("--all", action="store_true", help="check every level, whatever meta.json says")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    findings = check(a.project_root, None, a.all)
    if a.json:
        print(json.dumps([asdict(f) for f in findings], indent=2))
    else:
        mark = {"ok": "·", "found": "!", "not checked": "?", "not applicable": "–"}
        for f in findings:
            print(f"  {mark[f.status]} {f.level}: {f.detail}")
        if not findings:
            print("no observability level is active (stack.observability is empty) — module-add observability, or --all")
    return 1 if any(f.status == "found" for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
