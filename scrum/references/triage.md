# Triage — a bug's short path

A bug repairs what was already promised, so it does not go through the PRD or `tasks.md`. It goes straight to the
tracker, with a severity that decides when it is worked on.

## The severity

| | When | What happens | Priority |
|---|---|---|---|
| **S1** | broken for everyone, data lost or exposed, a security hole | worked on now: into the current sprint, outside the velocity target; fix, verify, release | highest (GitHub `priority: P0`) |
| **S2** | an important feature does not work and there is no way around it | into the current sprint | high (P1) |
| **S3** | there is a way around it | at the next sprint planning | medium (P2) |
| **S4** | cosmetic, copy | backlog | low (P3) |

The labels are `scrum.severity_labels` (`severity: S1` … — the repo's or workspace's own spelling when it already has
them) and `scrum.bug_label`. When unsure between two, take the higher one and say why.

## The four steps

1. **Reproduce** on the real app, with the project's `verify-<app>` manual (`app-verification`): the steps, what was
   expected, what happened. A bug that does not reproduce is recorded as such (S4, "not reproduced"), with what was
   tried, and the reporter is asked for more.
2. **Give the severity** with the table above, telling the user the reason in one line.
3. **Create the issue** on the tracker: the bug type or label, the severity, the priority; the body has *Steps*,
   *Expected*, *Observed*, *Evidence* (log lines, a screenshot, the `request_id` from observability), *Severity
   because*. **Never an end user's personal data**: an id, not an email; no screenshot with real data; redact log
   lines. The tracker is the team's tool, not a place the product's users agreed their data would go.
4. **Place it**: S1/S2 into the current sprint; S3 in the backlog, raised at the next sprint planning; S4 in the backlog. History entry
   `{skill: "scrum", action: "triage"}`.

## Where Triage stops

`scrum` does not touch code. The fix is the normal path, which dev-flow proposes:
- a test that reproduces the bug, red then green (`write-tests`);
- the skill that owns the code;
- a PR that cites the issue;
- verification on the app;
- the issue closed with the commit.

## A single small feature

Not a bug, but just as short: it passes `prd-from-idea/references/scope-check.md` (four questions), is recorded with
`scope.py record`, becomes one task in `tasks.md` (`prd-to-tasks` revise mode), and Sync pushes it. The PRD is not
rewritten.
