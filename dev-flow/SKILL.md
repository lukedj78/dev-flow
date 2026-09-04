---
name: dev-flow
description: 'Orchestrate an end-to-end product-development workflow built on atomic skills. Reads `.workflow/meta.json` in a project directory, works out which phase the user is in (idea → PRD → tasks → design → scaffolded → pages → modules → tests → pre-deploy gates → deployed), and delegates to whichever specialist skill owns the next move — across the web, mobile, monorepo and eve-agent families. Use when the user wants to "start a new project end-to-end", "advance my project to the next stage", "what should I do next on this project", or pastes a brand-new product idea / Figma URL / inspiration images with a request to "build the app". Not for: deeply-specialized work inside one stage (invoke that specialist skill directly).'
---

# dev-flow — workflow orchestrator

`dev-flow` does not do the work itself. It is a **router**: it inspects the project's `.workflow/` folder, decides what's next, and tells the user which specialist skill to invoke (or invokes it).

The whole point of this skill is that the user can say *"continue building this thing"* without remembering which step comes next. The orchestrator reads `meta.json`, looks at what's already there, and proposes the next move.

## When this skill applies

- The user pastes a Figma URL, a product idea, or a vague "let's build X" request and wants the entire pipeline.
- The user opens a project directory and asks "what's next" / "continue".
- The user is unsure which of the dev-flow specialist skills to use.

If the user is clearly inside one phase (e.g., "improve the auth module", "regenerate the pricing page from this screenshot"), call the relevant specialist skill directly — don't route through the orchestrator.

## The contract

`.workflow/` is the load-bearing convention. Read **`references/contracts.md`** before doing anything — it defines the folder layout, the `meta.json` schema, the `phase` enum, and which skill owns which file. **Do not improvise.** If a skill behaves in a way the contract doesn't describe, fix the contract or fix the skill — never silently diverge.

## Golden rules (enforced on every project)

Two non-negotiables, defined in full in `references/contracts.md` §Golden rules — every skill honors them:

