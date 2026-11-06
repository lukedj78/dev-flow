---
name: release-intelligence
description: 'Govern what happens between "the code is done" and "production is healthy": a Release Manifest with a measured risk floor, a feature-flag strategy, progressive exposure that advances only on measured health, pause and rollback, verification, and flag cleanup. Optional per project and off by default; provider-agnostic on the Vercel Flags SDK, with LaunchDarkly as the first adapter. Use when the user says "release", "rollout", "feature flag", "progressive delivery", "canary", "rollback", "is this safe to ship", "monitor the release", "clean up the old flags", or dev-flow routes here at `feature_complete` / `deployed`. Not for: shipping itself (`vercel-deploy`, `rn-eas-deploy`), wiring error tracking (`module-add observability`), the five pre-deploy audits (`compliance-audit`, `app-security`, `shadscan`, `vercel-doctor`, `launch-audit`), or reviewing the diff (`spec-review`).'
---

# release-intelligence — from code complete to production confidence

dev-flow takes a project from an idea to a deployment. This skill owns the stretch **after** that:
the release is live, and nobody has decided how much of it serves whom, what would make it stop, or
when the scaffolding comes out.

Today dev-flow names that stretch and owns none of it. `feature_complete` proposes five audits and a
deploy; `deployed` proposes a debt audit and says *"telemetry monitoring"* with nothing behind it.
Searched 2026-11-06: **the suite had zero mentions of feature flags as a capability**, and the only
progressive-delivery knowledge anywhere was two paragraphs about `vercel rolling-release` inside
`vercel-deploy`. That is the gap, and it is the whole scope of this skill.

## This is opt-in, and invisible until it is opted into

A project with no `meta.json#release` block behaves **exactly** as it did before this skill existed:
no gate applies, no skill changes behaviour, nothing is proposed. That is not politeness, it is
correctness — most projects ship a page and do not need progressive delivery, and a capability that
imposes itself on them is a tax.

```bash
python3 release-intelligence/scripts/release.py <project-root> enable --autonomy advisory
```

Four modes, and the default is the one that executes nothing:

| `autonomy` | What the agent may do |
|---|---|
| `disabled` | read and advise only; no mutating operation is ever proposed as executable |
| `advisory` | **the default on enable** — analyse, classify, recommend. Prepares no write |
| `assisted` | prepare every operation fully and wait for the user's explicit yes |
| `automated` | execute the low-risk classes on its own; everything else still waits |

`release.py <root> policy` prints the full table for the project. Two rows no mode can change, and
they are the asymmetry the whole capability rests on:

- **Pausing and aborting are always automatic.** A safety control that waits for a human who is
  asleep is not a safety control.
- **A destructive database operation is never automatic**, in any mode, at any risk level. The
  verdict is "ask the user" at best. See `references/database-migrations.md`.

## 🔴 Every command on this page is the agent's. The user types none of them.

Written down because it was not obvious the first time it was explained: the scripts below are **this
skill's own interface to itself**, plus the audit trail they leave in `meta.json`. They are not a UI,
and a user who has to assemble `--evidence '{"window_minutes":60,…}'` by hand is being handed the
agent's job.

| The user says | The agent does |
|---|---|
| *"is this safe to ship?"* | `risk.py`, then reports the level, the signals **and the `NOT CHECKED` list**, in prose |
| *"go ahead"* | `plan`, then `stage` one step at a time, reading the health numbers between them |
| *"something is broken"* | checks whether it is even the release (`references/incident-recovery.md` §1), then `pause`, then names which of the three rollbacks applies |
| *"how did it go?"* | `status`, reported as exposure, health and what is still open |

**Exactly two things need the user, and neither is a command.** A `high`/`critical` release needs
their yes, recorded in their own words (`approve --user-said`). And anything that touches production
data is described and **not executed**, in every mode.

Everything else — the manifest, the stages, the pauses, the verification, the cleanup list — the
agent does and then **reports in sentences**. Never paste a command list at the user as if it were
instructions; if a number or a decision is needed from them, ask for that one thing in one line.

## Scope — what this skill does not own

