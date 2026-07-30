# Ecosystem changelog watch — Vercel · shadcn/ui

Two fast-moving upstreams underpin dev-flow: **Vercel/eve** (eve is in beta, ships to the
changelog frequently) and **shadcn/ui** (the web UI layer, also releasing constantly). This
file tracks changelog items from both that affect our skills, so the skills stay current. It
is a living watchlist — periodically fetch each changelog, add new relevant rows below, and
apply the change to the affected skill.

## Vercel / eve

## Skills that track Vercel (check these when a relevant item ships)

| Skill | Vercel surface it depends on |
|---|---|
| `eve-agent` | eve framework + CLI, Vercel AI Gateway (models, service tiers), `eve deploy` |
| `module-add` (voice / realtime / deploy) | AI Gateway audio + realtime, `stack.deploy = "vercel"` |
| `design-md-to-app` | `stack.deploy = "vercel"` |
| `monorepo-bootstrap` | Vercel deploy for `apps/web` |
| `setup-deploy` | Vercel project setup |

## How to run a watch pass

1. Fetch <https://vercel.com/changelog> — read the newest entries since the last dated pass below.
2. For each entry, classify: **relevant** (touches a skill above) vs **not relevant** (a model id, an unrelated product).
3. For relevant items, edit the affected skill (mark new/unstable API `[VERIFY]` against the installed docs — eve is beta), and add a row to the log below with status `applied`.
4. Update the "Last pass" date. For anything ambiguous or out of scope, ask the user.

**Last pass: 2026-07-30** (entries through 2026-07-30). Previous: 2026-07-23 (through 2026-07-22).

## Log

| Date | Changelog item | Relevant to | Status |
|---|---|---|---|
| 2026-07-30 | **Run multiple isolated agents in a single Sandbox** — `@vercel/sandbox` SDK gains multiple Linux users/groups | `eve-agent` (watch) | ⏭️ **watch, not applied** — a platform primitive *beneath* eve's documented "exactly one sandbox per agent" model; **no eve-facing API**. Don't imply a capability eve doesn't expose. Revisit if eve ships per-tenant sandbox multiplexing (would matter to multi-tenant eve apps like EVE Hospitality). |
| 2026-07-30 | **Turborepo + Vercel Remote Cache support OIDC** — OIDC policies for CI/CD to reach Remote Cache | `monorepo-bootstrap` (watch) | ⏭️ **not applied** — our scaffolder doesn't set up Remote Cache; OIDC is an auth detail on a feature we don't wire. Out of scope for a bootstrap. Optional future: a "enable Remote Cache" post-bootstrap note. |
| 2026-07-30 | **mcp-handler 2.0** — latest (stateless) MCP spec, no Redis required | — (watch) | ⏭️ **not applied** — builds MCP *servers*; no skill scaffolds one. eve *consumes* MCP via `connections` (opposite direction). Revisit only if we add an "expose app/agent as MCP" skill. |
| 2026-07-30 | **Inkling Small** (Thinking Machines) · **GPT-5.6 pricing/speed** on AI Gateway | — | ⏭️ **not relevant** — model ids + pricing/latency; our skills don't pin model ids (default documented, choice is per-project). Same rule as the earlier Gemini/Laguna entries. |
| 2026-07-30 | **Deployments up to 7s faster** · **Server-Timing passthrough** · **Enterprise Flex Commit** (Marketplace) · **Latest MCP in Vercel MCP** | — | ⏭️ **not relevant** — infra perf / observability header / billing-procurement; no API or behavior our skills document. |
| 2026-07-22 | **eve extensions** — installable packages bundling tools/connections/skills/instructions/hooks (`npx eve extension init`, `agent/extensions/<name>.ts`, `eve extension build`, `defineExtension`, `disableTool`, `toolResultFrom`) | `eve-agent` | ✅ applied — new **Extension** capability in `eve-capabilities.md` + SKILL.md + CLI ref |
| 2026-07-22 | **AI Gateway streaming transcription** — AI SDK `streamTranscribe` for incremental transcripts | `module-add` voice/realtime | ✅ applied — note in `module-voice.md` STT step |
| 2026-07-21 | **AI Gateway service tiers** — `providerOptions.gateway.serviceTier` (`default`/`priority`/`flex`), OpenAI+Gemini only | `eve-agent`, `module-add` voice | ✅ applied earlier (`eve-scaffold.md §3`, `module-voice.md` caveat) |
| 2026-07-21 | Gemini 3.6 Flash / 3.5 Flash-Lite, Laguna S 2.1 on AI Gateway | — | ⏭️ not relevant — our skills don't pin model ids (default `anthropic/claude-sonnet-5` is documented, model choice is per-project) |
| 2026-07-21 | Vercel Connect: 90+ preset connectors | — (watch) | ⏭️ not applied — possible future tie-in with eve `connections`; revisit if it exposes an eve-facing API |
| 2026-07-21 | Vercel MCP supports purchases; Python bytecode bundles | — | ⏭️ not relevant to our skills |

> Convention: `[VERIFY]` any eve/AI-SDK identifier added from a changelog against `node_modules/eve/docs/` or the installed `@ai-sdk/*` before relying on it — beta surfaces move between the changelog announcement and the shipped API.

---

## shadcn/ui (<https://ui.shadcn.com/docs/changelog>)

**Skills that track shadcn:** `design-md-to-app` (+ `references/shadcn-mapping.md`, `library-choice.md`, `base-ui-mapping.md`, `chat-and-typeset.md`), `coss-ui` (rides the shadcn CLI + `@coss/*` registry), `screenshot-to-page`, `module-add`, `forms`, `dev-flow` (shadcn create params + `stack.ui_base`), the `.workflow` contract (`ui_base` enum/default).

**Last pass: 2026-07-23.**

| Date | Changelog item | Relevant to | Status |
|---|---|---|---|
| 2026-07 | **Base UI is now the default** for new shadcn projects (`npx shadcn init` → Base UI; Radix still supported, not deprecated) | contract, `dev-flow`, `design-md-to-app`, `library-choice.md` | ✅ applied — flipped `stack.ui_base` default `radix` → `base` everywhere |
| 2026-07 | **React Aria first-class base** (`--base aria`) | same | ✅ applied — added `aria` to the `ui_base` enum + guidance |
| 2026-07 | **Toast** — first-party Toast for Base UI (actions, status types, promises, stacking, swipe-dismiss) | `design-md-to-app`, `base-ui-mapping.md` | ✅ applied — primitive table now points to the native Toast (`sonner` still noted for Radix) |
| 2026-07 | **shadcn/typeset** — CSS typography system for rendered markdown | `chat-and-typeset.md` | ✅ already covered (§2) |
| 2026-07 | **`@shadcn/helpers`** — AI SDK + TanStack AI helpers for `useChat` prototyping without a backend | `chat-and-typeset.md` | ✅ applied — note added |
| 2026-06 | Chat interface components · GitHub registries | `chat-and-typeset.md`, namespaced registries | ✅ chat covered; `@coss/*` uses the namespaced-registry mechanism |
| 2026-03→05 | `shadcn preset` / `apply` / `eject`, registry include+validate, CLI v4 | `dev-flow` / `design-md-to-app` | ✅ CLI v4 + preset (`stack.shadcn_preset`) covered; `eject`/`apply` not needed by our flow |

> Convention: `[VERIFY]` any shadcn CLI flag / component / package added from the changelog against the installed shadcn version and <https://ui.shadcn.com/docs> before relying on it — the CLI surface moves fast.
