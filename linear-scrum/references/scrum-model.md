# Scrum model for dev-flow projects

The conventions `linear-scrum` applies. Depth = **structure + planning + reports**; human ceremonies (standup, retro) stay human.

## Cadence
- Default **2-week** cycles (`meta.json#scrum.cadence_weeks`). One Linear cycle = one sprint.

## Estimates
- **Fibonacci** story points (1, 2, 3, 5, 8, 13). Map a task's `Estimated: <2-8h>` hint to the nearest point (≤2h→1, ~half-day→2, day→3, 2-3 days→5, ~week→8, more→13, and split if >13).
- Tasks with no hint: batch-prompt the user once; default to unestimated rather than guessing.

## Workflow states (this workspace)
`Backlog · Todo · In Progress · In Review · Done · Canceled`. There is **no `Blocked` state** — use a **`blocked` label** on the issue instead (`meta.json#scrum.states.blocked_label`).

## Sprint planning
1. Determine the velocity target: `meta.json#scrum.velocity_target` if set, else the average completed points of the last 2-3 cycles, else ask the user for the first cycle.
2. Pull issues from `Todo`/`Backlog` in priority order until the sum of estimates reaches the target (don't exceed by more than the smallest remaining item).
3. Assign them to the active cycle; leave the rest in the backlog.

## Velocity report (to chat)
For the active/last cycle report: committed points, completed points, carry-over, blocked issues (by label), and the rolling velocity (last 3 cycles). No file is written.

## Labels
- `area:web` / `area:agent` — deduced from `meta.json#stack` and each task's `*(addressed by …)*` owner.
- `type:scaffold` — setup/foundation tasks owned by another skill.
- `blocked` — the stand-in for a Blocked state.
