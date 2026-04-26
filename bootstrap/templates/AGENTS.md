# dev-flow — Codex CLI bootstrap

You have access to **dev-flow**, a filesystem contract + 8 specialist skills for agent-driven product development. This file teaches you when and how to use them.

## What dev-flow is

A small set of skills that share one filesystem contract (`.workflow/meta.json`) to take a project from "idea" to "running app" without losing context across sessions.

The skills are loaded as reference material — you read their `SKILL.md` files and follow them like instructions. State lives on disk, not in your head.

## Skills available

The 8 skill folders are located at `<repo-root>/dev-flow-skills/`:

| Skill | When to use it |
|---|---|
| `dev-flow` | The orchestrator. Call first to figure out which other skill applies based on `meta.json#phase`. |
| `prd-from-idea` | User describes an idea → produces `PROJECT.md` + `PRD.md`. |
| `prd-to-tasks` | `PRD.md` → `tasks.md` checklist. |
| `figma-to-design-md` | Figma URL → `DESIGN.md` (Google design.md spec). |
| `image-to-design-md` | Raster images → `DESIGN.md` + screenshots. |
| `design-md-to-app` | `DESIGN.md` → scaffolded Next.js app with theme + showcase. |
| `screenshot-to-page` | One screenshot → one route, with pixel verification. |
| `module-add` | Wire a backend module (`auth` / `db` / `payments` / `email` / `test` / `ci`). |

## How to use a skill

1. The user says something that maps to a skill (e.g., "I have an idea: …" → `prd-from-idea`).
2. Read the skill's `SKILL.md` file end-to-end before acting:
   ```
   read_file <repo-root>/dev-flow-skills/<skill-name>/SKILL.md
   ```
3. Follow it as instructions. The skill body uses Claude Code tool names — see the mapping below.
4. If the skill references additional files (`references/<x>.md`), read those when its body says to.
5. After completing the skill's work, update `.workflow/meta.json`:
   ```bash
   python3 <repo-root>/dev-flow-skills/dev-flow/scripts/update_meta.py <project-root> \
     record-artifact --path <output-file> --produced-by <skill-name>
   python3 <repo-root>/dev-flow-skills/dev-flow/scripts/update_meta.py <project-root> \
     append-history --skill <skill-name> --outputs '[…]' --phase-after <new-phase>
   ```

## Tool name mapping (Claude Code → Codex CLI)

When a skill says "use `Bash` to …", do it with `shell`. The semantic mapping:

| Claude Code says | Use this on Codex |
|---|---|
| `Bash` (shell command) | `shell` |
| `Read` (read file) | `read_file` |
| `Edit` (string replace in file) | `apply_patch` |
| `Write` (create/overwrite file) | `apply_patch` with `*** Add File:` header |
| `Glob` (find files by pattern) | `shell` with `find` or `fd` |
| `Grep` (search file contents) | `shell` with `rg` |
| `WebFetch` (download web content) | `web_fetch` if available, else ask user |
| `Agent` (spawn sub-agent) | inline the work — Codex doesn't have sub-agents the same way |
| `TodoWrite` (track tasks) | maintain a markdown todo list inline |

## State management

Every dev-flow project has a `.workflow/` folder with these files (skills produce them in order):

```
<project-root>/.workflow/
├── meta.json           ← phase, stack, artifacts, history (THE source of truth)
├── PROJECT.md          ← strategic brief
├── PRD.md              ← requirements
├── tasks.md            ← task checklist
├── DESIGN.md           ← design system (Google design.md spec)
└── screenshots/        ← UI references
```

Before doing anything specialist, **read `.workflow/meta.json` first** to know the current phase. The `dev-flow` skill explains what's appropriate for each phase.

## Drift detection

When the user edits any contract file by hand (especially `DESIGN.md`), run:

```bash
python3 <repo-root>/dev-flow-skills/dev-flow/scripts/check_drift.py <project-root> --plan
```

This produces a migration plan showing which artifacts are stale (self-drift, upstream-stale, missing) and which skills should re-run, in what order. Tell the user.

## Important constraints

- **Don't invent.** If a skill references a file that doesn't exist, stop and ask. Never fabricate `meta.json` values.
- **Phase is monotonic forward.** Re-running a skill on an already-advanced project is fine, but never set `phase` backwards.
- **Idempotency.** Most skills are designed to detect their previous output and skip/update. Trust the skill's idempotency check before re-installing.
- **Codebase at project root.** All scaffolded code lives at `<project-root>/`, alongside (not inside) `.workflow/`.

## Example flow

User: *"I want to build a CRM for veterinary clinics."*

You:
1. `read_file dev-flow-skills/dev-flow/SKILL.md` — see the routing rules.
2. `python3 dev-flow-skills/dev-flow/scripts/init_workflow.py . --name "Vet CRM"` — phase=empty.
3. `read_file dev-flow-skills/prd-from-idea/SKILL.md` — see how to produce PRD.
4. Follow it, write PROJECT.md + PRD.md.
5. `python3 … update_meta.py . append-history --skill prd-from-idea --outputs '["PROJECT.md", "PRD.md"]' --phase-after prd_drafted`.
6. Tell the user what's next per the dev-flow router output.

That's the loop. The skills are content; the contract is the connective tissue.

## Reference docs

For deeper reading:
- `dev-flow-skills/dev-flow/references/contracts.md` — full `meta.json` schema.
- `dev-flow-skills/bootstrap/tool-mappings.md` — this same mapping in canonical form.
- The repo's main `README.md` — project overview + use cases.
