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

sys.path.insert(0, str(Path(__file__).resolve().parent))
import meta_io  # noqa: E402 — reads meta.json, refusing an invalid one with exit 2
import surfaces  # noqa: E402 — what the project is made of, the one place that decides it
import phases  # noqa: E402 — the phase enum and its aliases, shared with update_meta.py

# Next-step proposals per phase, keyed by `stack.framework`: THE routing table. dev-flow/SKILL.md
# §Stack-aware routing does not restate it — scripts/sync_routing_table.py renders this dict into it, and
# CI fails if the rendered copy is stale. It used to be a second, hand-kept table, and the two had drifted:
# the prose sent expo-rn to rn-bootstrap before the wireframes, this file sent next/expo-rn/monorepo to the
# scaffold straight from prd_drafted (which the wireframe gate refuses), and the agent stack had a
# module_added row for a phase the contract says it never reaches.
# All phase keys are snake_case (contract §phase enum); legacy kebab-case is normalized below.
COMMON_NEXT = {
    "empty":            "ask the user which kind of project this is — a product to sell whose market is not settled → founder-intelligence (the full check before any PRD); a prototype, internal tool, refactor or decided product → inventory first (references/before-you-build.md, inventory.py scan)  THEN  prd-from-idea",
    "idea_captured":    "prd-from-idea (expand PROJECT.md into PRD.md) — the inventory first if PROJECT.md has no 'what exists already'; if the user has not chosen yet, ask the user whether a full check (founder-intelligence) should come first",
}

PHASE_NEXT_BY_STACK = {
    "next": {
        "prd_drafted":      "prd-to-tasks  OR  figma-to-design-md / image-to-design-md / a hand-written DESIGN.md  THEN  wireframe-canvas  THEN  design-md-to-app",
        "tasks_split":      "linear-scrum (Setup)  THEN  figma-to-design-md / image-to-design-md  THEN  wireframe-canvas  THEN  design-md-to-app",
        "design_extracted": "wireframe-canvas (every screen, desktop + phone, approved)  THEN  design-md-to-app",
        "scaffolded":       "primitives guard check (setup_design_lint.py --check)  THEN  screenshot-to-page  OR  module-add (project-infra-setup first if the account does not exist)",
        "page_generated":   "spec-review on the diff (whenever work lands, whatever the phase)  THEN  module-add  OR  more screenshot-to-page  ·  app-verification create once (a manual to prove features on the real app)",
        "module_added":     "spec-review  OR  write-tests  OR  iterate — set phase feature_complete when the build is done",
        "feature_complete": "app-verification maintain  THEN  gates: compliance-audit + vercel-doctor + shadscan + launch-audit + app-security  THEN  vercel-deploy",
        "deployed":         "maintenance loop — re-run compliance-audit + vercel-doctor + shadscan + launch-audit + app-security after material changes",
    },
    "expo-rn": {
        "prd_drafted":      "prd-to-tasks  OR  image-to-design-md  THEN  wireframe-canvas  THEN  rn-bootstrap",
        "tasks_split":      "linear-scrum (Setup)  THEN  image-to-design-md  THEN  wireframe-canvas  THEN  rn-bootstrap",
        "design_extracted": "wireframe-canvas (every screen, desktop + phone, approved)  THEN  rn-bootstrap",
        "scaffolded":       "rn-add-screen (UI)  OR  rn-module-add (auth/db/storage/realtime/push/payments)",
        "page_generated":   "spec-review on the diff  THEN  rn-module-add  OR  more rn-add-screen  ·  app-verification create once",
        "module_added":     "spec-review  OR  rn-write-tests  OR  iterate — set phase feature_complete when the build is done",
        "feature_complete": "app-verification maintain  THEN  gates: compliance-audit + app-security (dependencies, secrets, the mobile checklist)  THEN  rn-eas-deploy",
        "deployed":         "maintenance loop — rn-add-screen for features, rn-eas-build-submit-update for OTA hotfixes, compliance-audit + app-security after material changes",
    },
    "monorepo": {
        "prd_drafted":      "prd-to-tasks  OR  figma-to-design-md / image-to-design-md  THEN  wireframe-canvas  THEN  monorepo-bootstrap",
        "tasks_split":      "linear-scrum (Setup)  THEN  figma-to-design-md / image-to-design-md  THEN  wireframe-canvas  THEN  monorepo-bootstrap",
        "design_extracted": "wireframe-canvas (every screen, desktop + phone, approved)  THEN  monorepo-bootstrap",
        "monorepo_initialized": "monorepo-bootstrap continues (design-md-to-app in apps/web, rn-bootstrap in apps/mobile)",
        "scaffolded":       "web: primitives guard check THEN screenshot-to-page / module-add · mobile: rn-add-screen / rn-module-add · agent: eve-agent · shared: monorepo-add-shared-package / monorepo-sync-types",
        "page_generated":   "spec-review  THEN  module-add / rn-module-add  OR  more screens  ·  app-verification create once per app",
        "module_added":     "spec-review  OR  monorepo-sync-types  OR  iterate — set phase feature_complete when the build is done",
        "feature_complete": "app-verification maintain  THEN  gates: compliance-audit + app-security (+ vercel-doctor, shadscan, launch-audit for web)  THEN  vercel-deploy + rn-eas-deploy + eve deploy, as apply",
        "deployed":         "maintenance loop on every side — the web gates, rn-eas-build-submit-update, compliance-audit + app-security after material changes",
    },
    "agent": {
        "prd_drafted":      "eve-agent (bootstrap — agent at the repo root, no web app; bumps phase to scaffolded)",
        "tasks_split":      "linear-scrum (Setup)  THEN  eve-agent (bootstrap)",
        "scaffolded":       "eve-agent (capability mode)  OR  eve-registry-porting  ·  app-verification create once — set phase feature_complete when the build is done",
        "feature_complete": "app-verification maintain  THEN  gates: compliance-audit + app-security  THEN  eve deploy",
        "deployed":         "maintenance loop — more capabilities (eve-agent), compliance-audit + app-security after material changes",
    },
}

