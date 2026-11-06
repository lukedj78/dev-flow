# `module-add flags` — the Flags SDK, wired so a release can actually use it

**What this module is for.** `release-intelligence` decides *which* flag a release needs, with what
default and how to open it. It does not install anything. This module is the installer: the packages,
`lib/flags.ts`, the environment variables, the discovery endpoint, the sub-processor entry, and a
check that says whether it is really wired.

**Prerequisite.** `meta.json#release.flag_provider` — run `release-intelligence`'s `enable` first, or
pass `--provider` and this module records it. Without a provider there is nothing to install.

> **Versions and names read from the shipped packages on 2026-11-06** (`npm pack` + the `dist`, never
> a quickstart): `flags@4.4.0` (MIT), `@flags-sdk/launchdarkly@1.1.1` (MIT), `@flags-sdk/edge-config@0.2.0`,
> `@flags-sdk/posthog@1.1.0`, `@flags-sdk/openfeature@0.1.3`, `@vercel/global-config@1.5.1` (Apache-2.0).
> Every env-var name below is the literal string the code passes to its own `assertEnv`.

## Step 1 — the packages

```bash
pnpm add flags
pnpm add @flags-sdk/launchdarkly     # or edge-config | posthog | openfeature | statsig | growthbook …
```

`flags@4.4.0` has two runtime dependencies (`@edge-runtime/cookies`, `jose`) and peers on `next`,
`react`, `react-dom`, `@opentelemetry/api`. **v4 ships no adapters**, which is why the provider is a
second install — a project on Edge Config never pulls a LaunchDarkly SDK.

## Step 2 — 🔴 `FLAGS_SECRET`, and why it is not optional

```bash
node -e "console.log(require('crypto').randomBytes(32).toString('base64url'))"
```

The shipped code decodes it and throws on anything else:

> *"flags: Invalid secret, it must be a 256-bit key (32 bytes)"*

**It is not only for the Flags Explorer.** `precompute` / `serialize` in `flags/next` read
`process.env.FLAGS_SECRET` and throw *"Can not serialize due to missing secret"* without it — and
`precompute` is the thing that keeps a flagged page **statically served**. So a project that skips
this secret does not get "no explorer"; it gets either a crash or a flag it cannot precompute, which
turns a static route dynamic. That is a `vercel-doctor` finding and a bill.

Set it through `project-infra-setup` (`vercel env add`), in every environment, **never pasted into
chat**. Put the name — not the value — in `.env.example`.

## Step 3 — the environment matrix, per provider

Each name below is read by the provider's **default** adapter through `assertEnv`, which **throws
when the variable is missing**. There is no fallback and no silent default.

| Provider | Variables the shipped code reads | Notes |
|---|---|---|
| **launchdarkly** | `EXPERIMENTATION_CONFIG`, `LAUNCHDARKLY_CLIENT_SIDE_ID`, `LAUNCHDARKLY_PROJECT_SLUG` | see the three traps below |
| **edge-config** | `EDGE_CONFIG` | no third party at all; the smallest answer for on/off switches |
| **posthog** | `POSTHOG_PROJECT_API_KEY`, `POSTHOG_HOST` (+ optional `POSTHOG_SECRET_KEY`) | `module-add analytics` may already have set these |
| **openfeature** | none | you construct the OpenFeature provider yourself and pass it in |
| *all of them* | `FLAGS_SECRET` | Step 2 |

### 🔴 The three LaunchDarkly traps, each read out of `dist/index.js`

1. **The variable is `EXPERIMENTATION_CONFIG`, not anything containing the word LaunchDarkly.** The
   default adapter does `assertEnv("EXPERIMENTATION_CONFIG")` and passes the result as the option
   named `globalConfigConnectionString`. The env name and the option name do not match, so searching
   the docs for the option name finds nothing.
2. **It is a `clientSideId`, not a server SDK key.** Using an SDK key here does not work, and pasting
   a *management* token here would put a credential that can archive flags into the app's
   environment. The management token belongs in your shell or a CI secret — never in the app
   (`release-intelligence/references/security-and-approvals.md`).
3. **The Vercel integration is a prerequisite, not an optimisation.** The adapter depends on
   `@launchdarkly/vercel-server-sdk` and `@vercel/global-config`: LaunchDarkly **syncs flag state
   into Vercel's config store** and the adapter reads it from there. It does not call LaunchDarkly on
   the request path. So without the integration connected there is nothing to read, and
   `EXPERIMENTATION_CONFIG` is the connection string to that store.

