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

# Next-step proposals per phase, keyed by `stack.framework`. Mirrors the routing tables
# in dev-flow/SKILL.md (§Stack-aware routing) — keep the two in sync.
# All phase keys are snake_case (contract §phase enum); legacy kebab-case is normalized below.
COMMON_NEXT = {
    "empty":            "prd-from-idea (capture idea + draft PRD)",
    "idea_captured":    "prd-from-idea (expand PROJECT.md into PRD.md)",
    "deployed":         "maintenance loop — re-run compliance-audit after material changes",
}

PHASE_NEXT_BY_STACK = {
    "next": {
        "prd_drafted":      "prd-to-tasks  OR  figma-to-design-md  OR  image-to-design-md  OR  design-md-to-app",
        "tasks_split":      "linear-scrum (Setup)  THEN  figma-to-design-md  OR  image-to-design-md  OR  design-md-to-app",
        "design_extracted": "design-md-to-app (scaffold the app)",
        "scaffolded":       "screenshot-to-page  OR  module-add",
        "page_generated":   "spec-review on the diff  THEN  module-add  OR  more screenshot-to-page",
        "module_added":     "spec-review  OR  write-tests  OR  iterate — set phase feature_complete when the build is done",
        "feature_complete": "gates: compliance-audit + vercel-doctor + shadscan  THEN  vercel-deploy",
    },
    "expo-rn": {
        "prd_drafted":      "prd-to-tasks  OR  image-to-design-md  OR  rn-bootstrap",
        "tasks_split":      "linear-scrum (Setup)  THEN  image-to-design-md  OR  rn-bootstrap",
        "design_extracted": "rn-bootstrap (scaffold the Expo app)",
        "scaffolded":       "rn-add-screen (UI)  OR  rn-module-add (auth/db/storage/realtime/push/payments)",
        "page_generated":   "spec-review on the diff  THEN  rn-module-add  OR  more rn-add-screen",
        "module_added":     "spec-review  OR  rn-write-tests  OR  iterate — set phase feature_complete when the build is done",
        "feature_complete": "gate: compliance-audit  THEN  rn-eas-deploy",
    },
    "monorepo": {
        "prd_drafted":      "prd-to-tasks  OR  figma-to-design-md  OR  image-to-design-md  OR  monorepo-bootstrap",
        "tasks_split":      "linear-scrum (Setup)  THEN  figma-to-design-md  OR  image-to-design-md  OR  monorepo-bootstrap",
        "design_extracted": "monorepo-bootstrap (turborepo + apps)",
        "monorepo_initialized": "monorepo-bootstrap continues (apps/web, apps/mobile, apps/agent)",
        "scaffolded":       "web: screenshot-to-page / module-add · mobile: rn-add-screen / rn-module-add · agent: eve-agent",
        "page_generated":   "spec-review  THEN  module-add / rn-module-add  OR  more screens",
        "module_added":     "spec-review  OR  monorepo-sync-types  OR  iterate — set phase feature_complete when the build is done",
        "feature_complete": "gates: compliance-audit (+ vercel-doctor, shadscan for web)  THEN  vercel-deploy + rn-eas-deploy",
    },
    "agent": {
        "prd_drafted":      "eve-agent (bootstrap — agent at the repo root, no web app)",
        "tasks_split":      "linear-scrum (Setup)  THEN  eve-agent (bootstrap)",
        "scaffolded":       "eve-agent (capability mode)  OR  eve-registry-porting",
        "module_added":     "eve-agent (capability mode) — set phase feature_complete when the build is done",
        "feature_complete": "gate: compliance-audit  THEN  eve deploy",
    },
}

# Legacy aliases still found in older meta.json files.
PHASE_ALIASES = {"module-added": "module_added", "page-generated": "page_generated", "design-extracted": "design_extracted"}


def next_step(phase: str | None, framework: str | None) -> str:
    phase = PHASE_ALIASES.get(phase or "", phase or "")
    if phase in COMMON_NEXT:
        return COMMON_NEXT[phase]
    fw = framework or "next"
    table = PHASE_NEXT_BY_STACK.get(fw)
    if table is None:
        return f"(stack.framework={fw!r} is not recognized — dev-flow refuses to guess; ask the user which stack)"
    if phase in table:
        return table[phase]
    return "(unknown phase — treat as empty: prd-from-idea)"


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

    framework = stack.get('framework')
    nxt = next_step(meta.get('phase'), framework)
    print(f"Next step proposal ({framework or 'next, default'}): {nxt}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
