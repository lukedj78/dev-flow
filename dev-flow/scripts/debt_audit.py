#!/usr/bin/env python3
"""debt_audit.py — dev-flow's debt audit: every audit the project has, plus a test check, in one ordered list.

    python3 debt_audit.py collect <project-root> [--skip NAME ...] [--json]
    python3 debt_audit.py show <project-root>

`collect` runs the sibling skills' local scanners, reads what shadscan and vercel-doctor last recorded, reads the
prose recipes' findings from `.workflow/debt/manual.json`, adds the test check, applies the decisions already taken
(gate acceptances per check, `.workflow/debt/reviewed.json` per finding), puts each finding in a band
(before-release / with-features / later), orders each band by how often its files changed, and writes:

- `docs/debt/debt-audit.md` — the report, for the user;
- `.workflow/debt/findings.json` — the same, for the agent (and the next run's new / closed);
- `meta.json#debt_audit` — the counts, through meta_io's lock; plus a history entry. Never `phase`.

What it could not see is listed under "not checked", never counted as ok. A fresh app-security or compliance hit is
a signal ("to confirm") until reviewed.json confirms it. `show` prints the last report without re-running anything.
Stdlib only. See dev-flow/references/debt-audit.md.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import debt_model as dm  # noqa: E402
import debt_sources as ds  # noqa: E402
import debt_tests as dt  # noqa: E402
import meta_io  # noqa: E402
import surfaces as sf  # noqa: E402

REPORT = "docs/debt/debt-audit.md"
TITLES = {"before-release": "Before the next release", "with-features": "With the features that touch these files",
          "later": "Later"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _read_json(path: Path, default):
    """The parsed file, `default` when it does not exist, None when it exists and cannot be read."""
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None


def _row(f: dm.Finding) -> str:
    where = f"{f.file}:{f.line}" if f.file and f.line else (f.file or "")
    tags = ("[to confirm] " if f.signal else "") + ("[stale] " if f.stale else "")
    route = f" → {f.routed_to}" if f.routed_to else ""
    return f"- {tags}{where + ' — ' if where else ''}{f.detail} ({f.source}/{f.check}{route})"


def _report(run_at: str, open_: list[dm.Finding], kept: list[dm.Finding], sources: list[ds.Source],
            notes: list[str], new: set[str], closed: set[str]) -> str:
    out = [f"# Debt audit — {run_at[:10]}", ""]
    for band in dm.BANDS:
        rows = [f for f in open_ if f.band == band]
        out += [f"## {TITLES[band]} ({len(rows)})", ""] + ([_row(f) for f in rows] or ["Nothing."]) + [""]
    unseen = [s for s in sources if s.status == "not checked"]
    out += ["## Not checked", "", "What this audit could not see — not the same as clean.", ""]
    out += [f"- {s.name}: {s.reason}" for s in unseen] or ["Every source ran."]
    stale = [s for s in sources if s.status in ("stale", "missing")]
    out += [f"- {s.name} ({s.status}): {s.reason or 'older than the last material change — re-run it'}" for s in stale]
    out += [f"- note: {n}" for n in notes] + [""]
    out += ["## Kept on purpose", ""] + ([f"{_row(f)} — kept: {f.kept}" for f in kept] or ["Nothing."]) + [""]
    out += ["## Since the last audit", "", f"- new: {len(new)}", f"- closed: {len(closed)}"]
    out += [f"  - closed: {i}" for i in sorted(closed)] + [""]
    return "\n".join(out)


def collect(root: Path, skip: set[str] = frozenset(), now: str | None = None) -> dict:
    root = root.resolve()
    run_at = now or _now()
    meta_path = root / ".workflow" / "meta.json"
    meta = _read_json(meta_path, {}) or {}
    web = any(s.kind == "web" for s in sf.surfaces(root, meta))
    last_change, _ = ds.last_material_change(meta)

    findings, sources = ds.run_scanners(root, meta, set(skip), web)
    rec, rec_sources = ds.recorded(root, meta, last_change)
    man, man_source = ds.manual(root)
    authz = {f.file for f in findings if f.source == "app-security" and f.check in ds.AUTHZ_CHECKS and f.file}
    tests, test_sources = dt.check(root, meta, authz)
    findings += rec + man + tests
    sources += rec_sources + [man_source] + test_sources

    debt = root / ".workflow" / "debt"
    reviewed = _read_json(debt / "reviewed.json", {})
    open_, kept, notes = dm.apply_decisions(findings, meta, reviewed if isinstance(reviewed, dict) else None, root)
    for f in open_ + kept:
        f.band = dm.band_for(f)
    churn = dm.churn(root)
    open_ = [f for band in dm.BANDS for f in dm.order([x for x in open_ if x.band == band], churn)]

    previous = _read_json(debt / "findings.json", {}) or {}
    prev_ids = {r.get("id") for r in previous.get("open", []) if isinstance(r, dict)}
    new, closed = dm.diff_runs(prev_ids, {f.id for f in open_}) if previous else (set(), set())

    def dump(f: dm.Finding) -> dict:
        return {"id": f.id, **asdict(f)}

    debt.mkdir(parents=True, exist_ok=True)
    meta_io.write_text(debt / "findings.json", json.dumps({
        "run_at": run_at, "open": [dump(f) for f in open_], "kept": [dump(f) for f in kept],
        "not_checked": [asdict(s) for s in sources if s.status == "not checked"],
        "sources": {s.name: s.status for s in sources}, "notes": notes}, indent=2) + "\n")
    report = root / REPORT
    report.parent.mkdir(parents=True, exist_ok=True)
    meta_io.write_text(report, _report(run_at, open_, kept, sources, notes, new, closed))

    confirmed = [f for f in open_ if not f.signal]
    block = {
        "last_run_at": run_at,
        "bands": {"before_release": sum(f.band == "before-release" for f in confirmed),
                  "with_features": sum(f.band == "with-features" for f in confirmed),
                  "later": sum(f.band == "later" for f in confirmed)},
        "to_confirm": sum(f.signal for f in open_),
        "not_checked": [s.name for s in sources if s.status == "not checked"],
        "sources": {s.name: s.status for s in sources},
        "new": len(new), "closed": len(closed), "report": REPORT,
    }
    if meta_path.is_file():
        with meta_io.locked(root / ".workflow"):
            current = meta_io.read_meta(meta_path)
            current["debt_audit"] = block
            current.setdefault("history", []).append({"skill": "dev-flow", "action": "debt-audit", "ran_at": run_at,
                                                      "outputs": [REPORT]})
            current["updated_at"] = run_at
            meta_io.write_json(meta_path, current)
    return block


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="op", required=True)
    c = sub.add_parser("collect")
    c.add_argument("project_root", type=Path)
    c.add_argument("--skip", nargs="*", default=[], choices=sorted(ds.SCANNERS), help="sources not to run (then not checked)")
    c.add_argument("--json", action="store_true")
    s = sub.add_parser("show")
    s.add_argument("project_root", type=Path)
    a = ap.parse_args(argv)
    if a.op == "show":
        report = a.project_root / REPORT
        if not report.is_file():
            print(f"no debt audit yet — run: debt_audit.py collect {a.project_root}")
            return 1
        print(report.read_text(encoding="utf-8"))
        return 0
    block = collect(a.project_root, set(a.skip))
    if a.json:
        print(json.dumps(block, indent=2))
    else:
        print((a.project_root / REPORT).read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
