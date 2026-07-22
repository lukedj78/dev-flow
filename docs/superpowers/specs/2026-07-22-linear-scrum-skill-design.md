# `linear-scrum` — Linear integration + agile scrum for every dev-flow project

> Design doc — 2026-07-22. Status: **approved** (design), pending spec review → implementation plan.
> Author: brainstormed with the user. Part of the dev-flow skill family.

## Problem

Two gaps in the current skill set:

1. **No real Linear integration.** `prd-to-tasks` produces `.workflow/tasks.md` that is *"Linear-CSV compatible"*, but nothing actually pushes a project into Linear. The only Linear material that exists is `docs/loop-engineering.md`, a runbook for the **headless autonomous loop** (Linear as a queue, API-key on a server) — not for interactive project creation.
2. **No scrum discipline across projects.** Projects already live in Linear ad-hoc (e.g. openapi-portal, bidmaster, gym-saas), but there is no skill that sets up cycles/sprints, estimates, and sprint reporting, and no policy that makes scrum the default way every project is run.

The enabler is that a **Linear MCP is connected** in the working environment (`save_project`, `save_issue`, `list_cycles`, `save_milestone`, `list_teams`, …), so project/issue/cycle creation can happen interactively — not just as an importable file.

## Decisions (locked during brainstorming)

| # | Decision | Choice |
|---|----------|--------|
| 1 | Structure vs existing skills | **New dedicated skill** `linear-scrum`. `prd-to-tasks` stays unchanged (still writes the file). |
| 2 | Source of truth after setup | **Linear becomes the source of truth** for **status, ordering, estimates and cycle assignment** — those are never hand-edited in `tasks.md` again. `tasks.md` stays the **append-only intake** for *new* work items (added by the user or by a `prd-to-tasks` revise run); Sync pushes those forward one-way. New work may also be created straight in Linear, in which case it simply isn't mirrored back to the file. |
| 3 | Scrum depth | **Structure + planning + reports.** Cycles/sprints, story-point estimates, workflow states, backlog + sprint planning, sprint/velocity reports. Human ceremonies (standup, retro) stay human — no generated ceremony artifacts. |
| 4 | Enforcement across all projects | **Default proposed, non-blocking.** dev-flow proposes the skill at project creation and at `tasks_split`; skipped only on explicit opt-out. Existing projects get an **Adopt** mode to retrofit on demand. No hard gate. |

## Environment facts (verified 2026-07-22 via the connected Linear MCP)

- **One team**: `Lucadigerlando` (`id 6e138486-3b3c-4c08-bd7e-fe368e1234d5`). ⇒ each dev-flow project maps to a **Linear Project** under this team, **not** a separate team.
- **Workflow states present**: `Backlog · Todo · In Progress · In Review · Done · Canceled · Duplicate`.
  **No `Blocked` state** (the loop-engineering runbook assumed one). ⇒ use a **`blocked` label**, not a state.
- **No cycles exist yet.** Cycles are a team-level setting; if the MCP cannot create/enable them, Setup instructs the user to enable "Cycles" once in Linear, then proceeds. `[VERIFY]`

## Scope

`linear-scrum` owns the **Linear side** of a dev-flow project. It:

