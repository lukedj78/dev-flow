---
name: ci-speed
description: >-
  Make a repository's CI fast without letting it lie: a pull request gets its answer in under 2 minutes at p50 and 3 at p95, and green still means the full suite passed. Audits the last 150 GitHub Actions runs into waiting / setup / running at p50 and p95 (`scripts/ci_audit.py`), fixes the biggest bucket first against per-stage budgets, proves test selection goes red on a hidden change, and lands one small PR per change with before and after numbers from real runs. Faster tools (oxlint, bun, Blacksmith) are candidates, switched only after a side-by-side run. Triggers: "la CI è lenta", "make CI faster", "velocizza la CI", "CI budget", "audit dei tempi di CI", "merge queue", "shard the tests". Not for: setting up CI the first time (`module-add` ci), deploy pipelines (`vercel-deploy`), a red test to fix (`write-tests`).
---

# ci-speed — fast CI that still tells the truth

Speed is the goal; **honest** is the constraint that outranks it. An honest CI is one whose green
means the full suite passed on the code that reaches `main`. Every step below keeps that true.

## Two rules above speed

1. **The full suite runs before anything reaches `main`.** Test selection only narrows the
   feedback on a pull request; the gate into `main` runs everything.
2. **A failure stays visible.** Every check runs once, inside its budget, on every test it owns.
   A check that passes only on a second try has a bug: find the race, the leak or the shared
   state and fix that.

## Where the work lives

- Reads `.workflow/meta.json#stack` when there is one (framework, package manager, data
  residency); works on any repository with GitHub Actions.
- Writes `docs/ci/ci-speed.md` in the project: the audit before, the budgets, each change with its
  numbers, the audit after. It never writes `meta.json` and never changes `phase`.
- The contract is `dev-flow/references/contracts.md` (dev-flow/SKILL.md); a change to a gate other
  skills own (`AGENTS.md`'s design lint, a phase gate) goes through the skill that owns it.

## Step 1 — Audit

```bash
python3 ci-speed/scripts/ci_audit.py <owner/repo> --runs 150 > docs/ci/audit-before.md
python3 ci-speed/scripts/ci_audit.py <owner/repo> --runs 150 --event pull_request
```

It splits every job into three **buckets** — waiting (queued, no runner yet), setup (checkout,
toolchain, cache, install, post-steps), running (the work) — at p50 and p95, gives the pull
requests' feedback time, and names the biggest bucket. Read the setup pattern it prints: a
repository with its own step names passes `--setup-pattern`.

Done when `docs/ci/ci-speed.md` holds the table, the feedback time at p50 and p95, and the bucket
to fix first. The biggest bucket is rarely the tests: fix the one the numbers name.

## Step 2 — The budgets

Each stage has a **budget**, a time it must finish in:

| Stage | Budget |
|---|---|
| Waiting | under 10 s |
| Setup | under 30 s |
| Lint | under 5 s |
| Typecheck | under 5 s |
| Tests | under 60 s per shard |
| Local pre-push hook | under 9 s |

The moves for each bucket, the tools to measure, and how to shape the jobs are in
`references/moves.md`: read it for the bucket you are fixing. Then, once a stage is inside its
budget, make the budget the job's `timeout-minutes`, so a job that slows down fails and says so.

Done when every stage has its budget written in `docs/ci/ci-speed.md`, with its p50 and p95 today.

## Step 3 — One change at a time

For each change, biggest bucket first:

1. **Side by side.** Run the old tool and the new one on the same commit, and list everything the
   new one misses or reports differently. A miss is a reason to keep the old tool for that part,
   written down with its cost.
2. **One small PR**, with the numbers before and after from real runs (`ci_audit.py` again, on the
   runs after the change), and the misses list.
3. A tool the project already has stays only with a measured reason; a newer one that is faster on
   this repository is taken once the side-by-side run is clean.

Done when every change is its own merged PR with its numbers, and the audit after is in
`docs/ci/ci-speed.md` beside the one before.

## Step 4 — Selection, proven red

On pull requests, run only what the diff can reach (`turbo run … --affected`, `nx affected`).
Then prove it cannot lie: on a throwaway branch, make a real change selection might miss — a
shared package, a config file, a fixture — that breaks a test outside the obvious path, and push
it. The run must go **red**. A green run means selection hides failures: widen what it treats as
reaching everything (lockfile, root config, shared packages) until the same change goes red.

Done when the throwaway branch's red run is linked in `docs/ci/ci-speed.md`, then the branch is
deleted.

## Step 5 — What needs Luca

Do everything that needs no account, secret or bigger bill first. Then bring one list: each item
with what it needs (an account, a secret, a plan), its expected monthly cost, and for a service
that receives the code or its logs, where its data lives (`compliance-audit` and dev-flow's
`data_residency.py add` for the register). End with total CI time and cost, before and after.

## Where the defaults meet the project

The tools in `references/moves.md` are defaults to measure. Three frictions come up on almost every
project:

- **No merge queue.** GitHub's merge queue exists for organization repositories that are public or
  on Enterprise Cloud; a private repository on a personal account has none, and on a free plan no
  branch protection either. Rule 1 then lives in whatever merges: the agent or tool that merges
  runs the full suite on the pull request's exact head and refuses on anything but green. Write
  down which path guarantees it.
- **Lint rules of the project's own.** A design-system lint (custom ESLint plugins, a
  `--max-warnings` cap, `AGENTS.md` rules) is a gate other skills own. oxlint takes the rules it
  covers; ESLint keeps the project's own rules until oxlint runs them, proven side by side. The cap
  stays where it is.
- **Data residency.** A third-party runner receives the code and its secrets. On a project with
  `stack.data_residency` set, the runner's regions and transfer terms are checked before moving a
  job, and the provider joins the register.
