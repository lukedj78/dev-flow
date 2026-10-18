"""debt_tests.py — the debt audit's test check: code that writes data with no test reaching it, and the coverage
figure when the project produces one.

"Writes data" is a `"use server"` file, a route handler exporting POST / PUT / PATCH / DELETE, or a file calling
Drizzle's `db.insert / update / delete`. A file is reached by a unit test that imports it (relative or `@/`) or
names its path, or by an e2e spec that visits a page importing it — Playwright reaches a Server Action through the
URL, never by import. No coverage threshold: a percentage is optimised against, a mutation without a test is not.

Stdlib only.
"""

from __future__ import annotations

import json
import os
import posixpath
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import surfaces as sf  # noqa: E402
from debt_model import Finding  # noqa: E402
from debt_sources import Source  # noqa: E402

CODE = (".ts", ".tsx", ".js", ".jsx", ".mjs")
SKIP = {"node_modules", ".next", ".git", "dist", "build", "out", "coverage", ".verification", ".workflow",
        ".eve", ".output", ".vercel", ".turbo", ".data"}   # generated code and runtime data, not source
NOT_APP = {"scripts", "drizzle", "migrations", "seed", "seeds"}   # seeds and one-off scripts: no user reaches them
TEST_FILE = re.compile(r"\.(test|spec)\.[a-z]+$")
E2E_DIRS = ("e2e/", "tests/e2e/")
USE_SERVER = re.compile(r"""^\s*(?:(?://[^\n]*|/\*.*?\*/)\s*)*['"]use server['"]""", re.S)
WRITE_VERB = re.compile(r"export\s+(?:async\s+)?(?:function|const)\s+(POST|PUT|PATCH|DELETE)\b")
DRIZZLE_WRITE = re.compile(r"\b(?:db|tx)\s*\.\s*(?:insert|update|delete)\s*\(")
IMPORT = re.compile(r"""(?:from\s*|import\s*\(\s*|require\s*\(\s*)['"]([^'"]+)['"]""")
PATH_LITERAL = re.compile(r"""["'`](/[^"'`\s?#]*)""")
COMMANDS = {
    "vitest": "pnpm add -D @vitest/coverage-v8 (once), then pnpm vitest run --coverage --coverage.reporter=json-summary --coverage.reportOnFailure=true",
    "jest": "npx jest --coverage --coverageReporters=json-summary",
}


