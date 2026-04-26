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

By default the command exits 0 with a status table. Pass `--exit-nonzero-on-drift`
in CI to fail builds when drift is present.

The command makes no changes — it's diagnostic. The intended workflow is:
  $ python3 check_drift.py <project-root>
  $ # Read the table, decide what to re-run.

Future (Sprint 5): `check_drift.py --plan` will produce a migration plan
("re-run design-md-to-app with --refresh registry,showcase").

Usage:
    python3 check_drift.py <project-root> [--exit-nonzero-on-drift]
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

    rows = []
    any_drift = False

    for rel_path, entry in artifacts.items():
        abs_path = (root / rel_path).resolve()
        recorded_sha = entry.get("sha256")
        produced_by = entry.get("produced_by", "?")

        if not abs_path.exists():
            rows.append({
                "path": rel_path,
                "produced_by": produced_by,
                "status": "missing",
                "detail": "file no longer exists on disk",
            })
            any_drift = True
            continue

        on_disk_sha = sha256_file(abs_path)
        if on_disk_sha != recorded_sha:
            rows.append({
                "path": rel_path,
                "produced_by": produced_by,
                "status": "self-drift",
                "detail": f"recorded {recorded_sha[:8]} vs on-disk {on_disk_sha[:8]}",
            })
            any_drift = True
            continue

        # Self matches — check upstream dependencies.
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
            rows.append({
                "path": rel_path,
                "produced_by": produced_by,
                "status": "upstream-stale",
                "detail": "; ".join(upstream_stale),
            })
            any_drift = True
        else:
            rows.append({
                "path": rel_path,
                "produced_by": produced_by,
                "status": "fresh",
                "detail": "",
            })

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

    if any_drift and args.exit_nonzero_on_drift:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
