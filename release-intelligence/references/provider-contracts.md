# Provider contracts — and the abstraction we did not have to invent

The capability needs four provider roles. The temptation is to define four interfaces of our own and
write adapters behind them. **For the flag role that would be a mistake**, because Vercel already
ships exactly that abstraction, it is MIT, and it has nine maintained adapters. Ecosystem-first is
the house rule, and this is the clearest case of it in the suite.

All versions below read from npm on **2026-11-06**.

## 1. Feature flags — the Vercel Flags SDK, not an interface of ours

| Package | Version | Licence | Role |
|---|---|---|---|
| `flags` | **4.4.0** | MIT | the declaration layer and the `Adapter` contract |
| `@flags-sdk/launchdarkly` | 1.1.1 | MIT | LaunchDarkly |
| `@flags-sdk/openfeature` | 0.1.3 | MIT | **anything OpenFeature speaks** — the escape hatch |
| `@flags-sdk/edge-config` | 0.2.0 | MIT | Vercel Edge Config, no third party at all |
| `@flags-sdk/posthog` | 1.1.0 | MIT | PostHog (and PostHog EU, which `module-add analytics` may already have) |
| `@flags-sdk/statsig` | 0.3.1 | MIT | Statsig |
| `@flags-sdk/growthbook` | 0.3.1 | MIT | GrowthBook (self-hostable) |
| `@flags-sdk/hypertune` | 0.3.5 | MIT | Hypertune |
| `@flags-sdk/optimizely` | 0.1.1 | MIT | Optimizely |
| `@flags-sdk/split` | 0.1.1 | MIT | Split |

`flags@4.4.0` has **two runtime dependencies** (`@edge-runtime/cookies`, `jose`) and peers on
`next`, `react`, `react-dom` and `@opentelemetry/api`. Its exports, read from the shipped
`package.json`: `.`, `./next`, `./react`, `./analytics`, `./sveltekit`.

⚠️ **v4 ships no adapters itself.** Every provider is a separate package, which is what makes the
dependency honest: a project that uses Edge Config never installs a LaunchDarkly SDK.

### The contract, from the shipped `dist/types-*.d.ts`

```ts
interface Adapter<ValueType, EntitiesType> {
  initialize?: () => Promise<void>;
  identify?: Identify<EntitiesType>;
  origin?: Origin | string | ((key: string) => Origin | string | undefined);
  config?: { reportValue?: boolean };
  adapterId?: string | symbol;   // flags sharing an id and an identify source batch into one bulkDecide
  decide: Decide<ValueType, EntitiesType>;
}
```

A flag is declared once, server-side, and the adapter is swapped without touching call sites:

```ts
// lib/flags.ts
import { flag } from "flags/next";
import { ldAdapter, type LDContext } from "@flags-sdk/launchdarkly";

export const newCheckout = flag<boolean, LDContext>({
  key: "us-7-new-checkout",
  adapter: ldAdapter.variation(),
  identify: async ({ cookies }) => ({ key: cookies.get("visitor")?.value ?? "anonymous" }),
  defaultValue: false,   // what it serves when the provider is unreachable — see below
});
```

**Changing provider is the `adapter:` line.** That is the provider independence the spec asks for,
and it is somebody else's tested code rather than ours.

