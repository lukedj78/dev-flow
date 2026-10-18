# GitHub — the adapter

How each `scrum` operation maps to GitHub when `meta.json#tracker.provider` is `github`. Everything goes through
`gh` (logged in: `gh auth status`), and the issue push is a script, `scripts/github_sync.py`.

## The rules (the user's, 2026-10-14)

- **A sprint is one milestone, named by its goal** (`Sprint 1 — Fondamenta`, not `Sprint 1`), with `due_on` the
  sprint's last day and, in its description, the goal in a sentence, dates, load against capacity, priorities, stories,
  ceremonies, Definition of Done.
- **Every issue carries `priority: Pn`** (P1–P3; P0 only for an S1 bug).
- **Every body is written to the standard** (`issue-standard.md`), never left as the stub the script creates.
- Size the sprints from the estimates and the capacity the user gives (hours per sprint, sprint length): pack in
  dependency order, setup and domain first; start a new sprint at the boundary between priority bands, so a release
  closes on a sprint boundary. Spare capacity in the last sprint of a release is kept for testing and review. Write
  the plan to `.workflow/sprints.md`.

GitHub Projects v2 is **not** used: the rule is milestones, and the projects already on GitHub use them.

## Operations

| Operation | How |
|---|---|
| The container | the repository (`project-infra-setup` creates it); `tracker.project = {"repo": "owner/name"}`, `url` its address |
| Push issues | `github_sync.py <root> --repo O/N --milestone "<Sprint N — goal>"` — creates the open tasks missing from `issue_map`, with `area:`, `tipo:`, `estimate: N`, `priority: Pn`; reuses the repo's labels (case-insensitive); records each issue in `meta.json#tracker.issue_map` as soon as it exists. `--dry-run` reads only |
| Bodies | one file per task under `.workflow/issue-bodies/<slug>.md`, applied with `gh issue edit <n> --body-file <file>`, 1 s apart |
| Move into a sprint | `gh issue edit <n> --milestone "<title>"` |
| States | open / closed, plus the labels `status: in progress`, `status: in review` and `blocked` (`scrum.states`) |
| Estimate | the label `estimate: N` (Fibonacci) |
| Comment | `gh issue comment <n> --body-file <file>` |
| Adopt | `gh issue list --repo O/N --state all --json number,title --limit 1000`, matched by title to `tasks.md`, then `meta_tracker.py record-issues`; an old `.workflow/github-issues.json` or a title-keyed map is folded in by `meta_tracker.py migrate` |

## Velocity

Sum the `estimate: N` labels of the issues closed in the last closed milestones
(`gh api "repos/O/N/milestones?state=closed"`, then `gh issue list --milestone "<title>" --state closed --json labels`).

## Data residency

github.com stores data in the US. EU residency is GitHub Enterprise Cloud with data residency (`*.ghe.com`), where the
API base changes (`gh auth login --hostname <name>.ghe.com`).
