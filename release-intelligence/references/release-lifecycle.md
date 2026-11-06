# The release lifecycle — the manifest, and when not to use any of this

## When not to use this

The first and most useful section. **Most projects should not enable this capability**, and an agent
that enables it on a brochure site has added ceremony, not safety.

| Say no when | Because |
|---|---|
| it is a brochure site, a landing page, a portfolio | the undo is a revert, and nobody is mid-transaction |
| it is a prototype or a demo | a rollout plan for software with no users is theatre |
| it is an internal tool with ten users who sit nearby | the rollout is "tell them"; the rollback is "tell them again" |
| nothing in it touches money, identity, a schema or a contract | the five pre-deploy gates and a deployment rollback already cover it |
| the team ships once a month and watches it by hand | the manifest adds a file; the practice already exists |

**Say yes when at least one of these is true:**

- a bad afternoon costs something real — payments, bookings, clinical, legal, a tender deadline;
- a release touches authorization, money, or a schema;
- the product wants a feature in production before it is finished for everyone;
- an incident already happened, and "roll back" turned out to mean three different things;
- several people deploy, and they are not all the people who understand the feature.

In the user's own portfolio: **EVE Hospitality**, **BidMaster** and a **gym SaaS** with paying tenants
are candidates. **Adastra Cefalù** (three apartments, a vitrine) is not, and
`show_state.py` will never suggest it there — because nothing suggests it anywhere. It is enabled by
hand, once, by the user.

## Enabling it

```bash
python3 release-intelligence/scripts/release.py <root> enable --autonomy advisory
python3 release-intelligence/scripts/release.py <root> policy     # the table for this project
```

`enable` writes `meta.json#release` with `autonomy: "advisory"` — the mode that executes nothing. It
is a deliberate default: the capability starts by having opinions, and earns execution later.

`disable` sets `enabled: false` and keeps every manifest as a record. The gate lifts, and the
decision is in the file rather than in somebody's memory.

## Phase 1 — Release planning

```bash
python3 release-intelligence/scripts/release.py <root> plan --feature US-7 --base origin/main \
  [--pr 42] [--flag-key us-7-new-checkout] [--description "..."]
```

What goes into the manifest, and where each field comes from — **nothing here is invented by the
agent except `description` and the risk raise:**

| Field | Source |
|---|---|
| `id` | `REL-<date>-<NN>`, sequential within the day |
| `feature` | the PRD story or task id. `--feature`, and it is required |
| `environment` | `production` unless told otherwise |
| `commit` | `git rev-parse --short HEAD` |
| `pr` | `--pr`, when there is one |
| `risk` / `risk_floor` / `risk_raised` | `risk.py` — the floor, plus the agent's raise with its reason |
| `risk_signals` | which signals matched, by id |
| `not_checked` | **everything the scan could not see** |
| `reversible_by_deployment_rollback` | false as soon as a migration or an infra change is in the diff |
| `destructive_migration` | the added SQL contains a statement a rollback does not undo |
| `approval` | `required` from the policy table; `granted_by_user`, `quote`, `at` from `approve` |
| `flag` | the key, the provider, whether it exists yet |
| `rollout` | the project's stages, the current exposure, and every step with the evidence that cleared it |
| `status` | `planned → approved → rolling → paused → complete \| rolled_back \| abandoned` |
| `events` | an append-only log, including **refused** stages |

The manifest is a record of decisions, not a plan document. It is short on purpose: a long one would
be written once and then diverge.

### Read the `NOT CHECKED` list out loud

It is the part of `plan`'s output that matters most, and the part an agent will skip. "`app-security`
never ran", "the committed diff was not read", "no verification manual proven" — these are not
caveats, they are the reason the level might be wrong. A release classified `low` because nothing
could be read is this capability's one real failure mode.

## Phase 2 — Risk

`references/risk-assessment.md`. In one line: a deterministic floor from the diff and from what the
gates already recorded, which the agent may **raise** with a reason and may never lower.

## Phase 3 — Flag strategy

`references/feature-flags.md`, which opens with the cases that should **not** get a flag.

## Phase 4 — Progressive delivery

`references/progressive-delivery.md`. Two layers (traffic vs audience), stages that are a parameter
rather than a default, and `stage` refusing to advance on anything but measured health.

## Phase 5 — Health

`references/release-health.md`. Four states, and `insufficient` is a refusal.

## Phase 6 — Recovery

`references/incident-recovery.md`. Three rollbacks that undo three different things, and the database
one that this skill will not run.

## Phase 7 — Verification and cleanup

`references/release-cleanup.md`. `verify` at 100% with evidence, then a soak period, then the flag
and the dead code come out — in that order, with evidence, never on a hunch that it is probably fine.

## Where this sits in dev-flow

```
feature_complete
  │  the five pre-deploy gates: compliance-audit · app-security · shadscan · vercel-doctor · launch-audit
  │
  ├─ release-intelligence: plan ─────────► the manifest, the risk floor, the flag decision
  │
  │  vercel-deploy / rn-eas-deploy / eve deploy        ← the deploy itself, phase → deployed
  │                                                      (the gate checks the manifest here)
  ├─ release-intelligence: stage × N ────► exposure, each stage cleared by evidence
  ├─ release-intelligence: verify ───────► complete
  │
deployed
  │  debt audit · the maintenance loop
  └─ release-intelligence: cleanup-due ──► the flag and the dead path come out
```

**The deploy is not this skill's.** It plans before, watches after, and routes to `vercel-deploy` for
every mechanic in between. The one place it touches the pipeline is the gate into `deployed`, and only
on a project that opted in.

## What it records, and what it never touches

- writes `meta.json#release`, through `meta_io`'s lock, only via `release.py`;
- appends to `meta.json#history` like every other skill;
- **never bumps `phase`** — that stays with the deploy skills;
- never writes application code. The flag declaration, the dual-write, the cleanup PR are produced as
  changes the user reviews, in the project's own conventions (`docs/conventions.md`);
- holds no credential, makes no provider call.