1. **Code is in English** — functions, variables, constants, types, file names, DB columns, API fields, comments. Independent of the conversation language (the user may speak Italian; the code is still English). Only user-facing copy is localized (rule 2).
2. **Every frontend ships i18n from day one** — no hardcoded user-facing strings; all copy through i18n keys. Web → **[next-intl](https://next-intl.dev/)** (`stack.i18n = "next-intl"`), mobile → the RN i18n stack. Minimum locales **English + Italian** (`stack.locales = ["en","it"]`, default `en`); more per project. Set at scaffold, not deferred.

Plus **ecosystem-first recommended defaults** (contract §Recommended default libraries) — e.g. maps → **mapcn** (web) / **mapcn-rn** (mobile). Reach for these when the capability is needed rather than hand-rolling.

## Stack-aware routing

`dev-flow` reads `meta.json#stack.framework` and routes to a stack-specific family of operative skills.

| `stack.framework` value | family | bootstrap skill | reference |
|---|---|---|---|
| `next` (default if missing) | existing web skills | `design-md-to-app` | (this file) |
| `expo-rn` | RN/Expo mobile skills | `rn-bootstrap` | `references/stack-expo-rn.md` |
| `monorepo` | turborepo (web + mobile, shared packages) | `monorepo-bootstrap` | `references/stack-monorepo.md` |
| `agent` | agent-only — eve at the repo root, no web app | `eve-agent` | contract § `framework` |

When `meta.json#stack.framework == "expo-rn"`:
- `prd_drafted` or `design_extracted` → invoke `rn-bootstrap`
- `scaffolded` or `page_generated` or `module_added` → invoke `rn-add-screen` (UI) or `rn-module-add` (backend/infra) or `rn-write-tests` (tests)
- `feature_complete` → invoke `rn-eas-deploy`
- `deployed` → maintenance loop: `rn-add-screen` for new features, `rn-eas-build-submit-update` for OTA hotfixes

When `meta.json#stack.framework == "monorepo"`:
- `prd_drafted` or `design_extracted` → invoke `monorepo-bootstrap`
- `monorepo_initialized` (new phase, mid-bootstrap) → `monorepo-bootstrap` continues (invokes `design-md-to-app` in `apps/web/` then `rn-bootstrap` in `apps/mobile/`)
- `scaffolded` or `page_generated` or `module_added` → web side: `screenshot-to-page` / `module-add` (operate in `apps/web/`). Mobile side: `rn-add-screen` / `rn-module-add` (operate in `apps/mobile/`). Agent side: `eve-agent` (operates in `apps/agent/` — see the agent-engine track below). Cross-cutting: `monorepo-add-shared-package`, `monorepo-sync-types`
- `feature_complete` → web: `vercel-deploy` (Vercel). Mobile: `rn-eas-deploy`. Agent: `eve-agent` ships via `eve deploy` (Vercel). Run all that apply.
- `deployed` → maintenance loop on all sides

When `meta.json#stack.framework == "agent"` (shape ③ — no web app):
- `prd_drafted` → invoke `eve-agent`, which is the **bootstrap** skill here and bumps `phase` to `scaffolded`
- `scaffolded` → `eve-agent` in capability mode (tools, channels, skills, schedules, subagents) and `eve-registry-porting` to borrow from a registry. No phase bump on those — they append to `history`
- `feature_complete` → `compliance-audit` (the one gate that still applies — there is no UI for `shadscan` and no Vercel cost surface for `vercel-doctor` beyond the agent's own functions), then ship with `eve deploy`
- `deployed` → maintenance loop: more capabilities, re-run `compliance-audit` after material changes

**Don't offer the web skills here and don't apologise for their absence** — `design-md-to-app`, `forms`, `data-fetching`, `state-discipline`, `transitions`, `shadscan` all correctly refuse a project with no frontend. `design_extracted`, `page_generated` and `module_added` are never reached.

If a stack value is not recognized, refuse and ask the user which stack to use. NEVER silently fall back to Next.js when `stack.framework` is set explicitly to something else.

See `references/stack-expo-rn.md` for the full RN stack configuration and `references/stack-monorepo.md` for the monorepo stack configuration.

## Workflow

### Step 1 — Locate or create the project root

Ask the user for the project's absolute path. If they don't have one, propose `~/projects/<slug>/` where slug is derived from the project name (see contract for derivation rules).

If `<root>/.workflow/` does not exist, create it and write a minimal `meta.json`:

```json
{
  "project_slug": "<slug>",
  "project_name": "<name>",
  "created_at": "<ISO-8601 UTC now>",
  "updated_at": "<same>",
  "phase": "empty",
  "stack": {
    "i18n": null, "locales": ["en", "it"],
    "framework": null, "ui": null, "auth": null, "db": null,
    "payments": null, "deploy": null, "agent": null
  },
  "history": []
}
```

Skills downstream require `meta.json` to exist — never skip this.

### Step 2 — Read state and decide the next move

Read `.workflow/meta.json`. Branch on `phase`:

| Current `phase` | Next move (in priority order) |
|---|---|
| `empty` | `prd-from-idea` (capture idea + draft PRD). If the user already has a Figma URL handy, can also detour via `figma-to-design-md` first — but PRD usually comes first for clarity. |
| `idea_captured` | `prd-from-idea` (expand `PROJECT.md` into a `PRD.md`). |
| `prd_drafted` | `prd-to-tasks` if user wants explicit task breakdown; OR `figma-to-design-md` if user has a Figma; OR `image-to-design-md` if user has 1+ raster images (PNG/JPG screenshots, mockups, Pinterest pins); OR jump to `design-md-to-app` if simple project + DESIGN.md will be hand-written. |
| `tasks_split` | **Propose `linear-scrum` (Setup)** to take the project into Linear + set up scrum (default, skip only on explicit opt-out); then `figma-to-design-md` or `image-to-design-md` or `design-md-to-app`. |
| `design_extracted` | `design-md-to-app` (this is the natural next step — DESIGN.md exists, time to scaffold). |
| `scaffolded` | `screenshot-to-page` if `screenshots/` has unmapped images; `module-add` to wire auth/db/etc.; `forms` for any form-building request; iterate. |
| `page_generated` | **Propose `spec-review`** on the diff; `module-add` or more `screenshot-to-page` runs; `forms` for forms inside generated routes; `data-fetching` if any page needs server reads. |
| `module_added` | **Propose `spec-review`** on the branch just landed (cheapest while it is still open — does the diff match `PRD.md`/`tasks.md`, and the declared stack?); `write-tests` to add per-feature coverage (especially after `module-add db` / `module-add auth`); more `screenshot-to-page`; or iterate. When the build is done, advance to `feature_complete` (all stacks) → `compliance-audit` pre-deploy gate, then deploy. |
| `feature_complete` | **Propose the three pre-deploy gates**: `compliance-audit` (legal — GDPR/AI-Act, any stack) + `vercel-doctor` (cost/perf — web on Vercel) + `shadscan` (UI quality + a11y — web on shadcn). Then deploy: mobile (`expo-rn`) → `rn-eas-deploy`; web → `vercel-deploy`; agent → `eve deploy`. |
| `deployed` | Maintenance loop: mobile → more screens via `rn-add-screen`, OTA hotfixes via `rn-eas-build-submit-update`; re-run `compliance-audit` + `vercel-doctor` + `shadscan` after material changes; telemetry monitoring. |
| anything else | Treat as `empty` (forward-compatible). |

**Project-management policy (Linear + scrum).** Every project is run in **Linear with agile scrum** unless the user explicitly opts out. When `tasks.md` exists (phase `tasks_split`, or `prd_drafted` once tasks are generated), propose `linear-scrum` **Setup**. `linear-scrum` is also a **horizontal capability** — invoke it any time for **Sync** (push new tasks, plan the sprint, report velocity), regardless of `phase`. It records `meta.json#linear` + `#scrum` and appends `history`, but never bumps `phase` and never gates progression. For an existing project already partly in Linear, `linear-scrum` **Adopt** backfills the link.

**Compliance policy (GDPR + EU AI Act).** `compliance-audit` is a **horizontal capability** — invoke it any time to audit an existing project against the 10-point GDPR/AI-Act risk register (DSAR, consent, EU data residency, retention/PII, AI-transparency, high-risk, sub-processors…) and, on request, apply the **safe** remediations while flagging the legal decisions. dev-flow **proposes it as a pre-deploy gate**: when a project reaches `feature_complete` (before `vercel-deploy` / `rn-eas-deploy` / `eve deploy`), and again in the `deployed` maintenance loop (re-audit after material changes). It records `meta.json#compliance` + appends `history`, **never bumps `phase`**, and never *blocks* deploy on its own — it surfaces findings so the user decides. Especially relevant when `stack.agent = "eve"` (AI-transparency + memory/residency risks) or the product handles user accounts (DSAR + Apple/Play deletion). Not legal advice — it produces engineering findings + a DPIA template, a DPO/counsel confirms.

**Cost/perf policy (Vercel).** `vercel-doctor` is the **cost/performance sibling** of `compliance-audit` — a horizontal pre-deploy gate for web projects on Vercel. It wraps the third-party `vercel-doctor` CLI (scans a Next.js codebase for costly Vercel patterns — caching that defeats the CDN, dead code, function duration, image waste, excessive invocations, config), applies the safe mechanical fixes, and **routes the real fixes to the owning skill** (`data-fetching` for caching/invocations, `design-md-to-app` for images). Proposed at `feature_complete` (beside `compliance-audit`) and in the `deployed` loop. Records `meta.json#vercel_doctor` + `history`, **never bumps `phase`**, never blocks deploy on its own. Refuses for non-Vercel/non-Next targets.

**Review policy (spec + conventions).** `spec-review` reads the **change**, not the finished artefact — which is what separates it from the three gates. Two axes in parallel sub-agents, **never merged**: *Spec* (does the diff implement what `.workflow/PRD.md` + `tasks.md` asked?) and *Standards* (does it obey the golden rules, the declared `meta.json#stack`, and the discipline skills — with a Fowler smell baseline as the floor). One combined verdict would let either axis hide behind the other: code can follow every convention and build the wrong feature, or build exactly the right feature ignoring the stack the project declared. Propose it **when a chunk of work lands** (`page_generated`, `module_added`), not only before shipping — a spec finding is cheapest while the branch is open. Records `meta.json#spec_review`; **never bumps `phase`**; never blocks. It is **not** Claude Code's built-in `/code-review`: that one reviews code generically and knows nothing about `.workflow/`. Without a `.workflow/`, `spec-review` refuses and points there instead.

**UI-quality policy (accessibility + fundamentals).** `shadscan` is the **third pre-deploy gate**, completing the trio: `compliance-audit` reads the **legal** surface, `vercel-doctor` the **cost** surface, `shadscan` the **UI** one. It wraps the third-party `@shadscan/cli` — a deterministic, read-only static audit of a React/shadcn app across six categories (Foundation, Interaction, States, Accessibility, Forms, Production Polish) scored out of 100 with file:line evidence — applies the high-confidence fixes, surfaces the product `decide` items to the user, and **routes the real corrections to the owning skill** (`forms` for form wiring, `transitions` for reduced-motion, `data-fetching` for Suspense/loading boundaries, `design-md-to-app` for shell/empty-state/metadata, `composition-patterns-guide` for anatomy). It is the only thing in dev-flow that can **mechanically verify our own contract landed** — that the `prefers-reduced-motion` guard `transitions` mandates and the error association `forms` prescribes are actually in the built UI. Proposed at `feature_complete` and in the `deployed` loop. Records `meta.json#shadscan` + `history`, **never bumps `phase`**, never blocks deploy on its own. **Never optimise for the score** — adding unused infrastructure to raise the number is a regression that scores well. Web only (DOM/React rules); refuses for `expo-rn`.

**Animated icons.** `heroicons-animated` adds one Motion-animated Heroicon from the `@heroicons-animated/*` shadcn registry (ecosystem-first: don't hand-animate an SVG). It requires the `motion` runtime (`module-add motion`) and enforces the `transitions` reduced-motion discipline the raw components lack. Web only; horizontal; no phase bump.

The orchestrator must propose, not impose. After deciding, **tell the user the proposed next step in one sentence**, and ask for confirmation before invoking. Example: *"You're at `design_extracted` (DESIGN.md + 6 screenshots in place). I propose running `design-md-to-app` to scaffold a Next.js + shadcn project. OK to proceed, or do you want to add modules / change stack first?"*

### Step 3 — Invoke the right skill

When the user confirms, invoke the specialist skill with explicit input:

- the project root path
- relevant `meta.json` fields (e.g., `stack` for `design-md-to-app`)
- any user-supplied input (Figma URL, screenshot path, brand brief)

The specialist skill writes its outputs into `.workflow/`, updates `phase` and appends to `history` in `meta.json`.

After the specialist returns, **read `meta.json` again** to confirm the phase advanced. If it didn't, the specialist either errored or the user aborted — propose the next move accordingly.

### Step 4 — Loop

Most projects need multiple specialists in sequence. The orchestrator's job is to keep going: after one specialist finishes, immediately re-evaluate state and propose the next step. Keep looping until the user says "stop" or `phase` reaches `module_added` and the user has nothing more to add.

## Stack decisions

When transitioning out of `prd_drafted` and into scaffolding, the user has to choose a stack. The orchestrator should ask once and persist in `meta.json#stack`. Sensible default-bundle suggestions:

| Profile | framework | ui | auth | db | payments | deploy |
|---|---|---|---|---|---|---|
| **SaaS B2B** (web, distinctive brand) | next | shadcn | better-auth | neon-drizzle | stripe | vercel |
| **SaaS B2B** (web, low-maintenance UI) | next | base-ui | better-auth | neon-drizzle | stripe | vercel |
| **B2C consumer** (web) | next | shadcn | clerk | supabase | stripe | vercel |
| **Marketing site** | astro | shadcn-astro | null | null | null | vercel |
| **Internal tool / enterprise** (web) | next | mui | better-auth | neon-drizzle | null | null |
| **Editorial / distinctive brand** (web) | next | shadcn | better-auth | neon-drizzle | null | vercel |
| **Headless + a11y-first** (web) | next | base-ui | better-auth | neon-drizzle | null | vercel |
| **Mobile app (iOS+Android)** | expo-rn | nativewind | supabase | supabase | revenuecat | eas |
| **Mobile app, custom backend** | expo-rn | nativewind | custom-rest | custom-rest | revenuecat | eas |
| **Monorepo (web + mobile)** *(planned)* | monorepo | `{web: <shadcn\|base-ui\|mui>, mobile: nativewind}` | supabase | supabase | revenuecat + stripe | eas + vercel |

Ask the user the project type, propose the bundle, let them override individual choices. Don't ask 6 separate questions when one ("what kind of app?") plus a confirmation gets you there.

**Optional agent engine.** As part of the same decision, ask once whether the product needs an **AI agent engine** (an agentic core: tools the model calls, an agent backend, an assistant surface). Default `stack.agent = null`. If yes → set `stack.agent = "eve"`. The user can also opt in later on demand — see "Agent engine (eve)" below. This is a scope decision, not a pipeline phase.

### Topology policy — app first, monorepo next, agent-only for the rare case

⚠️ **At init, if the shape is not specified, ASK. Do not derive it.** This is a blocking question,
not a default to apply quietly: the answer changes the directory layout, every command the user will
type, and how much scaffolding stands between them and the first line of product code. Deriving it —
"two roles, so two agents, so a monorepo" — reaches an answer without ever asking what the second
consumer is, which is the only question that decides it.

The question is short and it is one question, not six:

> Is this one app, or does the agent have a life of its own — its own deploy cadence, channels beyond
> the web UI, or a second consumer that shares its types? If there is no second consumer, it is one app.

Then say the shape out loud, with its reason, and let the user correct it before anything is
scaffolded. Getting this wrong is cheap to fix on day one and expensive on day ten.

When an agent is in scope, **three shapes are possible and the project decides which**. Propose in this order, and say which one you are proposing and why:

| Shape | `stack` | Choose it when |
|---|---|---|
| **1 · Single web app** *(default)* | `framework: "next"`, `agent: "eve"` (agent inside the app) | The product **is** the interface. One deploy, no workspace overhead — the ordinary case, and where a frontend developer does their actual work. |
| **2 · Monorepo** | `framework: "monorepo"`, `agent: "eve"` → `apps/web` + `apps/agent` | The agent has a life of its own — its own deploy cadence, channels beyond the web UI, or a second consumer (mobile, a second app) that must share types/tokens. |
| **3 · Agent only** | `framework: "agent"`, `agent: "eve"`, no web app | Every surface is somewhere else — Slack, email, GitHub, Linear — and **nothing needs rendering**. Vercel Labs' `kody-eve-template` is this shape. |

**The house default is 1, then 2.** Reach for 3 only when the product genuinely has no UI, not because the agent feels architecturally tidy on its own.

**Don't fossilise the choice** — it follows the product, not a habit. Two directions matter:
- A single app **can become** a monorepo later: that is `monorepo-bootstrap`'s job, and moving `agent/` into `apps/agent/` is a directory move, not a rewrite. Starting at 1 does not cost you 2.
- Choosing 2 up front costs workspace overhead on every command for a second app that may never ship. Ask what the *second* consumer is; if there is no answer, it is 1.

Say the shape out loud when you propose the stack — "single Next.js app with the agent inside it" is a different project from "monorepo with two deploys", and the user should be agreeing to one of them, not discovering it at scaffold time.

### shadcn create parameters (only when `ui = "shadcn"`)

shadcn CLI v4 scaffolds via `shadcn create`/`init` with several parameters (the same ones the <https://ui.shadcn.com/create> wizard asks). When `stack.ui = "shadcn"`, capture them into `meta.json#stack` so `design-md-to-app` can pass them to the CLI.

**First, offer the preset path.** Ask once: *"Hai un preset shadcn da ui.shadcn.com/create? (incolla il codice, es. `b5owWMfJ8l`)"*. A preset packs the whole shadcn visual system — style, base color, theme, icons, fonts, radius — into one code, made to hand off to agents.
- **If yes** → set `stack.shadcn_preset = <code>`. The preset owns the visual layer: **don't** ask base color / theme / icons, and the scaffold will pass `--preset` and skip the DESIGN.md token install for visuals. Still ask `ui_base` (the preset may not encode Radix-vs-Base-UI). You can `shadcn preset decode <code>` to show the user what it contains.
- **If no** → DESIGN.md-first path with the hybrid asking below.

**Hybrid policy (no-preset path): explicitly ask only the parameters that matter and that DESIGN.md does NOT own; leave the visual ones to DESIGN.md without asking.**

| Parameter | Stack key | Ask? | Values / default |
|---|---|---|---|
| **Primitive base** | `ui_base` | **ASK** | `base` (default — Base UI, shadcn's default since 2026-07) \| `radix` \| `aria` (React Aria). DESIGN.md does NOT override it. |
| Icon library | `icon_library` | **ASK** | lucide (default) \| radix-icons \| tabler |
| RTL | `rtl` | **ASK only if i18n/RTL relevant** | `false` (default) |
| Template / framework | (uses `stack.framework`) | already chosen | next \| vite \| start \| react-router \| laravel \| astro |
| Base color | `base_color` | **don't ask** — DESIGN.md owns it | scaffold default `neutral`; DESIGN.md tokens are the real palette |
| Starting theme | `ui_theme` | **don't ask** — DESIGN.md owns it | default `null`; DESIGN.md tokens override |
| CSS variables | `css_variables` | **don't ask** | stays `true` (required for token theming) |
| Monorepo | (uses `stack.framework="monorepo"`) | already chosen | — |

So in practice you ask **two** things (plus RTL only when relevant): *"shadcn su Base UI (default), Radix o React Aria?"* (`ui_base`) and *"icone: lucide o altro?"* (`icon_library`). Don't prompt for base color / theme — those come from the DESIGN.md tokens; setting `css_variables=true` silently. Record the answers in `meta.json#stack`; `base_color` defaults to `neutral` and `ui_theme` to `null` for the initial scaffold.

Just before scaffolding, `design-md-to-app` prints a **recap of the full resolved shadcn create config and asks for confirmation** (its Step 4 confirmation gate) — including the values derived from DESIGN.md — so nothing is scaffolded on assumed config.

> `ui = "base-ui"` (standalone Base UI, no shadcn CLI) is a **different** choice from `ui = "shadcn"` + `ui_base = "base"`. The latter keeps shadcn's component set + blocks on Base UI primitives and is usually preferable; pick standalone Base UI only when the user explicitly wants no shadcn CLI. See `design-md-to-app/references/library-choice.md`.

**`ui = "coss"` (Coss/UI — the Cal.com design system).** A fourth UI choice inside the shadcn/Base-UI family: Coss/UI is installed through the shadcn CLI's `@coss/*` registry, is built on Base UI, and ships CSS-variable tokens **with the same names as shadcn/ui**, so the DESIGN.md → tokens pipeline works unchanged. When the user picks Coss (`stack.ui = "coss"`, implies `ui_base = "base"`), route to the **`coss-ui`** skill, which owns the Coss-specific install/add and token reconciliation; `design-md-to-app` still owns the generic scaffold. It is a deliberate choice with two caveats — **Tailwind CSS v4 required** and a **mixed MIT/AGPLv3 license** — so don't default to it; offer it when the user wants the Cal.com aesthetic/DX or an AI-first Base-UI kit. See `coss-ui/SKILL.md`.

For mobile profiles (`framework: "expo-rn"`), see `references/stack-expo-rn.md` for the canonical wiring; the actual modules are wired by `rn-module-add` after `rn-bootstrap` scaffolds.

## Discipline skills (Next.js 16 web) — horizontal, trigger-driven

Four sibling skills live alongside the phase-driven flow above. They do **not** bump `phase` and they apply only to `stack.framework ∈ {"next", "monorepo"}` + `stack.nextjs_version = "16"`. Invoke them when the trigger fires, regardless of current `phase`:

| Skill | Trigger | What it does |
|---|---|---|
| `forms` | User mentions "form", "edit panel", "create dialog", "settings page", "save button" — OR you're about to write a form, `useState` for field values, raw `useForm`, hand-rolled dirty tracking, inline `toast` on submit | Routes through `lib/forms/` shared toolkit. Scaffolds it on first run via `forms/scripts/scaffold_lib_forms.py` (reads `stack.forms` = `"tanstack-form"` or `"react-hook-form"`). Refuses if Pages Router or pre-16. |
| `data-fetching` | User is about to add `useEffect` to fetch, convert a page to `"use client"` for filter state, add a `"use server"` `getX`/`listX`/`findX`, or pastes `useState + useEffect + fetch` | Walks the 4-rung ladder: Server Component → URL `searchParams` → `Promise<T>` + `use()` + `<Suspense>` → Route Handler + SWR (last resort). Bans Server Actions for reads. |
| `state-discipline` | User pastes `useState + useEffect`, reaches for `useState` to mirror a prop, derives a value via `useEffect + setState`, or asks "should I `useState` here?" | Walks the 8-rung ladder: derive → URL → lift → query lib → event handler → `key` reset → `useMountEffect` → honest `useState`. Bans bare `useEffect`. |
| `transitions` | User says "add a transition / animation", "animate this", "page transition", "stagger these cards" — OR you're about to write an inline `transition:` / `animate={{…}}` / `@keyframes` / a Tailwind `duration-[Xms]` | Routes motion through one token layer (`lib/motion/`) + a curated library, cheapest-tier-first (Tailwind/`tw-animate-css` → CSS keyframes → View Transitions → Motion). Always ships `prefers-reduced-motion`. Sits above `module-add motion`; routes there for Tier-3 spring/layout/gesture. Records `stack.motion`. |

All four append a `history` entry per run (no phase bump) and have `audit-recipe.md` references for "audit my codebase against X" requests. When in doubt about whether to call them: if `stack.framework` is web-shaped and the conversation touches forms / reads / `useEffect` / `useState` / motion, route there.

## Agent engine (eve) — an optional, on-demand component

`eve-agent` is **not** a discipline skill and **not** a phase stage. It is an **optional product component** — a scope decision, like "does this product take payments?". The user opts in, and from then on the project has an `apps/agent` surface (an **eve** agent — Vercel's filesystem-first agent framework) that the web app consumes as its AI engine. It is the agent counterpart to `design-md-to-app` + `module-add`: where those build/grow the Next.js app, `eve-agent` builds/grows `apps/agent`.

There are **two moments** to opt in:

1. **At analysis time** — during the stack/scope decision (see "Stack decisions" below), ask once: *"Does this product need an AI agent engine (eve)?"* If yes, set `meta.json#stack.agent = "eve"`. This promotes the project to a monorepo (`apps/web` + `apps/agent` + `packages/types`) if it isn't one already.
2. **Later, on demand** — the user says "add an agent / agent backend / AI core" or names "eve". Same effect: flip `stack.agent` to `"eve"` and bring in `eve-agent`.

Once opted in, route to `eve-agent` and let it pick its mode from state: **Scaffold mode** if `apps/agent` doesn't exist yet (sets up the engine once), **Capability mode** if it does (add one tool / skill / channel / connection / schedule / subagent / hook / eval, idempotently).

Why it sits **outside** the `phase` line: `phase` tracks the web app's linear build; the agent has its own cadence (an open-ended "add one capability" loop, often driven by Linear issues, not by dev-flow). So `eve-agent` records existence in `stack.agent` and appends to `history`, but never bumps `phase`. It owns `apps/agent/` exclusively (the orchestrator and the web/mobile skills never write there), and meets the web app at `packages/types` (re-exported eve session/event types) and the `withEve()` proxy in `apps/web`. eve's model calls bill through the Vercel AI Gateway, separate from the build tooling. Choosing the AI Gateway **service tier** (priority/flex/default) is `eve-agent`'s call, not dev-flow's — see `eve-agent/references/eve-scaffold.md` §3.

## Shipping the product's own agent-skill

Every product this flow builds may end up with an API. One that only its own
frontend calls is an implementation detail. One that **somebody else's coding
agent could drive** is a distribution channel — and it needs a single artefact to
be usable: a skill file telling that agent how the product works.

**Raise it once, at `feature_complete` → `deployed`,** when all three hold:

1. the product has a callable surface that is not only its own frontend —
   route handlers under `app/api/`, an OpenAPI spec, a public eve agent
   (`stack.agent = "eve"`), or an MCP server; **and**
2. there is a deployed origin to put in the file; **and**
3. `meta.json#stack.agent_skill` is not set yet.

Then say it plainly, once: *"your product is something a coding agent could
drive — want me to write its agent-skill, so your users can install it and use
`<product>` from Claude Code or Cursor?"* If yes, route to
**`product-to-agent-skill`**.

⚠️ **What it produces belongs to the product, not to dev-flow.** The file lands
in `<product-repo>/skills/`, ships and versions with that product, and is aimed
at whoever installs *that* repo. It is never added to dev-flow's own skills,
never copied into `~/.claude/skills/`, and never listed in `install.sh` —
the same relationship dev-flow has with the `app/` it builds and does not own.

Don't raise it when the API exists only to serve the product's own pages: a
skill describing an internal route handler is a lie with a nice table in it.

## External skills — suggest, never install

dev-flow ships its skills free. It is also allowed to **mention that
somebody else's skill exists** when a project reaches a point where one would
help — the way a colleague tells you which tool down the hall does the thing you
just asked for.

`references/external-skills.md` holds the list: what each one does, the single
moment in a project when it is worth raising, what it costs, and what dev-flow
already does for free instead.

Four rules keep this from turning dev-flow into a paid product:

1. **Suggest; the user installs.** Never run `npx skills add` on their behalf,
   never add one to `install.sh`, never let a dev-flow skill import or require one.
2. **Say the price in the same breath**, before the user goes anywhere near a
   signup page. A payment step must never arrive as a surprise.
3. **Name the free path we already have**, and let the user choose. The suggestion
   is an option, not a recommendation.
4. **Only when the work reaches it** — never as a menu of possibilities at kickoff.

Nothing in that file is a dependency: delete every row and dev-flow does exactly
what it did before.

## What dev-flow does NOT do

- **Doesn't do specialist work itself.** No PRD writing, no DESIGN.md generation, no scaffolding. If you find yourself doing actual work (other than reading state and routing), stop — call the right specialist.
- **Doesn't edit `app/`.** That's owned by `design-md-to-app` and friends.
- **Doesn't edit `apps/agent/`.** That's owned exclusively by `eve-agent`.
- **Doesn't make stack decisions silently.** Always ask the user, even if a default is obvious.
- **Doesn't skip phases.** If the user tries to jump from `empty` straight to `design-md-to-app`, gently push back: at minimum `PROJECT.md` should exist so the design-to-app skill knows the brand voice.

## Bundled scripts

- `scripts/init_workflow.py <project-root> [--name "Project Name"]` — creates `.workflow/` with a fresh `meta.json`. Use when the user opts into the orchestrator on an empty directory.
- `scripts/show_state.py <project-root>` — prints the current `phase`, the files present, and the proposed next step. Use early in every conversation when the user asks "what's next".
- `scripts/update_meta.py <project-root> <op>` — mutate `meta.json` from a skill. Three operations:
  - `record-artifact --path <p> --produced-by <skill> [--derived-from <p1> <p2> …]` — hash a file and record it under `meta.json#artifacts`. Skills call this after writing/updating contract files (DESIGN.md, registry.json, generated pages, schema, etc).
  - `set-phase <phase>` — bump phase forward (refuses regression unless `--allow-regress`).
  - `append-history --skill <name> --inputs <json> --outputs <json> --phase-after <phase>` — append a skill run to history.
- `scripts/check_drift.py <project-root>` — diagnostic command. Compares `meta.json#artifacts` against the on-disk files and reports:
  - **fresh**: file matches its recorded hash, all upstreams match too.
  - **self-drift**: the file has been edited since the producing skill last hashed it.
  - **upstream-stale**: the file is unchanged but a `derived_from` input has drifted (e.g., `DESIGN.md` was edited → `registry.json` is now derived from a stale snapshot).
  - **missing**: the file was recorded but no longer exists on disk.
  Exit code is always 0 unless `--exit-nonzero-on-drift` is passed (use in CI).

These scripts are JSON readers/writers; running them doesn't make decisions for the user. The artifact-hashing model is the foundation for **drift detection** — when the user later edits `DESIGN.md` by hand, `check_drift.py` surfaces what's now stale, and you (or the user) decide whether to re-run the relevant skills.

### When to record an artifact

Record an artifact whenever a skill writes a file that:
- Is part of the dev-flow contract (`.workflow/DESIGN.md`, `.workflow/PRD.md`, etc.), OR
- Is a generated config that downstream skills depend on (`registry.json`, `lib/db/schema.ts` initial scaffold, `app/showcase/page.tsx`), OR
- Is a derivative of an upstream artifact (record `derived_from` so drift detection can chain).

Don't record:
- Temporary files, cache, build artifacts.
- Files the user is expected to hand-edit freely (they'd always show as "self-drift").
- Files produced by external tools (`pnpm-lock.yaml`, `node_modules`).

The cost of recording is one shell-out per file; the benefit is a foundation for resumability and drift checks. Err on the side of recording when in doubt for contract-shaped files.
