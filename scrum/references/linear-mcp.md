# Linear MCP cookbook

How each `linear-scrum` operation maps to Linear MCP tools. Tool names/params below have been exercised
live and are confirmed for this workspace; the one part that stays workspace-specific and needs
re-checking on a new workspace is the **label taxonomy** (flagged `[VERIFY]` at that row) — everything
else does not need re-verification.

> **Why that marker can't be closed from here** (checked 2026-08-26): Linear's own MCP page does not
> enumerate tool names — it says only that the server *"has tools available for finding, creating and
> updating objects in Linear like issues, projects, and comments — **with more functionality on the
> way**"*. So the table below is confirmed by having *run* it, not by reading a spec, and the only way
> to re-confirm it on another workspace is to run it there. That is the honest shape of this
> dependency, not a gap in the write-up.

## Connecting — and the endpoint worth knowing

From <https://linear.app/docs/mcp> (2026-08-26): transport is **Streamable HTTP**, setup is OAuth 2.1
with dynamic client registration (a bearer token or Linear API key also works).

⚠️ **There is a read-only endpoint, and this skill's Sync/Adopt discovery should prefer it.**

| Endpoint | Exposes |
|---|---|
| `https://mcp.linear.app/mcp` | read **and** write (the default) |
| **`https://mcp.linear.app/mcp/readonly`** | *"only ever exposes read tools"* |

There is also a scope route: connect to `/mcp` but request only the **`read`** OAuth scope, and
*"the underlying token can't reach write APIs"*. Either way the guarantee is enforced by the server,
not by the agent remembering to behave — which is the right place for it when a skill's whole job is
writing to someone's issue tracker. Reach for a read-write connection only for the modes that actually
write.

| Operation | MCP tool | Notes |
|---|---|---|
| Resolve team | `list_teams` | Single team today (`Lucadigerlando`). Always call first. |
| List / find project | `list_projects` | Adopt mode discovery. |
| Create / link project | `save_project` | One per dev-flow project. Capture id + url. |
| Create milestone | `save_milestone` | Map epics from `tasks.md`. |
| Create issue | `save_issue` | Pass title, description, estimate, labels, project, milestone, `cycle`, `state`. `estimate` (numeric Fibonacci point) **works** when the team has an estimate scale enabled — confirmed live. |
| List issues | `list_issues` | Status/velocity pull; duplicate check in DoD. |
| Issue statuses | `list_issue_statuses` | Confirms the state names in `scrum-model.md`. |
| Issue labels | `list_issue_labels` / `create_issue_label` | **Discover the workspace taxonomy and map onto it** (see `scrum-model.md`); don't assume `area:*`/`type:*`. Create a label only when nothing matches. `[VERIFY]` — **and this one is permanent**: a label taxonomy is a property of *someone's workspace*, not of Linear, so it cannot be verified once and stamped like a version number. Re-discover on every workspace, and expect it to drift inside one. Discovery is a read — use the read-only endpoint above. |
| Cycles | `list_cycles` | **List only — cycles are NOT creatable via this MCP** — confirmed live. Enable "Cycles" + create the sprint in Linear team settings once; then attach issues via `save_issue`'s `cycle` field. |
| Comment | `save_comment` | Optional: post the sprint report as a project comment (still also to chat). |

## Idempotency
Never create an issue whose `task_key` is already in `meta.json#linear.issue_map`. Re-running Setup/Sync must be a no-op for already-pushed tasks. Verify by re-running and confirming `list_issues` count is unchanged.

## Headless loop handoff
The autonomous server loop (Linear → Claude Code → PR) uses a **Linear API key**, not this MCP — see `docs/loop-engineering.md` §1. The states, atomic-issue rule, and `area:*` labels there are the same conventions this skill sets up, so a project bootstrapped here drops straight into that loop. The Linear meter is separate from both billing meters in that runbook (it's just the PM tool).