| Concern | Owner |
|---|---|
| Building and promoting the deployment, `vercel rollback`, `vercel rolling-release` mechanics | **`vercel-deploy`** (`vercel-deploy/references/rollback-runbook.md`) |
| Mobile release trains, OTA updates, staged rollout on the stores | **`rn-eas-deploy`**, **`rn-eas-build-submit-update`** |
| Wiring the error tracker, logs and `/api/health` | **`module-add observability`** — this skill *reads* what it wired |
| Is the code attackable, lawful, costly, accessible, findable | the five pre-deploy gates. This skill **reads their verdicts**, never re-scans |
| Does the diff match the spec | **`spec-review`** |
| Installing a provider's agent skill or registry item | **`registry-intake skill-review`** |
| The schema change itself | **`module-add db`** writes the migration; this skill classifies it and refuses to run the destructive part |

**It decides and routes. It does not re-implement.** When a rollback is the answer, the answer is
`vercel-deploy`'s runbook — including the trap that a rollback turns off auto-assignment of
production domains, so the next push goes green and does not go live.

## When dev-flow routes here

- `feature_complete`, after the five audits and **before** the deploy → Release Planning + Risk.
- immediately after `vercel-deploy` / `rn-eas-deploy` → progressive exposure and health watching.
- `deployed`, on a material change → a new manifest.
- a production incident → `references/incident-recovery.md`, first page.
- a release complete and soaked → `references/release-cleanup.md`.

It is also invoked directly: *"is this safe to ship?"*, *"assess the risk of this PR"*, *"give me a
rollout plan"*, *"monitor the last release"*, *"prepare the cleanup PR for the old flags"*.

## The lifecycle, and where each step is written down

| # | Step | Where |
|---|---|---|
| 1 | **Release planning** — the manifest: what ships, at what risk, who must agree | `references/release-lifecycle.md` |
| 2 | **Risk assessment** — a deterministic floor the agent may raise and never lower | `references/risk-assessment.md` |
| 3 | **Feature-flag strategy** — whether this release needs a flag at all, and its lifecycle | `references/feature-flags.md` |
| 4 | **Progressive delivery** — two layers, stage gates, and why time never advances a stage | `references/progressive-delivery.md` |
| 5 | **Release health** — the observability contract, thresholds, baselines, and missing telemetry | `references/release-health.md` |
| 6 | **Incident recovery** — three different rollbacks, and what each one does not undo | `references/incident-recovery.md` |
| 7 | **Verification and cleanup** — evidence before deletion | `references/release-cleanup.md` |
| — | Database releases, expand/contract, Neon + Drizzle | `references/database-migrations.md` |
| — | Provider contracts, and the adapter ecosystem we did not have to build | `references/provider-contracts.md` |
| — | LaunchDarkly, verified against its own OpenAPI | `references/provider-launchdarkly.md` |
| — | Tokens, authorization, approvals, audit trail | `references/security-and-approvals.md` |

## Workflow

### Step 0 — is this project a candidate at all?

Read `meta.json`. If there is no `release` block, **say in one line what the capability would add and
let the user decide**; do not enable it. It earns its keep when at least one of these is true:

- the product has users whose bad afternoon costs something (payments, bookings, clinical, legal);
- a release touches authorization, money, or a schema;
- the team wants a feature in production before it is finished for everyone;
- an incident has already happened and "roll back" turned out to mean three different things.

A brochure site, an internal tool, a prototype: **say no**. `references/release-lifecycle.md` §When
not to use this has the argument in full.

### Step 1 — the manifest and the risk floor

```bash
python3 release-intelligence/scripts/risk.py    <root> --base origin/main
python3 release-intelligence/scripts/release.py <root> plan --feature US-7 --base origin/main
```

`risk.py` matches a fixed table of signals against the diff and against what the pre-deploy gates
already recorded, and returns the **highest** level any signal reached. The agent reads the result and
may **raise** it with a reason (`plan --raise-to high --reason "..."`); there is no instruction that
lowers it. A level the agent can argue down is a level that ships a destructive migration on a Friday.

Everything the scan could not see is printed under **NOT CHECKED** and copied into the manifest.
A release classified `low` because nothing could be read is the one failure mode that matters here,
so it is never silent.