def routing_phase(raw: object) -> str:
    """The phase to route on: aliases read as their canonical name, and anything that is not a phase as
    `empty` (contract: an unknown value must not crash and routes as `empty`). A missing phase is ''."""
    if not raw:
        return ''
    return phases.normalize(raw) if phases.index(raw) is not None else 'empty'


# dev-flow/references/contracts.md §stack — keep the two in step.
# The canonical order of the test layers. A fixed list of whole strings was the first shape and it
# was wrong: the first project to add a layer would have been told its honest value was invalid.
TEST_LAYERS = ('vitest', 'jest-expo', 'rntl', 'playwright', 'maestro', 'e2e')


def test_layers_ok(value) -> bool:
    """Known layers, in canonical order, no repeats — an array or a typo fails, a legitimate
    combination does not."""
    if not isinstance(value, str) or not value:
        return False
    parts = value.split('+')
    if len(set(parts)) != len(parts) or any(p not in TEST_LAYERS for p in parts):
        return False
    order = [TEST_LAYERS.index(p) for p in parts]
    return order == sorted(order)
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


PRE_CODE_PHASES = set(phases.before('scaffolded')) | {''}
SKIP_DIRS = {'node_modules', '.next', '.git', '.turbo', 'dist', 'build', '.expo'}


def app_code(root: Path) -> tuple[int, int]:
    """(routes, components) already written: page/layout files under an `app/` dir, and .tsx/.jsx under a
    `components/` dir outside the vendored primitives. Root, src/ and apps/* (monorepo) are all looked at."""
    bases = [root, root / 'src', *sorted(root.glob('apps/*')), *sorted(root.glob('apps/*/src'))]
    routes = components = 0
    for b in bases:
        for kind in ('app', 'components'):
            d = b / kind
            if not d.is_dir():
                continue
            for f in d.rglob('*'):
                if f.suffix not in {'.tsx', '.jsx'} or SKIP_DIRS & set(f.relative_to(root).parts):
                    continue
                if kind == 'app' and f.stem in {'page', 'layout'}:
                    routes += 1
                elif kind == 'components' and 'ui' not in f.relative_to(d).parts[:1]:
                    components += 1
    return routes, components


