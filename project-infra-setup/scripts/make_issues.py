#!/usr/bin/env python3
"""make_issues.py — moved: GitHub issues are now created by the `scrum` skill.

    make_issues.py --repo OWNER/NAME --tasks .workflow/tasks.md --map <ignored> [--footer T] [--pause S] [--dry-run]

Kept so existing commands keep working: it runs `scrum/scripts/github_sync.py` on the project that owns the
tasks.md. The issue map now lives in meta.json#tracker.issue_map, keyed by task_key — `--map` is ignored (an old
title-keyed file is folded in by `scrum/scripts/meta_tracker.py migrate`). The parsing and label helpers are
re-exported for the callers that import them.
"""
import argparse
import sys
from pathlib import Path

SCRUM = Path(__file__).resolve().parents[2] / "scrum" / "scripts"
sys.path.insert(0, str(SCRUM))
from github_sync import area_label, body_of, main as sync_main, parse, type_of  # noqa: E402,F401


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--repo", required=True)
    ap.add_argument("--tasks", required=True)
    ap.add_argument("--map", dest="map_path")
    ap.add_argument("--footer", default="")
    ap.add_argument("--pause", type=float, default=2.0)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    root = Path(a.tasks).resolve().parent.parent
    print(f"make_issues.py has moved: running {SCRUM / 'github_sync.py'} {root} --repo {a.repo}", file=sys.stderr)
    args = [str(root), "--repo", a.repo, "--pause", str(a.pause), "--footer", a.footer]
    return sync_main(args + (["--dry-run"] if a.dry_run else []))


if __name__ == "__main__":
    sys.exit(main())
