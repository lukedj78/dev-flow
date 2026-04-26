# dev-flow — Gemini CLI bootstrap

You have access to **dev-flow**, a filesystem contract + 8 specialist skills for agent-driven product development. Skills activate via the `activate_skill` tool.

## What dev-flow is

A small set of skills that share one filesystem contract (`.workflow/meta.json`) to take a project from "idea" to "running app" without losing context across sessions.

State lives on disk, not in your conversation memory.

## Skills available

The 8 skill folders live at `~/.gemini/skills/` (or your platform's equivalent):

| Skill | When to activate |
|---|---|
| `dev-flow` | The orchestrator — call first to determine the next step from `meta.json#phase`. |
| `prd-from-idea` | User describes an idea → `PROJECT.md` + `PRD.md`. |
| `prd-to-tasks` | `PRD.md` → `tasks.md`. |
| `figma-to-design-md` | Figma URL → `DESIGN.md`. |
| `image-to-design-md` | Raster images → `DESIGN.md`. |
| `design-md-to-app` | `DESIGN.md` → scaffolded Next.js app. |
| `screenshot-to-page` | One screenshot → one route. |
| `module-add` | Wire `auth` / `db` / `payments` / `email` / `test` / `ci`. |

## Activation pattern

```
1. User says something matching a skill's description.
2. Call activate_skill with the skill name.
3. The skill body loads — follow it as instructions.
4. Update `.workflow/meta.json` after the work via the bundled scripts.
```

## Tool name mapping (Claude Code → Gemini CLI)

The skills reference Claude Code tool names. Map them as follows:

| Claude Code | Gemini CLI |
|---|---|
| `Bash` | `run_shell_command` |
| `Read` | `read_file` |
| `Edit` | `replace` |
| `Write` | `write_file` |
| `Glob` | `glob` |
| `Grep` | `search_file_content` |
| `WebFetch` | `web_fetch` |
| `Agent` | `agent` (where supported) |

## State management

Every dev-flow project has `.workflow/`:

```
<project-root>/.workflow/
├── meta.json    ← single source of truth (phase, stack, artifacts, history)
├── PROJECT.md   ← brief
├── PRD.md       ← requirements
├── tasks.md     ← checklist
├── DESIGN.md    ← design system
└── screenshots/
```

Before any specialist work, `read_file <project-root>/.workflow/meta.json` to know the current phase.

## State-mutating commands

These run via `run_shell_command` and work identically on any runtime:

```bash
# Init
python3 ~/.gemini/skills/dev-flow/scripts/init_workflow.py <root> --name "X"

# Record artifact (after writing a contract file)
python3 ~/.gemini/skills/dev-flow/scripts/update_meta.py <root> \
  record-artifact --path <p> --produced-by <skill> [--derived-from <p1> <p2>]

# Bump phase + log run
python3 ~/.gemini/skills/dev-flow/scripts/update_meta.py <root> \
  append-history --skill <s> --outputs '["a", "b"]' --phase-after <phase>

# Drift check (when user edits files by hand)
python3 ~/.gemini/skills/dev-flow/scripts/check_drift.py <root> --plan
```

## Constraints

- **Read `meta.json` first.** Always. Don't guess the project's state.
- **Phase is forward-only.** Never set it backwards.
- **Idempotency.** Skills detect their previous output and skip — trust this before re-installing.
- **Codebase at project root.** Generated code lives at `<project-root>/`, alongside (not inside) `.workflow/`.

## Reference

- `~/.gemini/skills/dev-flow/references/contracts.md` — full `meta.json` schema.
- `~/.gemini/skills/bootstrap/tool-mappings.md` — canonical cross-platform tool mapping.
