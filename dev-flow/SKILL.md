---
name: dev-flow
description: 'Orchestrate an end-to-end product-development workflow built on atomic skills. Reads `.workflow/meta.json` in a project directory, figures out what phase the user is in (idea → PRD → tasks → design → scaffolded → pages → modules → tests), and delegates to the right specialist skill: `prd-from-idea`, `prd-to-tasks`, `figma-to-design-md`, `image-to-design-md`, `design-md-to-app`, `screenshot-to-page`, `module-add`, `write-tests`, `forms`, `data-fetching`, `state-discipline`, `eve-agent` (the eve agent engine behind the app). Use when the user wants to "start a new project end-to-end", "advance my project to the next stage", "what should I do next on this project", or pastes a brand-new product idea / Figma URL / inspiration images with a request to "build the app". Not for: deeply-specialized work inside one stage (in that case, invoke the specialist skill directly).'
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

## Stack-aware routing

`dev-flow` reads `meta.json#stack.framework` and routes to a stack-specific family of operative skills.

| `stack.framework` value | family | bootstrap skill | reference |
|---|---|---|---|
| `next` (default if missing) | existing web skills | `design-md-to-app` | (this file) |
| `expo-rn` | RN/Expo mobile skills | `rn-bootstrap` | `references/stack-expo-rn.md` |
| `monorepo` | turborepo (web + mobile, shared packages) | `monorepo-bootstrap` | `references/stack-monorepo.md` |

When `meta.json#stack.framework == "expo-rn"`:
- `prd_drafted` or `design_extracted` → invoke `rn-bootstrap`
- `scaffolded` or `page_generated` or `module_added` → invoke `rn-add-screen` (UI) or `rn-module-add` (backend/infra) or `rn-write-tests` (tests)
- `feature_complete` → invoke `rn-eas-deploy`
- `deployed` → maintenance loop: `rn-add-screen` for new features, `rn-eas-build-submit-update` for OTA hotfixes

When `meta.json#stack.framework == "monorepo"`:
- `prd_drafted` or `design_extracted` → invoke `monorepo-bootstrap`
- `monorepo_initialized` (new phase, mid-bootstrap) → `monorepo-bootstrap` continues (invokes `design-md-to-app` in `apps/web/` then `rn-bootstrap` in `apps/mobile/`)
- `scaffolded` or `page_generated` or `module_added` → web side: `screenshot-to-page` / `module-add` (operate in `apps/web/`). Mobile side: `rn-add-screen` / `rn-module-add` (operate in `apps/mobile/`). Agent side: `eve-agent` (operates in `apps/agent/` — see the agent-engine track below). Cross-cutting: `monorepo-add-shared-package`, `monorepo-sync-types`
- `feature_complete` → web: `setup-deploy` (Vercel). Mobile: `rn-eas-deploy`. Agent: `eve-agent` ships via `eve deploy` (Vercel). Run all that apply.
- `deployed` → maintenance loop on all sides

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
| `tasks_split` | `figma-to-design-md` or `image-to-design-md` or `design-md-to-app`. |
| `design_extracted` | `design-md-to-app` (this is the natural next step — DESIGN.md exists, time to scaffold). |
| `scaffolded` | `screenshot-to-page` if `screenshots/` has unmapped images; `module-add` to wire auth/db/etc.; `forms` for any form-building request; iterate. |
| `page_generated` | `module-add` or more `screenshot-to-page` runs; `forms` for forms inside generated routes; `data-fetching` if any page needs server reads. |
| `module_added` | `write-tests` to add per-feature coverage (especially after `module-add db` / `module-add auth`); more `screenshot-to-page`; or iterate. For `expo-rn` stack, also `rn-eas-deploy` once feature-complete. |
| `feature_complete` | (mobile only — `expo-rn` stack) → `rn-eas-deploy` to build, submit, and ship to App Store + Play Store. |
| `deployed` | (mobile only) maintenance loop: more screens via `rn-add-screen`, OTA hotfixes via `rn-eas-build-submit-update`, telemetry monitoring. |
| anything else | Treat as `empty` (forward-compatible). |

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