⚠️ `edgeConfigConnectionString` is **deprecated** in `createLaunchDarklyAdapter`'s options in favour
of `globalConfigConnectionString`. Any tutorial older than that rename configures a deprecated field,
and the deprecated one still "works", so nothing tells you.

## Step 4 — `lib/flags.ts`, one file

One declaration file, server-side, like every other shared concern in `docs/conventions.md`. Not
scattered at call sites, never evaluated in a client component.

```ts
// lib/flags.ts
import { flag } from "flags/next";
import { ldAdapter, type LDContext } from "@flags-sdk/launchdarkly";

export const newCheckout = flag<boolean, LDContext>({
  key: "us-7-new-checkout",
  // 🔴 what EVERY user gets when the provider is unreachable. Write it so an outage
  // falls back to the PREVIOUS behaviour: false for a new feature, never true for
  // a switch phrased "true means allowed".
  defaultValue: false,
  identify: async ({ cookies, headers }) => ({
    key: cookies.get("visitor")?.value ?? "anonymous",
  }),
  adapter: ldAdapter.variation(),
});
```

The two exports of `@flags-sdk/launchdarkly` are **`ldAdapter`** (pre-initialised, and its own
docblock calls it *"the recommended way"*) and `createLaunchDarklyAdapter` for explicit options.
There is no `launchDarkly` export.

**`identify` decides the bucket, which decides what a percentage means.** Bucketing by a user id is
25% of users; bucketing by an organisation is 25% of tenants, which on a B2B product can be 60% of
traffic. Pick deliberately and write which one in the release manifest
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
flags in the proxy and read them from the route — `flags/next`'s `precompute`, `generatePermutations`
and `getPrecomputed`. Do it when the flagged page is on a hot path; `vercel-doctor` is the gate that
notices when you did not.

## Step 6 — the discovery endpoint (optional, and useful)

```ts
// app/.well-known/vercel/flags/route.ts
import { createFlagsDiscoveryEndpoint, getProviderData } from "flags/next";
import * as flags from "@/lib/flags";

export const GET = createFlagsDiscoveryEndpoint(async () => getProviderData(flags));
```

It exposes the project's flag definitions to Vercel's toolbar, guarded by `FLAGS_SECRET` via
`verifyAccess`. ⚠️ It lists **flag keys and descriptions**, so keep product-sensitive names out of
them — a key called `acme-corp-trial-extension` leaks a customer and a negotiation.

## Step 7 — the sub-processor entry, which is not optional

A hosted flag provider sits **on the request path** and receives whatever you pass in `identify` — a
user id, often an organisation, sometimes an email. That is a processor.

- Register it in `docs/compliance/subprocessors.md` with its region and transfer basis;
  `dev-flow/references/eu-data-sovereignty.md` is the procedure and `compliance-audit` reads it.
- **LaunchDarkly is a US company.** An EU instance (`app.eu.launchdarkly.com`) limits where the data
  sits, not who controls the vendor — and that host is **not** in the `servers` list of
  LaunchDarkly's own OpenAPI spec, so it is a deliberate configuration, not a default.
- **Pass the smallest key that buckets correctly.** A hashed user id buckets exactly as well as an
  email and discloses nothing. Never put an email, a name or a phone number in `identify` because it
  was convenient for targeting rules.
- For `data_residency = "eu-sovereign"`, the honest answer is usually **`edge-config`** (no third
  party) or self-hosted GrowthBook, not a US SaaS with an EU region.

## Step 8 — record and check

```bash
python3 module-add/scripts/flags_check.py <project-root>
```

Statuses match the other checkers: `ok`, `found` (missing or wrong — exit 1), `not checked` (it
cannot see the answer: a value behind an env var with nothing in the env files), `not applicable`
(not a web surface). It verifies the packages, `FLAGS_SECRET` and its 32-byte length where a literal
is readable, the provider's variables, that `lib/flags.ts` exists and declares at least one flag with
an explicit `defaultValue`, that no flag is declared inside a `"use client"` file, and that the
sub-processor register names the provider.

Then `meta.json#stack.flags = "<provider>"`, plus a `history` entry. Never bumps `phase`.

## What this module does not do

- **It does not create flags at the provider.** That is `release-intelligence`, per release, under its
  approval policy.
- **It does not decide whether a release needs a flag.** `release-intelligence/references/feature-flags.md`
  opens with the cases that should not get one.
- **Mobile is out of scope.** The Flags SDK is web; React Native uses the provider's own SDK.
  `rn-module-add` has no `flags` module yet, and saying so is better than pretending.
