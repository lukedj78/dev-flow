# Progressive delivery — two layers, and the rule that time never advances a stage

## The distinction everything else depends on

"Roll out to 25%" means two completely different things, and a team that has not separated them
cannot say what a given user was served.

| | **Traffic-level** | **Audience-level** |
|---|---|---|
| What moves | requests, between **two deployments** | which users get **a branch inside one deployment** |
| Unit | % of traffic | % of a bucketed context (user, org, …) |
| Tool | `vercel rolling-release` | a feature flag |
| Granularity | the whole deployment, every change in it | one feature |
| Rollback | abort → traffic returns to the old deployment | turn the flag off |
| Covers a migration | **no** | **no** |
| Owner here | `vercel-deploy` | this skill |

They compose, and the composition is the useful part: ship the deployment behind a rolling release
so an infrastructure mistake is caught at 10% of traffic, and put the *feature* behind a flag so a
product mistake is caught on 5% of users without touching the deployment. What you must not do is
run both at once and then try to explain a metric: a user in the 10% traffic slice who is also
outside the 5% flag cohort saw the new deployment and the old feature. **Pick one layer per
question.**

### Traffic-level: `vercel-deploy` already owns it

`vercel rolling-release` (`rr`) with `enable`, `configure`, `approve`, `abort`, `complete`, `fetch`.
Vercel's own words: *"Rolling releases gradually shift traffic to a new deployment in stages,
allowing you to monitor for errors before serving all traffic"*. The runbook is
`vercel-deploy/references/rollback-runbook.md`, including the fact that **aborting a mid-flight
release is faster than rolling back** — it stops the shift instead of re-pointing domains after it.

Nothing about it is repeated here. When the answer is traffic, the answer is that file.

## Audience-level: the stage loop

```bash
python3 release-intelligence/scripts/release.py <root> stage REL-… --to 5 \
  --evidence '{"window_minutes":60,"error_rate_pct":0.2,"p95_ms":430,"sufficient":true}'
```

Where the provider has a native release primitive, **use it instead of this loop** —
LaunchDarkly's `POST …/releases` takes phases and their step schedule in one call, and its `…/stop`
resolves pending phases properly (`references/provider-launchdarkly.md`). The loop here is for
providers with no equivalent, and for the decision record either way.

### The stages are not a default, they are a parameter

`1 → 5 → 25 → 50 → 100` is what the script ships, and it is wrong for most products:

- **A low-traffic product learns nothing from 1%.** With 400 weekly users, 1% is four people and a
  0% error rate means "nobody tried it". Compute the smallest stage that yields a usable sample
  within one observation window, and start there.
- **A payment or auth flow should not jump 25 → 100.** Add 75, or stop at 50 for a day.
- **A B2B product should bucket by organisation, not user** — and then "25%" is 25% of tenants,
  which may be 60% of traffic. Say which, in the manifest.
- **An internal tool often wants two stages**: the team, then everyone.

```json
"release": { "rollout_strategy": { "stages": [5, 25, 50, 100] },
             "thresholds": { "min_observation_minutes": 120 } }
```

### Each stage has five parts, and four of them are not the percentage

| Part | Where it comes from |
|---|---|
| **Audience** | the flag's targeting: a rule, a context kind, a bucket-by attribute |
| **Observation window** | `thresholds.min_observation_minutes` — the minimum the evidence must cover |
| **Health criteria** | `thresholds` + the baseline — `references/release-health.md` |
| **Next action** | one of `continue`, `pause`, `rollback`, `insufficient`, or an approval request |
| **Who decides** | the policy table — `references/security-and-approvals.md` |

### 🔴 Time does not advance a stage

This is the rule the whole mechanism exists to enforce, and it is enforced in code rather than in
prose: **`stage` requires `--evidence`, and refuses anything that cannot prove health.**

| The evidence says | Verdict | What happens |
|---|---|---|
| within thresholds, window covered | `continue` | the stage is recorded with the numbers that cleared it |
| over a threshold | `pause` | refused; `pause` is suggested, and needs no approval |
| far over (default: > 2× the error threshold) | `rollback` | refused; `rollback` is suggested |
| no numbers / short window / `sufficient: false` / `provider_error` | **`insufficient`** | refused |

`insufficient` is the default answer, not an error case. Every path that cannot *prove* health lands
there. **Missing telemetry has never been proof that a release is healthy** — and a rollout that
advances because thirty minutes elapsed is exactly a rollout with no telemetry, dressed up.

A refused stage is still **recorded as an event** on the release, with the evidence that failed. That
is the audit trail: six weeks later, "why did this sit at 5% for two days" has an answer.

### The other refusals

- **A stage cannot go backwards.** `--to` must exceed the current exposure; reducing exposure is what
  `pause` and `rollback` are for, and they have their own records and their own semantics.
- **In `assisted` mode a stage needs an approval even with perfect evidence.** The health check and
  the authorisation are different questions; good numbers are not permission.
- **In `automated` mode only a `low`-risk release advances unattended.** `medium` and above wait.
  `flag_rollback` is the one row allowed up to `medium`, because turning a flag off is cheap to undo.

## Catching up after a stall — a platform behaviour worth knowing

If a scheduler cannot deliver on time it may deliver late, and when delivery resumes it can fire
every occurrence that has not expired. Vercel Schedules documents this for cron: an every-minute
schedule delayed two hours *"runs up to 12 times when delivery resumes"* (read 2026-11-06). Anything
in a rollout loop that is driven by a schedule — a health poll, a stage advance, a dispatcher —
must therefore be **idempotent and must compare the scheduled time to now**, or a stall produces a
burst that advances several stages in a minute. If the loop runs as an eve schedule, the
atomic-lease pattern in `eve-agent/references/eve-patterns.md` §4 is the shape that survives it.

## What a percentage does not do

- **It does not reduce blast radius for a migration.** The schema is shared by 100% of the traffic
  from the moment it is applied. `references/database-migrations.md`.
- **It does not contain a side effect.** The 5% cohort that sent a wrong email sent a wrong email.
  Exposure limits who sees the branch, not what the branch did.
- **It does not make the feature optional for the server.** The endpoint is reachable by anyone who
  can form the request. The flag is UI; the session check is security.
- **It does not sample randomly.** Bucketing is a stable hash, your own team is usually individually
  targeted, and the first stage therefore looks healthy to the people watching it.
