# dev-flow's bundled scripts

The full reference; `SKILL.md` §Bundled scripts lists them one line each.
Moved out of `dev-flow/SKILL.md` on 2026-10-17 to cut the router's every-turn cost; SKILL.md keeps an
index line pointing here. The text is unchanged.

- `scripts/init_workflow.py <project-root> [--name "Project Name"]` — creates `.workflow/` with a fresh `meta.json`. Use when the user opts into the orchestrator on an empty directory.
- `scripts/show_state.py <project-root>` — prints the current `phase`, the files present, and the proposed next step. Use early in every conversation when the user asks "what's next". On a project already at or past `scaffolded` without the design lint, the **primitives guard**, registry intake or an approved wireframe canvas — it predates the gates, or its phase was edited by hand — it prints what is missing and the command that fixes it. **When the app already has routes or components but the phase is still before `scaffolded`, it prints PHASE BEHIND THE CODE**, shows the gates anyway, and replaces the proposal with the realignment (retrofit → `set-phase page_generated` → `spec-review` + `shadscan`). When you see either warning, run the fix before proposing the next step. Projects started before the guard existed get it with one command, `design-md-to-app/scripts/setup_design_lint.py <root>` (lint rule + guard + AGENTS.md section); show_state proposes it, nothing installs it unasked.
- `scripts/update_meta.py <project-root> <op>` — mutate `meta.json` from a skill. Three operations:
  - `record-artifact --path <p> --produced-by <skill> [--derived-from <p1> <p2> …]` — hash a file and record it under `meta.json#artifacts`. Skills call this after writing/updating contract files (DESIGN.md, registry.json, generated pages, schema, etc).
  - `set-phase <phase> [--skill <name>]` — bump phase forward (refuses regression unless `--allow-regress`)
    and record the change in `history` (`action: "set-phase"`; a reset carries `allow_regress: true`). **Also the
    design-lint gate**: moving a Next web app on a Tailwind UI (shadcn, base-ui, coss) into
    `scaffolded` is refused until `design-md-to-app/scripts/setup_design_lint.py --check` passes, or an
    opt-out is recorded — `stack.design_lint = "none"` with `stack_config.design_lint_reason`. Mobile,
    agent-only and MUI projects are not affected. **And the registry-intake gate** at the same
    crossing: a Next app on a Tailwind UI or an eve agent needs `registry-intake/scripts/registry_intake.py
    check` to pass (lock, hook, nothing installed around them), or `stack.registry_intake = "none"` with
    `stack_config.registry_intake_reason`. **And the wireframe gate**, one step earlier for a monorepo:
    crossing into `monorepo_initialized` or `scaffolded` needs `meta.json#wireframes` approved by the user
    (`wireframe-canvas`), or skipped with a reason — every stack except agent-only (`scripts/wireframes_gate.py`).
    **And the primitives-guard gate (golden rule 3) at
    `scaffolded` and every later phase**: a Next web app on a Tailwind UI needs `design/no-handmade-ui` at
    `error` in the preset and the write-time guard installed (`scripts/primitives_guard_gate.py`, which runs
    `design-md-to-app/scripts/setup_primitives_guard.py --check`), or `stack.primitives_guard = "none"` with
    `stack_config.primitives_guard_reason`; from then on the design-lint gate is re-checked at every phase
    change too. Skills move phase through this command so the gates run; a phase written by hand skips them.
  - `append-history --skill <name> --inputs <json> --outputs <json> --phase-after <phase>` — append a skill run to history.
    When `--phase-after` moves the phase forward, every gate above runs, the same list as `set-phase`
    (`gate_refusal()`). A run recorded at the current phase is not gated. A `--phase-after` behind the
    current phase is not applied: the entry records the phase the project has, plus `phase_requested`.
- `scripts/data_residency.py <decide|add|check|render> <project-root>` — the data-residency decision (four answers → `stack.data_residency`, `compliance.data_categories`), the sub-processor register (`meta.json#compliance.sub_processors`, rendered to `docs/compliance/subprocessors.md`), and `check`: register vs. declared stack, regions in `vercel.json` and `.env*.example`. Flags inform and never fail; only an undecided residency does. How-to: `references/eu-data-sovereignty.md`.
- `scripts/inventory.py <scan|record>` — step 1 of the inventory as a command (`scan`: installed skills, plugins, the other projects on this machine, `resources.md`; prints what it searched and what it could not read) and the record of the verdict in `meta.json#inventory` (`record`). `scripts/inventory_gate.py` is what `set-phase` and `append-history --phase-after` check before a project leaves `idea_captured`. Stdlib only; `scan` writes nothing.
- `scripts/founder_gate.py` — the founder path's gate, checked first at the crossing into `prd_drafted` through both doors: with `meta.json#founder` present (`mode: "new"`), no PRD until the founder approved the Playbook (`approved` or `approved_experiment`, their quote recorded, the Playbook's sha256 unchanged since) or the path was bypassed with a reason. A project without the field is on the direct path and is not affected. Written by `founder-intelligence/scripts/founder.py`.
- `scripts/research.py <status|repos|reddit|thread|hn|post|read|papers>` — the outside half of the inventory step: GitHub through `gh`, plus the four channels a `WebSearch` reads badly (a whole Reddit thread, an X post, a paper, a page as markdown). Stdlib only, no API key, nothing written. Exit `0` answered · `3` answered and empty · `4` could not look, and a `4` goes into the plan as a channel **not covered**. `read` refuses loopback, private IPv4 and `.local`/`.internal`/`.test`, because it renders through a third party. How-to: `references/before-you-build.md` §4.
- `scripts/check_drift.py <project-root>` — diagnostic command. Compares `meta.json#artifacts` against the on-disk files and reports:
  - **fresh**: file matches its recorded hash, all upstreams match too.
  - **self-drift**: the file has been edited since the producing skill last hashed it.
  - **upstream-stale**: the file is unchanged but a `derived_from` input has drifted (e.g., `DESIGN.md` was edited → `registry.json` is now derived from a stale snapshot).
  - **missing**: the file was recorded but no longer exists on disk.
  Exit code is always 0 unless `--exit-nonzero-on-drift` is passed (use in CI).

These scripts are JSON readers/writers; running them doesn't make decisions for the user. The artifact-hashing model is the foundation for **drift detection** — when the user later edits `DESIGN.md` by hand, `check_drift.py` surfaces what's now stale, and you (or the user) decide whether to re-run the relevant skills.

### When to record an artifact

Record an artifact whenever a skill writes a file that:
- Is part of the dev-flow contract (`.workflow/DESIGN.md`, `.workflow/PRD.md`, etc.), OR
- Is a generated config that downstream skills depend on (`registry.json`, `lib/db/schema.ts` initial scaffold, `app/showcase/page.tsx`), OR
- Is a derivative of an upstream artifact (record `derived_from` so drift detection can chain).

Don't record:
- Temporary files, cache, build artifacts.
- Files the user is expected to hand-edit freely (they'd always show as "self-drift").
- Files produced by external tools (`pnpm-lock.yaml`, `node_modules`).

The cost of recording is one shell-out per file; the benefit is a foundation for resumability and drift checks. Err on the side of recording when in doubt for contract-shaped files.
