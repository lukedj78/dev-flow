# Jira — the adapter

How each `scrum` operation maps to Jira when `meta.json#tracker.provider` is `jira`. Jira is driven through the
**Atlassian Rovo MCP** (`https://mcp.atlassian.com`, OAuth — the user connects it; tools as listed on Atlassian's
«supported tools» page, read 2026-10-18), plus one script for story points.

**First real run: 2026-10-20** (streaming-hub, a new team-managed Scrum project on Jira Cloud). What the run proved
is in §Verified on a real site below; where it contradicts the table, the verified section wins.

## Connecting

- The MCP needs Jira enabled for the user's account; `delete_jira` and `manage_jira` (project creation, workflows)
  are off by default — this skill needs neither.
- **The Jira project and its scrum board are created by the user** (Jira's own UI): creating a project is
  `manage_jira`, an admin permission. Setup links what exists.
- Data residency: EU or Germany on the Standard, Premium and Enterprise plans (Atlassian's data-residency page); Free
  is not listed.

| Operation | Tool | Notes |
|---|---|---|
| Find the project | `listJiraProjects` | record `site` (`<name>.atlassian.net`), `project_key` in `tracker.project` |
| Find the scrum board | `listJiraBoards`, `getJiraBoardConfig` | record `board_id`; the config names the board's estimation field |
| Issue types and fields | `listJiraProjectIssueTypesMetadata`, `getJiraIssueTypeMetaWithFields` | which types exist (Story, Task, Bug) and which fields are editable |
| Create an issue | `createJiraIssue` | summary, description (the issue standard), type, labels, priority |
| Edit an issue | `editJiraIssue` | labels, priority; **not story points** (below) |
| Story points | `scripts/jira_estimate.py <root> --key ABC-1 --points 3` | Jira's estimation endpoint, credentials from `JIRA_EMAIL` / `JIRA_API_TOKEN` |
| Move an issue | `listJiraIssueTransitions` → `transitionJiraIssue` | also moves it into a sprint or the backlog |
| Sprints | `listJiraBoardSprints`, `manageJiraSprint` | create, populate, start, close a sprint (since 2026-08-29) |
| Search | `searchJiraIssuesUsingJql` | Adopt discovery, velocity, the duplicate check |
| Comment | `addOrEditJiraIssueComment` | scope-change reasons, the sprint report if the user wants it there |

## Story points — why a script

`editJiraIssue` sets only fields that are editable on the issue's screen, and writing the story-points custom field
through the MCP is reported not to work. Jira's agile REST writes the **board's** estimation field whatever the
screen: `PUT /rest/agile/1.0/issue/{key}/estimation?boardId=`. `jira_estimate.py` does that with Basic auth from
the environment. It sends the credentials only to `https://<name>.atlassian.net`, or to the exact site in `JIRA_SITE`
(Jira Data Center, a proxy) — `meta.json` is in the repository and must not be able to point them elsewhere. The
token is created by the user at id.atlassian.com → Security, and **never passes through the chat**.

## Priority and severity

Jira's priority is native. A bug is the Bug issue type (or the `bug` label where the project has no such type), with
the severity label and a priority: S1 → Highest, S2 → High, S3 → Medium, S4 → Low (`triage.md`).

## Velocity

There is no velocity endpoint. Sum the estimates of the issues Done in the last closed sprints
(`listJiraBoardSprints` state closed, then `searchJiraIssuesUsingJql` `sprint = <id> AND statusCategory = Done`).

## Idempotency

Never create an issue whose `task_key` is in `meta.json#tracker.issue_map`; record each new one with
`meta_tracker.py record-issues` right after it is created.


## Verified on a real site (2026-10-20, team-managed project)

- **How the tools are exposed.** Only a few are direct tools (`createJiraIssue`, `editJiraIssue`,
  `transitionJiraIssue`, `getJiraIssue`, `searchJiraIssuesUsingJql`, `addOrEditJiraIssueComment`,
  `getAccessibleAtlassianResources`). Everything else is found with `discover` and run through `executeRead` /
  `executeWrite` by name, always with `cloudId` (from `getAccessibleAtlassianResources`, once per session).
- **`listJiraBoards` is not exposed.** Find the board with `getJiraBoardSprintData` (`projectKeyOrId`, `boardType:
  "all"`, a dummy `sprintName`): with no active sprint it errors, with an unknown sprint name it returns the board
  id **and** the list of sprints. A team-managed project has one "simple" board; `createJiraBoard` rejects it.
- **`manageJiraSprint` is not exposed.** No sprint can be created, renamed or started from the MCP. A new Scrum
  project ships with `<KEY> Sprint 1` (future): fill it with `createJiraIssue(assignToSprint: <id>)` or
  `transitionJiraIssue(sprintId)`; the owner creates later sprints in Jira, and Setup writes the plan to
  `.workflow/sprints.md` meanwhile.
- **Story points work through the MCP** on team-managed projects: the field is `Story point estimate`. Its
  `customfield_*` ID differs per site — read it on the site with `getJiraIssueTypeMetaWithFields`
  (`requiredFieldsOnly: false`), never reuse one from another project. Set it with
  `createJiraIssue(additional_fields: {"<that id>": 3})` and read it back with `getJiraIssue(fields: [...])`. `scripts/jira_estimate.py` stays the fallback for company-managed screens; no token
  was needed here.
- **Priority:** the field is not on a team-managed Story's create screen, yet every issue reads `Medium`. The
  owner chose labels `P1`/`P2`; whether `createJiraIssue(priority: …)` is accepted there is **untested**.
- **Epics:** `issueType: "Epic"`, then Stories with `parent: <EPIC-KEY>` — verified.
- **Task lists:** markdown `- [ ]` is stored escaped (`\[ \]`), shown as literal brackets — readable, not interactive.
- **The project is created by the user** (Jira UI): the MCP has no Jira project creation (`createProject` is an
  Atlassian *Projects* item, not a Jira project).
- **Versions (milestones):** `manageJiraProjectVersion` (via `executeDestructive`) creates them, but on a team-managed
  project `fixVersions` is not on the Story screen until the owner turns on **Releases** (Project settings ›
  Features): `editJiraIssue` fails with `INVALID_FIELD_VALUE … "fixVersions" was not found`. Ask the owner first.
- **Subtasks:** `createJiraIssue(issueType: "Subtask", parent: <STORY>)` works (89 created, 2026-10-20); plan kept in
  `.workflow/subtasks.md`.

