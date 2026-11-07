# LaunchDarkly — what it has that Vercel Flags does not, verified against its own OpenAPI

> **Read this only when one of three things is the reason.** The default provider for our stack is
> **Vercel Flags** (`@flags-sdk/vercel`, zero env vars, no new sub-processor — see
> `module-add/references/module-flags.md`). LaunchDarkly earns a project when it needs its
> **approval requests** (reviews plus an explicit apply, enforced provider-side, where Vercel's
> *"Review and save"* is a change record and not a gate), its **`migration-safety-issues`**
> pre-flight, or its **stale-flag detection** and `dependent-flags`. Those three are below, and they
> are not available by paying more elsewhere. "We already use LaunchDarkly" is also a reason; "it is
> the industry standard" is not.

Everything on this page was read from **`https://app.launchdarkly.com/api/v2/openapi.json`** on
**2026-11-06** (OpenAPI 3.0.3, `info.version` `2.0`, 3.1 MB), not from a tutorial and not from
memory. That is the house rule: for anything that leaves the machine, the shipped artefact outranks
the page describing it. Re-fetch the spec before leaning on a path; LaunchDarkly adds resources
continuously and the spec is the only thing that is never behind.

```bash
curl -sS https://app.launchdarkly.com/api/v2/openapi.json -o ld.json
python3 -c "import json;d=json.load(open('ld.json'));print(len(d['paths']),'paths')"
```

## The two halves nobody separates, and the confusion that follows

| | **Evaluation** | **Management** |
|---|---|---|
| Question | "what should this user see right now?" | "change the rollout to 25%" |
| Where it runs | inside the app, on every request | once, from a CLI or a release step |
| Who talks | the Flags SDK adapter (`@flags-sdk/launchdarkly`) | the LaunchDarkly **REST API v2** |
| Credential | an SDK key / client-side id, in the app's env | a **service access token**, never in the app |
| This skill | documents it, `module-add` wires it | documents the exact calls; **makes none of them** |

Conflating them is how a management token ends up in a client bundle. `references/security-and-approvals.md`
has the token rules.

## Servers, headers, rate limits

`servers` in the spec lists exactly two, and **the EU host is not among them** — it is documented
separately, which matters for any project with `stack.data_residency` set to `eu` or `eu-sovereign`:

| Host | From |
|---|---|
| `https://app.launchdarkly.com` | the spec's `servers[0]`, *"Default"* |
| `https://app.launchdarkly.us` | the spec's `servers[1]`, *"Federal"* |
| `https://app.eu.launchdarkly.com` | LaunchDarkly's API docs page, **not** the spec's `servers` list |

⚠️ **For an EU project this is a data-residency decision, not a base-URL setting.** LaunchDarkly is a
US company; an EU-hosted instance limits where the data sits, not who controls the vendor. Record it
in `docs/compliance/subprocessors.md` with its transfer basis — `dev-flow/references/eu-data-sovereignty.md`
is the procedure, and `compliance-audit` reads the register.

Headers, all three verified in the spec:

| Header | Value |
|---|---|
| `Authorization` | the access token **raw** — no `Bearer` prefix |
| `LD-API-Version` | a date, e.g. `20240415`. `beta` for beta resources |
| `Content-Type` | `application/json; domain-model=launchdarkly.semanticpatch` **for a semantic patch** |

⚠️ **Omit the `domain-model` part and a semantic patch is parsed as a JSON patch and returns 400.**
That is the single most common first failure against this API.

Rate limits are per team and **per ten seconds**, reported in response headers rather than published
as numbers: `X-Ratelimit-Global-Limit` / `-Remaining`, `X-Ratelimit-Route-Limit` / `-Remaining`,
`X-Ratelimit-Auth-Token-Limit` / `-Remaining` / `-Reset`, plus `X-Ratelimit-Reset`. A `429` carries
`Retry-After` for IP-based limiting. **Read the headers; do not hard-code a number.**

## The endpoints this capability needs

Paths as the spec spells them, with the methods it declares.

| Operation | Method and path |
|---|---|
| List / create a flag | `GET`, `POST` `/api/v2/flags/{projectKey}` |
| Read / update / delete a flag | `GET`, `PATCH`, `DELETE` `/api/v2/flags/{projectKey}/{featureFlagKey}` |
| Flag status across environments | `GET` `/api/v2/flag-status/{projectKey}/{featureFlagKey}` |
| Flag statuses in one environment | `GET` `/api/v2/flag-statuses/{projectKey}/{environmentKey}` |
| **Start a progressive release** | `POST` `/api/v2/projects/{projectKey}/flags/{flagKey}/environments/{environmentKey}/releases` |
| Read a release | `GET` `…/releases/{releaseId}` |
| **Stop a release** | `PUT` `…/releases/{releaseId}/stop` |
| **Migration safety issues for a patch** | `POST` `/api/v2/projects/{projectKey}/flags/{flagKey}/environments/{environmentKey}/migration-safety-issues` |
| Approval requests | `GET`, `POST` `/api/v2/projects/{projectKey}/flags/{featureFlagKey}/environments/{environmentKey}/approval-requests` |
| Apply / review an approval request | `POST` `…/approval-requests/{id}/apply`, `…/{id}/reviews` |
| Scheduled changes | `GET`, `POST` `/api/v2/projects/{projectKey}/flags/{featureFlagKey}/environments/{environmentKey}/scheduled-changes` |
| Stale-flag chart data | `GET` `/api/v2/engineering-insights/charts/flags/stale` |
| Dependent flags (prerequisites) | `GET` `/api/v2/flags/{projectKey}/{featureFlagKey}/dependent-flags` |

