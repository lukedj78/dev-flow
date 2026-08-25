---
name: linear-scrum
description: 'Take a dev-flow project into Linear and run it with agile scrum: creates or links the Linear Project, pushes `.workflow/tasks.md` into estimated, labelled issues, sets up 2-week cycles, then keeps **Linear as the source of truth** — syncing new tasks up, status and velocity down, planning each sprint to the velocity target. Triggers: "porta il progetto in Linear", "crea le issue in Linear", "setup scrum", "pianifica lo sprint", "report di velocity", "adotta questo progetto in Linear", or dev-flow routing from `prd_drafted`/`tasks_split`. Modes: Setup, Adopt, Sync. Not for: writing or estimating the tasks themselves (use `prd-to-tasks`), building the app or agent (design-md-to-app / eve-agent), or the headless server loop (docs/loop-engineering.md).'
---

# linear-scrum — Linear integration + agile scrum for a dev-flow project

This skill owns the **Linear side** of a dev-flow project. It writes to Linear (via the connected Linear MCP) and to the `linear` / `scrum` blocks of `.workflow/meta.json`. It **never** touches `app/`, `apps/agent/`, or other framework files, and it **does not change the `phase` enum** — like `eve-agent` and the discipline skills it records state in `meta.json` and appends `history`, and is never a phase gate.

Read `references/contracts.md` for the `.workflow/` contract, `references/scrum-model.md` for the scrum conventions, and `references/linear-mcp.md` for the exact Linear MCP operations.

## Preconditions

- A **Linear MCP must be connected** in the session. Confirm with `list_teams` before any write. For the headless server loop use the API-key path in `docs/loop-engineering.md` instead — this skill is the interactive counterpart.
- `.workflow/meta.json` exists (dev-flow project). If not, tell the user and stop.
- `.workflow/tasks.md` exists for Setup mode (run `prd-to-tasks` first otherwise). **Coupled format**: `scripts/task_key.py` derives its dedup key from the `- [ ] **<Title>** — <body>` line shape produced by `prd-to-tasks`, splitting on the em-dash (` — `) to isolate the title — if `tasks.md` was hand-edited to use a different separator, dedup breaks and Setup/Sync can create duplicate issues.

## Read state, then pick a mode

Read `.workflow/meta.json`:
- No `meta.json#linear` and `tasks.md` present → **Setup mode**.
- A Linear Project already exists for this project but `meta.json#linear` is absent/partial → **Adopt mode**.
- `meta.json#linear` present → **Sync mode**.

Do **one** logical operation per invocation, then stop. Every mode is idempotent.

## Setup mode (new project)

1. `list_teams` → resolve the team (single team today: `Lucadigerlando`). One dev-flow project = one **Linear Project** under that team, never a new team.
2. Ensure scrum config on the team:
   - **Estimates** — verified working: `save_issue` accepts a Fibonacci `estimate` (numeric point value) when the team has an estimate scale enabled.
   - **Cycles** — the MCP can only *list* cycles (`list_cycles`), **not create** them. Ask the user to enable "Cycles" in Linear team settings once and create the first cycle there, then continue; issues are attached to an existing cycle via `save_issue`'s `cycle` field.
3. Create/link the Linear Project (`save_project`); capture its id + url.
4. Push `tasks.md` → issues (`save_issue`), one per `- [ ]` task:
   - **estimate**: from the task's `Estimated:` hint mapped to the nearest Fibonacci point; for tasks with no hint, **batch-prompt once** (list them, ask for points in one message) and default to unestimated if skipped.
   - **labels**: **discover, don't assume.** Call `list_issue_labels` and map the conceptual buckets — web / agent / scaffold — onto the workspace's own labels (e.g. this workspace uses `frontend` / `agent-eve` / `setup`, not `area:*`). Derive web-vs-agent from `meta.json#stack` + the task's `*(addressed by …)*` tag; record the resolved mapping in `meta.json#scrum.labels`. Create a label only if no reasonable match exists.
   - **milestone**: map epics/milestones via `save_milestone` when `tasks.md` groups by epic.
   - record each `task_key(line) → issue identifier` for the next step.
5. Attach issues to the active cycle if one exists (`list_cycles`; the cycle itself is created in Linear per step 2 — 2-week cadence). If none exists yet, leave the issues in the backlog and note it.
6. Persist state:
   ```bash
   python3 scripts/meta_linear.py <root>/.workflow/meta.json upsert-linear \
     --team-id <id> --team-name <name> --project-id <pid> --url <url>
   python3 scripts/meta_linear.py <root>/.workflow/meta.json record-issues \
     --mapping '{"<task_key>":"LUC-123", ...}'
   ```
   Then append a `history` entry via `dev-flow/scripts/update_meta.py`:
   `{ "skill": "linear-scrum", "action": "setup", "ran_at": "<ISO8601>" }` (no phase bump).

## Adopt mode (existing project already partly in Linear)

1. Discover the existing Project and its issues (`list_projects`, `list_issues`).
2. Match issues to `tasks.md` lines by title (`task_key`) and **backfill** `issue_map` without creating anything (`meta_linear.py record-issues`).
3. Fill any missing scrum config (`meta_linear.py ensure-scrum`), then `upsert-linear` with the discovered project id/url.
4. Append history `{ "skill": "linear-scrum", "action": "adopt", … }`.

## Sync mode (ongoing, horizontal)

- **Push new tasks**: for each `tasks.md` line whose `task_key` is not in `issue_map`, `save_issue` + `record-issues`. Never edit or re-push existing issues — Linear owns status/ordering/estimates.
- **Pull status/velocity**: read issue states + completed points from Linear (`list_issues`, `list_cycles`).
- **Sprint planning**: move items from `Backlog`/`Todo` into the active cycle up to the **velocity target** (`meta.json#scrum.velocity_target`; learned from past cycles, asked on the first). See `references/scrum-model.md`.
- **Report**: produce a sprint/velocity summary **to chat** (points committed vs done, carry-over, blocked issues). Do not write a report file.
- Append history `{ "skill": "linear-scrum", "action": "sync", … }`.

## Definition of Done (per run)

- **Setup**: `list_issues` on the Project returns the pushed issues; `meta.json#linear` populated; a re-run creates **no duplicates** (verify by re-running Setup and confirming the issue count is unchanged).
- **Sync**: the active cycle holds planned issues up to the velocity target and a report was produced.
- Scripts stay green: `cd linear-scrum/scripts && python3 -m unittest test_scripts`.

## What this skill does NOT do

- Doesn't write/estimate tasks (that's `prd-to-tasks`).
- Doesn't build the app or agent (`design-md-to-app` / `eve-agent`).
- Doesn't run human ceremonies (standup/retro) or generate ceremony artifacts.
- Doesn't create a Linear team per project — one team, many Projects.
- Doesn't bump `phase`.
