# bootstrap/

Cross-platform glue that lets dev-flow's skills load on runtimes other than Claude Code.

## Structure

```
bootstrap/
├── README.md              ← you are here
├── tool-mappings.md       ← canonical Claude → Codex → Copilot → Gemini → Cursor table
└── templates/
    ├── AGENTS.md          ← Codex CLI bootstrap
    ├── GEMINI.md          ← Gemini CLI bootstrap
    ├── .cursorrules       ← Cursor bootstrap
    └── system-prompt.md   ← Generic fallback for any LLM agent
```

## How it fits together

The skills' `SKILL.md` files use Claude Code tool names (`Bash`, `Read`, `Edit`, …). For non-Claude runtimes, the bootstrap files do two things:

1. Tell the LLM that dev-flow exists, where to find it, and when to invoke each skill.
2. Provide the tool-name mapping so the LLM can translate `Bash` → its runtime's shell tool.

Once a bootstrap is loaded, the LLM follows the same `SKILL.md` instructions as on Claude Code — the prose is intentionally portable.

## Updating mappings

When a runtime renames a tool, edit `tool-mappings.md` once. The bootstrap files reference the same canonical table, so the change propagates.

When adding a new runtime:

1. Add a column to `tool-mappings.md`.
2. Create `templates/<RUNTIME>.md` (or whatever filename the runtime expects for its entry point) modeled after the existing templates.
3. Add a case to `install.sh`'s platform switch — pick the right install path and bootstrap target.
4. Update the support matrix in the main `README.md`.

## What's not in here

- The skill bodies themselves — those live one directory up, in `<skill>/SKILL.md`. Bootstraps **point to** the skills; they don't duplicate the prose.
- The Python contract package — that's at `../contract-package/` and is the runtime-agnostic state-mutation API.
- Skill installation logic — that's in `../install.sh`.

The `bootstrap/` directory is the "make dev-flow speak runtime X" layer. Keep it small.
