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

`.workflow/` is the load-bearing convention. **`references/contracts.md`** defines the folder layout, the `meta.json` schema, the `phase` enum, and which skill owns which file. Read the part you are about to act on before acting — the phase enum and the folder layout on a routing turn, §stack at the stack decision, the owning skill's rows before invoking it — rather than the whole file every turn. **Do not improvise.** If a skill behaves in a way the contract doesn't describe, fix the contract or fix the skill — never silently diverge.

## Golden rules (on every project)

Three non-negotiables, defined in full in `references/contracts.md` §Golden rules — every skill honors them. **Rule 3 is enforced by tools** (the design lint, the write-time guard, the `set-phase` gate); **rules 1 and 2 are checked in review** (`spec-review`) — no tool catches a breach of either, so don't report them as verified because the lint is green:

1. **Code is in English** — functions, variables, constants, types, file names, DB columns, API fields, comments. Independent of the conversation language (the user may speak Italian; the code is still English). Only user-facing copy is localized (rule 2).
2. **Every frontend ships i18n from day one** — no hardcoded user-facing strings; all copy through i18n keys. Web → **[next-intl](https://next-intl.dev/)** (`stack.i18n = "next-intl"`), mobile → the RN i18n stack. Minimum locales **English + Italian** (`stack.locales = ["en","it"]`, default `en`); more per project. Set at scaffold, not deferred.
3. **UI is composed only from the chosen library's primitives** — for shadcn, the components the CLI installs into `components/ui/` (all of them, at `scaffolded`), customised only through DESIGN.md tokens and `cva` variants; domain components are compositions of them. Never hand-roll a primitive the library ships, never add a second component library, never fork a primitive's behaviour. **Before writing a component, search `components/ui/` (or the mobile equivalent) for the primitive; if it is there, use it.** A truly new primitive needs a recorded exception with its reason (ADR, or `meta.json#stack_config.primitive_exceptions`). Same rule for MUI, standalone Base UI, Coss/UI and the RN/NativeWind stack. **The primitive renders the design**: when a board or an approved screen differs from a primitive, the primitive is tuned — `cva` variants and DESIGN.md tokens, a new variant in DESIGN.md first — until it matches pixel by pixel; the drift is never accepted, the look is never rebuilt with call-site classes, and the board changes only when the user changes the design. Converting existing screens is proved with a before/after screenshot and a pixel diff. **A hand-made element is a violation with no import at all** — a raw `<button>`/`<label>`/`<a>`/`<hr>`/`<img>`, a hand-written ARIA role, a `div`/`span` whose classes redraw a Card, Badge, Alert or Separator. **A missing variant is added, not worked around** (DESIGN.md first, then the `cva`); only when no primitive can render it without a fork does the work stop for the user. Never write the element by hand or `eslint-disable` it. Enforced by the design-system lint (`design/no-handmade-ui` at `error`, plus the import bans), **the write-time guard** — Claude Code hooks (`.claude/settings.json` → `scripts/guard/primitives-guard.mjs`) that refuse a write adding hand-made UI, installed at scaffold on every web project with a Tailwind UI and recorded as `stack.primitives_guard` — `set-phase` (refuses `scaffolded` and every later phase without rule and guard), `spec-review` (Standards, check 4) and `shadscan`'s gate. A green lint or a screenshot matching the board is never proof of conformity. Mobile (NativeWind) has no guard yet — an open gap (contracts.md). Pattern → primitive: `design-md-to-app/references/primitives-first.md`.

Plus **ecosystem-first recommended defaults** (contract §Recommended default libraries) — e.g. maps → **mapcn** (web) / **mapcn-rn** (mobile). Reach for these when the capability is needed rather than hand-rolling.

## Stack-aware routing

`dev-flow` reads `meta.json#stack.framework` and routes to a stack-specific family of operative skills.

| `stack.framework` value | family | bootstrap skill | reference |
|---|---|---|---|
| `next` (default if missing) | existing web skills | `design-md-to-app` | (this file) |
| `expo-rn` | RN/Expo mobile skills | `rn-bootstrap` | `references/stack-expo-rn.md` |
| `monorepo` | turborepo (web + mobile, shared packages) | `monorepo-bootstrap` | `references/stack-monorepo.md` |
| `agent` | agent-only — eve at the repo root, no web app | `eve-agent` | contract § `framework` |

<!-- BEGIN:routing-table — generated by scripts/sync_routing_table.py from dev-flow/scripts/show_state.py; edit the dict there, not this block -->

**Every stack**

- `empty` → inventory first (references/before-you-build.md, inventory.py scan)  THEN  prd-from-idea  — optional alternative for a commercial idea whose market is not settled: founder-intelligence instead of the inventory
- `idea_captured` → prd-from-idea (expand PROJECT.md into PRD.md) — the inventory first if PROJECT.md has no 'what exists already'; optional alternative for a commercial idea: founder-intelligence

**`next` (the default when `stack.framework` is missing)**

- `prd_drafted` → prd-to-tasks  OR  figma-to-design-md / image-to-design-md / a hand-written DESIGN.md  THEN  wireframe-canvas  THEN  design-md-to-app
- `tasks_split` → linear-scrum (Setup)  THEN  figma-to-design-md / image-to-design-md  THEN  wireframe-canvas  THEN  design-md-to-app
- `design_extracted` → wireframe-canvas (every screen, desktop + phone, approved)  THEN  design-md-to-app
- `scaffolded` → primitives guard check (setup_design_lint.py --check)  THEN  screenshot-to-page  OR  module-add (project-infra-setup first if the account does not exist)
- `page_generated` → spec-review on the diff (whenever work lands, whatever the phase)  THEN  module-add  OR  more screenshot-to-page
- `module_added` → spec-review  OR  write-tests  OR  iterate — set phase feature_complete when the build is done
- `feature_complete` → gates: compliance-audit + vercel-doctor + shadscan + launch-audit  THEN  vercel-deploy
- `deployed` → maintenance loop — re-run compliance-audit + vercel-doctor + shadscan + launch-audit after material changes
- never reached on this stack: `monorepo_initialized`

**`expo-rn`**

- `prd_drafted` → prd-to-tasks  OR  image-to-design-md  THEN  wireframe-canvas  THEN  rn-bootstrap
- `tasks_split` → linear-scrum (Setup)  THEN  image-to-design-md  THEN  wireframe-canvas  THEN  rn-bootstrap
- `design_extracted` → wireframe-canvas (every screen, desktop + phone, approved)  THEN  rn-bootstrap
- `scaffolded` → rn-add-screen (UI)  OR  rn-module-add (auth/db/storage/realtime/push/payments)
- `page_generated` → spec-review on the diff  THEN  rn-module-add  OR  more rn-add-screen
- `module_added` → spec-review  OR  rn-write-tests  OR  iterate — set phase feature_complete when the build is done
- `feature_complete` → gate: compliance-audit  THEN  rn-eas-deploy
- `deployed` → maintenance loop — rn-add-screen for features, rn-eas-build-submit-update for OTA hotfixes, compliance-audit after material changes
- never reached on this stack: `monorepo_initialized`

**`monorepo`**

- `prd_drafted` → prd-to-tasks  OR  figma-to-design-md / image-to-design-md  THEN  wireframe-canvas  THEN  monorepo-bootstrap
- `tasks_split` → linear-scrum (Setup)  THEN  figma-to-design-md / image-to-design-md  THEN  wireframe-canvas  THEN  monorepo-bootstrap
- `design_extracted` → wireframe-canvas (every screen, desktop + phone, approved)  THEN  monorepo-bootstrap
- `monorepo_initialized` → monorepo-bootstrap continues (design-md-to-app in apps/web, rn-bootstrap in apps/mobile)
- `scaffolded` → web: primitives guard check THEN screenshot-to-page / module-add · mobile: rn-add-screen / rn-module-add · agent: eve-agent · shared: monorepo-add-shared-package / monorepo-sync-types
- `page_generated` → spec-review  THEN  module-add / rn-module-add  OR  more screens
- `module_added` → spec-review  OR  monorepo-sync-types  OR  iterate — set phase feature_complete when the build is done
- `feature_complete` → gates: compliance-audit (+ vercel-doctor, shadscan, launch-audit for web)  THEN  vercel-deploy + rn-eas-deploy + eve deploy, as apply
- `deployed` → maintenance loop on every side — the web gates, rn-eas-build-submit-update, compliance-audit after material changes

**`agent` (shape ③ — no web app)**

- `prd_drafted` → eve-agent (bootstrap — agent at the repo root, no web app; bumps phase to scaffolded)
- `tasks_split` → linear-scrum (Setup)  THEN  eve-agent (bootstrap)
- `scaffolded` → eve-agent (capability mode)  OR  eve-registry-porting — set phase feature_complete when the build is done
- `feature_complete` → gate: compliance-audit  THEN  eve deploy
- `deployed` → maintenance loop — more capabilities (eve-agent), compliance-audit after material changes
- never reached on this stack: `design_extracted`, `monorepo_initialized`, `page_generated`, `module_added`

<!-- END:routing-table -->

The proposal for each phase is that table — what `show_state.py` prints. The notes below are not routing:

- **monorepo, any phase from `scaffolded` on** — `scaffolded` / `page_generated` / `module_added`, when the PRD needs work the JS ecosystem does not do well (vision, OCR, classical ML, scientific computing) → **propose** `monorepo-add-python-service`. A second runtime is a stack decision: offer it, never impose it. The app it creates (`apps/<name>/`) is **owned by that skill** — never propose `design-md-to-app`, `screenshot-to-page`, `forms`, `transitions`, `shadscan` or `coss-ui` for a path listed in `stack.monorepo.services`, and do not apply golden rule 2 to it: a JSON service has no UI to localise.
- **monorepo, `feature_complete`** — A Python service in `stack.monorepo.services` is a **container**, not a Vercel target — see `monorepo-add-python-service/references/deploy-container.md`.
- **agent** — **Don't offer the web skills here and don't apologise for their absence** — `design-md-to-app`, `forms`, `data-fetching`, `state-discipline`, `transitions`, `shadscan` all correctly refuse a project with no frontend. `design_extracted`, `page_generated` and `module_added` are never reached.

If a stack value is not recognized, refuse and ask the user which stack to use. NEVER silently fall back to Next.js when `stack.framework` is set explicitly to something else.

See `references/stack-expo-rn.md` for the full RN stack configuration and `references/stack-monorepo.md` for the monorepo stack configuration.

## Workflow

### Step 0 — Look before you build (the first action on any new idea)

**Two doors (the user's decision, 2026-10-17).** For a **commercial idea whose market is not settled** — a product to
sell, external paying users, unclear competition, talk of customers or pricing — propose `founder-intelligence` in one
line: it replaces this step with research, a founder interview, competitors, business model and MVP scope in a
Playbook the founder approves, and records the same inventory verdict. For a prototype, a refactor, an internal tool or
a product already decided, this step as it is. **The direct path is the default; the user chooses**, and nothing here
requires the founder path. Once started, `show_state.py` routes by the founder's decision.

**Before the first question, before the brainstorming, before a project folder exists:** does this
already exist? Run the house search as a command, not as an intention:

```bash
python3 dev-flow/scripts/inventory.py scan <two or three words for the idea, in both languages>
```

It searches installed skills, plugins, **the other projects on this machine** and `references/resources.md`,
and prints what it searched and what it could not read. Open what it finds. A project already on disk with
the same idea is the most common hit and the one a skill search never shows.

This holds when another process skill is loaded alongside this one — `brainstorming` included. Its
checklist starts at "explore project context", which in an empty folder reads as *nothing to explore*;
that is the gap this step closes. **The inventory comes first; the brainstorming starts after the verdict.**

Then finish steps 2–4 of `references/before-you-build.md` as the idea needs, and record the verdict:

```bash
python3 dev-flow/scripts/inventory.py record <root> --verdict <have-it|adapts|halfway|build> \
    --searched <what you looked at> [--not-covered <what you could not>] --summary "<one line>"
```

`set-phase` refuses to leave `idea_captured` without it (`scripts/inventory_gate.py`), through `append-history
--phase-after` as well. Skipping is allowed and visible: `--verdict skipped --reason "…"`. An unexplained
skip is not.

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

Read `.workflow/meta.json`. The next move per phase is §Stack-aware routing's table; for a web project this is how to carry each step out, in priority order:

| Current `phase` | Next move (in priority order) |
|---|---|
| `empty` | **`references/before-you-build.md` first** (does it exist already?), then `prd-from-idea` (capture idea + draft PRD). If the user already has a Figma URL handy, can also detour via `figma-to-design-md` first — but PRD usually comes first for clarity. |
| `idea_captured` | **`references/before-you-build.md` first if `PROJECT.md` carries no *what exists already* section** — an idea captured by someone else, or imported from a brief, has never been through it; then `prd-from-idea` (expand `PROJECT.md` into a `PRD.md`). |
| `prd_drafted` | `prd-to-tasks` if user wants explicit task breakdown; OR `figma-to-design-md` if user has a Figma; OR `image-to-design-md` if user has 1+ raster images (PNG/JPG screenshots, mockups, Pinterest pins); OR, for a simple project whose DESIGN.md will be hand-written, write it, then `wireframe-canvas`, then `design-md-to-app`. |
| `tasks_split` | **Propose `linear-scrum` (Setup)** to take the project into Linear + set up scrum (default, skip only on explicit opt-out — the user may choose **GitHub Issues** instead; `project-infra-setup` creates the repo and the issues; record the opt-out in `history`); then `figma-to-design-md` or `image-to-design-md`, then `wireframe-canvas` before any scaffold. |
| `design_extracted` | **`wireframe-canvas`** — the screen inventory, then every screen as a desktop + phone artboard on a Design canvas, reviewed area by area; the user approves it. Then `design-md-to-app` (web) / `rn-bootstrap` (mobile) / `monorepo-bootstrap`. `set-phase` refuses the scaffold before the approval. |
| *code exists, phase is before `scaffolded` / `page_generated`* | **Realign first** — `show_state.py` prints **PHASE BEHIND THE CODE**: no check has been proposed for anything built so far. Run the retrofit (`design-md-to-app/scripts/setup_design_lint.py <root>`: lint rule + write-time guard + AGENTS.md section), then `update_meta.py set-phase page_generated` (or `module_added`), then `spec-review` on everything built and `shadscan`. Only then resume building. |
| `scaffolded` | **Check the primitives guard first** (`show_state.py` flags it; `setup_design_lint.py --check`): without it no write is refused and `set-phase` will not move on. Then `screenshot-to-page` if `screenshots/` has unmapped images; **`project-infra-setup` first when a module needs an account that does not exist yet** (Vercel project, Neon, Resend, Blob, DNS); then `module-add` to wire auth/db/etc. (**the inventory step first** when the capability is new — a subscription already paid for may cover it); `forms` for any form-building request; iterate. |
| `page_generated` | **Propose `spec-review`** on the diff; `module-add` or more `screenshot-to-page` runs; `forms` for forms inside generated routes; `data-fetching` if any page needs server reads. |
| `module_added` | **The inventory step first for each further capability** — the same reason as at `scaffolded`: a tool already paid for may cover it. Then **propose `spec-review`** on the branch just landed (cheapest while it is still open — does the diff match `PRD.md`/`tasks.md`, and the declared stack?); `write-tests` to add per-feature coverage (especially after `module-add db` / `module-add auth`); more `screenshot-to-page`; or iterate. When the build is done, advance to `feature_complete` (all stacks) → the pre-deploy gates, then deploy. |
| `feature_complete` | **Propose the four pre-deploy gates**: `compliance-audit` (legal — GDPR/AI-Act, any stack) + `vercel-doctor` (cost/perf — web on Vercel) + `shadscan` (UI quality + a11y — web on shadcn) + `launch-audit` (commercial readiness — web; metadata on every route, the legal and identity pages, a CTA someone can reach). They ask four different questions and none substitutes for another: an app can pass the first three and still have no way to buy and no company name on it. Then deploy: mobile (`expo-rn`) → `rn-eas-deploy`; web → `vercel-deploy`; agent → `eve deploy`. |
| `deployed` | Maintenance loop: mobile → more screens via `rn-add-screen`, OTA hotfixes via `rn-eas-build-submit-update`; re-run `compliance-audit` + `vercel-doctor` + `shadscan` + `launch-audit` after material changes; telemetry monitoring. |
| anything else | Treat as `empty` (forward-compatible). |

**Policies** — each lives in **`references/policies.md`**; read the one that applies before acting on it:

- **Inventory** — before building anything new, look for what already exists (Step 0, and each new capability).
- **Wireframes** — every screen drawn and approved before any code, on every project with a UI.
- **Infrastructure** — `project-infra-setup` before a module needs an account that does not exist yet.
- **Project management** — every project runs in Linear with agile scrum unless the user opts out.
- **Compliance** — `compliance-audit` any time, and as a pre-deploy gate.
- **Cost/perf** — `vercel-doctor`, the pre-deploy gate for web projects on Vercel.
- **Review** — `spec-review` on every change that lands, whatever the phase.
- **Parallel builds** — the brief every sub-agent gets and the checks its diff passes before it is accepted.
- **UI quality** — `shadscan`, one of the four pre-deploy gates.
- **Animated icons** — `animated-icons`, web only, horizontal, no phase bump.
- **The product's own agent-skill** — when the product exposes an API another agent could drive.
- **Resources the user hands over** — analyse, record in `references/resources.md`, then actually use them.

### Step 3 — Invoke the right skill

When the user confirms, invoke the specialist skill with explicit input:

- the project root path
- relevant `meta.json` fields (e.g., `stack` for `design-md-to-app`)
- any user-supplied input (Figma URL, screenshot path, brand brief)

The specialist skill writes its outputs into `.workflow/`, updates `phase` and appends to `history` in `meta.json`.

After the specialist returns, **read `meta.json` again**. For a skill that owns a phase move (the scaffolders, `prd-from-idea`, `prd-to-tasks`, the deploy skills), confirm the phase advanced; if it didn't, the specialist either errored, the user aborted, or a phase gate refused it — `update_meta.py` prints which — so propose the next move accordingly. **Horizontal skills never bump the phase by design** (the four gates, `spec-review`, `forms`, `data-fetching`, `state-discipline`, `transitions`, `linear-scrum`, `eve-agent` in capability mode): for them, confirm the `history` entry they append instead. An unchanged phase after one of those is success, not failure.

### Step 4 — Loop

Most projects need multiple specialists in sequence. The orchestrator's job is to keep going: after one specialist finishes, immediately re-evaluate state and propose the next step. Keep looping until the user says "stop" or `phase` reaches `deployed` — after which the `deployed` row's maintenance loop applies.

## Stack decisions

When a project leaves `prd_drafted` for scaffolding, the user chooses a stack once and it is persisted in
`meta.json#stack`. The default bundles per product profile, the **Topology policy** (single app first,
monorepo next, agent-only for the rare case) and the shadcn create parameters are in
**`references/stack-decisions.md`** — read it at that transition, or when an agent comes into scope.

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

`eve-agent` is **not** a discipline skill and **not** a phase stage. It is an **optional product component** — a scope decision, like "does this product take payments?". The user opts in, and from then on the project has an agent (an **eve** agent — Vercel's filesystem-first agent framework) that the web app consumes as its AI engine. Where it lives follows the Topology policy (`references/stack-decisions.md`): `agent/` beside `app/` in the single app (shape 1, the default), `apps/agent/` in a monorepo (shape 2), or `agent/` at the repo root when there is no web app (shape 3). It is the agent counterpart to `design-md-to-app` + `module-add`: where those build/grow the Next.js app, `eve-agent` builds/grows `apps/agent`.

There are **two moments** to opt in:

1. **At analysis time** — during the stack/scope decision (§Stack decisions), ask once: *"Does this product need an AI agent engine (eve)?"* If yes, set `meta.json#stack.agent = "eve"`. This does **not** by itself make the project a monorepo: pick the shape with the Topology policy in `references/stack-decisions.md` (default: the agent inside the single app; a monorepo only when the agent has its own deploy cadence or a second consumer).
2. **Later, on demand** — the user says "add an agent / agent backend / AI core" or names "eve". Same effect: flip `stack.agent` to `"eve"` and bring in `eve-agent`.

Once opted in, route to `eve-agent` and let it pick its mode from state: **Scaffold mode** if the agent's folder doesn't exist yet (sets up the engine once), **Capability mode** if it does (add one tool / skill / channel / connection / schedule / subagent / hook / eval, idempotently).

Why it sits **outside** the `phase` line: `phase` tracks the web app's linear build; the agent has its own cadence (an open-ended "add one capability" loop, often driven by Linear issues, not by dev-flow). So `eve-agent` records existence in `stack.agent` and appends to `history`, but never bumps `phase`. It owns the agent's folder exclusively (the orchestrator and the web/mobile skills never write there), and meets the web app through the `withEve()` proxy — plus, in a monorepo, `packages/types` (re-exported eve session/event types). eve's model calls bill through the Vercel AI Gateway, separate from the build tooling. Choosing the AI Gateway **service tier** (priority/flex/default) is `eve-agent`'s call, not dev-flow's — see `eve-agent/references/eve-scaffold.md` §3.

## External skills, merge conflicts

- **External skills — suggest, never install**: `references/external-skills.md`.
- **Merge conflicts — intent first, derived files rebuilt**: `references/merge-conflicts.md`.

## Autonomous runs — when nobody can answer

Every question in this skill and its specialists — "OK to proceed?", "which stack?", the seven PRD questions — assumes a person at the keyboard. In an **autonomous run** there is none: a background agent, a scheduled task, `claude -p`, a batch that rebuilds a project from a brief. There a blocking question is not answered; it stalls the pipeline with nothing delivered.

Detect it, don't guess it. The run is autonomous when the user said so up front (*"run it end-to-end without asking"*, *"non chiedermi niente, vai fino in fondo"*) or when the harness states it is non-interactive. **When in doubt, it is interactive — ask.**

In an autonomous run every skill follows the same four rules:

1. **Derive before defaulting.** Answer the question from the material at hand — the brief, the transcript, the PRD, `meta.json`, the repo, git history. A brief that says "book from the phone" has answered "web or mobile?". Quote the passage that decided it.
2. **Default only where the contract has one.** Locales `["en", "it"]`, the i18n library per stack, the stack bundle for the product type (§Stack decisions), `cms = null`, `agent = null`. A default the contract does not name is an invention.
3. **Write every derived or defaulted answer down as an assumption**, in the artefact it shaped — `PRD.md` §Open questions as `Assumed: <answer> — because <source | contract default>`, and in the `history` entry as `inputs.assumptions: [...]`. Never silently: the user reviews assumptions, not transcripts.
4. **Some questions are never derived.** They stop the run with one line — *"needs a human: <question>"* — and the skill finishes everything that does not depend on the answer:
   - the topology shape (`references/stack-decisions.md` §Topology policy: single app / monorepo / agent-only) — deriving it reaches an answer without asking what the second consumer is;
   - approving the wireframe canvas — the run draws every area and stops at *"needs a human: approve the wireframe canvas"*;
   - anything outward-facing or hard to undo: `vercel-deploy`, `rn-eas-deploy` and store submission, `eve deploy`, paid services, deleting data;
   - credentials and accounts (Supabase, Sanity, Stripe, Apple, Linear): the skill writes `.env.example` and the out-of-band steps, and stops before the step that needs the key.

The report of an autonomous run opens with the assumptions made — count, then the list — before anything else: that list is what the user has to check, and it is short when the brief was good.

"Propose, not impose" (Step 2) still holds: in an autonomous run the proposal is written into the report instead of asked, and the specialist is invoked without waiting.

## What dev-flow does NOT do

- **Doesn't do specialist work itself.** No PRD writing, no DESIGN.md generation, no scaffolding. If you find yourself doing actual work (other than reading state and routing), stop — call the right specialist.
- **Doesn't edit `app/`.** That's owned by `design-md-to-app` and friends.
- **Doesn't edit `apps/agent/`.** That's owned exclusively by `eve-agent`.
- **Doesn't make stack decisions silently.** Always ask the user, even if a default is obvious — or, in an autonomous run, derive or default it and write the assumption down (§Autonomous runs). Silent is the failure, not unasked.
- **Doesn't skip phases.** If the user tries to jump from `empty` straight to `design-md-to-app`, gently push back: at minimum `PROJECT.md` should exist so the design-to-app skill knows the brand voice. **And no scaffold before the wireframe canvas is approved** — not for a "quick start", not because DESIGN.md looks complete: the canvas is where missing screens are found, and the gate in `set-phase` refuses it anyway. The only way around it is a recorded skip with its reason (`wireframes.py skip`).

## Bundled scripts

The full reference — every flag, the phase gates `set-phase` holds, the drift states, and when to record
an artifact — is **`references/scripts.md`**.

- `scripts/init_workflow.py <root> [--name …]` — create `.workflow/` with a fresh `meta.json`.
- `scripts/show_state.py <root>` — current phase, files present, the proposed next step and any missing gate.
- `scripts/update_meta.py <root> record-artifact | set-phase | append-history` — the only way to change
  `meta.json`; `set-phase` and `append-history --phase-after` hold the phase gates.
- `scripts/data_residency.py <decide|add|check|render> <root>` — the residency decision and the sub-processor register.
- `scripts/inventory.py <scan|record>` — the inventory step as a command.
- `scripts/research.py <status|repos|reddit|thread|hn|post|read|papers>` — the outside half of the inventory.
- `scripts/check_drift.py <root>` — which recorded artifacts are fresh, drifted, stale upstream or missing.
