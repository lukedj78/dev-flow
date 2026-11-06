# Verification and cleanup — evidence before deletion

## Verify first, and verify means measured

```bash
python3 release-intelligence/scripts/release.py <root> verify REL-… --evidence '{…}'
```

Two refusals, both deliberate:

- **below 100% exposure** — a release is verified at full exposure, not part-way. A feature that is
  healthy for 50% of users is a feature with an unmeasured half.
- **without evidence that clears the thresholds** — the same `health_verdict` the stages use. A
  release is complete when its health was measured at full exposure, **not when the last stage was
  set**. Setting the last stage is a write; completing a release is a finding.

What else belongs in the verification, which the script cannot check and the agent must:

- the feature was **driven on the real app** — `app-verification`'s feature file for this story, with
  its evidence. Errors show failures, not wrong-but-successful work: an email that sent the wrong
  total throws nothing;
- the **business metric** moved, or did not. One metric, from the PRD's success criteria
  (`references/release-health.md` §Business health);
- no unresolved errors in the release's own tag that were dismissed as noise during the rollout.

`verify` writes `verified_at` and `status: "complete"`. That timestamp starts the soak clock.

## Then wait — the soak period

```json
"release": { "cleanup_policy": { "min_days_at_100": 7 } }
```

Seven days by default. The number exists because of weekly patterns: a flag removed on Friday
afternoon takes the monthly-invoice path with it, and nobody runs the monthly invoice until the
first. **Set it to cover at least one full cycle of whatever the feature participates in** — a week
for ordinary traffic, a month for anything that runs monthly.

```bash
python3 release-intelligence/scripts/release.py <root> cleanup-due
```

Three buckets, and the two that are not "due" are as useful as the one that is:

| Bucket | Meaning |
|---|---|
| **DUE** | verified, soaked, and the flag has outlived its purpose |
| **WAITING** | verified, not yet old enough — with the date and the policy |
| **NOT ELIGIBLE** | the release is not `complete`: a flag is not retired before its release is verified |

## Cleanup is a code change first, an API call second

This is the ordering mistake that creates the worst outcome of the whole lifecycle: **archive the
flag while the code still reads it, and the code takes the provider's default** — which, for a flag
that was `true` in production, is usually `false`. The feature silently reverts for everyone, with no
deploy, no error, and no event anywhere.

So the order is fixed:

1. **Remove the branch from the code.** Delete the losing path, inline the winner, delete the
   `flag()` declaration, delete the tests for the dead path.
2. **Ship that**, as its own release. It is a behaviour-preserving change, which makes it `low` risk
   and a one-line revert — the cheapest release the project will ever do.
3. **Then archive the flag** at the provider (`archiveFlag`, not `deleteFlag` — archiving is
   reversible and keeps the audit history; `references/provider-launchdarkly.md`).
4. **Then the schema contract phase**, if the release had one
   (`references/database-migrations.md` §4).

`cleanup-due` greps the repository for the flag key and tells you which files still mention it,
precisely so step 1 is visible before step 3 is attempted.

## 🔴 A grep sees this repository, not the other clients

The one thing the script cannot know. The same flag key may be evaluated by:

- a mobile app on a version users have not updated — **and will not update**;
- another service, another repo, a job, a webhook handler;
- a cached client bundle still in someone's browser.

**Before archiving, confirm with the provider that nothing still evaluates it.** LaunchDarkly answers
this directly: `GET /api/v2/flag-status/{projectKey}/{featureFlagKey}` for the evaluation status
across environments, and `GET /api/v2/engineering-insights/charts/flags/stale` for its own staleness
view. Check `GET /api/v2/flags/{projectKey}/{featureFlagKey}/dependent-flags` too — a flag used as a
prerequisite by another flag is not dead, and removing it changes the other one's behaviour.

A grep that comes back empty plus a provider that says "last evaluated 40 days ago" is evidence. A
grep alone is a guess.

## The cleanup PR

`cleanup_pr` is `auto` up to `high` risk in `automated` mode — because **a PR is a proposal, and
merging it is still a person's click**. What it should contain:

- the dead path removed and the winner inlined, nothing else — no drive-by refactor, or the revert
  stops being one line;
- the `flag()` declaration gone from `lib/flags.ts`;
- the tests for the removed path deleted, and the remaining tests no longer parameterised over the
  flag;
- a body that names the release id, the verification date, and the provider evidence that nothing
  evaluates the key.

⚠️ GitHub notifies the owner of any `@name` in a PR body. Do not interpolate a flag maintainer's
handle out of a provider API response into prose; put it in backticks or leave it out.

## Legacy code is not only the flag

While the branch is being removed, the things that usually survive it and should not:

- the **dual-write** from a migration's expand phase — still writing a column nobody reads;
- the **backfill script**, which will be run again by accident one day;
- **feature-specific env vars** in Vercel, in every environment, which outlive the code by years;
- the **old route** kept "just in case", unreachable from the UI and reachable from the internet —
  and still a surface `app-security` has to audit.

## Where the findings go

Cleanup that cannot be done now is **a task on the tracker**, through `scrum`, with the release id in
it. Not a list inside this skill's own files. dev-flow has one register for work and it is the
tracker — the user's standing rule, and the reason a "minor findings ledger" is not a thing here
(`feedback_leave_nothing_behind`: the minors of a review get closed, not parked).

If the cleanup turns out to need a product decision — someone still wants the old path —
that is a scope change, and it goes through `prd-from-idea/references/scope-check.md`.
