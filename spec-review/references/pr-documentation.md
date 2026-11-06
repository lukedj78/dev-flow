# The PR body — twelve sections, and the ones you are allowed to leave out

A PR is where a review stops being the agent's working notes and becomes something a person can act
on. This is the template, and the rule that matters more than the template: **a section that says
nothing is worse than a missing one**, because it reads as "checked and fine".

Everything here is filled from what was actually recorded — `meta.json#spec_review` (the findings and
the level), `#verification`, `#security`, `#release` — or it says, in words, that it was not assessed.

## 🔴 Three rules before the template

1. **Never write a section you did not do.** *"Tests: all passing"* with no command output is an
   opinion. The honest forms are **"not assessed"**, **"not verified"**, **"not applicable"** — and
   each of them is a legitimate, final answer that a reviewer can price.
2. **Missing evidence is never evidence.** A blank Verification section does not mean the change is
   safe; it means nobody looked. Say which.
3. **Do not flood GitHub.** One body, no per-finding comments, no bot replying to itself. Only open
   findings, accepted trades and the human decisions go in — a rejected finding stays in
   `meta.json#spec_review` where it belongs.

## The template

```markdown
## Summary
<two or three sentences: what changes for a user, not what changed in the files>

## Requirements and scope
- Implements: <US-N / T-NN from tasks.md, quoted>
- Out of scope, deliberately: <what a reader might expect and will not find>
- Scope changes: <a row of PRD ## Scope changes, or "none">

## Files and components affected
<the diffstat, plus one line per area that matters and why it was touched>

## Tests executed
| What | Command | Result |
|---|---|---|
| unit | `pnpm test` | 48 passed |
| types | `pnpm tsc --noEmit` | clean |
| lint | `pnpm lint` | clean |
| e2e | — | **not executed** — no suite on this project yet

<Paste the last lines of output for anything load-bearing. "Green ✓" is an opinion;
the output is a fact the reviewer can re-run.>

## E2E verification
<The flows actually driven, with the manual that drove them (.claude/skills/verify-<app>/).
Never list a flow that was not executed. If none were: "not verified — no flow was driven".>

## Verification artifacts
<Before/after screenshots for a visible change, a recording only when a still cannot show it.
Say where they are. Omit the section entirely if there are none — do not write "N/A".>

## Impact assessment
<From the Risk axis: which sensitive areas are touched (auth, permissions, payments, PII,
migrations, multi-tenancy, API contracts, infra) and whether the change widens access,
weakens validation or logs sensitive data. Name the modules downstream.>

## Rollback strategy
<Two-way door or one-way door, and the one-way doors by name. For a migration: what a
deployment rollback leaves behind. Required for anything high-impact — "revert the commit"
is only true when it is true.>

## Monitoring and error detection
<If this breaks in production, who finds out first, and from what? Against
meta.json#observability, not against an ideal. "No monitoring on this project" is an
answer, and an earlier conversation.>

## Merge risk
<The three axes' verdicts, not a score. The level, and what it means for who merges.>

## Outstanding findings
| ID | Severity | Where | What | Status |
|---|---|---|---|---|
| F3 | high | `lib/db/schema.ts:42` | migration drops `client_choice` with no backfill | open |
| F7 | medium | `app/api/orders/route.ts` | no owner filter on the query | accepted — "ok, single-tenant for now" (luca) |

## Required human decisions
<One line per thing the agent will not decide. Each is a question with the options,
not a description of a problem.>
```

## Filling it from what was recorded

| Section | Source |
|---|---|
| Requirements and scope | `.workflow/tasks.md`, `PRD.md ## Scope changes` |
| Tests executed | the commands you ran, with output |
| E2E verification | `meta.json#verification` + the run's own evidence directory |
| Impact, Rollback, Monitoring | `meta.json#spec_review.risk` (verdicts, `one_way_doors`, `sixth_question`) |
| Merge risk | `meta.json#spec_review` — verdicts and `level` |
| Outstanding findings | `findings.py status --json`, filtered to `open` and `accepted` |
| Required human decisions | the findings flagged `needs_human` |

## The sections you may drop, and the ones you may not

**Droppable when genuinely empty**: Verification artifacts (no screenshots), Scope changes (none),
Required human decisions (none — which is what level 1 and 2 mean).

**Never droppable, because their absence is the finding**: Tests executed, E2E verification, Rollback
strategy, Merge risk. If any of them has no content, it says **"not assessed"** or **"not verified"**
and the review level reflects that — a criterion nobody could check drops the work to level 3 by
definition (`contracts.md` §Intervention levels).

## Two things a PR body must never contain

- **A secret, or a screenshot with one in it.** Check the images before attaching them: an
  authenticated screenshot carries a session, a terminal screenshot carries whatever was in scrollback.
- **A bare `@name`.** GitHub notifies whoever owns that handle. A code owner you mean to involve is a
  deliberate mention; a handle interpolated out of a provider's API response or a `CODEOWNERS` parse
  is a stranger's notification. Put roles and placeholders in backticks.

## Where this fits

`dev-flow/references/finishing-a-feature.md` decides *whether* to merge and at what level; this file
decides what the PR says. The body is written **after** the review closes, so the level and the
findings are real values rather than predictions — and `release-intelligence`'s manifest, where that
capability is enabled, carries the same risk facts forward to the release.
