#!/usr/bin/env python3
"""Show current `.workflow/` state and propose the next step.

Usage:
    python3 show_state.py <project-root>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PHASE_NEXT = {
    "empty":            "prd-from-idea (capture idea + draft PRD)",
    "idea_captured":    "prd-from-idea (expand PROJECT.md into PRD.md)",
    "prd_drafted":      "prd-to-tasks  OR  figma-to-design-md  OR  image-to-design-md  OR  design-md-to-app",
    "tasks_split":      "figma-to-design-md  OR  image-to-design-md  OR  design-md-to-app",
    "design_extracted": "design-md-to-app (scaffold the app)",
    "scaffolded":       "screenshot-to-page  OR  module-add",
    "page_generated":   "module-add  OR  more screenshot-to-page",
    "module-added":     "iterate — ask the user what's next",
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('project_root', type=Path)
    args = ap.parse_args()

    root = args.project_root.resolve()
    workflow = root / '.workflow'
    meta_path = workflow / 'meta.json'

    if not meta_path.exists():
        print(f"No .workflow/meta.json at {root}")
        print("Run init_workflow.py first, or this isn't a dev-flow project root.")
        return 1

    meta = json.loads(meta_path.read_text())
    print(f"Project:  {meta.get('project_name')!r}  ({meta.get('project_slug')!r})")
    print(f"Phase:    {meta.get('phase')}")
    print(f"Updated:  {meta.get('updated_at')}")
    stack = meta.get('stack') or {}
    stack_str = ", ".join(f"{k}={v}" for k, v in stack.items() if v) or "(undecided)"
    print(f"Stack:    {stack_str}")
    print()

    files = []
    for f in ('PROJECT.md', 'PRD.md', 'tasks.md', 'DESIGN.md'):
        if (workflow / f).exists():
            files.append(f"  ✓ {f}")
    sd = workflow / 'screenshots'
    if sd.exists():
        n = len(list(sd.glob('*')))
        files.append(f"  ✓ screenshots/ ({n} files)")
    pkg = root / 'package.json'
    if pkg.exists():
        files.append(f"  ✓ codebase scaffolded (package.json at project root)")
    if files:
        print("Files in .workflow/:")
        for f in files:
            print(f)
        print()

    history = meta.get('history') or []
    if history:
        print(f"Skill runs: {len(history)}")
        for h in history[-3:]:
            print(f"  - {h.get('skill')} @ {h.get('ran_at')}  → phase={h.get('phase_after')}")
        print()

    nxt = PHASE_NEXT.get(meta.get('phase'), "(unknown phase — treat as empty)")
    print(f"Next step proposal: {nxt}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
