# Release health — and the four states, because "healthy" and "unmeasured" are not the same

## The four states, kept apart on purpose

Most rollout tooling has two: good and bad. That collapse is the bug, because the third and fourth
states are where real releases live.

| State | What it means | What the rollout does |
|---|---|---|
| **technically healthy** | errors and latency within thresholds, over a window long enough to mean something | may advance |
| **technically unhealthy** | a threshold crossed, or a regression against the baseline | pause, or roll back |
| **business-unhealthy** | the technical numbers are clean and the product metric fell | **pause** — and this is the one nobody watches |
| **insufficient** | not measured, not measured long enough, or the provider failed | **refuse to advance** |

`release.py` returns exactly these (`insufficient`, `pause`, `rollback`, `continue`), and `stage`
and `verify` both refuse on anything but `continue`.

## 🔴 Insufficient is not a pass

A release that cannot be measured is not a healthy release. Every one of these is `insufficient`,
and each has a test:

| Input | Why it is a refusal |
|---|---|
| no `--evidence` at all | nothing was measured |
| `"sufficient": false` | the agent that collected the numbers said they do not support a decision |
| `"provider_error": "sentry 503"` | **a provider failure is not a green light.** The most dangerous shape: the dashboard is empty, so the chart looks perfect |
| `window_minutes` below the project's minimum | a stage is not cleared by waiting less than the window |
| neither `error_rate_pct` nor `p95_ms` present | there is no signal to judge |

The asymmetry is deliberate and it is the opposite of fail-open: **advancing requires proof,
retreating requires none.** `pause` and `rollout_abort` are `auto` in every autonomy mode.

## The thresholds

Defaults in `release.py`, overridable per project in `meta.json#release.thresholds`:

```json
"thresholds": {
  "error_rate_pct": 1.0,
  "p95_ms": 1200,
  "min_observation_minutes": 30,
  "rollback_multiple": 2.0
}
```

- `error_rate_pct` — above it, `pause`. Above `error_rate_pct × rollback_multiple`, `rollback`
  without waiting for a person: two thresholds, because "slightly worse" and "on fire" are different
  decisions and a single number forces you to pick one of them.
- `p95_ms` — above it, `pause`. Latency rarely warrants an automatic rollback; it warrants stopping.
- `min_observation_minutes` — the floor on the evidence window. **Set it from traffic, not from
  taste**: the window must contain enough requests for the error rate to be meaningful. At 10
  requests a minute, 30 minutes is 300 requests and a 1% threshold is noise.

**Every default here is wrong for some project.** An API with a 1% baseline error rate from client
retries will pause constantly at `error_rate_pct: 1.0`; a payment flow should be at `0.1`.

## The baseline, and why an absolute threshold is not enough

A release at 0.6% errors passes a 1.0% threshold and is a disaster if the previous release ran at
0.05%. So when the evidence carries a `baseline`, a release that **more than doubles** the baseline
error rate pauses even while under the absolute limit — with a floor of 0.1 percentage points, so
that 0.00% → 0.02% is not treated as a tenfold regression.

```json
"baseline": { "release": "def5678", "error_rate_pct": 0.05, "p95_ms": 410 }
```

Getting the baseline right needs one thing from `module-add observability`, which it already does:
**every event carries the release tag.** Without it, "before" and "after" cannot be separated and the
comparison is between two overlapping populations.

⚠️ **Compare like with like.** The 5% cohort is a bucketed hash, not a random sample: it may skew to
heavy users, to one region, or — if your team is individually targeted — to people who know how the
feature is supposed to work. A cohort/baseline comparison across a weekday boundary is also not a
comparison. When the populations are not comparable, the honest answer is `insufficient`.

## Business health — the state that gets skipped

Technical health answers *did it break*. It does not answer *did it work*. A checkout that throws no
errors and converts at 40% instead of 61% is a successful release by every number on this page except
the one that matters.

```json
"business": { "checkout_completion_pct": 40.1, "baseline_checkout_completion_pct": 61.2 }
```

Pick **one** business metric per release, from the PRD's own success criteria (`PROJECT.md`
§Success criteria, or the Playbook §Success metrics on the founder path) — not a dashboard full of
them. The one metric the feature was built to move is the one that says whether to continue.

This is also the limit of automation, honestly stated: a conversion drop needs a person, because the
alternative explanation is always "it is Tuesday". The script does not judge `business`; it carries
it into the record so the person deciding sees it.

## Where the numbers come from

The evidence is **passed in**, not fetched by this skill. Two reasons, and the second is the one that
matters: the decision stays auditable from `meta.json` alone, and this skill never holds an
observability credential.

| Source | How the agent reads it |
|---|---|
| **Sentry / GlitchTip** | wired by `module-add observability`, verified by `observability_check.py`. Issues and events filtered by the release tag |
| **Vercel** | `vercel logs --environment production --status-code 5xx --since 30m`, and Observability in the dashboard. ⚠️ **runtime logs are kept one hour on Hobby** — on that plan, capture before you fix, or the evidence is gone |
| **Own-database metrics** | the product level of `module-add analytics`: the activation and conversion SQL, which is where the business metric usually lives |
| **manual** | the user pastes the numbers. Perfectly valid; record `"source": "manual"` so it is visible later |

## What a health check cannot tell you

- **Whether anyone used the feature.** A 0% error rate at 5% exposure is also what "nobody clicked
  it" looks like. Ask for the count, not only the rate — and if the count is tiny, the verdict is
  `insufficient`, not `continue`.
- **Whether the side effects were right.** Emails sent, rows written, payments taken: errors show
  failures, not wrong-but-successful work. That is `app-verification`'s question, and a release of
  anything with side effects should have its feature file proven before the rollout, not after.
- **Whether the schema is fine.** Nothing on this page sees the database.
  `references/database-migrations.md`.
