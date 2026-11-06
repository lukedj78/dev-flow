# Feature flags — when not to create one, and the lifecycle if you do

## Start with the refusals

A flag is **a branch in production that someone has to delete later**. It costs a code path, a test
matrix that doubles, a provider dependency on the request path, and a cleanup task that will be
skipped. Creating one per change buys that permanent cost to avoid a one-line revert.

**Do not create a flag for:**

| Case | What to do instead |
|---|---|
| a copy change, a style fix, a new static page | ship it; the undo is a revert |
| a bug fix | ship the fix; a flag means choosing to keep serving the bug |
| a refactor with no behaviour change | if there is no behaviour change there is nothing to flag; if there is, it is not a refactor |
| "so we can turn it off if it breaks" with nothing identified that could break | that is a deployment rollback, and it already exists |
| controlling who is *allowed* to do something | **authorization** — the session and tenant check. See below |
| a migration | expand/contract, `references/database-migrations.md`. A flag chooses which shape you read; it does not make a schema change reversible |
| an experiment nobody will read the result of | an A/B test with no owner for the decision is a flag with extra steps |

**Create a flag when at least one of these is true**, and say which in the manifest:

- the feature should reach some users before it is finished for everyone;
- it must be switchable **without a deploy** — because the people who will switch it cannot deploy,
  or because minutes matter;
- it is the read-side switch during a dual-write migration window;
- it is a genuine **kill switch** for a dependency you do not control;
- it gates something per tenant for a contractual reason.

## 🔴 A flag is not an access control

The one failure on this page that is a vulnerability rather than a cost.

A flag decides **what the interface offers**. It does not decide **what the server permits**. A
flagged endpoint is reachable by anyone who can form the request — the flag evaluates to `false`
for them and the handler still runs if nothing else stops it.

So, on every flagged surface:

- the Server Action or route handler still checks the session **and** the owner/tenant, exactly as
  `app-security/references/review.md` requires;
- the flag check is **not** the authorization check, and the two are not in the same `if`;
- `app-security` still has to pass. A flagged feature is not exempt from the gate because it is
  "not live yet" — it is live for whoever calls it directly.

Where a feature must be restricted *by entitlement* (plan, role, contract), that is data in your own
database, checked server-side. A flag provider's targeting rules are a convenience for rollout, not
a permission system — and they are evaluated with a client-side id on the client.

## The eight stages, and the two that get skipped

| # | Stage | Who | Recorded |
|---|---|---|---|
| 1 | **Decide a flag is warranted** | agent proposes, user agrees | `flag` block on the manifest |
| 2 | **Create it** | `flag_create`: auto only at `low` risk in `automated` mode | `flag.created` |
| 3 | **Declare it in code** | one `flag()` declaration in `lib/flags.ts` | the diff |
| 4 | **Associate it with the feature** | the key carries the story id: `us-7-new-checkout` | `feature` on the manifest |
| 5 | **Activate for the first audience** | usually the team, individually targeted | stage 0 |
| 6 | **Progressive rollout** | `references/progressive-delivery.md` | `rollout.steps` |
| 7 | **Verify at 100%** ← *skipped* | `verify` refuses below full exposure and without evidence | `verified_at` |
| 8 | **Remove it** ← *skipped* | `references/release-cleanup.md` | `cleanup` |

Stages 7 and 8 are the ones every team skips, which is why a two-year-old codebase has forty flags
and nobody knows which are load-bearing. `cleanup-due` exists to make stage 8 arrive on its own.

## Naming, so that cleanup is possible at all

```
us-7-new-checkout          # <story>-<what it gates>
kill-switch-stripe-webhook # a kill switch says so
```

- **The story id in the key** is what lets `cleanup-due` connect a flag to a release and a release to
  a PRD story. A key called `newCheckout` is orphaned the day its author leaves.
- **Mark temporary flags temporary.** LaunchDarkly has `makeFlagTemporary` /
  `makeFlagPermanent` as semantic-patch instructions, and its stale-flag reporting uses it. A kill
  switch is permanent; a rollout flag is temporary and should be flagged as such at creation, not
  reclassified at cleanup.
- **One flag, one decision.** A flag that gates three things cannot be removed until all three are
  settled, so it never is.

## Kinds, and the one that is usually right

| Kind | Use |
|---|---|
| **boolean** | almost always. The new path or the old one |
| multivariate | a real experiment with more than two arms and someone who will read the result |
| environment targeting | on in preview, off in production — often better expressed as `defaultValue` plus an env check, with no provider call |
| user / context targeting | the team first, then the cohort. Your own account is individually targeted, which is why stage 1 always looks healthy |
| organisation / tenant targeting | B2B. "25%" then means a quarter of tenants, not of traffic — say so |
| kill switch | permanent, boolean, and its **default must fail toward the previous behaviour** |

## 🔴 The default value is a release decision

From `references/provider-contracts.md`, repeated here because it is the one line of flag code that
decides what happens during an outage:

**`defaultValue` is what every user gets when the provider is unreachable.** For a new feature it is
`false` — the new path disappears, the old one serves. For a switch phrased *"`true` means allowed"*
a provider outage opens the gate for everybody. Write it so that an outage fails toward the previous
behaviour, and record which direction that is in the manifest.

This also means a flag provider is **on the critical path of your request**. That is a new dependency
with its own availability, and on an `eu`/`eu-sovereign` project a new sub-processor
(`dev-flow/references/eu-data-sovereignty.md`; `compliance-audit` reads the register). Vercel Edge
Config via `@flags-sdk/edge-config` avoids both, and for a project that only needs on/off switches it
is the smaller answer.

## Installing the library is not this skill's job

`module-add flags` does it: the packages, `FLAGS_SECRET`, the provider's environment variables,
`lib/flags.ts`, the discovery endpoint, the sub-processor entry, and `flags_check.py` to verify it.
Read `module-add/references/module-flags.md` before wiring anything by hand — it carries the four
facts that are easy to get wrong and silent when you do: that LaunchDarkly's connection string lives
in a variable called **`EXPERIMENTATION_CONFIG`**, that it wants a **`clientSideId`** and not a server
SDK key, that the **Vercel integration is a prerequisite** because the adapter reads flag state out of
Vercel's config store rather than calling LaunchDarkly per request, and that **`FLAGS_SECRET` must be
32 bytes** or `precompute` throws.

`meta.json#stack.flags` records what was installed; `meta.json#release.flag_provider` records what a
release plans to use. They are normally the same, and when they differ the plan is ahead of the code.

## In the codebase

One declaration file, server-side, like every other shared concern in
`docs/conventions.md`:

```
lib/flags.ts        # every flag() declaration, with its key, adapter, identify and defaultValue
```

Not scattered at call sites, not read from `process.env` in a component, and never evaluated in a
client component with a management key. `flags/next`'s `precompute` keeps a flagged page statically
served; without it a flag on a hot path quietly turns a static route dynamic, which is a
`vercel-doctor` finding and a bill.
