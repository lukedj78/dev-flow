# `module-add flags` — the Flags SDK, wired so a release can actually use it

**What this module is for.** `release-intelligence` decides *which* flag a release needs, with what
default and how to open it. It does not install anything. This module is the installer: the packages,
`lib/flags.ts`, the environment variables (when the provider needs any), the discovery endpoint, the
sub-processor entry (when there is a new one), and a check that says whether it is really wired.

**Prerequisite.** `meta.json#release.flag_provider`, or `--provider`. Without a provider there is
nothing to install.

> **Versions and names read from the shipped packages**, never from a quickstart. `flags@4.4.0` (MIT),
> `@flags-sdk/vercel@1.6.0` + `@vercel/flags-core@1.11.0` (MIT, read 2026-11-07),
> `@flags-sdk/launchdarkly@1.1.1`, `@flags-sdk/edge-config@0.2.0`, `@flags-sdk/posthog@1.1.0`,
> `@flags-sdk/openfeature@0.1.3`, `@vercel/global-config@1.5.1` (Apache-2.0, 2026-11-06). Every env-var
> name below is the literal string the code passes to its own `assertEnv`.

## 🔴 The default is Vercel Flags, and the reason is an empty table

**`stack.flags = "vercel"` unless there is a reason against it.** Not out of platform loyalty — out of
three things that are checkable:

1. **It reads no environment variable at all.** `vercelAdapter()` authenticates with the OIDC token the
   platform injects into every deployment. Verified by grepping `@flags-sdk/vercel@1.6.0`'s shipped
   `dist` for `process.env` and `assertEnv` on 2026-11-07: **zero hits**. Nothing to set, nothing to
   leak, nothing to forget. Compare LaunchDarkly's three `assertEnv` calls, each of which throws, one
   of them named `EXPERIMENTATION_CONFIG`.
2. **No new sub-processor.** Same vendor as the deployment, same DPA. On a project with
   `stack.data_residency` of `eu` or `eu-sovereign` this closes the discussion on its own: a hosted
   flag provider sits on the request path and receives whatever `identify()` passes it.
3. **Build-time resilience the application does not have to write.** Vercel's build fetches the flag
   definitions and bundles them into the deployment, so every function uses one snapshot and there is
   a runtime fallback if the flags service is unreachable. That is a better answer to a provider
   outage than `defaultValue` discipline alone — which still applies.

It is a full provider, not storage: dashboard, **entities**, targeting rules, **segments**, splits,
drafts, per-environment control, a `vercel flags` CLI, and a *"Review and save"* message on every
change. And `@vercel/flags-core/openfeature` ships an **OpenFeature** provider, so the exit is a
standard rather than a promise.

⚠️ **An earlier draft of this file listed nine adapters and omitted this one**, making LaunchDarkly the
reference integration without checking whether the platform we deploy on had its own. An
ecosystem-first miss, corrected 2026-11-07. Read `dev-flow/references/before-you-build.md` §2 before
reaching for a third party: *does the tool we already pay for do this?*

### When to choose something else, and the only honest reasons

