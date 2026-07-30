# Full walkthrough — a product that exercises every skill

A worked end-to-end example that touches **all 39 skills** in the family. To use them all,
the product must span **web + mobile + agent**, so this imagines a full monorepo. A real
project usually needs only a subset (e.g. web + eve, no mobile).

> **Product: "Helmsman"** — an AI support desk: a web dashboard for agents, a mobile app for
> replying on the go, and an **eve agent** that drafts replies (with a **voice** mode and
> realtime team **presence**).

Throughout, **dev-flow** is the router: it reads `.workflow/meta.json`, decides the next
move, and delegates to the specialist skills below. `phase` transitions are noted per stage.

---

## Phase 0 — idea → plan *(core)*

| Skill | Produces |
|---|---|
| `dev-flow` | creates `.workflow/meta.json`, routes everything that follows |
| `prd-from-idea` | `PROJECT.md` + `PRD.md`; sets `route_groups`, `forms=tanstack-form`, asks **"web + mobile?" → `framework=monorepo`** and **"need an agent? yes → `stack.agent=eve`"** |
| `prd-to-tasks` | `tasks.md` — the issues that feed the loop |

`phase: empty → prd_drafted`

## Phase 1 — design

| `figma-to-design-md` | from a Figma URL → `DESIGN.md` *(alternative: `image-to-design-md` from inspiration images)* |

`phase → design_extracted`

## Phase 2 — scaffold the monorepo

| Skill | Produces |
|---|---|
| `monorepo-bootstrap` | turborepo root + `apps/{web,mobile}` + `packages/*` |
| `design-md-to-app` | scaffolds `apps/web` (Next 16 + shadcn, TanStack Form) |
| `rn-bootstrap` | scaffolds `apps/mobile` (Expo + NativeWind) |
| `eve-agent` *(scaffold mode)* | `apps/agent` (eve) + `packages/types`; sets `stack.agent=eve` |

`phase → scaffolded`

## Phase 3 — build the web app

| Skill | Produces |
|---|---|
| `screenshot-to-page` | pages from screenshots (ticket list, detail, dashboard) |
| `forms` | reply form + settings (TanStack Form, `lib/forms/`) |
| `data-fetching` | server-component reads + `searchParams` filters (ticket list) |
| `state-discipline` | local UI state done right (filters, toggles) — no stray `useEffect` |
| `transitions` | one motion system: tokenized modal/toast/stagger + a View-Transitions route change; `prefers-reduced-motion` throughout |
| `module-add` | `auth` (better-auth), `db` (drizzle+neon), `payments` (stripe), `email` (resend), `ci`, `motion`, `storage`, `deploy` |
| `composition-patterns-guide` | refactor a bloated component (boolean props → compound) |
| `promote-component` | lift `TicketCard` once it's used in 3+ pages |
| `write-tests` | Vitest/Playwright for server actions and pages |

`phase → page_generated → module_added`

## Phase 4 — build the mobile app *(rn-\*)*

| Skill | Produces |
|---|---|
| `rn-add-screen` | screens (login, inbox, ticket detail) from a description/screenshot |
| `rn-styling` | NativeWind tokens from `DESIGN.md` |
| `rn-fundamentals` · `rn-expo-router` · `rn-components-apis` | knowledge skills guiding the build |
| `rn-data-fetching` | TanStack Query on mobile |
| `rn-animations-gestures` | Reanimated interactions (swipe on tickets) |
| `rn-push-notifications` | push on new tickets |
| `rn-backend` | client-side backend knowledge |
| `rn-module-add` | wire auth/db (consume `packages/api`) |
| `rn-write-tests` | screen tests |
| `rn-publishing-payments` | RevenueCat IAP |
| `rn-eas-build-submit-update` · `rn-eas-deploy` | build, submit to stores + OTA updates |

## Phase 5 — shared code *(monorepo)*

| `monorepo-add-shared-package` | extract shared logic/types into `packages/shared` |
| `monorepo-sync-types` | propagate DB types (drizzle) into `packages/shared/types` |

## Phase 6 — grow the agent *(eve-agent, capability mode)*

One capability per issue: `draft_reply` (tool), `search_kb` (tool), an MCP connection to
Stripe/Linear, an **eval** for each, an audit **hook**, a daily-digest **schedule**.

## Phase 7 — voice + realtime *(the two promoted modules)*

| `module-add voice` | voice mode **over the agent** (STT → eve → TTS) |
| `module-add realtime` | team presence/typing via Vercel WebSockets |

## Phase 8 — compliance gate (pre-deploy)

At `feature_complete`, before shipping, dev-flow proposes **`compliance-audit`**. Helmsman has
user accounts (DSAR + Apple/Play deletion), an **eve agent** (AI-transparency Art. 50, memory
residency), and US-default infra — so it flags R1/R3/R5 and auto-applies the safe fixes (DSAR
export/erasure endpoints, a cookie-consent banner, the AI disclosure in the agent + chat header,
a sub-processor register from `meta.json#stack`), leaving the EU-region and legal-basis calls as
`TODO(compliance)`. It writes `docs/compliance/audit-report.md`, records `meta.json#compliance`,
and does **not** block deploy — the user decides.

## Phase 9 — deploy

`apps/web` → Vercel · `apps/agent` → `eve deploy` · `apps/mobile` → EAS.

---

## The loop engineering layer (the harness that built all of it)

None of the above is done by hand. Each line of `tasks.md` becomes a **Linear issue** → the
runner on the **Hetzner CX23** launches **Claude Code headless** → **dev-flow** routes the
issue to the right skill (e.g. "give the agent a tool" → `eve-agent`; "generate /report
page" → `screenshot-to-page`) → **PR** → **CI gates** → merge. dev-flow is the brain of *one*
iteration; the runner **repeats** it. (See `docs/loop-engineering.md`.)

## One-sentence summary

dev-flow orchestrates the specialists phase by phase (web, mobile, agent, shared); the
**discipline** skills (`forms`/`data-fetching`/`state-discipline`/`transitions`) and **refactor** skills
(`composition-patterns-guide`/`promote-component`) act cross-cutting at any phase; `eve-agent`
+ `voice`/`realtime` add the brain and its senses; and the **loop** runs the whole thing
automatically from Linear.