**Optional agent engine.** As part of the same decision, ask once whether the product needs an **AI agent engine** (an agentic core: tools the model calls, an agent backend, an assistant surface). Default `stack.agent = null`. If yes → set `stack.agent = "eve"`; this adds an `apps/agent` (eve) surface and promotes the project to a monorepo. The user can also opt in later on demand — see "Agent engine (eve)" below. This is a scope decision, not a pipeline phase.

### shadcn create parameters (only when `ui = "shadcn"`)

shadcn CLI v4 scaffolds via `shadcn create`/`init` with several parameters (the same ones the <https://ui.shadcn.com/create> wizard asks). When `stack.ui = "shadcn"`, capture them into `meta.json#stack` so `design-md-to-app` can pass them to the CLI.

**First, offer the preset path.** Ask once: *"Hai un preset shadcn da ui.shadcn.com/create? (incolla il codice, es. `b5owWMfJ8l`)"*. A preset packs the whole shadcn visual system — style, base color, theme, icons, fonts, radius — into one code, made to hand off to agents.
- **If yes** → set `stack.shadcn_preset = <code>`. The preset owns the visual layer: **don't** ask base color / theme / icons, and the scaffold will pass `--preset` and skip the DESIGN.md token install for visuals. Still ask `ui_base` (the preset may not encode Radix-vs-Base-UI). You can `shadcn preset decode <code>` to show the user what it contains.
- **If no** → DESIGN.md-first path with the hybrid asking below.

**Hybrid policy (no-preset path): explicitly ask only the parameters that matter and that DESIGN.md does NOT own; leave the visual ones to DESIGN.md without asking.**

| Parameter | Stack key | Ask? | Values / default |
|---|---|---|---|
| **Primitive base** | `ui_base` | **ASK** | `radix` (default) \| `base` (Base UI). The Radix-vs-Base-UI choice — DESIGN.md does NOT override it. |
| Icon library | `icon_library` | **ASK** | lucide (default) \| radix-icons \| tabler |
| RTL | `rtl` | **ASK only if i18n/RTL relevant** | `false` (default) |
| Template / framework | (uses `stack.framework`) | already chosen | next \| vite \| start \| react-router \| laravel \| astro |
| Base color | `base_color` | **don't ask** — DESIGN.md owns it | scaffold default `neutral`; DESIGN.md tokens are the real palette |
| Starting theme | `ui_theme` | **don't ask** — DESIGN.md owns it | default `null`; DESIGN.md tokens override |
| CSS variables | `css_variables` | **don't ask** | stays `true` (required for token theming) |
| Monorepo | (uses `stack.framework="monorepo"`) | already chosen | — |

So in practice you ask **two** things (plus RTL only when relevant): *"shadcn su Radix o Base UI?"* (`ui_base`) and *"icone: lucide o altro?"* (`icon_library`). Don't prompt for base color / theme — those come from the DESIGN.md tokens; setting `css_variables=true` silently. Record the answers in `meta.json#stack`; `base_color` defaults to `neutral` and `ui_theme` to `null` for the initial scaffold.

Just before scaffolding, `design-md-to-app` prints a **recap of the full resolved shadcn create config and asks for confirmation** (its Step 4 confirmation gate) — including the values derived from DESIGN.md — so nothing is scaffolded on assumed config.

> `ui = "base-ui"` (standalone Base UI, no shadcn CLI) is a **different** choice from `ui = "shadcn"` + `ui_base = "base"`. The latter keeps shadcn's component set + blocks on Base UI primitives and is usually preferable; pick standalone Base UI only when the user explicitly wants no shadcn CLI. See `design-md-to-app/references/library-choice.md`.

For mobile profiles (`framework: "expo-rn"`), see `references/stack-expo-rn.md` for the canonical wiring; the actual modules are wired by `rn-module-add` after `rn-bootstrap` scaffolds.

## Discipline skills (Next.js 16 web) — horizontal, trigger-driven

Three sibling skills live alongside the phase-driven flow above. They do **not** bump `phase` and they apply only to `stack.framework ∈ {"next", "monorepo"}` + `stack.nextjs_version = "16"`. Invoke them when the trigger fires, regardless of current `phase`:

| Skill | Trigger | What it does |
|---|---|---|
| `forms` | User mentions "form", "edit panel", "create dialog", "settings page", "save button" — OR you're about to write a form, `useState` for field values, raw `useForm`, hand-rolled dirty tracking, inline `toast` on submit | Routes through `lib/forms/` shared toolkit. Scaffolds it on first run via `forms/scripts/scaffold_lib_forms.py` (reads `stack.forms` = `"tanstack-form"` or `"react-hook-form"`). Refuses if Pages Router or pre-16. |
| `data-fetching` | User is about to add `useEffect` to fetch, convert a page to `"use client"` for filter state, add a `"use server"` `getX`/`listX`/`findX`, or pastes `useState + useEffect + fetch` | Walks the 4-rung ladder: Server Component → URL `searchParams` → `Promise<T>` + `use()` + `<Suspense>` → Route Handler + SWR (last resort). Bans Server Actions for reads. |
| `state-discipline` | User pastes `useState + useEffect`, reaches for `useState` to mirror a prop, derives a value via `useEffect + setState`, or asks "should I `useState` here?" | Walks the 8-rung ladder: derive → URL → lift → query lib → event handler → `key` reset → `useMountEffect` → honest `useState`. Bans bare `useEffect`. |

All three append a `history` entry per run (no phase bump) and have `audit-recipe.md` references for "audit my codebase against X" requests. When in doubt about whether to call them: if `stack.framework` is web-shaped and the conversation touches forms / reads / `useEffect` / `useState`, route there.

## Agent engine (eve) — an optional, on-demand component

`eve-agent` is **not** a discipline skill and **not** a phase stage. It is an **optional product component** — a scope decision, like "does this product take payments?". The user opts in, and from then on the project has an `apps/agent` surface (an **eve** agent — Vercel's filesystem-first agent framework) that the web app consumes as its AI engine. It is the agent counterpart to `design-md-to-app` + `module-add`: where those build/grow the Next.js app, `eve-agent` builds/grows `apps/agent`.

There are **two moments** to opt in:

1. **At analysis time** — during the stack/scope decision (see "Stack decisions" below), ask once: *"Does this product need an AI agent engine (eve)?"* If yes, set `meta.json#stack.agent = "eve"`. This promotes the project to a monorepo (`apps/web` + `apps/agent` + `packages/types`) if it isn't one already.
2. **Later, on demand** — the user says "add an agent / agent backend / AI core" or names "eve". Same effect: flip `stack.agent` to `"eve"` and bring in `eve-agent`.

Once opted in, route to `eve-agent` and let it pick its mode from state: **Scaffold mode** if `apps/agent` doesn't exist yet (sets up the engine once), **Capability mode** if it does (add one tool / skill / channel / connection / schedule / subagent / hook / eval, idempotently).

Why it sits **outside** the `phase` line: `phase` tracks the web app's linear build; the agent has its own cadence (an open-ended "add one capability" loop, often driven by Linear issues, not by dev-flow). So `eve-agent` records existence in `stack.agent` and appends to `history`, but never bumps `phase`. It owns `apps/agent/` exclusively (the orchestrator and the web/mobile skills never write there), and meets the web app at `packages/types` (re-exported eve session/event types) and the `withEve()` proxy in `apps/web`. eve's model calls bill through the Vercel AI Gateway, separate from the build tooling.

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
