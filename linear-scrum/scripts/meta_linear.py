#!/usr/bin/env python3
"""meta_linear.py — upsert the `linear` and `scrum` blocks of .workflow/meta.json.

Pure dict transforms (unit-testable) plus a thin CLI. Linear is the source of
truth after setup; these helpers only track the mapping + config on our side.
issue_map is keyed by task_key(), so merges are naturally duplicate-free.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_STATES = {
    "backlog": "Backlog", "todo": "Todo", "in_progress": "In Progress",
    "in_review": "In Review", "done": "Done", "blocked_label": "blocked",
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def upsert_linear(meta: dict, *, team_id: str, team_name: str,
                  project_id: str, url: str) -> dict:
    block = meta.get("linear", {})
    block.update({
        "team_id": team_id, "team_name": team_name,
        "project_id": project_id, "url": url,
        "issue_map": block.get("issue_map", {}),
        "last_synced_at": _now(),
    })
    meta["linear"] = block
    return meta


def record_issues(meta: dict, mapping: dict) -> dict:
    block = meta.setdefault("linear", {})
    im = block.setdefault("issue_map", {})
    im.update(mapping)                 # dict keyed by task_key → no duplicates
    block["last_synced_at"] = _now()
    return meta


def ensure_scrum(meta: dict, *, cadence_weeks: int = 2,
                 estimate_scale: str = "fibonacci") -> dict:
    s = meta.get("scrum", {})
    s.setdefault("cadence_weeks", cadence_weeks)
    s.setdefault("estimate_scale", estimate_scale)
    s.setdefault("velocity_target", None)
    s.setdefault("states", dict(DEFAULT_STATES))
    meta["scrum"] = s
    return meta


def _load(p: Path) -> dict:
    return json.loads(p.read_text())


def _save(p: Path, meta: dict) -> None:
    p.write_text(json.dumps(meta, indent=2) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("meta_path")
    sub = ap.add_subparsers(dest="op", required=True)

    ln = sub.add_parser("upsert-linear")
    for f in ("team-id", "team-name", "project-id", "url"):
        ln.add_argument(f"--{f}", required=True)

    ri = sub.add_parser("record-issues")
    ri.add_argument("--mapping", required=True, help="JSON object key->identifier")

    sub.add_parser("ensure-scrum")

    args = ap.parse_args()
    p = Path(args.meta_path)
    meta = _load(p)
    if args.op == "upsert-linear":
        meta = upsert_linear(meta, team_id=args.team_id, team_name=args.team_name,
                             project_id=args.project_id, url=args.url)
        meta = ensure_scrum(meta)
    elif args.op == "record-issues":
        meta = record_issues(meta, json.loads(args.mapping))
    elif args.op == "ensure-scrum":
        meta = ensure_scrum(meta)
    _save(p, meta)


if __name__ == "__main__":
    main()