def phase_behind_code(meta: dict, root: Path) -> tuple[int, int] | None:
    """The phase says nothing is built yet, but the app has routes or components. dev-flow proposes
    spec-review, shadscan and the gates only from `page_generated` on, so a phase left behind silently
    switches every check off — smart-travel was at `design_extracted` through three days of building and
    238 hand-made elements. Returns the counts when that is the case."""
    phase = routing_phase(meta.get('phase'))
    fw = (meta.get('stack') or {}).get('framework')
    if phase not in PRE_CODE_PHASES or fw == 'agent':
        return None
    routes, components = app_code(root)
    return (routes, components) if routes or components else None


def next_step(phase: object, framework: str | None) -> str:
    phase = routing_phase(phase) or 'empty'
    if phase in COMMON_NEXT:
        return COMMON_NEXT[phase]
    fw = framework or "next"
    table = PHASE_NEXT_BY_STACK.get(fw)
    if table is None:
        return f"(stack.framework={fw!r} is not recognized — dev-flow refuses to guess; ask the user which stack)"
    if phase in table:
        return table[phase]
    # A real phase this stack does not pass through (agent-only has no page_generated, a single app no
    # monorepo_initialized). It used to say "unknown phase — treat as empty: prd-from-idea", which sent a
    # built project back to the PRD.
    return (f"(no step for {phase!r} on stack {fw!r} — this stack does not pass through it; "
            "check the phase with the user before moving on)")


# The founder path (founder-intelligence) is optional: dev-flow must route without the skill installed, so its
# labels are borrowed from founder.py when it sits beside dev-flow, and the raw fields are shown otherwise.
FOUNDER_SCRIPT = Path(__file__).resolve().parents[2] / "founder-intelligence" / "scripts" / "founder.py"
FOUNDER_DECISIONS = ("pending", "approved", "approved_experiment", "revise", "stop", "bypassed")


# app-verification: what counts as a change the manual must follow, and where there is first something to drive
MATERIAL_SKILLS = {"module-add", "screenshot-to-page", "rn-add-screen", "rn-module-add", "eve-agent"}


def verification_line(meta: dict, root: Path) -> str | None:
    """A note when a project that has something to drive has no verification manual, or one older than the last
    material change. None when there is nothing to say."""
    framework = (meta.get("stack") or {}).get("framework")
    first = "scaffolded" if framework == "agent" else "page_generated"
    phase = routing_phase(meta.get("phase"))
    if phase not in phases.PHASES or phases.PHASES.index(phase) < phases.PHASES.index(first):
        return None
    found = surfaces.surfaces(root, meta)
    missing = [s for s in found if not (root / ".claude" / "skills" / f"verify-{s.name}" / "SKILL.md").is_file()]
    if not found and not isinstance(meta.get("verification"), dict) \
            and not any((root / ".claude" / "skills").glob("verify-*/SKILL.md")):
        missing = [surfaces.Surface("web", "web", ".")]
    if missing:   # one manual per surface the project has (surfaces.py)
        names = ", ".join(f"verify-{s.name} ({s.kind}" + (f", served by {s.mounted_in})" if s.mounted_in else ")")
                          for s in missing)
        return (f"Verification: missing manual for {names} — app-verification create (how to launch, drive and "
                "prove each surface, written once into .claude/skills/)")
    names = {s.name for s in found}
    skills = root / ".claude" / "skills"
    gone = sorted(d.name for d in skills.glob("verify-*") if (d / "SKILL.md").is_file()
                  and d.name[len("verify-"):] not in names) if found and skills.is_dir() else []
    if gone:   # a renamed or removed surface: the filled manual is the valuable part, say where it is
        return (f"Verification: {', '.join(gone)} — no surface by that name any more (renamed or removed?); move "
                "what it says into the new surface's manual, then delete it")
    block = meta.get("verification")
    if not isinstance(block, dict):
        return ("Verification: the manual is written but not proven (no meta.json#verification) — a manual never "
                "run is a draft: prove it live, then `verify_map.py record` (app-verification)")
    seen = block.get("maintained_at") or block.get("proven_at") or ""
    changes = [h for h in meta.get("history") or [] if isinstance(h, dict) and h.get("skill") in MATERIAL_SKILLS
               and str(h.get("ran_at") or "") > seen]
    if not changes:
        return None
    last = max(changes, key=lambda h: str(h.get("ran_at")))
    return (f"Verification: the manual predates the last change ({last.get('skill')} at {last.get('ran_at')}) — "
            "app-verification maintain")


