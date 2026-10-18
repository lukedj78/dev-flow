# Scrum model for dev-flow projects

The conventions `scrum` applies on every tracker; each adapter (`linear.md`, `jira.md`, `github.md`) says how. Depth = **structure + planning + reports**; human ceremonies (standup, retro) stay human.

## Cadence
- Default **2-week** sprints (`meta.json#scrum.cadence_weeks`). A sprint is a Linear cycle (created by the user in the
  app — the MCP cannot), a Jira sprint (`manageJiraSprint`), or a GitHub milestone named by its goal.

## Estimates
- **Fibonacci** story points (1, 2, 3, 5, 8, 13). Map a task's `Estimated: <2-8h>` hint to the nearest point (≤2h→1, ~half-day→2, day→3, 2-3 days→5, ~week→8, more→13, and split if >13).
- Tasks with no hint: batch-prompt the user once; default to unestimated rather than guessing.

## Workflow states
`Backlog · Todo · In Progress · In Review · Done` (`meta.json#scrum.states`), mapped onto each tracker's own: Linear's
workflow states, Jira's transitions, GitHub's open/closed plus `status:` labels. Blocked is a **`blocked` label**
everywhere (`scrum.states.blocked_label`), since not every tracker has the state.

## Sprint planning
1. Determine the velocity target: `meta.json#scrum.velocity_target` if set, else the average completed points of the last 2-3 cycles, else ask the user for the first cycle.
2. Pull issues from `Todo`/`Backlog` in priority order until the sum of estimates reaches the target (don't exceed by more than the smallest remaining item).
3. Assign them to the active cycle; leave the rest in the backlog.

## Velocity report (to chat)
For the active/last cycle report: committed points, completed points, carry-over, blocked issues (by label), and the rolling velocity (last 3 cycles). No file is written.

## Labels — discover, don't assume
Every workspace has its own label taxonomy. **Do not hardcode `area:web` / `type:scaffold`.** At Setup, call `list_issue_labels` and map three conceptual buckets onto whatever labels already exist, recording the result in `meta.json#scrum.labels`:

| Bucket | Meaning | Example match in the current workspace |
|---|---|---|
| `web` | web/frontend work | `frontend` |
| `agent` | eve agent work | `agent-eve` |
| `scaffold` | setup/foundation owned by another skill | `setup` |

Derive `web` vs `agent` from `meta.json#stack` and each task's `*(addressed by …)*` owner. Create a new label only when no reasonable existing one matches. The `blocked` label is the stand-in for the missing Blocked state (`meta.json#scrum.states.blocked_label`); create it if absent.

## Priority and severity

- **Priority** orders the planned work: native on Linear and Jira, the `priority: Pn` label on GitHub (P1–P3, the
  user's rule; P0 only for an S1 bug). Sprint planning pulls by priority.
- **Severity** (S1–S4, `scrum.severity_labels`) is for bugs only, set by Triage (`triage.md`). A bug has both: S1/S2
  take the highest priority and enter the current sprint outside the velocity target.
- The velocity report lists open bugs by severity.
