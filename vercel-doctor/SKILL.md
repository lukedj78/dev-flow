---
name: vercel-doctor
description: 'Run vercel-doctor on a Next.js project to find costly Vercel patterns BEFORE they inflate the bill, then route the fixes to the right dev-flow skills. vercel-doctor (https://www.vercel-doctor.com/, an independent open-source CLI — npm package `vercel-doctor`, MIT, github.com/Aniket-508/vercel-doctor; run with `npx -y vercel-doctor@latest .`) scans the codebase for cost/performance anti-patterns across six areas — caching that defeats the CDN, unused code (dead files/exports/types), serverless function duration, image-optimization waste, excessive function invocations, and platform/deploy config — and emits a markdown report, AI-fix prompts, and a project health score. This skill wraps that run: it interprets the report, applies the safe mechanical fixes, and hands the judgment calls to the owning skill (`data-fetching` for Next 16 caching, `design-md-to-app` for image patterns, plain cleanup for dead code). Cost/performance counterpart to `compliance-audit` (which is the legal-risk pre-deploy gate). Horizontal capability; dev-flow proposes it as a pre-deploy gate at `feature_complete` and in the `deployed` maintenance loop. Records a `vercel_doctor` block in meta.json; does NOT bump phase. Use when the user says "my Vercel bill is high", "optimize for Vercel", "reduce Vercel cost", "vercel-doctor", "check caching / function duration / image cost", or dev-flow routes here before a Vercel deploy. Refuses for non-Vercel / non-Next targets. Not for: legal/privacy audit (use compliance-audit), building features, or actually deploying (use vercel-deploy).'
---

# vercel-doctor — cost & performance pre-deploy gate for Vercel/Next.js