The names above are read from `@flags-sdk/launchdarkly@1.1.1`'s shipped `dist/index.d.ts`, which
exports exactly two things — `ldAdapter` (the pre-initialised one, and its own docblock calls it *"the
recommended way"*) and `createLaunchDarklyAdapter`. **An earlier draft of this file wrote
`launchDarkly.variation()`, which does not exist**; it was corrected by reading the package rather
than by trusting the draft, which is the whole of rule zero.

⚠️ **Two things the shipped package reveals that no quickstart leads with.** Its dependencies are
`@launchdarkly/vercel-server-sdk` and `@vercel/global-config`, so on Vercel the adapter does **not**
poll LaunchDarkly on the request path — LaunchDarkly syncs flag state into Vercel's config store and
the adapter reads it from there. That is why it is viable at the edge, and it means **the Vercel
integration is a prerequisite**, not an optimisation. And its explicit constructor takes
`{ projectSlug, clientSideId, globalConfigConnectionString }` — a **client-side id**, not a server SDK
key, and `edgeConfigConnectionString` is **deprecated** in favour of `globalConfigConnectionString`,
so a tutorial older than that rename will configure a deprecated field silently.

🔴 **`defaultValue` is a release decision, not a formality.** It is what every user gets when the
provider is down. For a new feature behind a flag that is `false` — the new path disappears and the
old one serves, which is the safe direction. For a kill switch written as *"`true` means allowed"*
a provider outage opens the gate for everyone. **Write the default so that a provider outage fails
in the direction of the previous behaviour**, and say in the manifest which direction that is.

### Other things worth knowing before adopting it

- `flags/next`'s `precompute` + `generatePermutations` let flags be evaluated at the edge and
  encoded into the route, so a flagged page stays statically served. That is the reason to prefer
  this SDK over a raw provider SDK on Vercel, and it is also a `vercel-doctor` concern — an
  un-precomputed flag on a hot path turns a static page dynamic.
- `reportValue` / `flags/analytics` emit which value was served. That is the join key between a
  release and its metrics; without it, "the error rate rose" cannot be attributed to a cohort.
- The SDK is **web**. React Native has no equivalent; on mobile use the provider's own SDK and keep
  the manifest and the risk floor, which are stack-agnostic.

## 2. Observability — read what `module-add observability` already wired

There is nothing to choose here, because dev-flow has already chosen: `module-add observability`
wires **Sentry** (Frankfurt org for `eu`) or **GlitchTip** (for `eu-sovereign`), with the release tag,
`sendDefaultPii` off and no Replay. `module-add/scripts/observability_check.py` verifies it.

The contract this skill needs is a **shape, not a client** — the `--evidence` payload:

```json
{
  "source": "sentry | glitchtip | vercel | manual",
  "release": "abc1234",
  "window_minutes": 60,
  "error_rate_pct": 0.21,
  "p95_ms": 430,
  "p99_ms": 980,
  "availability_pct": 99.98,
  "baseline": { "release": "def5678", "error_rate_pct": 0.18, "p95_ms": 410 },
  "business": { "checkout_completion_pct": 61.2 },
  "sufficient": true,
  "provider_error": null,
  "reason": null
}
```

Three fields exist only to make blindness expressible, and `release.py` treats each of them as a
refusal: `sufficient: false`, a non-null `provider_error`, and a `window_minutes` below the project's
own minimum. `references/release-health.md` is the full reasoning.

**Why the evidence is passed in rather than fetched.** The agent reads the numbers from the project's
observability and hands them to the script, so the decision is auditable from `meta.json` alone and
this skill never holds an observability token. It also means the same command works when the numbers
came from a dashboard the user pasted.

## 3. Deployment — `vercel-deploy` owns it, including the progressive part

| Capability | Where it already lives |
|---|---|
| current production deployment, build logs, `inspect`, `ls --prod` | `vercel-deploy/references/rollback-runbook.md` §Useful while diagnosing |
| instant rollback and its trap (auto-assignment of production domains goes off) | same file, §The trap |
| **traffic-level progressive delivery** — `vercel rolling-release` with `enable`, `configure`, `approve`, `abort`, `complete`, `fetch` | `vercel-deploy/SKILL.md` |
| plan-eligible rollback targets (Hobby: the previous production deployment only) | the runbook's table |

**Do not re-document any of it here.** The one thing this skill adds is the distinction in
`references/progressive-delivery.md`: a rolling release shifts **traffic between deployments**, a
flag shifts **audience within one deployment**. They compose, and confusing them produces a rollout
where nobody can say what a user was served.

## 4. Source control — `gh`, and nothing new

`gh pr view --json files,additions,deletions,statusCheckRollup` supplies the PR, the changed files
and the check results; `risk.py` reads the same information from `git diff` so it works without a
remote. The cleanup PR is an ordinary `gh pr create`.

⚠️ GitHub notifies the owner of any `@name` written in a PR body. A generated cleanup PR must not
interpolate a flag maintainer's handle from a provider API response into prose.

## Adding a provider

1. Is there a `@flags-sdk/*` adapter? Then there is nothing to build: record
   `meta.json#release.flag_provider` and use it.
2. Does the provider speak **OpenFeature**? Use `@flags-sdk/openfeature` with its OpenFeature
   provider. Still nothing to build.
3. Neither? Write an `Adapter` — the interface above, five optional members and one required
   `decide`. It belongs **in the project's repo**, not in this skill, and it goes through
   `registry-intake` if it came from a registry.
4. Then document the **management** half, as `references/provider-launchdarkly.md` does: read the
   provider's own OpenAPI or SDK source and transcribe the exact calls. Do not infer endpoints from
   a quickstart.
