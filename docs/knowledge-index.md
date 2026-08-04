# Knowledge index — the doc-grounded how-tos

The skills are a **second brain**: when a skill says *"use library X"*, there must be a reference that says **how**, grounded in X's official documentation. A bare name-drop is an incomplete skill (contract §Knowledge principle — rule zero).

This index is the map of those how-tos: what we're expert in, where the knowledge lives, and which upstream to re-verify when it moves. **Use it two ways**: before wiring a library, read its how-to instead of improvising; when running a periodic knowledge refresh, walk this table and re-check each upstream.

> 🧠 Browsing this as a graph? The repo is also an Obsidian vault — see **[OBSIDIAN.md](OBSIDIAN.md)**. Pin this note as your home.

## Frontend foundations

| Domain | How-to | Upstream (source of truth) | Used by |
|---|---|---|---|
| **i18n — web** | `design-md-to-app/references/i18n-next-intl.md` | <https://next-intl.dev/docs> | golden rule 2; `design-md-to-app`, `forms` |
| **i18n — mobile** | `rn-bootstrap/references/i18n-rn.md` | <https://docs.expo.dev/guides/localization/>, <https://react.i18next.com> | golden rule 2; `rn-bootstrap`, `rn-add-screen` |
| **URL state** | `data-fetching/references/nuqs.md` | <https://nuqs.dev/docs> | `data-fetching` rung 2, `state-discipline` rung 2 |
| **Motion (Tier 0)** | `transitions/references/tw-animate-css.md` | <https://github.com/Wombosvideo/tw-animate-css> | `transitions`, shadcn scaffolds |
| **Motion (runtime)** | `module-add/references/module-motion.md` | <https://motion.dev/docs/react> | `transitions` Tier 3, `heroicons-animated` |
| **Illustrations** | `design-md-to-app/references/illustrations.md` | <https://koboyo.com/icons> + its [licence](https://koboyo.com/icons/license) | `design-md-to-app` (⚠️ use sparingly — DESIGN.md decides; licence forbids art-as-the-product) |
| **Maps — web** | `design-md-to-app/references/maps-mapcn.md` | <https://mapcn.dev/docs> | `design-md-to-app` (⚠️ CARTO tiles: commercial licence) |
| **Maps — mobile** | `rn-components-apis/references/maps-mapcn-rn.md` | <https://mapcn-rn.dev/docs> | `rn-add-screen` (⚠️ needs a dev build) |

## Backend & infrastructure modules (`module-add`)

| Module | How-to | Upstream | Default |
|---|---|---|---|
| `auth` | `module-add/references/module-auth.md` | <https://better-auth.com/docs> | better-auth |
| `db` | `module-add/references/module-db.md` | <https://orm.drizzle.team>, <https://neon.tech/docs> | drizzle + neon |
| `payments` | `module-add/references/module-payments.md` | <https://docs.stripe.com> | Stripe |
| `email` | `module-add/references/module-email.md` | <https://resend.com/docs>, <https://react.email> | Resend + React Email |
| `storage` | `module-add/references/module-storage.md` | <https://vercel.com/docs/vercel-blob> | **Vercel Blob** (UploadThing / S3 optional) |
| `deploy` | `module-add/references/module-deploy.md` | <https://vercel.com/docs> | Vercel project config |
| `realtime` | `module-add/references/module-realtime.md` | provider docs | per stack |
| `voice` | `module-add/references/module-voice.md` | AI Gateway / STT-TTS docs | per stack |
| `ci` · `test` | `module-add/references/module-ci.md` · `module-test.md` | GitHub Actions · Vitest/Playwright | — |

## Mobile stack

| Domain | How-to | Upstream |
|---|---|---|
| **Server state** | `rn-data-fetching/references/tanstack-query-rn.md` | <https://tanstack.com/query/latest> |
| **Client state** | `rn-fundamentals/references/zustand-rn.md` | <https://zustand.docs.pmnd.rs> |
| **E2E tests** | `rn-write-tests/references/maestro.md` | <https://docs.maestro.dev> |
| **Versions** | `rn-fundamentals/references/stack-defaults.md` | npm registry (snapshot-dated) |

## Agent engine (eve)

`eve-agent/references/` is a complete mirror of the eve docs surface — `eve-docs-coverage.md` maps **every** page of <https://eve.dev/docs> to the reference that covers it. Highlights: `eve-scaffold.md` (init/deploy), `eve-capabilities.md` (tools/skills/channels/connections/extensions + the `eve add` registry CLI), `eve-concepts.md` (sandbox, durability, HITL), `eve-patterns.md` (multi-tenant, audit hook, read-vs-egress), `eve-evals.md`, `eve-web-integration.md` (+ `ai-elements.md` as the opt-in UI kit).

## UI system

`design-md-to-app/references/` — `shadcn-mapping.md`, `base-ui-mapping.md`, `mui-mapping.md`, `library-choice.md`, `chat-and-typeset.md`, `anti-slop-fallbacks.md`; plus `coss-ui/references/` for the Coss/UI registry.

## Pre-deploy gates (third-party CLIs)

Three gates run at `feature_complete` — legal, cost, UI. Two of them wrap an **external CLI whose flags and
report schema move independently of us**, so they belong in this index: a gate documented against a stale
surface fails silently.

| Gate | How-to | Upstream (source of truth) | Pinned surface to re-verify |
|---|---|---|---|
| **Legal** — GDPR / EU AI Act | `compliance-audit/SKILL.md` + `references/` | EU regulation texts (see the skill) | the 10-point risk register |
| **Cost/perf** — Vercel | `vercel-doctor/SKILL.md` | <https://www.vercel-doctor.com/> · [repo](https://github.com/Aniket-508/vercel-doctor) | CLI flags (`--help`), the **required path argument**, `--offline` vs score |
| **UI quality + a11y** | `shadscan/SKILL.md` | <https://www.shadscan.com/> · [repo](https://github.com/TheOrcDev/shadscan) | CLI flags (`--help`), report `schemaVersion` + `rulesetVersion`, the `agentHandoff` shape |

⚠️ shadscan's report is **versioned** (`schemaVersion`, `rulesetVersion`, `engineVersion`): scores only compare
within the same ruleset, and the `agentHandoff.actionables` shape this skill parses can change with the schema.
Re-read the JSON before trusting a diff across versions. shadscan also **ships its own agent skills**
(`.agents/skills/migrate-radix-to-base/` — Radix → **Base UI**, our default `ui_base`): ecosystem-first, read
theirs rather than writing our own migration notes.

## Keeping it current (rule zero #4)

Stale grounding is a bug. Two mechanisms:

1. **`docs/vercel-changelog-watch.md`** — the dated watch log for the Vercel/eve and shadcn ecosystems (fetch changelog → classify → apply → log the pass).
2. **Periodic sweep of this index** — walk the upstreams above, verify the pinned APIs/commands still hold, fix what drifted, and note the pass. Past sweeps have caught real breakage: a wrong CLI invocation, a removed utility class, a deprecated option, an API removed two majors ago.

When you add a new "use library X" default anywhere in the skills, **add its row here** — that's what keeps the index the true map of what we know.