| Choose | When |
|---|---|
| **`launchdarkly`** | you need its **approval requests** (reviews + an explicit apply, enforced provider-side — Vercel's "Review and save" is a change record, not a gate), its **`migration-safety-issues`** pre-flight, or its **stale-flag detection** and `dependent-flags`. `release-intelligence/references/provider-launchdarkly.md` |
| **`edge-config`** | on/off switches with no targeting at all. Smaller than Vercel Flags, and still the platform |
| **`posthog`** | `module-add analytics` already installed PostHog and you want flags beside the funnels |
| **`openfeature`** | the organisation has standardised on OpenFeature, or you are migrating between providers |
| **`growthbook`** | you need a self-hosted provider for sovereignty reasons Vercel's EU posture does not satisfy |

**"We already use LaunchDarkly" is a reason.** "LaunchDarkly is the industry standard" is not — the
question is what this project needs, and the three advantages above are not available by paying more.

## Step 1 — the packages

```bash
pnpm add flags @flags-sdk/vercel      # the default
# or: @flags-sdk/launchdarkly | edge-config | posthog | openfeature | statsig | growthbook …
```

`flags@4.4.0` has two runtime dependencies (`@edge-runtime/cookies`, `jose`) and peers on `next`,
`react`, `react-dom`, `@opentelemetry/api`. **v4 ships no adapters**, which is why the provider is a
second install — a project on Vercel Flags never pulls a LaunchDarkly SDK.

On Vercel, link the project and pull the OIDC credentials for local development:

```bash
vercel link && vercel env pull
```

## Step 2 — 🔴 `FLAGS_SECRET`, and why it is not optional on any provider

```bash
node -e "console.log(require('crypto').randomBytes(32).toString('base64url'))"
```

The shipped code decodes it and throws on anything else:

> *"flags: Invalid secret, it must be a 256-bit key (32 bytes)"*

**It belongs to `flags` core, not to the provider, so choosing Vercel does not remove it.** And it is
not only for the Flags Explorer: `precompute` / `serialize` in `flags/next` read
`process.env.FLAGS_SECRET` and throw *"Can not serialize due to missing secret"* without it — and
`precompute` is what keeps a flagged page **statically served**. A project that skips this secret does
not get "no explorer"; it gets a crash, or a flag it cannot precompute, which turns a static route
dynamic. That is a `vercel-doctor` finding and a bill.

Set it through `project-infra-setup` (`vercel env add`), in every environment, **never pasted into
chat**. Put the name — not the value — in `.env.example`.

## Step 3 — the environment matrix, per provider

Each name is read by the provider's **default** adapter through `assertEnv`, which **throws when the
variable is missing**. No fallback, no silent default.

| Provider | Variables the shipped code reads | Notes |
|---|---|---|
| **vercel** | **none** | OIDC, injected by the platform. The empty row is the argument |
| **edge-config** | `EDGE_CONFIG` | still the platform; no targeting engine |
| **launchdarkly** | `EXPERIMENTATION_CONFIG`, `LAUNCHDARKLY_CLIENT_SIDE_ID`, `LAUNCHDARKLY_PROJECT_SLUG` | see the three traps below |
| **posthog** | `POSTHOG_PROJECT_API_KEY`, `POSTHOG_HOST` (+ optional `POSTHOG_SECRET_KEY`) | `module-add analytics` may already have these |
| **openfeature** | none | you construct the OpenFeature provider and pass it in |
| *all of them* | `FLAGS_SECRET` | Step 2 |

### 🔴 The three LaunchDarkly traps, each read out of `dist/index.js`

1. **The variable is `EXPERIMENTATION_CONFIG`**, not anything containing the word LaunchDarkly. The
   default adapter does `assertEnv("EXPERIMENTATION_CONFIG")` and passes it as the option named
   `globalConfigConnectionString`. The env name and the option name do not match, so searching the
   docs for the option finds nothing.
2. **It is a `clientSideId`, not a server SDK key.** An SDK key does not work, and a *management*
   token here would put a credential that can archive flags into the app's environment. That token
   belongs in a shell or a CI secret (`release-intelligence/references/security-and-approvals.md`).
3. **The Vercel integration is a prerequisite, not an optimisation.** The adapter depends on
   `@launchdarkly/vercel-server-sdk` and `@vercel/global-config`: LaunchDarkly **syncs flag state into
   Vercel's config store** and the adapter reads it from there. It does not call LaunchDarkly on the
   request path. Without the integration connected there is nothing to read.

⚠️ `edgeConfigConnectionString` is **deprecated** in `createLaunchDarklyAdapter`'s options in favour of
`globalConfigConnectionString`, and the deprecated one still works, so nothing tells you.

## Step 4 — `lib/flags.ts`, one file

One declaration file, server-side, like every other shared concern in `docs/conventions.md`. Not
scattered at call sites, never evaluated in a client component.

```ts
// lib/flags.ts
import { flag, dedupe } from "flags/next";
import { vercelAdapter } from "@flags-sdk/vercel";

type Entities = {
  user?: { id: string; plan: string };
  team?: { id: string };
};

// `dedupe` fetches the session once per request even when several flags call identify
const identify = dedupe(async (): Promise<Entities> => {
  const session = await getSession();
  return session?.user
    ? { user: { id: session.user.id, plan: session.user.plan }, team: session.team && { id: session.team.id } }
    : {};
});

export const newCheckout = flag<boolean, Entities>({
  key: "us-7-new-checkout",
  // 🔴 what EVERY user gets when the provider is unreachable. Write it so an outage falls
  // back to the PREVIOUS behaviour: false for a new feature, never true for a switch
  // phrased "true means allowed".
  defaultValue: false,
  identify,
  adapter: vercelAdapter(),
});
```

`@flags-sdk/vercel` exports `vercelAdapter`, `createVercelAdapter`, `getProviderData` and
`resetDefaultVercelAdapter` — nothing else. `createVercelAdapter({ projectId })` reads another
project's flags in the same team with this deployment's OIDC token, which is how a monorepo shares one
set of flags; the other project must connect this one first.

For LaunchDarkly the two exports are **`ldAdapter`** (pre-initialised, and its own docblock calls it
*"the recommended way"*) and `createLaunchDarklyAdapter`. There is no `launchDarkly` export.

**`identify` decides the bucket, which decides what a percentage means.** Bucketing by user id is 25%
of users; by organisation it is 25% of tenants, which on a B2B product can be 60% of traffic. Pick
deliberately and write which in the release manifest
(`release-intelligence/references/progressive-delivery.md`).

⚠️ **A flag is not an access control.** It decides what the UI offers, never what the server permits.
Every flagged Server Action and route handler still checks the session and the owner, and
`app-security` still has to pass. A flag used as authorization is a vulnerability with a dashboard.

## Step 5 — reading it, and keeping the page static

```tsx
// app/checkout/page.tsx — a Server Component
import { newCheckout } from "@/lib/flags";

export default async function Page() {
  return (await newCheckout()) ? <NewCheckout /> : <LegacyCheckout />;
}
```

That works and makes the route dynamic. For a page that must stay statically served, precompute the
flags in the proxy and read them in the route — `flags/next`'s `precompute`,
`generatePermutations` and `getPrecomputed`. Do it when the flagged page is on a hot path;
`vercel-doctor` is the gate that notices when you did not.

## Step 6 — the discovery endpoint (optional, and useful)

```ts
// app/.well-known/vercel/flags/route.ts
import { createFlagsDiscoveryEndpoint } from "flags/next";
import { getProviderData } from "@flags-sdk/vercel";   // or from "flags/next" for a generic set
import * as flags from "@/lib/flags";

export const GET = createFlagsDiscoveryEndpoint(async () => getProviderData(flags));
```

It exposes the project's flag definitions to the Flags Explorer in the Vercel toolbar, guarded by
`FLAGS_SECRET` via `verifyAccess`. ⚠️ It lists **flag keys and descriptions**, so keep
product-sensitive names out of them — a key called `acme-corp-trial-extension` leaks a customer and a
negotiation.

## Step 7 — the sub-processor entry, when there is one

| Provider | Register it? |
|---|---|
| **vercel**, **edge-config** | **no** — same vendor as the deployment, same DPA, nothing new on the request path |
| everything else | **yes**, in `docs/compliance/subprocessors.md` with its region and transfer basis |

`dev-flow/references/eu-data-sovereignty.md` is the procedure and `compliance-audit` reads the
register. Two rules that apply whatever the provider:

- **Pass the smallest key that buckets correctly.** A hashed user id buckets exactly as well as an
  email and discloses nothing. Never put an email, a name or a phone number in `identify` because it
  was convenient for a targeting rule.
- **LaunchDarkly is a US company.** Its EU instance (`app.eu.launchdarkly.com`) limits where the data
  sits, not who controls the vendor — and that host is **not** in the `servers` list of LaunchDarkly's
  own OpenAPI spec, so it is a deliberate configuration rather than a default.

## Step 8 — record and check

```bash
python3 module-add/scripts/flags_check.py <project-root>
```

Statuses match the other checkers: `ok`, `found` (missing or wrong — exit 1), `not checked` (it cannot
see the answer: a value that lives only in the deployment), `not applicable` (not a web surface, or no
sub-processor to register). It verifies the packages, `FLAGS_SECRET` and its 32-byte length where a
literal is readable, the provider's variables, that `lib/flags.ts` exists and declares at least one
flag with an explicit `defaultValue`, that no flag is declared inside a `"use client"` file, and the
sub-processor register where the provider is a third party.

Then `meta.json#stack.flags = "<provider>"`, plus a `history` entry. Never bumps `phase`.

## What this module does not do

- **It does not create flags at the provider.** That is `release-intelligence`, per release, under its
  approval policy. On Vercel the dashboard or `vercel flags` does it; on LaunchDarkly its REST API.
- **It does not run the rollout.** And note that **both providers' native progressive rollout advances
  on a schedule** — Vercel's stages are *"a target percentage and a duration"* (changelog 2026-05-11),
  LaunchDarkly's release phases carry a step schedule. Time is exactly what
  `release-intelligence/references/progressive-delivery.md` refuses to advance on. Use the provider to
  **set** the percentage; let the manifest decide **when**.
- **It does not decide whether a release needs a flag.**
  `release-intelligence/references/feature-flags.md` opens with the cases that should not get one.
- **Mobile is out of scope.** The Flags SDK is web; React Native uses the provider's own SDK.
  `rn-module-add` has no `flags` module yet, and saying so is better than pretending.

## The official agent skills

Vercel ships two (`npx skills add vercel/flags --skill vercel-flags`, and `--skill flags-sdk`), which
help plan flags, drive the `vercel flags` CLI and run rollouts. **They go through
`registry-intake skill-review` before installation**, like any third-party agent skill — the review is
the gate, and the user runs the install.