Runs on a project that already exists and **targets Vercel**. It wraps the third-party [vercel-doctor](https://www.vercel-doctor.com/) CLI — which scans a Next.js codebase for **patterns that cost money on Vercel** — and turns its report into applied fixes, routing each finding to the skill that owns it.

> **Third-party tool.** vercel-doctor is **not** an official Vercel product — it's an independent
> open-source project by [Aniket-508](https://github.com/Aniket-508/vercel-doctor), published to npm as
> **`vercel-doctor`** (bin `vercel-doctor`, **MIT**). Verified against the npm registry + repo README
> (latest at time of writing: **1.2.0** — pin or re-check, the flag set can change). It reads your
> codebase and phones home unless `--offline`; treat its AI-fix prompts as suggestions to verify, not gospel.

## Verified invocation + flags

```bash
npx -y vercel-doctor@latest .                       # scan the project at <path>
npx -y vercel-doctor@latest . --output markdown --report docs/vercel/doctor-report.md
npx -y vercel-doctor@latest . --ai-prompts docs/vercel/doctor-fixes.json
```

| Flag | Effect |
|---|---|
| `--output <human\|json\|markdown>` | report format (default `human`) |
| `--report <file>` | write the report to a file |
| `--ai-prompts <file>` | export fix prompts as JSON (only issues with a known fix strategy) |
| `--score` | print only the health score |
| `--verbose` | list the matching files per rule |
| `--diff [base]` | scan only files changed vs the base branch |
| `--project <name>` / `-y, --yes` | pick workspace project(s) / scan all without prompting |
| `--no-lint` / `--no-dead-code` | skip the lint / dead-code analyses |
| `--offline` | skip telemetry |
| `-v, --version` / `-h, --help` | version / help |

If a flag above is rejected, the CLI has moved — run `npx -y vercel-doctor@latest --help` and use what
it reports rather than guessing.

### ⚠️ Two behaviours the `--help` does not tell you (found by running it)

1. **With uncommitted changes it silently scans only those.** You don't have to pass `--diff` — if the
   working tree is dirty the run prints *"Scanning uncommitted changes"* and looks at just those files.
   A dirty tree can therefore produce a confident **"No issues found!"** that means nothing. **Run it on a
   clean tree** (commit or stash first) when you want a real audit, and check the line that says either
   *"Found N source files"* (full scan) or *"Scanning N changed source files"* (diff mode) before you
   trust the result.
2. **`--offline` also disables the score.** Telemetry is what computes it (`--help`: *"anonymous, not
   stored, only used to calculate score"*). Use `--offline` for a private codebase and accept there is no
   number; drop it only when the user is happy for the scan to phone home.

## The six cost areas it scans

| Area | Typical finding | Who fixes it in dev-flow |
|---|---|---|
| **Caching** | `fetch`/routes that opt out of the CDN; missing `"use cache"` / `revalidate` | **`data-fetching`** (Next 16 Cache Components — `"use cache"`, `cacheLife`, `revalidateTag`) |
| **Unused code** | dead files, exports, types | safe cleanup (delete + `tsc` verify) — mechanical, this skill |
| **Function duration** | long-running serverless work, blocking awaits, oversized bundles | this skill flags; heavy refactors → the owning feature skill |
| **Image optimization** | unoptimized images, missing `sizes`, raster where SVG fits | **`design-md-to-app`** image patterns / `next/image` config |
| **Function invocations** | patterns triggering excessive serverless calls (per-request fan-out) | **`data-fetching`** (lift reads to Server Components, batch) |
| **Platform / config** | `next.config` / `vercel.json` / region / runtime misconfig | this skill (config is mechanical) |

## Run, then route

1. **Preconditions.** `meta.json#stack.framework ∈ {"next","monorepo"}` and the deploy target is Vercel (`stack.deploy = "vercel"` or the user says so). Refuse otherwise — the checks are Vercel-specific.
2. **Run** `npx -y vercel-doctor@latest . --output markdown --report docs/vercel/doctor-report.md` at the project root (or `apps/web/`, or `--project <name>` in a monorepo). Add `--ai-prompts docs/vercel/doctor-fixes.json` when you want the fix prompts. Capture the **markdown report** + **health score** (`--score` alone if you only need the number).
3. **Triage** each finding by area (table above). **Verify it in the code** before acting — a scan is a
   signal, not a verdict. Trust the categories unequally:

   | Category | Trust | Why |
   |---|---|---|
   | Caching / route policy | **high** | reading a route's headers is a fact |
   | Deployment + config (file count, `--archive=tgz`, Fluid Compute) | **high** | mechanical, verifiable |
   | Static-asset size | medium | the threshold is low (~25 KB); judge each asset |
   | Link prefetch | **read the version first** — see below | |
   | **Dead code (`Unused file` / `Unused export` / `Unused type`)** | **lowest — never act on it alone** | see below |

   ⚠️ **The dead-code pass is the one that will hurt you.** It runs `knip`, which resolves imports on its
   own and does **not** know about framework-discovered entry points. On a real run against a Next 16 +
   eve project it flagged **67 of 115 files (58%) as unused** — and every one we spot-checked was wrong:
   `agent/agent.ts` (the **eve agent entry point**, discovered by path, imported by nobody — deleting it
   destroys the agent), `db/index.ts` (imported by `agent/tools/*` via a relative path), `hooks/use-mobile.ts`
   (imported through the `@/` alias), and `buttonVariants` (used by `components/ui/calendar.tsx`).
   **Open every file before deleting it**, and treat anything a framework discovers by convention —
   `agent/**`, route files, `middleware`/`proxy`, `instrumentation.ts`, config files — as a guaranteed
   false positive. When in doubt, `--no-dead-code` and audit that separately.

   ⚠️ **The Link-prefetch advice predates Next 16.3.** It says "add `prefetch={false}`… add `prefetch={true}`
   only to critical links", which was right when every link cost a prefetch request. Under **Partial
   Prefetching** (16.3) Next prefetches one reusable **App Shell per route**, so rendering a `<Link>` is
   effectively free and `prefetch={true}` means something different (deeper per-link prefetch + runtime
   prefetching). On ≤16.2 the advice stands; on 16.3+ with `partialPrefetching` on, **ignore it** and follow
   `data-fetching` §Instant Navigations instead.
4. **Apply the safe, mechanical fixes** here (dead-code deletion with `tsc --noEmit` green, config corrections, `next/image` `sizes`/format tweaks).
5. **Route the judgment calls** to the owning skill rather than hand-fixing: caching + invocation findings → `data-fetching` (it owns the Next 16 read/caching ladder); image-pattern findings → `design-md-to-app`. Don't re-implement their rules here.
6. **Persist**: write the report to `docs/vercel/doctor-report.md`, update `meta.json#vercel_doctor`, append `history`. **No phase bump.**

## `meta.json#vercel_doctor` block

```jsonc
"vercel_doctor": {
  "last_run_at": "<ISO>",
  "health_score": 0,            // as reported
  "findings": { "high": 0, "medium": 0, "low": 0 },
  "fixed": ["unused-code","image-sizes"],
  "routed": { "data-fetching": ["caching","invocations"], "design-md-to-app": ["images"] }
}
```

## dev-flow hook

Horizontal capability — run any time. dev-flow **proposes it as a pre-deploy gate** at `feature_complete` (right beside `compliance-audit` — legal gate + cost gate before shipping), and re-runs it in the `deployed` maintenance loop (catch cost regressions after changes). It records `meta.json#vercel_doctor` + `history` and **never bumps `phase`**. It never *blocks* the deploy on its own — it surfaces the score + findings so the user decides.

## Relationship to other skills

- **`compliance-audit`** — the sibling gate: legal/privacy risk (GDPR/AI-Act) vs vercel-doctor's cost/perf risk. Both are `feature_complete` pre-deploy gates, both no-phase-bump, both "auto-fix safe + route/flag the rest."
- **`data-fetching`** — owns the real fix for the two biggest cost areas (caching, invocations). vercel-doctor **detects**, `data-fetching` **corrects** (Next 16 `"use cache"` / Server-Component reads). Don't duplicate its ladder.
- **`shadscan`** — the third gate: UI quality + accessibility. Same shape (pre-deploy, no phase bump, auto-fix safe + route the rest), different surface. Worth noting the contrast in *precision*: shadscan reports what is present in the file it names, while the dead-code pass here resolves imports speculatively and gets it wrong most of the time.
- **`vercel-deploy`** — the actual Vercel deploy. vercel-doctor runs *before* it, not instead of it.

## Definition of Done

- `docs/vercel/doctor-report.md` written; `meta.json#vercel_doctor` populated with the score + findings.
- Safe fixes applied as reviewable diffs (dead code removed with `tsc` green; config/image tweaks); judgment calls routed to `data-fetching` / `design-md-to-app` with a one-line pointer each.
- Every reported finding was **verified in code** before acting (no raw scan noise).

## What this skill does NOT do

- **Not a legal/privacy audit** — that's `compliance-audit`.
- **Doesn't deploy** — that's `vercel-deploy`.
- **Doesn't re-implement** the caching/read rules — it routes to `data-fetching`.
- **Doesn't bump `phase`**, and never blocks deploy by itself.

## Reference files

- `references/contracts.md` — the `.workflow/` dev-flow contract (vendored).