def _files(base: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for d, dirs, names in os.walk(base):
        dirs[:] = sorted(x for x in dirs if x not in SKIP)
        for n in sorted(names):
            if n.endswith(CODE):
                p = Path(d) / n
                try:
                    out[p.relative_to(base).as_posix()] = p.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    pass
    return out


def _is_e2e(rel: str) -> bool:
    return rel.startswith(E2E_DIRS)


def _is_test(rel: str) -> bool:
    return bool(TEST_FILE.search(rel)) or _is_e2e(rel)


def _mutations(files: dict[str, str]) -> list[str]:
    out = []
    for rel, text in files.items():
        if _is_test(rel) or rel.split("/", 1)[0] in NOT_APP:
            continue
        route = posixpath.basename(rel).split(".")[0] == "route" and ("app/" in f"/{rel}")
        if USE_SERVER.match(text) or (route and WRITE_VERB.search(text)) or DRIZZLE_WRITE.search(text):
            out.append(rel)
    return sorted(out)


def mutations(base: Path) -> list[str]:
    """The files under `base` that write data, relative to it."""
    return _mutations(_files(base))


def _stem(rel: str) -> str:
    stem = rel.rsplit(".", 1)[0]
    return stem[: -len("/index")] if stem.endswith("/index") else stem


def _targets(text: str, from_rel: str) -> set[str]:
    """The stems a file imports: `@/x` as `x` and `src/x`, a relative path resolved from the importing file."""
    out: set[str] = set()
    for spec in IMPORT.findall(text):
        if spec.startswith("@/"):
            out |= {spec[2:], f"src/{spec[2:]}"}
        elif spec.startswith("."):
            target = posixpath.normpath(posixpath.join(posixpath.dirname(from_rel), spec))
            out |= {target, _stem(target + ".x")}
    return out


def _imports(text: str, from_rel: str, stem: str) -> bool:
    return stem in _targets(text, from_rel)


def _importers(files: dict[str, str], rel: str) -> set[str]:
    """Every non-test file that imports `rel`, directly or through other files (a page → an action → a library)."""
    reverse: dict[str, set[str]] = {}
    stems = {_stem(f): f for f in files}
    for f, text in files.items():
        if _is_test(f):
            continue
        for t in _targets(text, f):
            if t in stems:
                reverse.setdefault(stems[t], set()).add(f)
    seen: set[str] = set()
    todo = [rel]
    while todo:
        for importer in reverse.get(todo.pop(), ()):
            if importer not in seen:
                seen.add(importer)
                todo.append(importer)
    return seen


def page_url(rel_page: str) -> str:
    """`app/[locale]/(marketing)/plans/[id]/page.tsx` → `/plans/[id]`: groups dropped, leading dynamic segments
    (the locale) dropped, inner ones kept to match any value. A `route.ts` reads the same way."""
    parts = rel_page.split("/")
    if parts and parts[0] == "src":
        parts = parts[1:]
    parts = [p for p in parts[1:-1] if not (p.startswith("(") and p.endswith(")"))]
    while parts and parts[0].startswith("["):
        parts = parts[1:]
    return "/" + "/".join(parts)


def _url_pattern(url: str) -> re.Pattern:
    segs = [r"[^/]+" if s.startswith("[") else re.escape(s) for s in url.strip("/").split("/") if s]
    return re.compile("^/" + "/".join(segs) + "/?$")


def _tested_by(files: dict[str, str], rel: str) -> str | None:
    stem = _stem(rel)
    for t, text in files.items():
        if _is_test(t) and not _is_e2e(t) and (_imports(text, t, stem) or stem in text):
            return "unit"
    # a page that uses it (directly or through other files), or a route handler — itself or one that uses it —
    # whose own URL an e2e spec calls (`request.post("/api/…")`)
    reach = _importers(files, rel) | {rel}
    entries = [p for p in reach if posixpath.basename(p).split(".")[0] in ("page", "route") and "app/" in f"/{p}"]
    patterns = [_url_pattern(page_url(p)) for p in entries]
    for t, text in files.items():
        if _is_e2e(t) and any(pat.match(lit) for lit in PATH_LITERAL.findall(text) for pat in patterns):
            return "e2e"
    return None


def tested_by(base: Path, rel: str) -> str | None:
    """"unit", "e2e" or None for the file `rel` under `base`."""
    return _tested_by(_files(base), rel)


def coverage(base: Path) -> tuple[dict | None, str]:
    """The line coverage from `coverage/coverage-summary.json` (istanbul json-summary: Vitest and Jest write the same
    shape), or (None, why)."""
    p = base / "coverage" / "coverage-summary.json"
    if not p.is_file():
        return None, "no coverage/coverage-summary.json"
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        total = data["total"]["lines"]["pct"]
        files = {}
        for key, v in data.items():
            if key == "total":
                continue
            try:
                rel = Path(key).resolve().relative_to(base.resolve()).as_posix()
            except ValueError:
                rel = key
            files[rel] = v["lines"]["pct"]
    except (ValueError, KeyError, TypeError) as e:
        return None, f"coverage/coverage-summary.json unreadable ({type(e).__name__})"
    return {"total": total, "files": files}, ""


def _command(meta: dict) -> str:
    layers = str((meta.get("stack") or {}).get("test") or "")
    return COMMANDS["jest"] if "jest" in layers else COMMANDS["vitest"]


def check(root: Path, meta: dict, authz_files: set[str]) -> tuple[list[Finding], list[Source]]:
    found = sf.surfaces(root, meta)
    webs = [s for s in found if s.kind == "web"]
    findings: list[Finding] = []
    counts = {"unit": 0, "e2e": 0, "none": 0}
    for web in webs:
        base = root / web.path
        files = _files(base)
        for rel in _mutations(files):
            path = rel if web.path == "." else f"{web.path}/{rel}"
            how = _tested_by(files, rel)
            counts[how or "none"] += 1
            if how is None:
                findings.append(Finding("tests", "untested-mutation",
                                        "writes data and no test reaches it (no unit test imports it, no e2e spec "
                                        "visits a page that uses it)", file=path,
                                        severity="authz" if path in authz_files else "", routed_to="write-tests"))
    if webs:
        tests = Source("tests", "fresh", f"{sum(counts.values())} files write data: {counts['unit']} reached by a unit "
                                         f"test, {counts['e2e']} by e2e only, {counts['none']} by none")
    else:
        tests = Source("tests", "not applicable", "no web surface — the mutation check is web only")
    measured, missing = [], []
    for s in [s for s in found if s.kind in ("web", "mobile")]:
        cov, why = coverage(root / s.path)
        (measured if cov else missing).append(f"{s.name}: {cov['total']}% lines" if cov else f"{s.name}: {why}")
    if measured:
        cov_src = Source("coverage", "fresh", "; ".join(measured + missing))
    elif missing:
        cov_src = Source("coverage", "not checked", f"{'; '.join(missing)} — produce it with: {_command(meta)}")
    else:
        cov_src = Source("coverage", "not applicable", "no web or mobile surface")
    return findings, [tests, cov_src]