**Three of these change the design of this skill**, and all three were found in the spec rather than
assumed:

1. **`releases` is LaunchDarkly's own progressive rollout.** Its summary: *"Creates and starts a
   release on a flag in an environment … A release has one or more phases. Each phase is an audience,
   targeted by one flag rule, and has its own steps: the schedule of allocations at which that rule
   serves the target variation."* So when the provider is LaunchDarkly, **drive its release resource**
   rather than re-implementing stages with repeated patches — and `…/stop` takes a `resolution` that
   decides how completed and pending phases are treated. Our own stage loop in
   `references/progressive-delivery.md` is for providers that have no equivalent.
2. **`approval-requests` is a native human-approval workflow**, with reviews and an explicit apply
   step. On a team that already uses it, an `approval` verdict from our policy table should become a
   LaunchDarkly approval request, not a chat message — the audit trail then lives where the auditors
   look.
3. **`migration-safety-issues` takes a semantic patch and returns the safety issues it would cause.**
   A read-only pre-flight for a targeting change. Use it before any `high`/`critical` flag change;
   it is cheaper than discovering the issue from the error rate.

## Semantic patch: the 52 instructions, and the one unit that bites

The `PATCH` body carries `{environmentKey, instructions: [...], comment?}`. The spec's description
enumerates **52** instruction kinds; the ones this capability uses:

| Intent | `kind` |
|---|---|
| kill switch on / off | `turnFlagOff`, `turnFlagOn` |
| percentage rollout on the default rule | `updateFallthroughVariationOrRollout` |
| percentage rollout on one targeting rule | `updateRuleVariationOrRollout` |
| add an audience rule | `addRule`, `removeRule`, `reorderRules` |
| individual targeting | `addTargets`, `removeTargets`, `replaceTargets`, `clearTargets` |
| retire | `archiveFlag`, `deprecateFlag`, `restoreFlag`, `restoreDeprecatedFlag`, `deleteFlag` |
| permanence | `makeFlagTemporary`, `makeFlagPermanent` |

🔴 **`rolloutWeights` are in thousandths of a percent, 0–100000 — not percent.** The spec's own
example, verbatim:

```json
{
  "environmentKey": "environment-key-123abc",
  "instructions": [{
    "kind": "updateFallthroughVariationOrRollout",
    "rolloutContextKind": "user",
    "rolloutWeights": {
      "2f43f67c-3e4e-4945-a18a-26559378ca00": 15000,
      "e5830889-1ec5-4b0c-9cc9-c48790090c43": 85000
    }
  }]
}
```

`15000` is **15%**. Writing `15` there means 0.015% — a stage that looks applied, serves almost
nobody, and produces a beautifully healthy error rate at every observation window. It is the perfect
silent failure for a progressive rollout, which is why it is the only 🔴 on this page.

**The weights must sum to 100000**, and `variationId`s come from the `GET` flag response — they are
server-assigned, so a rollout patch always reads the flag first. Same for `ruleId` and `clauseId`,
which the spec states are returned by Get feature flag.

## Bucketing, and why "25%" is not 25% of your users

`rolloutBucketBy` (default: the context key) and `rolloutContextKind` (default `user`) decide **what**
is bucketed. Three consequences worth knowing before reading a stage's numbers:

- Bucketing is a **stable hash**, so the same user stays in the same bucket across evaluations —
  that is the point, and it is also why a 5% cohort is not a random sample of your traffic.
- Bucketing by an **organisation** rather than a user means 25% of tenants, which can be 60% of
  traffic if one tenant is large. On a B2B product this is usually what you want and almost never
  what the percentage reads like.
- A user with an **individual target** is served regardless of the rollout. Your own team usually
  sits there, which is why the first stage looks healthy to the people watching it.

## What this skill does, concretely

It writes none of the above. It produces the **plan**: which instruction, which environment, which
weights, read back from which `variationId`s — and the user (or the app's own release step) runs it
with their token. Where a project wants it automated, the automation belongs in the project's repo,
reviewed like any other code, with `references/security-and-approvals.md`'s token rules.

For the evaluation half in a Next.js app, `references/provider-contracts.md` has the Flags SDK
adapter and the version floors.
