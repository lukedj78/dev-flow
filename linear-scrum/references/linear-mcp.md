# Linear MCP cookbook

How each `linear-scrum` operation maps to Linear MCP tools. **Verify names/params against the connected MCP** before relying on them — tool names are workspace-specific and may change. `[VERIFY]`

| Operation | MCP tool | Notes |
|---|---|---|
| Resolve team | `list_teams` | Single team today (`Lucadigerlando`). Always call first. |
| List / find project | `list_projects` | Adopt mode discovery. |
| Create / link project | `save_project` | One per dev-flow project. Capture id + url. |
| Create milestone | `save_milestone` | Map epics from `tasks.md`. |
| Create issue | `save_issue` | Pass title, description, estimate, labels, project, milestone, `cycle`, `state`. `estimate` (numeric Fibonacci point) **works** when the team has an estimate scale enabled — verified. |
| List issues | `list_issues` | Status/velocity pull; duplicate check in DoD. |
| Issue statuses | `list_issue_statuses` | Confirms the state names in `scrum-model.md`. |
| Issue labels | `list_issue_labels` / `create_issue_label` | **Discover the workspace taxonomy and map onto it** (see `scrum-model.md`); don't assume `area:*`/`type:*`. Create a label only when nothing matches. |
| Cycles | `list_cycles` | **List only — cycles are NOT creatable via this MCP.** Enable "Cycles" + create the sprint in Linear team settings once; then attach issues via `save_issue`'s `cycle` field. |
| Comment | `save_comment` | Optional: post the sprint report as a project comment (still also to chat). |

## Idempotency
Never create an issue whose `task_key` is already in `meta.json#linear.issue_map`. Re-running Setup/Sync must be a no-op for already-pushed tasks. Verify by re-running and confirming `list_issues` count is unchanged.

## Headless loop handoff
The autonomous server loop (Linear → Claude Code → PR) uses a **Linear API key**, not this MCP — see `docs/loop-engineering.md` §1. The states, atomic-issue rule, and `area:*` labels there are the same conventions this skill sets up, so a project bootstrapped here drops straight into that loop. The Linear meter is separate from both billing meters in that runbook (it's just the PM tool).