### Step 2 — does it need a flag?

Not every change does, and `references/feature-flags.md` opens with the cases that **should not get
one**. A flag is a branch in production that somebody has to delete later; creating one per commit
buys a permanent maintenance cost to avoid a one-line revert.

**If the answer is yes and the project has no flag library yet, that is `module-add flags`** — it
installs `flags` plus the chosen `@flags-sdk/*` adapter, `FLAGS_SECRET`, the provider's own
environment variables, `lib/flags.ts`, the discovery endpoint and the sub-processor entry, and
`module-add/scripts/flags_check.py` says whether it is really wired. This skill decides *which* flag
and *how to open it*; it installs nothing. Check `meta.json#stack.flags` before planning a flagged
release — a manifest naming a flag the project cannot evaluate is a plan with a hole in it.

⚠️ **A feature flag is not an access control.** It decides what the UI offers, not what the server
permits. Every flagged endpoint still checks the session and the tenant, and `app-security` still has
to pass. A flag used as authorization is a vulnerability with a dashboard.

### Step 3 — exposure, one stage at a time

```bash
python3 release-intelligence/scripts/release.py <root> stage REL-… --to 5 \
  --evidence '{"window_minutes":60,"error_rate_pct":0.2,"p95_ms":430,"sufficient":true}'
```

**`stage` refuses without evidence, and refuses on evidence that cannot prove health.** No numbers,
a window shorter than the project's own, a provider that errored, an explicit `sufficient: false` —
all of them are `insufficient`, which is a refusal. Missing telemetry has never been proof that a
release is healthy, and this is where that sentence becomes executable.

The stage list (`1 → 5 → 25 → 50 → 100` by default) is **a starting point, not a truth**: a product
with 400 weekly users learns nothing from 1%, and a payment flow should not jump 25 → 100. Set it
per project in `meta.json#release.rollout_strategy.stages`.

### Step 4 — when it goes wrong

Pause first — it needs no approval and costs nothing. Then read
`references/incident-recovery.md`, whose first question is the one that saves the afternoon: **is it
even the deployment?** If the errors predate the release, rolling back costs you the fix.

### Step 5 — verify, then clean up, in that order

```bash
python3 release-intelligence/scripts/release.py <root> verify REL-… --evidence '…'
python3 release-intelligence/scripts/release.py <root> cleanup-due
```

`verify` refuses below 100% exposure and refuses without evidence: a release is complete when its
health was measured at full exposure, not when the last stage was set. `cleanup-due` then waits out
the soak period (7 days by default) and reports which flags have outlived their purpose — and greps
the repo for the key, because removing a flag is a **code change first** and an API call second.

⚠️ A grep sees this repository. It does not see the other clients that may evaluate the same flag.
Confirm with the provider that nothing still reads it before archiving.

## What this skill records

`meta.json#release`, written only through `release.py`, through `meta_io`'s lock. **It never bumps
`phase`** — that stays with the deploy skills — and it always appends to `history`.

One gate, and it applies **only** when the capability is enabled: `update_meta.py set-phase` (and
`append-history --phase-after`) refuses to cross into `deployed` without a Release Manifest covering
production, and refuses a `high` or `critical` release that carries no human approval with the user's
own words. `dev-flow/scripts/release_gate.py`; `release.py disable` lifts it and leaves the decision
in the file.

## Honest limits, stated once

- **No provider integration in this skill executes a network call.** The contracts, the exact verified
  endpoints and the payload shapes are in `references/provider-contracts.md` and
  `references/provider-launchdarkly.md`; the calls are made by the app's own code or by the user's
  CLI, with the user's credentials. Nothing here holds a token.
- **The health evidence is passed in, not fetched.** `--evidence` takes the numbers the agent read
  from the project's own observability (`module-add observability` wired it) or from a dashboard the
  user pasted. This keeps the decision auditable and keeps this skill out of the credential business.
- **Mobile is partly out of scope.** Store rollouts are staged by Apple and Google on their own
  schedule; `rn-eas-build-submit-update` owns that. The manifest and the risk floor still apply.
