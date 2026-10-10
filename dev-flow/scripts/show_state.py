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
        "design_extracted": "wireframe-canvas (every screen, desktop + phone, approved)  THEN  design-md-to-app",
        "scaffolded":       "screenshot-to-page  OR  module-add",
        "page_generated":   "spec-review on the diff  THEN  module-add  OR  more screenshot-to-page",
        "module_added":     "spec-review  OR  write-tests  OR  iterate — set phase feature_complete when the build is done",
        "feature_complete": "gates: compliance-audit + vercel-doctor + shadscan + launch-audit  THEN  vercel-deploy",
    },
    "expo-rn": {
        "prd_drafted":      "prd-to-tasks  OR  image-to-design-md  OR  rn-bootstrap",
        "tasks_split":      "linear-scrum (Setup)  THEN  image-to-design-md  OR  rn-bootstrap",
        "design_extracted": "wireframe-canvas (every screen, desktop + phone, approved)  THEN  rn-bootstrap",
        "scaffolded":       "rn-add-screen (UI)  OR  rn-module-add (auth/db/storage/realtime/push/payments)",
        "page_generated":   "spec-review on the diff  THEN  rn-module-add  OR  more rn-add-screen",
        "module_added":     "spec-review  OR  rn-write-tests  OR  iterate — set phase feature_complete when the build is done",
        "feature_complete": "gate: compliance-audit  THEN  rn-eas-deploy",
    },
    "monorepo": {
        "prd_drafted":      "prd-to-tasks  OR  figma-to-design-md  OR  image-to-design-md  OR  monorepo-bootstrap",
        "tasks_split":      "linear-scrum (Setup)  THEN  figma-to-design-md  OR  image-to-design-md  OR  monorepo-bootstrap",
        "design_extracted": "wireframe-canvas (every screen, desktop + phone, approved)  THEN  monorepo-bootstrap",
        "monorepo_initialized": "monorepo-bootstrap continues (apps/web, apps/mobile, apps/agent)",
        "scaffolded":       "web: screenshot-to-page / module-add · mobile: rn-add-screen / rn-module-add · agent: eve-agent",
        "page_generated":   "spec-review  THEN  module-add / rn-module-add  OR  more screens",
        "module_added":     "spec-review  OR  monorepo-sync-types  OR  iterate — set phase feature_complete when the build is done",
        "feature_complete": "gates: compliance-audit (+ vercel-doctor, shadscan, launch-audit for web)  THEN  vercel-deploy + rn-eas-deploy",
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


# dev-flow/references/contracts.md §stack — keep the two in step.
TEST_VALUES = {'vitest', 'vitest+playwright', 'jest-expo+rntl', 'jest-expo+rntl+maestro'}
LINT_VALUES = {'eslint', 'biome', 'eslint+biome'}


def linters_present(root: Path) -> set[str]:
    """What the repository actually runs, read from dependencies and config files.

    ⚠️ Looks in `apps/*` and `packages/*` as well as the root: in a monorepo the toolchain lives in
    the workspaces, and a root-only scan reported six healthy projects as having no linter at all."""
    found: set[str] = set()
    roots = [root, *sorted(root.glob('apps/*')), *sorted(root.glob('packages/*'))]
    for d in roots:
        pkg = d / 'package.json'
        if pkg.exists():
            try:
                data = json.loads(pkg.read_text())
            except json.JSONDecodeError:
                data = {}
            deps = {**(data.get('devDependencies') or {}), **(data.get('dependencies') or {})}
            if 'eslint' in deps:
                found.add('eslint')
            if any('biome' in k for k in deps):
                found.add('biome')
        if any((d / f).exists() for f in ('eslint.config.mjs', 'eslint.config.js', 'eslint.config.ts', '.eslintrc.json')):
            found.add('eslint')
        if any((d / f).exists() for f in ('biome.json', 'biome.jsonc')):
            found.add('biome')
    return found


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

    # A project already at or past `scaffolded` without the design lint — it predates the gate,
    # or its phase was edited by hand. Not blocking here; set-phase blocks the transition.
    phase_norm = PHASE_ALIASES.get(meta.get('phase') or '', meta.get('phase') or '')
    if phase_norm not in {'empty', 'idea_captured', 'prd_drafted', 'tasks_split',
                          'design_extracted', 'monorepo_initialized', ''}:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import data_residency_gate
        import design_lint_gate
        import registry_intake_gate
        import wireframes_gate

        passed, why = data_residency_gate.verify(root, meta)
        if passed and ("⚠" in why or "⚑" in why):
            print("⚑ Data residency — flagged, not blocking:")
            for line in why.splitlines()[1:]:
                print(f"  {line}")
            print()
        for gate, what in ((data_residency_gate, "Data-residency decision"),
                           (design_lint_gate, "Design lint"), (registry_intake_gate, "Registry intake"),
                           (wireframes_gate, "Wireframe canvas approval")):
            passed, why = gate.verify(root, meta)
            if not passed:
                print(f"⚠ {what} missing on a scaffolded project:")
                for line in why.splitlines():
                    print(f"  {line}")
                print(gate.remedy(root))
                print()

    # Approved but not yet on the tracker: the second half of the wireframe step. Informs, never blocks.
    wf = meta.get('wireframes') or {}
    if wf.get('approved_by_user') is True and not wf.get('screenshots_posted_at'):
        print("⚑ Wireframes approved but the screenshots are not on the issues yet:")
        print("  render every artboard to docs/wireframes/png/, comment them on each issue whose story maps")
        print("  to the screen (wireframe-canvas §After approval), then: wireframes.py posted <root>")
        print()

    # `stack.test` was free text until 2026-10-10 and drifted into four spellings across eleven
    # projects, one of them an array. `write-tests` reads it as the NAME of a framework, so a
    # value outside the enum fails silently: no error, just tests written in whatever style the
    # sibling files happen to use. Reported, never blocking — a project may ship untested.
    test = stack.get('test')
    # `in` against a set raises on a list, which is the very value this check is here to catch.
    if test is not None and not (isinstance(test, str) and test in TEST_VALUES):
        shape = 'an array' if isinstance(test, list) else f'{type(test).__name__} {test!r}'
        print(f"⚠ stack.test is {shape} — not one of {', '.join(sorted(TEST_VALUES))}")
        print("  write-tests reads this as a framework name; an unknown value picks no patterns.")
        print("  The enum is dev-flow/references/contracts.md §stack.")
        print()

    # `stack.lint` is a cache of what the repository runs, and a cache nothing checks goes stale:
    # surveyed 2026-10-10, it was declared in two projects out of 36 and wrong in both.
    lint = stack.get('lint')
    if lint is not None:
        if not (isinstance(lint, str) and lint in LINT_VALUES):
            print(f"⚠ stack.lint is {lint!r} — not one of {', '.join(sorted(LINT_VALUES))}")
            print()
        elif (present := linters_present(root)) and set(lint.split('+')) != present:
            print(f"⚠ stack.lint says {lint}, the repository runs {'+'.join(sorted(present))}")
            print("  The repository is the truth; the key is a cache of it (contracts.md §stack).")
            print()
    # @shadcn/lint is an ESLint plugin, so a biome-only project cannot run the design lint.
    if stack.get('design_lint') == 'shadcn-lint' and (present := linters_present(root)) and 'eslint' not in present:
        print("⚠ design_lint is shadcn-lint but the project has no ESLint — @shadcn/lint is an ESLint")
        print("  plugin, so the declared design lint cannot run. Add ESLint, or record design_lint")
        print("  \"none\" with stack_config.design_lint_reason.")
        print()

    framework = stack.get('framework')
    nxt = next_step(meta.get('phase'), framework)
    print(f"Next step proposal ({framework or 'next, default'}): {nxt}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
