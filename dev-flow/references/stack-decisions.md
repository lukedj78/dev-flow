# Stack decisions

Read when a project leaves `prd_drafted` for scaffolding, or when an agent comes into scope.
Moved out of `dev-flow/SKILL.md` on 2026-10-17 to cut the router's every-turn cost; SKILL.md keeps an
index line pointing here. The text is unchanged.

When transitioning out of `prd_drafted` and into scaffolding, the user has to choose a stack. The orchestrator should ask once and persist in `meta.json#stack`. Sensible default-bundle suggestions:

| Profile | framework | ui | auth | db | payments | deploy |
|---|---|---|---|---|---|---|
| **SaaS B2B** (web, distinctive brand) | next | shadcn | better-auth | neon-drizzle | stripe | vercel |
| **SaaS B2B** (web, low-maintenance UI) | next | base-ui | better-auth | neon-drizzle | stripe | vercel |
| **B2C consumer** (web) | next | shadcn | clerk | supabase | stripe | vercel |
| **Marketing site** | next | shadcn | null | null | null | vercel |
| **Internal tool / enterprise** (web) | next | mui | better-auth | neon-drizzle | null | null |
| **Editorial / distinctive brand** (web) | next | shadcn | better-auth | neon-drizzle | null | vercel |
| **Headless + a11y-first** (web) | next | base-ui | better-auth | neon-drizzle | null | vercel |
| **Mobile app (iOS+Android)** | expo-rn | nativewind | supabase | supabase | revenuecat | eas |
| **Mobile app, custom backend** | expo-rn | nativewind | custom-rest | custom-rest | revenuecat | eas |
| **Monorepo (web + mobile)** *(planned)* | monorepo | `{web: <shadcn\|base-ui\|mui>, mobile: nativewind}` | supabase | supabase | revenuecat + stripe | eas + vercel |

Ask the user the project type, propose the bundle, let them override individual choices. Don't ask 6 separate questions when one ("what kind of app?") plus a confirmation gets you there.

**Optional agent engine.** As part of the same decision, ask once whether the product needs an **AI agent engine** (an agentic core: tools the model calls, an agent backend, an assistant surface). Default `stack.agent = null`. If yes → set `stack.agent = "eve"`. The user can also opt in later on demand — see "Agent engine (eve)" below. This is a scope decision, not a pipeline phase.

**Optional content layer (CMS).** In the same breath, ask once whether the product has **content a non-developer edits and the app only reads** — a catalogue, pages, articles, FAQs, pricing copy. If yes → `stack.cms = "sanity"` (contract §Recommended default libraries), wired later by `module-add cms` (web) or `rn-module-add cms` (mobile): the hosted **Sanity Studio is the admin panel**, so the project builds **no admin CRUD screens and no admin roles in the transactional database** for that content. User-owned data (accounts, orders, bookings) is never CMS content — it stays in `db` behind RLS. Default `null`; the user can opt in later on demand ("add a CMS", "aggiungi un CMS").

**Where the data lives — asked in the same decision, never deferred.** Once the bundle is agreed, ask the four questions in `references/eu-data-sovereignty.md` §The four questions: (a) does the product process data of people in the EU? (b) which sensitive categories — identity documents, tax, health, biometrics, minors, financial? (c) do customers or sectors impose residency (public administration, healthcare, finance)? (d) must exposure to the US CLOUD Act be avoided? Record them with `scripts/data_residency.py decide` — it writes `stack.data_residency` (`"eu"` | `"eu-sovereign"` | `"none"`), `compliance.data_categories` and the answers. Then, when residency is not `"none"`, walk the bundle through the reference's service table and **propose, for each service, its EU region and the European alternative** — the user picks; the defaults stay available. `set-phase scaffolded` refuses an undecided residency; it never refuses a provider. A service with no EU option is **flagged in the sub-processor register with its transfer basis, and the work goes on**.

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
| Icon library | `icon_library` | **ASK** | lucide (default) \| radix-icons \| tabler \| hugeicons \| phosphor — and note the shadcn **style** sets it: `maia`/`mira` → hugeicons, `lyra` → phosphor |
| RTL | `rtl` | **ASK only if i18n/RTL relevant** | `false` (default) |
| Template / framework | (uses `stack.framework`) | already chosen | `next` — the only web framework dev-flow's skills accept (shadcn also offers vite, start, react-router, laravel and astro templates; a project on one of those is outside dev-flow's web family) |
| Base color | `base_color` | **don't ask** — DESIGN.md owns it | scaffold default `neutral`; DESIGN.md tokens are the real palette |
| Starting theme | `ui_theme` | **don't ask** — DESIGN.md owns it | default `null`; DESIGN.md tokens override |
| CSS variables | `css_variables` | **don't ask** | stays `true` (required for token theming) |
| Monorepo | (uses `stack.framework="monorepo"`) | already chosen | — |

So in practice you ask **two** things (plus RTL only when relevant): *"shadcn su Base UI (default), Radix o React Aria?"* (`ui_base`) and *"icone: lucide o altro?"* (`icon_library`). Don't prompt for base color / theme — those come from the DESIGN.md tokens; setting `css_variables=true` silently. Record the answers in `meta.json#stack`; `base_color` defaults to `neutral` and `ui_theme` to `null` for the initial scaffold.

Just before scaffolding, `design-md-to-app` prints a **recap of the full resolved shadcn create config and asks for confirmation** (its Step 4 confirmation gate) — including the values derived from DESIGN.md — so nothing is scaffolded on assumed config.

> `ui = "base-ui"` (standalone Base UI, no shadcn CLI) is a **different** choice from `ui = "shadcn"` + `ui_base = "base"`. The latter keeps shadcn's component set + blocks on Base UI primitives and is usually preferable; pick standalone Base UI only when the user explicitly wants no shadcn CLI. See `design-md-to-app/references/library-choice.md`.

**`ui = "coss"` (Coss/UI — the Cal.com design system).** A fourth UI choice inside the shadcn/Base-UI family: Coss/UI is installed through the shadcn CLI's `@coss/*` registry, is built on Base UI, and ships CSS-variable tokens **with the same names as shadcn/ui**, so the DESIGN.md → tokens pipeline works unchanged. When the user picks Coss (`stack.ui = "coss"`, implies `ui_base = "base"`), route to the **`coss-ui`** skill, which owns the Coss-specific install/add and token reconciliation; `design-md-to-app` still owns the generic scaffold. It is a deliberate choice with two caveats — **Tailwind CSS v4 required** and a **mixed MIT/AGPLv3 license** — so don't default to it; offer it when the user wants the Cal.com aesthetic/DX or an AI-first Base-UI kit. See `coss-ui/SKILL.md`.

For mobile profiles (`framework: "expo-rn"`), see `references/stack-expo-rn.md` for the canonical wiring; the actual modules are wired by `rn-module-add` after `rn-bootstrap` scaffolds.

