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
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import surfaces as sf  # noqa: E402 — vendored copy of dev-flow/scripts/surfaces.py; lint_skills.py keeps it identical

LEVELS = ("errors", "logs", "uptime")
CODE = (".ts", ".tsx", ".js", ".jsx", ".mjs")
SKIP = {"node_modules", ".next", ".git", "dist", "build", "out", ".verification"}
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
    out = {}
    for p in base.rglob("*"):
        if p.is_file() and p.suffix in CODE and not (set(p.relative_to(base).parts[:-1]) & SKIP):
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


def _csp_sources(text: str) -> list[list[str]]:
    """The source lists of every `connect-src` directive written in the code."""
    # a template literal's interpolation is cut: what follows `${` is code, not sources
    return [m.group(1).split("${")[0].split() for m in re.finditer(r"connect-src\s+([^;\"`\n]*)", text)]


def _allows(sources: list[str], host: str) -> bool:
    for src in sources:
        bare = re.sub(r"^\w+://", "", src).split("/")[0].split(":")[0].lower()
        if src in ("*", "https:") or bare == host or (bare.startswith("*.") and host.endswith(bare[1:])):
            return True
    return False


def _code(text: str) -> str:
    return re.sub(r"/\*.*?\*/|(?<![:'\"])//[^\n]*", "", text, flags=re.S)


def _dsn_host(base: Path, root: Path, texts: str) -> tuple[str | None, str]:
    """The DSN's host, and where it came from; (None, why) when it cannot be seen."""
    m = re.search(r"\bdsn\s*:\s*(['\"`])([^'\"`]+)\1", texts)
    if m:
        return _host(m.group(2)), "a literal"
    v = re.search(r"\bdsn\s*:\s*process\.env\.(\w+)", texts)
    if not v:
        return None, "no `dsn:` found"
    for d in (base, root):
        for name in ENV_FILES:
            hit = re.search(rf"^\s*{v.group(1)}\s*=\s*['\"]?([^'\"\s#]+)", _read(d / name), re.M)
            if hit and "://" in hit.group(1):
                return _host(hit.group(1)), f"{v.group(1)} in {name}"
    return None, f"the DSN is read from {v.group(1)}, which has no value in the env files"


def _host(dsn: str) -> str:
    m = re.match(r"\w+://(?:[^@/]+@)?([^/:]+)", dsn)
    return (m.group(1) if m else dsn).lower()


def _errors(base: Path, root: Path, meta: dict, texts: dict[Path, str]) -> list[Finding]:
    found: list[Finding] = []
    def miss(detail: str) -> None:
        found.append(Finding("errors", "found", detail))
    all_code = _code("\n".join(texts.values()))
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
    pii = re.search(r"\bsendDefaultPii\s*:\s*(true|false)", all_code)
    if pii and pii.group(1) == "true":
        miss("sendDefaultPii is true — IP addresses, cookies and user data go to the tracker")
    if re.search(r"replayIntegration|\bReplay\s*\(", all_code):
        miss("Session Replay is on — the module keeps it off by default (privacy)")
    if re.search(r"\bwithSentryConfig\b[^}]*\}\s*from\s*['\"]@sentry/nextjs['\"]", all_code):
        miss("withSentryConfig is imported from \"@sentry/nextjs\" — version 11 exports it from \"@sentry/nextjs/config\" "
             "only, and the build fails")
    residency = ((meta.get("stack") or {}).get("data_residency")) or ""
    provider = (((meta.get("stack") or {}).get("observability_provider")) or {}).get("errors", "sentry")
    host, origin = _dsn_host(base, root, all_code)
    # a Content-Security-Policy that lists hosts must let the browser reach the ingest, unless a tunnel keeps it 'self'
    if not re.search(r"\btunnel(Route)?\s*:", all_code):
        for sources in _csp_sources(all_code):
            if "*" in sources or "https:" in sources:
                continue
            if host is None:
                found.append(Finding("errors", "not checked", f"connect-src lists hosts and the DSN host is not visible ({origin})"))
            elif not _allows(sources, host):
                miss(f"the Content-Security-Policy's connect-src does not allow {host} — the browser's events are blocked "
                     "(add the host, or tunnelRoute)")
    if residency in ("eu", "eu-sovereign"):
        if host is None:
            found.append(Finding("errors", "not checked", f"region not checked: {origin}"))
        elif host.endswith(".ingest.de.sentry.io") or (provider == "glitchtip" and not host.endswith("sentry.io")):
            pass
        else:
            miss(f"DSN host {host} ({origin}) is outside the EU region `stack.data_residency = {residency}` asks for "
                 "— use the Frankfurt org (*.ingest.de.sentry.io) or GlitchTip")
    return found


def _pii_visibility(texts: dict[Path, str]) -> Finding | None:
    code = _code("\n".join(texts.values()))
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
                fs = [] if _first(base, "app/api/health/route.ts", "app/api/health/route.js") else \
                    [Finding("uptime", "found", "app/api/health/route.ts is missing — nothing for an uptime monitor to call")]
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