def founder_labels(founder: dict) -> list[str] | None:
    if not FOUNDER_SCRIPT.is_file():
        return None
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("founder_for_show_state", FOUNDER_SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        if str(FOUNDER_SCRIPT.parent) not in sys.path:  # founder.py imports its own meta_io copy; add the folder once
            sys.path.insert(0, str(FOUNDER_SCRIPT.parent))
        spec.loader.exec_module(mod)
        return mod.labels(founder)
    except Exception:  # an installed copy that does not load must not break routing
        return None


def founder_line(founder: object) -> str:
    if not isinstance(founder, dict):
        return "meta.json#founder is not an object — run founder-intelligence/scripts/founder.py status"
    raw = (f"{founder.get('mode')} · research {founder.get('research')} · decision {founder.get('decision')}"
           f" · Playbook v{founder.get('version', 0)}")
    found = founder_labels(founder)
    return raw + (f" · {' · '.join(found)}" if found else "")


def founder_step(meta: dict, root: Path) -> str | None:
    """The proposal when the founder path decides what comes next; None to route as the phase table says."""
    founder = meta.get("founder")
    if founder is None:
        return None
    script = "founder-intelligence/scripts/founder.py"
    if not isinstance(founder, dict) or founder.get("decision") not in FOUNDER_DECISIONS:
        return f"fix meta.json#founder first ({script} status {root} says what is wrong)"
    decision, playbook = founder["decision"], founder.get("playbook") or ".workflow/founder/founder-playbook.md"
    if decision == "bypassed":
        return None
    if decision == "stop":
        return (f"nothing — the founder stopped this project ({founder.get('reason') or 'no reason recorded'}). "
                f"To reopen: python3 {script} start {root} --mode {founder.get('mode', 'new')}")
    if decision == "pending" and founder.get("research") == "complete":
        return (f"present the Playbook to the founder — conclusions, the strongest evidence against, the open "
                f"hypotheses, the recommendation and its alternatives — and record their decision: "
                f"{script} approve | decide | bypass {root}. The founder decides; dev-flow waits")
    if decision in ("pending", "revise"):
        what = "review and the proposals in handoff.md" if founder.get("mode") == "existing" else "Playbook"
        return (f"founder-intelligence — continue the {what} ({script} status {root}); "
                "dev-flow waits for the founder's decision")
    if founder.get("mode") == "existing":
        return (f"apply the proposals the founder accepted in .workflow/founder/handoff.md — prd-from-idea for the "
                f"PRD, prd-to-tasks for new tasks — then continue: {next_step(meta.get('phase'), (meta.get('stack') or {}).get('framework'))}")
    if (phases.index(routing_phase(meta.get("phase")) or "empty") or 0) >= phases.index("prd_drafted"):
        return None
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import founder_gate

    passed, why = founder_gate.verify(root, meta)
    if not passed:  # what set-phase prd_drafted would refuse: say it now, before a whole PRD is written
        return (f"the approval no longer holds ({why.splitlines()[0]}) — show the founder the current Playbook and "
                f"record their decision again: {script} approve {root} --user-said \"<their words>\"")
    scope = (" (limited to the approved experiment: founder.experiment)"
             if decision == "approved_experiment" else "")
    return (f"prd-from-idea, from the approved Playbook ({playbook}){scope} — the decisions it marks as locked "
            "go into PROJECT.md / PRD.md unchanged; the open hypotheses into §Open questions")


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

    meta = meta_io.load_or_exit(meta_path)
    print(f"Project:  {meta.get('project_name')!r}  ({meta.get('project_slug')!r})")
    print(f"Phase:    {meta.get('phase')}")
    if meta_io.edited_outside(meta):
        print("⚠ meta.json was changed outside dev-flow's scripts since they last wrote it (its meta_digest no longer")
        print("  matches). That is allowed; it means nothing checked the edit.")
    checked = meta_io.checked_phase(meta)
    if (phases.index(meta.get('phase')) or 0) > (phases.index(checked) if phases.index(checked) is not None else 99):
        print(f"⚠ phase {meta.get('phase')!r} was set without the gates — the last phase they checked is {checked!r}.")
        print(f"  The next set-phase checks them from {checked!r}.")
    if (meta.get('contract_version') or 0) > meta_io.CONTRACT_VERSION:
        print(f"⚠ meta.json was written under a newer contract (version {meta['contract_version']}; this dev-flow "
              f"knows {meta_io.CONTRACT_VERSION}). Update the dev-flow skills before any script writes it.")
    if meta.get('phase') and phases.index(meta.get('phase')) is None:
        print(f"⚠ {meta.get('phase')!r} is not a phase of the contract — routed as 'empty'. update_meta.py refuses to")
        print(f"  move it without --allow-regress; valid phases: {', '.join(phases.PHASES)}")
    print(f"Updated:  {meta.get('updated_at')}")
    stack = meta.get('stack') or {}
    stack_str = ", ".join(f"{k}={v}" for k, v in stack.items() if v) or "(undecided)"
    print(f"Stack:    {stack_str}")
    if meta.get('founder') is not None:  # absent or null: the direct path, as founder.py and the gate read it
        print(f"Founder:  {founder_line(meta['founder'])}")
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
    phase_norm = routing_phase(meta.get('phase'))
    behind = phase_behind_code(meta, root)
    if behind:
        routes, components = behind
        print(f"⚠⚠ PHASE BEHIND THE CODE: phase is {phase_norm or '(none)'!r}, but the app already has "
              f"{routes} route file(s) and {components} component(s).")
        print("  No check is being proposed: spec-review, shadscan and the phase gates (design lint, primitives")
        print("  guard) start from page_generated. Nothing has verified the code written so far.")
        print("  Realign before building more (see the proposal at the bottom).")
        print()
    if phase_norm not in PRE_CODE_PHASES or behind:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import data_residency_gate
        import design_lint_gate
        import primitives_guard_gate
        import registry_intake_gate
        import wireframes_gate

        passed, why = data_residency_gate.verify(root, meta)
        if passed and ("⚠" in why or "⚑" in why):
            print("⚑ Data residency — flagged, not blocking:")
            for line in why.splitlines()[1:]:
                print(f"  {line}")
            print()
        for gate, what in ((data_residency_gate, "Data-residency decision"),
                           (design_lint_gate, "Design lint"),
                           (primitives_guard_gate, "PRIMITIVES GUARD (golden rule 3 — hand-made UI is not blocked)"),
                           (registry_intake_gate, "Registry intake"),
                           (wireframes_gate, "Wireframe canvas approval")):
            passed, why = gate.verify(root, meta)
            if not passed:
                print(f"⚠ {what} missing on a project with code:" if behind else
                      f"⚠ {what} missing on a scaffolded project:")
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
    if test is not None and not test_layers_ok(test):
        shape = 'an array' if isinstance(test, list) else f'{type(test).__name__} {test!r}'
        print(f"⚠ stack.test is {shape} — expected the layers {' · '.join(TEST_LAYERS)} "
              "joined by `+`, in that order, no repeats")
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

    if (note := verification_line(meta, root)):
        print(note)
        print()

    framework = stack.get('framework')
    nxt = founder_step(meta, root) or next_step(meta.get('phase'), framework)
    if behind:
        here = Path(__file__).resolve().parent
        dmta = here.parents[1] / 'design-md-to-app' / 'scripts' / 'setup_design_lint.py'
        nxt = ("REALIGN THE PHASE before anything else —\n"
               f"  1. retrofit golden rule 3 (lint rule + write-time guard + AGENTS.md, one command): python3 {dmta} {root}\n"
               f"  2. python3 {here / 'update_meta.py'} {root} set-phase page_generated   (module_added if modules are wired)\n"
               "  3. spec-review on everything built so far (Standards axis: golden rule 3) + shadscan, then resume")
    print(f"Next step proposal ({framework or 'next, default'}): {nxt}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