- writes to **Linear** (via the connected MCP) and to the `linear` / `scrum` blocks of `.workflow/meta.json`;
- **never** touches `app/`, `apps/agent/`, or other framework territory;
- **does not add a new `phase` enum value** — like `eve-agent` and the discipline skills, it records its state in `meta.json` and appends `history`, and never acts as a phase gate (consistent with decision #4);
- reuses `docs/loop-engineering.md` for the **headless API-key path** (the two billing meters stay separate: Claude Code writing code vs. the eve agent's runtime model calls — the Linear meter is neither, it is just the PM tool).

Out of scope: writing/estimating the tasks themselves (that is `prd-to-tasks`), running ceremonies, and any non-Linear PM tool.

## The three modes

One logical operation per invocation, then stop (same discipline as `module-add` / `eve-agent`). Every mode is **idempotent**.

### Setup mode — new project
Trigger: a project has `.workflow/tasks.md` and no `meta.json#linear`.
1. Resolve the team (single team today) and **create or link a Linear Project** for this dev-flow project.
2. Ensure scrum config on the team: **cycles enabled** and an **estimate scale** (Fibonacci). If cycles/estimates can't be toggled via MCP, stop and instruct the user to enable them once in Linear, then re-run. `[VERIFY]`
3. **Push `tasks.md` → issues**: one issue per `- [ ]` task, with:
   - **story-point estimate** (Fibonacci) — from the task's `Estimated:` hint, else prompt/skip;
   - **labels**: `area:web` / `area:agent` (deduced from `meta.json#stack` and the task's `*(addressed by …)*` tag), plus `type:scaffold` for setup tasks;
   - **milestone** mapping when the task list groups by epic/milestone.
4. **Create the first cycle** (cadence default **2 weeks**).
5. Populate `meta.json#linear` + `#scrum` (schema below), record every issue in `issue_map` (anti-duplicate), append `history`.

### Adopt mode — existing project already partly in Linear
Trigger: a Linear Project/issues already exist for the project but `meta.json#linear` is absent or partial.
1. Discover the existing Project and its issues.
2. Reconcile against `tasks.md` / `meta.json` and **backfill** `meta.json#linear.issue_map` without creating duplicates.
3. Fill any missing scrum config (cadence, estimate scale, states) into `meta.json#scrum`.

### Sync mode — ongoing, horizontal
Trigger: `meta.json#linear` exists and the user wants to reconcile / plan / report.
- **Push new tasks**: any `tasks.md` line not in `issue_map` (i.e. appended since the last sync) becomes a new issue. Never edits or re-pushes existing ones (Linear owns status/ordering/estimates).
- **Pull status/velocity**: read issue states + completed points from Linear.
- **Sprint planning**: pull items from `Backlog`/`Todo` into the **active cycle** up to the **velocity target** (learned from past cycles; on the first cycle, ask).
- **Sprint/velocity report**: generated by reading Linear — delivered to chat by default. (Persisting a report file is an open question, see below.)

## `meta.json` additions

```jsonc
"linear": {
  "team_id": "6e138486-3b3c-4c08-bd7e-fe368e1234d5",
  "team_name": "Lucadigerlando",
  "project_id": "<linear project id>",
  "url": "<linear project url>",
  "issue_map": { "<stable hash of the tasks.md line>": "LUC-123" },
  "last_synced_at": "<ISO-8601 UTC>"
},
"scrum": {
  "cadence_weeks": 2,
  "estimate_scale": "fibonacci",
  "velocity_target": null,          // learned from cycle history; asked on first cycle
  "states": {
    "backlog": "Backlog", "todo": "Todo", "in_progress": "In Progress",
    "in_review": "In Review", "done": "Done", "blocked_label": "blocked"
  }
}
```

- `issue_map` keys are a **stable hash of the tasks.md task line** so re-running Setup/Sync never creates duplicate issues.
- `velocity_target` is null until there is cycle history to learn from.

## dev-flow changes (minimal)

- **Routing**: at `prd_drafted` / `tasks_split`, propose `linear-scrum` (Setup) as the default PM step, skipped only on explicit opt-out.
- **Horizontal family**: add `linear-scrum` to the ongoing-capability skills (alongside the discipline skills) for recurring Sync.
- **Policy line** in dev-flow: *"every project is run in Linear with scrum unless the user explicitly opts out."*
- No `phase` enum change; no change to `contracts.md` beyond documenting the optional `linear` / `scrum` `meta.json` blocks.

## Constraints & `[VERIFY]` markers (house-style)

- Depends on the **connected Linear MCP**; the headless loop uses the API-key path in `loop-engineering.md`.
- **Cycles** may not be creatable via MCP → Setup falls back to instructing the user to enable "Cycles" in Linear once. `[VERIFY]`
- **Estimates** require the estimate scale enabled on the team. `[VERIFY save_issue accepts estimate]`
- **`blocked` is a label, not a state** (the team has no Blocked state).
- **One team, many Projects** — never create a team per project.

## Definition of Done (of the skill's runs)

- After Setup: `list_issues` on the Project returns the pushed issues; `meta.json#linear` populated; **a re-run creates no duplicates**.
- After Sync on a project with an active cycle: a sprint/velocity report is produced and the active cycle contains planned issues up to the velocity target.

## Open questions (to settle in the plan)

1. **Report persistence**: deliver sprint/velocity reports to chat only, or also write `.workflow/reports/sprint-<n>.md`? (Leaning chat-only to avoid another drift-prone artifact.)
2. **Estimate source**: when `tasks.md` has no `Estimated:` hint, prompt per task, batch-prompt, or default to unestimated? 
3. **Skill name**: `linear-scrum` vs `project-to-linear` vs `scrum-sync`. (Current pick: `linear-scrum`.)
