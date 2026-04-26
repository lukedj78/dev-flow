#!/usr/bin/env python3
"""Detect when artifacts in `.workflow/meta.json` are out of sync with disk.

Two kinds of drift:

  1. **Self-drift** — the file recorded as `path` has been edited since the
     skill last hashed it. The on-disk SHA-256 no longer matches the recorded
     one. Whoever owns this file (the `produced_by` skill) should re-run, or
     accept that the file is now hand-maintained and re-record manually.

  2. **Upstream drift** — the file is still as the skill wrote it, but a file
     listed in its `derived_from` has changed. The output is technically in
     the right state on disk but is now derived from stale inputs. Example:
     `DESIGN.md` changed → `registry.json` and `app/showcase` are upstream-stale.

The drift propagates **transitively**: if `DESIGN.md` is stale, then anything
derived from `DESIGN.md` is stale, AND anything derived from those is stale,
and so on through the DAG.

The `--plan` flag produces a migration plan grouped by the skill that should
re-run, with the artifacts that need refreshing.

By default the command exits 0 with a status table. Pass `--exit-nonzero-on-drift`
in CI to fail builds when drift is present.

The command makes no changes — it's diagnostic. The intended workflow is:
  $ python3 check_drift.py <project-root>
  $ python3 check_drift.py <project-root> --plan
  $ # Read the plan, run the recommended skills.

Usage:
    python3 check_drift.py <project-root> [--exit-nonzero-on-drift] [--plan]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Hashing helpers (intentionally duplicated from update_meta.py to keep
# check_drift.py importable / runnable as a standalone script)
# ---------------------------------------------------------------------------


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("project_root", type=Path)
    ap.add_argument(
        "--exit-nonzero-on-drift",
        action="store_true",
        help="Exit code 1 if any artifact is stale or missing (useful in CI).",
    )
    ap.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON instead of a human table.",
    )
    ap.add_argument(
        "--plan",
        action="store_true",
        help="After the table, print a migration plan grouped by skill.",
    )
    args = ap.parse_args()

    root = args.project_root.resolve()
    meta_path = root / ".workflow" / "meta.json"
    if not meta_path.exists():
        sys.stderr.write(f"No .workflow/meta.json at {root}\n")
        return 1

    meta = json.loads(meta_path.read_text())
    artifacts: dict[str, dict[str, Any]] = meta.get("artifacts") or {}

    if not artifacts:
        msg = "No artifacts recorded yet — nothing to check."
        if args.json:
            print(json.dumps({"status": "no-artifacts", "rows": []}))
        else:
            print(msg)
        return 0

    # First pass: classify each artifact based on its own hash + immediate
    # upstreams (single-hop).
    rows: list[dict[str, Any]] = []
    rows_by_path: dict[str, dict[str, Any]] = {}
    any_drift = False

    for rel_path, entry in artifacts.items():
        abs_path = (root / rel_path).resolve()
        recorded_sha = entry.get("sha256")
        produced_by = entry.get("produced_by", "?")

        row: dict[str, Any] = {
            "path": rel_path,
            "produced_by": produced_by,
            "status": "fresh",
            "detail": "",
        }

        if not abs_path.exists():
            row["status"] = "missing"
            row["detail"] = "file no longer exists on disk"
            any_drift = True
        else:
            on_disk_sha = sha256_file(abs_path)
            if on_disk_sha != recorded_sha:
                row["status"] = "self-drift"
                row["detail"] = f"recorded {recorded_sha[:8]} vs on-disk {on_disk_sha[:8]}"
                any_drift = True
            else:
                # Self matches — check immediate upstream dependencies.
                upstream_stale: list[str] = []
                for dep in entry.get("derived_from") or []:
                    dep_path = (root / dep["path"]).resolve()
                    if not dep_path.exists():
                        upstream_stale.append(f"{dep['path']} (missing)")
                        continue
                    current_dep_sha = sha256_file(dep_path)
                    if current_dep_sha != dep["sha256"]:
                        upstream_stale.append(
                            f"{dep['path']} ({dep['sha256'][:8]} → {current_dep_sha[:8]})"
                        )
                if upstream_stale:
                    row["status"] = "upstream-stale"
                    row["detail"] = "; ".join(upstream_stale)
                    any_drift = True

        rows.append(row)
        rows_by_path[rel_path] = row

    # Second pass: propagate drift transitively. If artifact X is stale and
    # artifact Y is `derived_from` X (directly OR indirectly), Y is stale too.
    # This catches multi-hop chains: DESIGN.md → registry.json → app/showcase.
    # Iterate to fixed point — for a small DAG the number of passes is tiny.
    def is_stale(row: dict[str, Any]) -> bool:
        return row["status"] in {"self-drift", "upstream-stale", "missing"}

    changed = True
    while changed:
        changed = False
        for rel_path, entry in artifacts.items():
            row = rows_by_path[rel_path]
            if is_stale(row):
                continue
            for dep in entry.get("derived_from") or []:
                dep_row = rows_by_path.get(dep["path"])
                if dep_row and is_stale(dep_row):
                    row["status"] = "upstream-stale"
                    row["detail"] = (
                        f"transitively via {dep['path']} ({dep_row['status']})"
                    )
                    any_drift = True
                    changed = True
                    break

    if args.json:
        print(json.dumps({
            "status": "drift" if any_drift else "fresh",
            "rows": rows,
        }, indent=2))
    else:
        col1 = max(len(r["path"]) for r in rows)
        col2 = max(len(r["produced_by"]) for r in rows)
        for r in rows:
            icon = {
                "fresh": "✓",
                "self-drift": "✗",
                "upstream-stale": "⚠",
                "missing": "✗",
            }.get(r["status"], "?")
            line = f"  {icon} {r['path']:<{col1}}  {r['produced_by']:<{col2}}  {r['status']}"
            if r["detail"]:
                line += f"  ({r['detail']})"
            print(line)

        print()
        fresh = sum(1 for r in rows if r["status"] == "fresh")
        print(f"Summary: {fresh}/{len(rows)} artifacts fresh.")
        if any_drift:
            print("Drift detected. Inspect the table above and re-run the relevant skills.")
        else:
            print("All artifacts in sync with their recorded state.")

    # Migration plan — group stale artifacts by the skill that should re-run.
    if args.plan and any_drift:
        print()
        print("Migration plan (re-run these skills, in order):")
        # Group by skill, dedupe paths.
        by_skill: dict[str, list[dict[str, Any]]] = {}
        for r in rows:
            if r["status"] == "fresh":
                continue
            by_skill.setdefault(r["produced_by"], []).append(r)
        # Output in topological-ish order: skills that have NO stale upstream
        # come first. Cheap heuristic: sort by phase order if the skill is
        # known.
        SKILL_ORDER = [
            "prd-from-idea", "prd-to-tasks",
            "figma-to-design-md", "image-to-design-md",
            "design-md-to-app", "screenshot-to-page",
            "module-add",
        ]
        ordered = sorted(by_skill.keys(), key=lambda s: SKILL_ORDER.index(s) if s in SKILL_ORDER else 999)
        for skill in ordered:
            items = by_skill[skill]
            print(f"  {skill}:")
            for r in items:
                marker = {"self-drift": "✗", "upstream-stale": "⚠", "missing": "✗"}.get(r["status"], "?")
                print(f"    {marker} {r['path']}  ({r['status']})")
                if r["detail"]:
                    print(f"        {r['detail']}")
        print()
        print("Run the skills in the order shown — each one's outputs will refresh")
        print("the artifacts and clear the drift downstream.")

    if any_drift and args.exit_nonzero_on_drift:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
