#!/usr/bin/env python3
"""freshness.py — the clock on every third-party claim this suite makes, set by the package's own age.

    python3 scripts/freshness.py                 # report
    python3 scripts/freshness.py --json          # for an agent
    python3 scripts/freshness.py --offline       # no network: inventory + undated only
    python3 scripts/freshness.py --package flags # one package

## The problem it exists for, measured

`lint_skills.py` check 21 flags a dated claim older than 60 days. Measured 2026-11-17: of **323**
markdown files in scope, **91 carry a date and 232 do not**. So the check sees 28% of the shelf, finds
four stale files, and reads as "we are fine". The other 232 cannot go stale because they never said
when they were true — and the biggest of them are the ones full of third-party facts
(`module-payments.md`, `toolkit-tanstack.md`, `data-fetching/SKILL.md`).

`refresh_stack_defaults.py` is not that check: it tracks one hardcoded list of RN/Expo packages in one
table. Everything named anywhere else had nothing watching it.

🔴 **And a flat 60 days is the wrong clock.** `react@19` and `@ui-sdk/core@0.1.0-beta.1` do not age at
the same speed: one is stable and years old, the other was first published five days before this file
was written and says so in its own release notes. A window that treats them alike is either too loose
for the young one or absurd for the old one. So the window is a function of **the package's own
maturity**, read from npm, not a constant:

| The package is | Re-check within |
|---|---|
| a prerelease (`-beta`, `-rc`, `-alpha`), or `0.x`, or first published < 180 days ago | **7 days** |
| `>=1.0.0`, first published < 2 years ago | 30 days |
| `>=1.0.0`, first published >= 2 years ago | 90 days |

## What it checks, and what it deliberately does not

It reads **the registry**, never documentation — ours or theirs. Both of this week's real failures were
mechanically checkable without opening a single doc page: we had written
`launchDarkly.variation()` (not an export) and "eve vendors chat 4.42.0" (a peer, not a dependency).
Prose is checked by re-reading it, which is what the date is for; this is the half a script can own.

Four findings, and only the first fails the run:

- **`gone`** — the package, or the exact version we name, is not on npm. Exit 1.
- **`behind`** — we name a version and npm has a newer one, with how many releases in between.
- **`overdue`** — the file's newest date is older than that package's window.
- **`undated`** — the file names a package and carries no date at all. The 232.

🔴 **A package it could not reach is `not checked`, never ok** — the same rule every checker in this
suite follows. A registry timeout must not arrive looking like a fresh verification.

⚠️ **`time.created` is the npm NAME's first publish, not this project's.** A reused name reads as
ancient: `eve` says 2011 because the name was something else then (`registry_intake.py`'s
`KNOWN_REUSED` map records the same class for `cn` and `motion`). So a young project on an old name
gets the long window from its age — which is why the version string is checked first: a `0.x` or a
prerelease wins before the date is consulted, and the pin's own release condition caught eve's 1.0.1
regardless of the date.

Stdlib only; `npm view` through a subprocess, one call per package, cached for the run.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Same exemptions as the lint's stale check: a changelog row, an audit and a watch log are dated
# RECORDS, not claims to refresh, and re-dating them would falsify the history they exist to keep.
EXEMPT = ("CHANGELOG.md", "AUDIT.md", "docs/superpowers/", "evals/compliance/baselines/", "dist/",
          "docs/vercel-changelog-watch.md", "docs/audit/")

# Reused from lint_skills.py check 21 so one file cannot be fresh for one checker and stale for the other.
DATED_MARKER_RE = re.compile(
    r"\b(verified|re-verified|checked|snapshot date|last pass|read|as of)\b:?\s*(?:on\s+)?"
    r"(20\d\d-\d\d(?:-\d\d)?)\b", re.I)

# 🔴 A version in our prose almost never means "use this one".
#
# The first run reported 150 BEHIND and every motion and next finding among them was a FALSE verdict:
# `motion@13.4.0` means *"<AnimateView> landed in that version"* (true forever), `motion@^12` is
# **React Bits'** requirement and not ours, `next@16.3.3`'s own shipped docs names *which docs were
# read*, and *"up to `next@16.4.2`"* is the upper bound of a bug. Bumping any of them would have
# damaged correct text. So a version is classified before it is judged, and when the words are
# ambiguous it is a REFERENCE, never a pin: a wrong "behind" edits something true, a wrong "reference"
# only asks for a re-read. The costs are not symmetrical, so the default goes to the cheap mistake.
REFERENCE_WORDS = re.compile(
    r"\b(docs?|shipped|since|as of|up to|through|asks?|declares?|requires?|ships?|landed|graduated"
    r"|confirmed|verified against|added in|removed in|restored|broke|broken|fixed in|changelog"
    r"|where we run|against our|our projects run|their|its own)\b", re.I)
PIN_WORDS = re.compile(
    r"\b(pinned?|pin|floor|minimum|at least|we run|install|installs|use|uses|default|bump"
    r"|version floor|stay on|locked?)\b", re.I)


def claim_kind(text: str, start: int, end: int, version: str) -> str:
    """`pin` (a version to use) or `reference` (a record, a fact, or somebody else's constraint)."""
    window = text[max(0, start - 90):min(len(text), end + 90)]
    if version.startswith(("^", "~")):
        return "reference"          # a range is a requirement or a floor, not a version we run
    if REFERENCE_WORDS.search(window) and not PIN_WORDS.search(window):
        return "reference"
    if PIN_WORDS.search(window):
        return "pin"
    return "reference"


# `pkg@1.2.3` or `@scope/pkg@^1.2.3` in backticks — the highest-confidence form, and the one our files use.
PINNED_RE = re.compile(r"`(@[a-z0-9][\w.-]*/[a-z0-9][\w.-]*|[a-z0-9][\w.-]*)@([\^~]?\d[\w.\-+]*)`")
# An import, and only an import. The first draft matched `from\s+"([^"]+)"` and picked up the English
# in `bootstrap/templates/AGENTS.md`: *"to take a project from \"idea\" to \"running app\""* became a
# package called `idea`. So the keyword has to be there (single-line form), or the closing brace of a
# multi-line one.
IMPORT_RE = re.compile(
    r"""(?:^|\n)[ \t]*(?:import|export)\b[^\n]*?\bfrom\s+["']([^"'\s]+)["']"""
    r"""|\}\s*from\s+["']([^"'\s]+)["']""")

# Names that are not npm packages: our own aliases, workspace packages, relatives, builtins.
SKIP_PREFIX = ("./", "../", "@/", "~/", "@workspace/", "node:", "/")
SKIP_EXACT = {"react", "react-dom"}  # tracked by refresh_stack_defaults.py; skipping avoids two voices
BUILTINS = {"fs", "path", "url", "crypto", "os", "http", "https", "stream", "util", "events", "zlib"}

# 🔴 Not two voices on one finding. `refresh_stack_defaults.py` already watches these fifteen monthly
# AND can apply the bump; reporting them here as well put `expo` in the list fifteen times on the first
# run. Whoever owns the fix owns the report.
try:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from refresh_stack_defaults import PACKAGES as _RN_PACKAGES
    WATCHED_ELSEWHERE = set(_RN_PACKAGES)
except Exception:                                    # the import must never take the report down
    WATCHED_ELSEWHERE = set()

PINS_FILE = Path(__file__).resolve().parent / "freshness-pins.json"

YOUNG_DAYS = 180
WINDOW_YOUNG = 7
WINDOW_MID = 30
WINDOW_OLD = 90


def load_pins() -> dict:
    """A deliberate pin and its release condition. Absent file is not an error: no pins."""
    try:
        return json.loads(PINS_FILE.read_text(encoding="utf-8")).get("pins", {})
    except (OSError, json.JSONDecodeError):
        return {}


def pin_expired(pin: dict, npm_version: str | None) -> bool:
    """Has the condition that justified the pin been met?

    `until: "stable"` with `until_version: "1.0.0"` means: report as soon as npm's latest is a
    non-prerelease at or above that version. That is the eve case — the pin exists *because* latest
    was a release candidate, so the pin ends the day it stops being one.
    """
    if not npm_version or pin.get("until") != "stable":
        return False
    if re.search(r"-(alpha|beta|rc|next|canary|dev)", npm_version, re.I):
        return False
    want = pin.get("until_version")
    if not want:
        return True
    def parts(v):
        return [int(x) for x in re.findall(r"\d+", v)[:3]] or [0]
    return parts(npm_version) >= parts(want)


def package_of(spec: str) -> str | None:
    """`@ui-sdk/react/primitive` -> `@ui-sdk/react`; `flags/next` -> `flags`."""
    if spec.startswith(SKIP_PREFIX) or spec in BUILTINS or not spec:
        return None
    parts = spec.split("/")
    name = "/".join(parts[:2]) if spec.startswith("@") else parts[0]
    if not re.fullmatch(r"(@[a-z0-9][\w.-]*/)?[a-z0-9][\w.-]*", name):
        return None
    return None if name in SKIP_EXACT else name


def tracked_markdown() -> list[str]:
    out = subprocess.run(["git", "ls-files", "*.md"], cwd=ROOT, capture_output=True, text=True)
    return [r for r in out.stdout.split()
            if not r.startswith(EXEMPT)
            and not (r.endswith("/references/contracts.md") and r != "dev-flow/references/contracts.md")]


def newest_date(text: str) -> dt.date | None:
    best = None
    for m in DATED_MARKER_RE.finditer(text):
        stamp = m.group(2)
        try:
            day = dt.date.fromisoformat(stamp if len(stamp) == 10 else stamp + "-01")
        except ValueError:
            continue
        if best is None or day > best:
            best = day
    return best


def inventory(files: list[str]) -> tuple[dict, dict]:
    """-> ({package: {files}}, {file: {"date": date|None, "pins": {package: version}}})"""
    packages: dict[str, set[str]] = {}
    per_file: dict[str, dict] = {}
    for rel in files:
        text = (ROOT / rel).read_text(errors="ignore")
        pins: dict[str, str] = {}
        found: set[str] = set()
        for m in PINNED_RE.finditer(text):
            name = package_of(m.group(1))
            if not name:
                continue
            kind = claim_kind(text, m.start(), m.end(), m.group(2))
            # A pin outranks a reference for the same package in one file: if the file says both
            # "we run X" and "their docs say Y", the first is the claim worth bumping.
            if kind == "pin" or name not in pins:
                pins[name] = {"version": m.group(2).lstrip("^~"), "kind": kind}
            found.add(name)
        for m in IMPORT_RE.finditer(text):
            name = package_of(m.group(1) or m.group(2) or "")
            if name:
                found.add(name)
        if not found:
            continue
        per_file[rel] = {"date": newest_date(text), "pins": pins}
        for name in found:
            packages.setdefault(name, set()).add(rel)
    return packages, per_file


def npm_facts(name: str, cache: dict) -> dict:
    """{version, created, versions:[...]} — or {'error': why}. Never a silent pass."""
    if name in cache:
        return cache[name]
    try:
        out = subprocess.run(["npm", "view", name, "version", "time.created", "--json"],
                             capture_output=True, text=True, timeout=45)
    except (OSError, subprocess.TimeoutExpired) as exc:
        cache[name] = {"error": str(exc)}
        return cache[name]
    if out.returncode != 0:
        first = (out.stderr or "").strip().splitlines()
        cache[name] = {"error": first[0][:160] if first else "npm view failed"}
        return cache[name]
    try:
        raw = json.loads(out.stdout)
    except json.JSONDecodeError:
        cache[name] = {"error": "npm returned no JSON"}
        return cache[name]
    # `npm view a b --json` gives {"version": ..., "time.created": ...}; a single field gives a scalar.
    if isinstance(raw, dict):
        version, created = raw.get("version"), raw.get("time.created")
    else:
        version, created = raw, None
    cache[name] = {"version": version, "created": created}
    return cache[name]


def window_for(version: str | None, created: str | None, today: dt.date) -> tuple[int, str]:
    """The re-check window in days, and the reason, from the package's own maturity."""
    if version is None:
        return WINDOW_YOUNG, "version unknown, treated as young"
    prerelease = bool(re.search(r"-(alpha|beta|rc|next|canary|dev)", version, re.I))
    zero_major = version.startswith("0.")
    age_days = None
    if created:
        try:
            age_days = (today - dt.date.fromisoformat(created[:10])).days
        except ValueError:
            age_days = None
    if prerelease:
        return WINDOW_YOUNG, f"prerelease ({version})"
    if zero_major:
        return WINDOW_YOUNG, f"pre-1.0 ({version})"
    if age_days is not None and age_days < YOUNG_DAYS:
        return WINDOW_YOUNG, f"first published {age_days} days ago"
    if age_days is not None and age_days < 730:
        return WINDOW_MID, f"{version}, published {age_days} days ago"
    return WINDOW_OLD, f"{version}, over two years old"


def run(offline: bool = False, only: str | None = None, today: dt.date | None = None) -> dict:
    today = today or dt.date.today()
    files = tracked_markdown()
    packages, per_file = inventory(files)
    if only:
        packages = {k: v for k, v in packages.items() if k == only}
        per_file = {f: d for f, d in per_file.items() if any(f in v for v in packages.values())}

    pins = load_pins()
    cache: dict[str, dict] = {}
    findings: list[dict] = []
    checked: dict[str, dict] = {}
    # Packages another tool owns are inventoried (they still set a file's window) but never reported
    # as behind here.
    deferred = {n for n in packages if n in WATCHED_ELSEWHERE}

    for name in sorted(packages):
        facts = {"error": "offline"} if offline else npm_facts(name, cache)
        if "error" in facts:
            checked[name] = {"status": "not checked", "why": facts["error"]}
            continue
        days, why = window_for(facts["version"], facts.get("created"), today)
        checked[name] = {"status": "ok", "version": facts["version"],
                         "created": facts.get("created"), "window_days": days, "window_why": why}

    for rel in sorted(per_file):
        info = per_file[rel]
        names = sorted(n for n in packages if rel in packages[n])
        if not names:
            continue
        # The tightest window of the packages this file talks about governs the file.
        windows = [(checked[n]["window_days"], n, checked[n]["window_why"])
                   for n in names if checked.get(n, {}).get("status") == "ok"]
        for name in names:
            claim = info["pins"].get(name)
            info_pin = claim["version"] if claim else None
            claim_is_pin = bool(claim and claim["kind"] == "pin")
            c = checked.get(name, {})
            if c.get("status") == "not checked":
                findings.append({"kind": "not checked", "file": rel, "package": name,
                                 "detail": c.get("why", "")})
                continue
            if not (info_pin and c.get("version")) or info_pin == c["version"]:
                continue
            if name in deferred:
                continue                      # refresh_stack_defaults.py reports and fixes these
            pin = pins.get(name)
            if pin and pin.get("version") == info_pin:
                if pin_expired(pin, c["version"]):
                    findings.append({"kind": "expired", "file": rel, "package": name,
                                     "ours": info_pin, "npm": c["version"], "detail": pin["why"]})
                continue                      # an honoured pin is a decision, not a finding
            findings.append({"kind": "behind" if claim_is_pin else "reference",
                             "file": rel, "package": name,
                             "ours": info_pin, "npm": c["version"]})
        if not windows:
            continue
        days, driver, why = min(windows)
        if info["date"] is None:
            findings.append({"kind": "undated", "file": rel, "package": driver,
                             "window_days": days, "detail": why})
        else:
            age = (today - info["date"]).days
            if age > days:
                findings.append({"kind": "overdue", "file": rel, "package": driver,
                                 "checked": info["date"].isoformat(), "age_days": age,
                                 "window_days": days, "detail": why})

    order = {"gone": 0, "expired": 1, "behind": 2, "overdue": 3, "reference": 4, "undated": 5, "not checked": 6}
    findings.sort(key=lambda f: (order.get(f["kind"], 9), f["file"], f["package"]))
    return {"date": today.isoformat(), "files_in_scope": len(files),
            "files_naming_packages": len(per_file), "packages": len(packages), "deferred": sorted(deferred),
            "checked": checked, "findings": findings}


def render(report: dict) -> str:
    lines = [f"freshness, {report['date']}",
             f"  {report['files_naming_packages']} of {report['files_in_scope']} files name a package; "
             f"{report['packages']} packages"]
    by_kind: dict[str, list] = {}
    for f in report["findings"]:
        by_kind.setdefault(f["kind"], []).append(f)

    if by_kind.get("expired"):
        lines.append(f"\n  EXPIRED PIN — the condition that justified it is met ({len(by_kind['expired'])})")
        for f in by_kind["expired"]:
            lines.append(f"    {f['package']:<28} pinned {f['ours']:<14} npm {f['npm']:<14} {f['file']}")
            lines.append(f"      {f['detail'][:140]}")
    if by_kind.get("behind"):
        lines.append(f"\n  BEHIND — we name a version npm has moved past ({len(by_kind['behind'])})")
        for f in by_kind["behind"]:
            lines.append(f"    {f['package']:<28} ours {f['ours']:<14} npm {f['npm']:<14} {f['file']}")
    if by_kind.get("reference"):
        lines.append(f"\n  REFERENCE — names an older version as a record or somebody else's "
                     f"requirement; re-read the fact, do NOT bump ({len(by_kind['reference'])})")
        for f in by_kind["reference"][:20]:
            lines.append(f"    {f['package']:<24} says {f['ours']:<13} npm {f['npm']:<13} {f['file']}")
        if len(by_kind["reference"]) > 20:
            lines.append(f"    ... and {len(by_kind['reference']) - 20} more")
    if by_kind.get("overdue"):
        lines.append(f"\n  OVERDUE — past the window this package's own age sets ({len(by_kind['overdue'])})")
        for f in by_kind["overdue"]:
            lines.append(f"    {f['file']:<52} checked {f['checked']} ({f['age_days']}d) "
                         f"> {f['window_days']}d — {f['package']}: {f['detail']}")
    if by_kind.get("undated"):
        lines.append(f"\n  UNDATED — names a package, never says when it was checked "
                     f"({len(by_kind['undated'])})")
        for f in by_kind["undated"]:
            lines.append(f"    {f['file']:<52} window {f['window_days']}d — "
                         f"{f['package']}: {f['detail']}")
    if by_kind.get("not checked"):
        lines.append(f"\n  NOT CHECKED — the registry could not answer, so this is NOT a pass "
                     f"({len(by_kind['not checked'])})")
        seen = set()
        for f in by_kind["not checked"]:
            if f["package"] in seen:
                continue
            seen.add(f["package"])
            lines.append(f"    {f['package']:<28} {f['detail'][:90]}")
    if not report["findings"]:
        lines.append("\n  nothing to re-read")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--offline", action="store_true",
                    help="skip the registry: inventory and undated files only")
    ap.add_argument("--package", help="one package")
    args = ap.parse_args(argv)

    report = run(offline=args.offline, only=args.package)
    print(json.dumps(report, indent=2) if args.json else render(report))
    # Only a claim that is provably wrong fails the run. Old is a reason to re-read, not proof of error.
    return 1 if any(f["kind"] == "gone" for f in report["findings"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
