# Merge conflicts in a dev-flow project

The method is not ours. [`mattpocock/skills` → `resolving-merge-conflicts`](https://github.com/mattpocock/skills/blob/main/skills/engineering/resolving-merge-conflicts/SKILL.md)
(MIT, read 2026-09-15) is five steps worth following as written: see the state; **find the primary
sources** of each side before touching a hunk; preserve both intents where compatible, and where not,
pick the side matching the merge's goal and *name what was dropped*; never invent behaviour; run the
project's checks before finishing. It is in `external-skills.md`.

This file is what that skill cannot know: **where intent lives in a dev-flow project, which files are
derived and must be regenerated instead of merged, which checks prove the merge, and where its last step
collides with how we work.** Read it with the skill, not instead of it.

## 1. Two overrides to the skill's step 5

The skill ends with *"Stage everything and commit"*. In a dev-flow project, don't:

- **Stage the resolved paths and the regenerated files by name — never `git add -A` / `git add .`.**
  Other agents work in the same trees (annotix has one permanently), and "everything" includes their
  uncommitted files. `git diff --name-only --diff-filter=U` lists what was in conflict; add those plus
  what §3 regenerated, then read `git status` before committing.
- **Commit only when the user started or asked for the merge/rebase.** Finishing a merge they asked for
  is part of that request. A merge an agent started on its own is left resolved and staged, and reported.

And one refinement to *"never `--abort`"*: never abort on your own, agreed — but a conflict that is a
**product decision** (two token values in `DESIGN.md`, two scopes for the same PRD section, two prices)
is not the agent's to pick. Stop with the merge in progress, lay out both sides with their sources, ask.

## 2. Where intent lives

Read these before the diff, in this order — the first that names the change wins:

| Source | What it tells you |
|---|---|
| Commit messages on each side (`git log --merge -p <file>`) | this repo's commits explain *why*; quote them |
| The Linear issue (`LUC-…` in branch or commit) when `meta.json#linear` is set | the scope that was agreed — Linear is the source of truth under `linear-scrum` |
| `.workflow/tasks.md` | which task the change belongs to, and whether it was checked off |
| `.workflow/PRD.md`, `.workflow/DESIGN.md` | product and visual intent; a hunk that contradicts them is the wrong side, whichever branch it came from |
| `meta.json#history` | which skill produced the file and when (`skill`, `ran_at`, `outputs`) |

## 3. Derived files: regenerate, never hand-merge

A hand-merged generated file looks resolved and is wrong in a way no reviewer sees. Resolve the
**inputs**, then rebuild the output. Take either side of the output to clear the markers
(`git checkout --ours -- <file>` is fine *here*, because the next command replaces it).

| File | Resolve by |
|---|---|
| `pnpm-lock.yaml` | resolve `package.json` first, then `pnpm install` (pnpm resolves lockfile conflicts itself). pnpm's own caveat: it builds from the most updated lockfile and cannot guarantee the right head — read the diff before staging |
| `registry.json` (from DESIGN.md) | resolve `.workflow/DESIGN.md`, then `python3 design-md-to-app/scripts/build_registry.py <root>` |
| `.workflow/meta.json` | by field, below — it is state, not text |
| `registry-lock.json` + `vendor/registry/**` | union of `registries` (a registry in only one side stays, with its reason). An item approved on both sides with different `sha256` is **re-approved**: `registry_intake.py review` shows the upstream diff, then `approve`. Never edit a snapshot by hand — `check` refuses the hash |
| `.claude/hooks/registry_intake.py`, `.claude/settings.json` hook entry | `registry_intake.py setup <root>` rewrites both |
| `AGENTS.md` managed blocks (`<!-- BEGIN:design-system-lint -->`, `<!-- BEGIN:registry-intake -->`, `<!-- BEGIN:nextjs-agent-rules -->`) | keep the text outside the markers from both sides; for the block itself rerun its owner — `setup_design_lint.py`, `registry_intake.py setup`, `next dev` |
| `package.json` `lint --max-warnings N` | **the lower N**, then run the lint. A raised cap is how a merge hides warnings; `registry_intake.py check` fails on it |
| Generated DB migrations (drizzle-kit) | keep the schema change from both sides in the schema source, delete the generated migration files that conflict, regenerate with the project's `db:generate` script. `[VERIFY]` drizzle-kit's journal behaviour on the installed version before deleting anything that already ran against a shared database — a migration applied in production is history, not a conflict |
| `messages/en.json`, `messages/it.json` | union of keys; the two locales must end with the same key set (golden rule 2) |

**In `~/my-skills` itself:** the 38 `*/references/contracts.md` are copies — resolve
`dev-flow/references/contracts.md` and copy it over the rest. `skills.json`, `docs/skills/`,
`docs/index.html`, `.claude-plugin/plugin.json` and the skill-map row meta are rebuilt by
the repo's `regenerate.sh` (the pre-commit hook runs it). Counts in README and the skill map: take either
side, then let the repo's `lint_skills.py` name the right number.

### `meta.json`, field by field

- `phase` — the **further** of the two in the `PHASES` order, and never by writing it: resolve the file
  with the earlier phase, then `python3 dev-flow/scripts/update_meta.py <root> set-phase <further>`, so
  the scaffold gates (design lint, registry intake) run on the merged tree.
- `history` — union of both lists, ordered by `ran_at`; drop exact duplicates only.
- `artifacts` — for each path, keep the entry whose `sha256` matches the file **after** the merge; then
  `python3 dev-flow/scripts/check_drift.py <root>` and `update_meta.py record-artifact` for anything it
  reports as self-drift that the merge legitimately changed.
- `stack` — a disagreement here is a stack decision (two `db`, two `ui`) → §1, ask. A key present on one
  side only is kept.

## 4. The checks that prove it

Run what applies, before the commit — typecheck, then lint, then tests is the skill's order and ours:

- `pnpm tsc --noEmit` (every workspace that changed) · the project's `lint` script with its cap
- `python3 design-md-to-app/scripts/setup_design_lint.py <root> --check`
- `python3 registry-intake/scripts/registry_intake.py check <root>`
- `python3 dev-flow/scripts/check_drift.py <root>` · `python3 dev-flow/scripts/show_state.py <root>` (no gate warnings)
- tests (`write-tests` / `rn-write-tests` conventions) · `eve build` and the eve error log when `agent/` changed
- in `~/my-skills`: its `lint_skills.py` and the unittest suites the CI workflow runs

## 5. Parallel work

From the same page, and it matches how dev-flow runs subagents and worktrees: **the session that wrote a
change is the one that merges it back**, because it already holds the intent §2 would otherwise have to
reconstruct. Batching everyone's conflicts onto one agent at the end throws that context away. Zoning
files between parallel tasks mostly costs more than it saves; the exception worth keeping is to land
large renames and refactors **first**, before the branches fork off them.
