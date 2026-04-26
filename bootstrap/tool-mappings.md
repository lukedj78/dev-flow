# Cross-platform tool mappings

dev-flow's `SKILL.md` files reference tools by their **Claude Code** names (`Bash`, `Read`, `Edit`, `Write`, `Glob`, `Grep`). When you load these skills on a different runtime, the LLM needs to map those names to the runtime's actual tools.

Most modern coding agents have semantically equivalent tools — only the names differ. The table below is the canonical mapping. Bootstrap files (`AGENTS.md`, `GEMINI.md`, `.cursorrules`) include this table so the loaded skill body remains valid regardless of runtime.

## Canonical mapping

| Concept | Claude Code | Codex CLI | Copilot CLI | Gemini CLI | Cursor |
|---|---|---|---|---|---|
| Run shell command | `Bash` | `shell` | `bash` | `run_shell_command` | terminal MCP |
| Read a file | `Read` | `read_file` | `read_file` | `read_file` | filesystem MCP |
| Edit a file (string replace) | `Edit` | `apply_patch` | `apply_patch` | `replace` | `edit_file` |
| Write/create a file | `Write` | `apply_patch` (with `*** Add File`) | `apply_patch` | `write_file` | `edit_file` (new) |
| Glob file paths | `Glob` | `shell` w/ `find`/`fd` | `glob` | `glob` | `find_files` |
| Search file contents | `Grep` | `shell` w/ `rg` | `grep` | `search_file_content` | `grep_search` |
| Spawn sub-agent | `Agent` | n/a | `agent` | `agent` | n/a |
| Track tasks | `TodoWrite` | n/a (use plain markdown) | `todos` | n/a | n/a |
| Web fetch | `WebFetch` | `web_fetch` | `web_fetch` | `web_fetch` | n/a |

### Fallback strategy

When a tool concept doesn't exist on the target runtime, the skill should:

1. **Substitute with a shell command** when feasible (`find` instead of `Glob`, `rg` or `grep -r` instead of `Grep`, `sed` or `python3 -c` instead of `Edit`).
2. **Inline the work** when no equivalent exists (e.g., for `Agent` sub-agents: do the work in the current context instead of delegating).
3. **State the limitation** rather than fabricate. If `WebFetch` isn't available and a skill needs to download something, ask the user to provide it.

The skills don't need to be rewritten — they just need this table loaded into context. The LLM picks the right tool from the runtime's list using semantic equivalence.

## Filesystem-contract operations

Beyond tool names, dev-flow has a few **filesystem-contract operations** that are runtime-agnostic. They're invoked by shell, so they work everywhere:

| Operation | Command | Runtime |
|---|---|---|
| Init a workflow | `python3 dev-flow/scripts/init_workflow.py <root> --name "X"` | any |
| Show state | `python3 dev-flow/scripts/show_state.py <root>` | any |
| Record an artifact | `python3 dev-flow/scripts/update_meta.py <root> record-artifact --path <p> --produced-by <skill>` | any |
| Bump phase | `python3 dev-flow/scripts/update_meta.py <root> set-phase <phase>` | any |
| Append history | `python3 dev-flow/scripts/update_meta.py <root> append-history --skill <s> --inputs <json> --outputs <json>` | any |
| Check drift | `python3 dev-flow/scripts/check_drift.py <root> [--plan]` | any |

Or, equivalently from any Python runtime:

```python
from dev_flow_contract import (
    init_workflow, record_artifact, set_phase, append_history, check_drift, Phase
)
```

The contract package is the **portable surface** — every runtime that can run Python (or shell out to it) can read and write `.workflow/` correctly.

## When this table goes stale

Tool names evolve. When a runtime renames a tool (e.g., Codex moves from `shell` to something else), update this file in one place and the bootstraps inherit it. The skills themselves never need to change — that's the point of routing through this mapping rather than hard-coding tool names in every `SKILL.md`.

If you're porting to a runtime not listed here, follow the pattern: add a column, fill the equivalents you know, mark `n/a` where there's no analogue, and submit a PR.
