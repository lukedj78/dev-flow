---
name: scrum
description: 'Run a dev-flow project with agile scrum on the tracker chosen at design time — Linear, Jira or GitHub Issues: records the choice, creates or links the project, pushes `.workflow/tasks.md` into estimated, labelled, prioritised issues, sets up 2-week sprints (Linear cycles, Jira sprints, GitHub milestones), then keeps **the tracker as the source of truth** — new tasks up, status and velocity down, each sprint planned to the velocity target — and triages bugs by severity (S1–S4) without a PRD round-trip. Triggers: "porta il progetto in Linear / Jira / GitHub", "crea le issue", "setup scrum", "pianifica lo sprint", "report di velocity", "adotta questo progetto", "ho trovato un bug", "triage", or dev-flow routing from `tasks_split`. Modes: Choose, Setup, Adopt, Sync, Triage. Not for: writing or estimating the tasks (prd-to-tasks), fixing the bug or building the app (the owning skill), the headless server loop (docs/loop-engineering.md).'
---

# scrum — agile scrum on Linear, Jira or GitHub

This skill owns the **tracker side** of a dev-flow project. It writes to the chosen tracker and to the `tracker` /
`scrum` blocks of `.workflow/meta.json`. It **never** touches app code, and it **never changes `phase`**: it records
state and appends `history`, and is never a phase gate.

The method is the same on every tracker (`references/scrum-model.md`); only the adapter changes:

| | Reference | How it talks |
|---|---|---|
| Linear | `references/linear.md` | the Linear MCP |
| Jira | `references/jira.md` | the Atlassian Rovo MCP; story points with `scripts/jira_estimate.py` |
| GitHub | `references/github.md` | `gh`; issues with `scripts/github_sync.py`; a sprint is a milestone |

Issue bodies follow `references/issue-standard.md` on every tracker. Bugs follow `references/triage.md`.
The `.workflow/` contract is `references/contracts.md`.

## Preconditions

- `.workflow/meta.json` exists (a dev-flow project). If not, say so and stop.
- The tracker's connection works, checked with a read before any write: `list_teams` (Linear), `listJiraProjects`
  (Jira), `gh auth status` (GitHub). No account is created by this skill, and **no token goes through the chat**:
  Jira REST reads `JIRA_EMAIL` / `JIRA_API_TOKEN` from the environment, GitHub uses `gh auth`, the MCPs the user's
  OAuth.
- Setup needs `.workflow/tasks.md` (`prd-to-tasks` first). **Coupled format**: `scripts/task_key.py` derives the
  dedup key from the `- [ ] **<Title>** — <body>` line, splitting on the em-dash; a hand-edited separator breaks
  dedup.

## Read state, then pick a mode

Run `python3 scripts/meta_tracker.py <root>/.workflow/meta.json migrate` first when `meta.json` has an older shape (a
`linear` block, `tracker.kind`, a map keyed by title — `show_state.py` names it): it moves everything into
`tracker` without dropping a key, and keeps titles it cannot find in `tracker.unmatched`.

- No `tracker.provider` → **Choose**.
- A provider, no `tracker.project`, `tasks.md` present → **Setup**.
- The project already exists on the tracker but `tracker.project` or `issue_map` is missing → **Adopt**.
- `tracker.project` present → **Sync**.
- A bug reported (by the user, a test, an alert) → **Triage**, whatever the state.

Do **one** logical operation per invocation, then stop. Every mode is idempotent.

## Choose (normally done by prd-from-idea)

Ask once where the work is managed. Default: the tracker the project or the client already uses; otherwise Linear.
Record it: `meta_tracker.py <meta> choose --provider linear|jira|github`.

## Setup (new project)

**Ask the user's yes before the first write** — it creates a project and issues on an outside service.

1. Resolve the container in the tracker's reference: Linear Project under the team; Jira project + scrum board
   (`listJiraBoards`); GitHub repository.
2. Ensure the scrum configuration: estimates, the sprint (Linear: the user creates the cycle in the app; Jira:
   `manageJiraSprint`; GitHub: the milestone named by the sprint goal), the states.
3. Labels: **discover, don't assume.** Map the buckets (web / agent / scaffold) and the severity labels onto what the
   tracker already has; create only what is missing (`scrum-model.md`).
4. Push `tasks.md` → issues, one per open task: estimate from the `Estimated:` hint (Fibonacci), priority from the
   `Priority:` hint, labels. GitHub: `scripts/github_sync.py <root> --repo O/N` (it migrates an older map first and
   names the tasks with no priority). Linear and Jira: the reference's tools, then `meta_tracker.py <meta>
   record-issues --mapping '{"<task_key>": "<KEY>"}'`. **Then pack the sprints** (`scrum-model.md`: by priority band
   and capacity, spare capacity kept at the end of a release) and assign each issue to its sprint — on GitHub
   `gh issue edit <n> --milestone "<Sprint N — goal>"`, with the plan in `.workflow/sprints.md`. Never every task into
   Sprint 1.
5. Write the bodies to `references/issue-standard.md` — one sample first, approved by the user.
6. Persist: `meta_tracker.py <meta> upsert --provider P --project '<json ids>' --url <url>` (it also ensures the
   `scrum` defaults), then a history entry through `dev-flow/scripts/update_meta.py append-history --skill scrum`
   (`action: setup`). No phase bump.

## Adopt (existing project, partly on the tracker)

1. Discover the existing project and issues (reads only).
2. Match issues to `tasks.md` by title → `task_key`, and **backfill** `issue_map` with `record-issues`; create
   nothing.
3. `ensure-scrum`, then `upsert` with the discovered ids. History `action: adopt`.

## Sync (ongoing)

- **Push new tasks**: each `tasks.md` line whose `task_key` is not in `issue_map` (GitHub: `github_sync.py` does
  exactly this; `--milestone` puts that run's new issues straight into the current sprint). Never edit or re-push existing issues — the tracker owns status, ordering, estimates.
- **Pull status and velocity** from the tracker (the reference says how).
- **Plan the sprint** up to `scrum.velocity_target` (`scrum-model.md`).
- **Report to chat**: committed vs done, carry-over, blocked, open bugs by severity. No report file.
- An issue created mid-sprint that matches no PRD story is a **scope change**: it passes
  `prd-from-idea/references/scope-check.md` before it enters the sprint. A descoped story's issues go back to the
  backlog with the reason in a comment — never deleted.
- History `action: sync`.

## Triage (a bug)

`references/triage.md`: reproduce on the real app (`verify-<app>`), give the severity (S1–S4) with a one-line
reason, create the issue (`bug` + severity, steps, expected, observed, evidence — **never an end user's personal
data**), put S1/S2 in the current sprint, S3 up for the next sprint planning and S4 in the backlog, history
`action: triage`. **Triage stops there**:
the fix is the normal path — a test that reproduces it (red → green), the skill that owns the code, a PR that cites
the issue, verification on the app, then the issue closed with the commit.

## Definition of Done (per run)

- **Setup**: the tracker lists the pushed issues; `meta.json#tracker` populated; a re-run creates **no duplicates**.
- **Sync**: the sprint holds planned issues up to the velocity target, and a report was given.
- **Triage**: the issue exists with severity and evidence, in the right sprint or the backlog.
- Scripts green: `cd scrum/scripts && python3 -m unittest discover -p 'test_*.py'`.

## What this skill does NOT do

- Write or estimate the tasks (`prd-to-tasks`), fix a bug or build the app (the owning skill).
- Run human ceremonies (standup, retro).
- Move a project from one tracker to another, or support other trackers.
- Bump `phase`.
