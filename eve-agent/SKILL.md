---
name: eve-agent
description: >-
  Scaffold and manage an eve agent (Vercel's filesystem-first agent framework) — inside a Next.js app,
  as `apps/agent` in a monorepo, or alone at the repo root when the product has no UI. Use whenever
  the user wants to create, set up or initialize an eve agent; add a tool, skill, channel, connection,
  schedule, subagent or hook to one; or wire a frontend to consume one. Trigger for ANY mention of
  "eve", "the agent engine", "agent tools", "agent backend", or building the agentic core of an app —
  even without the word "skill". The eve counterpart to design-md-to-app / module-add. Not for:
  building the Next.js app itself or its pages/forms (use design-md-to-app / screenshot-to-page /
  module-add), scaffolding the monorepo (use monorepo-bootstrap), or React Native (eve is
  server-side).
---

# eve-agent

Scaffold and manage an eve agent — Vercel's filesystem-first agent framework, built on the open-source Workflow SDK — as the engine of a product. This skill is part of the dev-flow family and shares the same `.workflow/` filesystem contract. Where dev-flow's `design-md-to-app` builds the Next.js app, this skill builds and grows the `apps/agent` (eve) that the app uses as its engine.

## The one rule that matters most

**Never guess the eve API.** The source of truth is the bundled docs. Once eve is installed, its full documentation lives at `node_modules/eve/docs/`, and the live docs are at <https://eve.dev/docs>. Read the relevant doc there and run `npx eve --help` (or `eve info`) BEFORE scaffolding or before adding any capability. (Vercel's own official `eve` skill — `npx skills add vercel/eve --skill eve` — consists of exactly this rule and nothing else: read `node_modules/eve/docs/README.md` first.) eve is young and its surface can change between versions; this skill encodes the workflow and conventions, not a frozen copy of the API. If anything in this skill disagrees with the installed docs, the installed docs win.

`references/eve-conventions.md` carries the cross-cutting rules that apply to every mode — the per-capability **import map**, identity-by-path, the durability/idempotency contract, the security model, fail-closed auth, and deploy/monorepo wiring. Read it before scaffolding or adding a capability.

**The second rule:** eve runs every turn as a **durable workflow**, and an interrupted step **re-runs** on resume. So any tool with a non-idempotent side effect (payment, delete, email, external write) MUST be made idempotent or **approval-gated** (`approval: always()`/`once()` from `eve/tools/approval`). eve's defaults are permissive — do not rely on model behavior to prevent sensitive or irreversible actions.

## Where the agent lives (two layouts — pick one)

The agent is the engine; the web app consumes it through eve's **official** Next.js integration — the `withEve()` wrapper mounts eve's routes same-origin and the `useEveAgent()` hook drives a session from the browser (see `references/eve-web-integration.md`). The web app never imports the agent's internals as a library, and never hand-rolls the HTTP/NDJSON plumbing that eve already provides. That boundary is the same in both layouts below.

**A — Embedded single-app (simplest; one deploy).** The eve agent and the Next.js app live in **one** project, `agent/` and `app/` as sibling folders at the root. `withEve(nextConfig)` with the default `eveRoot` mounts the agent into the same Next process — one `vercel deploy`, no cross-package types, no workspace wiring. This is the layout of Vercel's own [`roprgm/worldcup-eve`](https://github.com/roprgm/worldcup-eve) reference and of dev-flow's **Studio**. Prefer it when the agent exists only to power this one app.

```
<project-root>/
├─ .workflow/            # dev-flow metadata (if a dev-flow project)
├─ agent/                # eve agent — tools/, instructions.md, channels/, schedules/, hooks/, sandbox.ts, lib/
├─ app/                  # Next.js App Router — the product UI
├─ components/           # incl. the widget renderers the agent's output drives
├─ lib/                  # domain logic shared by BOTH agent tools and web routes
└─ next.config.ts        # withEve(nextConfig)
```

Here `packages/types` doesn't exist — the app imports eve's types directly (`eve/react`, `eve/client`), and one `lib/` is shared by tool `execute` and web code alike. Skip every monorepo/`packages/types` step below.

**B — Monorepo (Turborepo + pnpm).** Separate `apps/web` + `apps/agent`, with a shared `packages/types`. Prefer it when the agent is independently deployable, serves more than one surface, or the repo is already a monorepo.

```
<project-root>/
├─ .workflow/            # dev-flow planning/design metadata (meta.json is the source of truth)
├─ apps/
│  ├─ web/               # Next.js app — the product (built by design-md-to-app)
│  └─ agent/             # eve agent — the engine (built by THIS skill)
└─ packages/
   └─ types/             # re-exports eve's session/event types so web + agent share one contract
```

The `EVE_NEXT_PRODUCTION_ORIGIN` env var (see `references/eve-web-integration.md`) lets even layout A's agent deploy separately later without touching client code — so starting embedded is not a one-way door. The rest of this skill is written for layout B (the fuller case); when you're in layout A, read `apps/agent/` as the root `agent/`, drop the `pnpm --filter agent` prefix, and skip the `packages/types` wiring.

### Which layout? Count the consumers (ask before scaffolding)

**The deciding factor is how many clients consume the agent, not aesthetics.** `withEve()` embeds the agent in the Next runtime and gives same-origin access **only to that web app's browser**. A **React Native / mobile** client is *always* cross-origin — there is no same-origin in a native app; every call hits a remote host. So the moment a second consumer exists, embedding the agent in the web app makes that client inherit the web's deploy, uptime, and scaling (the web becomes the mobile's server), plus hand-managed CORS/auth. An agent with **≥2 consumers is a service**, and belongs in its own independently-deployable `apps/agent` (layout B), with `packages/types` single-sourcing the eve contract that both `apps/web` and `apps/mobile` import.

Decide like this — and when the signal is ambiguous, **ask the user, do not assume**:

| Signal (in this order) | Layout |
|---|---|
| `.workflow/meta.json#stack.framework == "agent"`, or the product has **no web app at all** and every surface is elsewhere (Slack, email, GitHub, Linear) | **C** — agent-only: `agent/` at the **repo root**, no `apps/*`, no `packages/types`. No need to ask. |
| `.workflow/meta.json#stack.framework == "monorepo"`, or an `apps/mobile` / `apps/*` web already exists | **B** — monorepo already serves web + mobile; add the agent as `apps/agent`. No need to ask. |
| Framework is a single `next` app AND the user confirms the agent serves **only** this app | **A** — embedded single-app |
| Single `next` app but mobile/RN, a 2nd web, or external services are planned | **B** — start monorepo now; migrating later (`EVE_NEXT_PRODUCTION_ORIGIN`) is possible but avoidable |
| No `.workflow/`, or intent unclear | **Ask:** *"Will this eve agent serve only this Next.js app, or also a mobile/React Native app (or other clients)? One consumer → embedded single-app; more than one → monorepo with the agent as its own deployable app."* |

**Layout C — agent-only.** The zero-consumer-browsers case: nothing renders, so there is no `withEve()`, no `apps/web`, no shared types package to single-source. `agent/` sits at the repo root and the repo *is* the agent — Vercel Labs' [`kody-eve-template`](https://github.com/vercel-labs/kody-eve-template) is the reference shape. Two consequences worth stating: (1) in this layout **this skill is the bootstrap skill** and bumps `phase` to `scaffolded` once the agent exists (contract § `agent`) — in A and B it never bumps phase, because the web/mobile bootstrap owns that; (2) the channels carry the whole product, so `agent/channels/` is where the design effort goes, not a UI. Don't scaffold a Next.js app to have somewhere to put a chat box: if the users already talk to you in email or Slack, that *is* the interface.

A mobile client consumes the agent over plain HTTP — `useEveAgent({ host, auth })` pointed at the agent's origin, or the `eve/client` typed client — never through `withEve()` (that wrapper is Next-only). Same durable HTTP contract, different transport; see `references/eve-web-integration.md`. `[VERIFY]` RN client specifics against the installed eve version — `eve/react` is verified, but eve ships no React Native guide, so the RN side is ours to prove.

## The eve project layout (verify against the docs)

A scaffolded eve app (`apps/agent`) looks like this — confirm against `node_modules/eve/docs/`:

```
apps/agent/
├─ agent/
│  ├─ agent.ts            # model & runtime config (root-only)
│  ├─ instructions.md     # system prompt (required for the root agent)
│  ├─ instrumentation.ts  # OpenTelemetry config (root-only, optional)
│  ├─ tools/              # one file per tool, auto-registered by filename
│  ├─ skills/             # on-demand procedures (.md)
│  ├─ channels/           # entrypoints; the default HTTP channel is channels/eve.ts
│  ├─ connections/        # auth for external services
│  ├─ schedules/          # cron-style triggers
│  ├─ subagents/          # specialist child agents
│  ├─ hooks/              # lifecycle subscribers
│  ├─ sandbox/            # sandbox config
│  └─ lib/                # shared helper code
├─ evals/                 # eval cases — SIBLING of agent/, NOT inside it
└─ .eve/                  # build artifacts (generated by `eve build`)
```

## Read state first, then pick a mode

1. If `.workflow/meta.json` exists, read it. Check `stack.agent`. (If there is no `.workflow/`, this is not a dev-flow project — still proceed, just skip the meta.json updates and tell the user.)
2. Run `python scripts/check_eve_state.py <project-root>` to detect whether the agent is already scaffolded and what capabilities exist.
3. Choose the mode:
   * `stack.agent` unset / no `apps/agent` → **Scaffold mode** (set the agent up once).
   * agent already present → **Capability mode** (add a tool / skill / channel / connection / schedule / subagent / hook / eval, idempotently).
4. **In Scaffold mode, resolve the layout first** using the *Which layout?* table above — check `stack.framework` / existing `apps/*`, and **ask the user about other consumers (mobile/RN, a 2nd web, external services) when it's ambiguous** before creating any files. The layout (embedded A vs monorepo B) changes where the agent goes and whether `packages/types` is wired, so it must be settled before scaffolding, not after.

**Do exactly one logical operation per invocation, then stop.** Like `module-add`, this skill is idempotent: re-running an add that already exists detects it and skips.

## Scaffold mode

Goal: a running eve agent at `apps/agent`, wired into the monorepo, exposing its HTTP API, with a baseline eval, and a shared types package the web app re-exports.

Follow `references/eve-scaffold.md` for the full procedure. In short:

1. Read `node_modules/eve/docs/` (install eve first if needed) and run `eve info` / `npx eve --help` to confirm the current init flow and folder layout.
2. Initialize the agent inside `apps/agent` (`npx eve@latest init apps/agent`, or `eve init .` from within it). Keep the default HTTP channel (`agent/channels/eve.ts`) — that is what the web app consumes. The Next.js app provides the UI via `useEveAgent()`, so you do not need eve's own starter chat UI.
3. Pin the model in `agent/agent.ts` — our default choice is `anthropic/claude-sonnet-5` via the Vercel AI Gateway; that is **not** eve's own scaffold default (`zai/glm-5.2` since 0.36.0, still so at 0.45.0) — and write a real `agent/instructions.md`. The model can also be `defineDynamic({ events })` (no `fallback` since 0.33.0 — every handler must return a concrete model). Document the model choice in a comment. For an OpenAI/Gemini model you can also opt into an AI Gateway **service tier** (`priority`/`flex`/`default`) to tune latency vs. cost — see `references/eve-scaffold.md` §3.
4. Set the channel auth in `agent/channels/eve.ts`: `localDev()` for development, a real authenticator (`vercelOidc()` / `jwtHmac()` / `httpBasic()`) for production. eve **fails closed** in prod — browser traffic is rejected unless an authenticator accepts it.
5. Add at least one baseline eval in `evals/` (sibling of `agent/`) so `eve eval` has a gate to enforce in CI.
6. Wire `apps/agent` into the pnpm workspace and `turbo.json` pipelines (`dev`, `build`, `lint`, `typecheck`, plus an `eval` task that runs `eve eval`).
7. Create / update `packages/types` so it **re-exports eve's** session request + stream-event types — do not hand-roll a parallel contract (see `references/eve-web-integration.md`). If `packages/types` doesn't exist yet, don't assume it — create it first via **`monorepo-add-shared-package`**, then populate it.
8. Verify: `eve info` resolves the app, `pnpm --filter agent lint typecheck build` and `eve eval` exit 0, and a real HTTP round-trip returns a non-empty response. Document the exact commands you used.
9. Update `.workflow/meta.json`: set `stack.agent = "eve"` and append a `history` entry (`{ "skill": "eve-agent", "action": "scaffold", "ran_at": "<ISO8601>" }`).

## Capability mode

Goal: add ONE capability to an existing agent, following eve's filesystem conventions. Follow `references/eve-capabilities.md`. The capability types:

* **Tool** → a single file in `agent/tools/<name>.ts` using `defineTool` from `eve/tools`. The filename becomes the tool name; eve auto-registers it. No manual registration, no orchestration graph. This is the eve analogue of "add a feature" — exactly what an autonomous loop is good at.
* **Skill** → an on-demand procedure in `agent/skills/<name>.md`.
* **Channel** → a new entrypoint via `eve add channel/<kind>` under `agent/channels/` (⚠️ `eve channels add` was **removed in eve 0.29.0**; only `eve channels list` remains).
* **Schedule** → a cron-style trigger under `agent/schedules/<name>` (root-only; `defineSchedule` from `eve/schedules`).
* **Connection** → MCP or OpenAPI access under `agent/connections/<service>` (`defineMcpClientConnection` / `defineOpenAPIConnection` from `eve/connections`).
* **Subagent** → a local child agent dir `agent/subagents/<name>/agent.ts` (mirrors `agent/`; no channels/schedules), or a remote one via `defineRemoteAgent` from `eve`. There is no `defineSubagent`.
* **Hook** → a lifecycle subscriber under `agent/hooks/<name>` (`defineHook` from `eve/hooks`).
* **Extension** → install a capability *package* (tools/connections/skills/instructions/hooks bundled, versioned like a dependency) by adding `agent/extensions/<name>.ts` (`import x from "@pkg"; export default x({ …config })`), or author one with `npx eve extension init`. The filename namespaces its tools (`x__toolname`); tune with `disableTool()` / `toolResultFrom`. New in eve (2026-07); the package route complements `eve-registry-porting` (which vendors source instead). See `references/eve-capabilities.md`.
* **Eval** → a new case in `evals/` so the quality gate covers the new capability.

For each: read the matching section of `node_modules/eve/docs/` first, add the single file following the existing house style in `apps/agent`, add/extend an eval that exercises it, run the verification gate, then update `meta.json` history (`{ "skill": "eve-agent", "action": "add-<type>", "inputs": { "name": "<name>" } }`).

**Ecosystem-first — don't reinvent.** Before authoring a channel, connection, or extension by hand, search the registry from the CLI: **`eve registry search <capability>`** → **`eve add <kind>/<name>`** (`eve add channel/slack`, `eve add connection/linear`, `eve add extension/agent-browser`, `eve add instrumentation/braintrust`; `--skip-install`/`--overwrite`; third-party sources via `eve registry add @acme=<url>` in shadcn-registry format). The full catalog is the **integrations directory** (<https://eve.dev/integrations>): 11+ prebuilt channels, **50+ MCP/OpenAPI connections** (Stripe, Supabase, Notion, Linear, Sentry, PostHog, Vercel, PlanetScale, Airtable, Zapier…), and official **extensions** (GitHub Tools, Browserbase, Browser Use, KERNEL, Jetty). Adopt an official/prebuilt one over hand-rolling; after install, review the generated files + add config before running — see `references/eve-capabilities.md` (§Install from the registry FIRST; Connection / Channel / Extension).

**Multi-tenant SaaS agent?** Before adding any tool, schedule, connection, or memory that touches tenant data, read `references/eve-patterns.md`. Tenant auth, per-tenant approvals, tenant-scoped long-term memory, and dynamic scheduling are **composed recipes** with one non-negotiable rule — derive tenant/user from `ctx.session.auth`, never from model input — not ad-hoc code. This is the same tenant-safety backbone `eve-registry-porting` enforces when porting.

## Definition of Done (every mode)

A run is complete only when these pass with exit code 0:

```bash
pnpm --filter agent lint typecheck build
pnpm --filter agent eval      # runs `eve eval`
```

…plus, for scaffold/web-integration work, a real HTTP round-trip to the agent returns a non-empty response (e.g. `eve dev --no-ui`, then `POST /eve/v1/session` and read `GET /eve/v1/session/:sessionId/stream`). If you cannot verify with a command, the task is under-specified — stop and say so rather than guessing.

## How this composes with the loop and with dev-flow

* dev-flow owns the web app, this skill owns the agent. They meet at `packages/types` (re-exported eve types) and at the `withEve()` proxy in `apps/web`.
* In an autonomous Claude Code loop (Linear → Claude Code → PR), a Linear issue like "give the agent a tool to do X" maps cleanly to "create `agent/tools/x.ts`" — let the loop invoke this skill in Capability mode. Linear stays the orchestrator; do not let dev-flow's `meta.json` phase machine drive the loop.
* Deployment is Vercel-native: `eve link` pulls AI Gateway credentials, `eve deploy` ships the agent to Vercel. The agent's model calls bill through the **Vercel AI Gateway**, separate from any Claude Code subscription used to build it.

## Reference files

* `references/eve-conventions.md` — cross-cutting rules: import map, identity-by-path, durability/idempotency, security model, fail-closed auth, sandbox-backend choice (just-bash vs VM), deploy/monorepo wiring, built-in tools.
* `references/eve-scaffold.md` — full scaffold procedure + monorepo wiring + per-session token limits.
* `references/eve-capabilities.md` — adding tools / skills / channels / connections / schedules / subagents / hooks (incl. the external observability-sink hook pattern).
* `references/eve-channels.md` — per-surface channel guides: **Telegram** (webhook registration, group dispatch rules, the `onMessage` gate, session vs raw send), **Discord** (3-second ACK, command propagation), **Teams** (the `onInputResponse` authorization bypass), **WhatsApp** via Chat SDK, and how to tell when an adapter's threading model doesn't fit your domain.
* `references/eve-web-integration.md` — the official `withEve()` + `useEveAgent()` integration, the shared types package, the **widget protocol** (rich UI from agent output), the `prepareSend`→`clientContext`→`defineDynamic` bridge, and resumable chats from a persisted event log.
* `references/eve-patterns.md` — the composed **multi-tenant & dynamic recipes**: tenant auth (`AuthFn` stamps `tenantId` on the principal), per-tenant **approvals** (policy gate ≠ authorization), tenant-scoped **long-term memory** (auth + `defineDynamic` on `turn.started` + tools + external store), **dynamic scheduling** (dispatcher + CRUD tools + atomic-lease store, at-least-once), the **multi-agent team** (a lead that routes, specialists that don't overlap), the **autonomous pipeline** (declared stations, and what a run with nobody watching may do), and the **cross-channel notification** (`to()` starts a turn — a notification wants the platform API plus an app-owned outbox). The through-line: **identity from `ctx.session.auth`, never the model.** Read it for any multi-tenant SaaS agent — and read §8 the moment anything triggers the agent without a human in the room, because that is when "park for approval" silently becomes "hang forever".
* `references/eve-evals.md` — the **full evals API**: cases + driver (`t.send`/`start`/`reply`/`events`), the complete assertion set + matchers (`eve/evals/expect`), the LLM judge (`t.judge.autoevals`, model resolution, `.gate`/`.soft`/`.atLeast`), targets (`t.target.fetch`/`dispatchSchedule`/`attachSession`, remote auth), reporters (Console/JUnit/Braintrust), and every `eve eval` flag + exit code + the CI gate.
* `references/eve-concepts.md` — the cross-cutting **concepts**: `agent.ts` config (model/reasoning/**compaction**/limits/`experimental.workflow.world`), instructions (static vs dynamic), context control, the default harness (built-in tools + override/disable), the sandbox (backends/seeding/network-policy/credential-brokering), the execution model & durability (session→turn→step, at-least-once), sessions/runs/streaming (the NDJSON event types + endpoints), human-in-the-loop, `defineState`, **dynamic capabilities** (`defineDynamic` for model/tools/skills/instructions), **dynamic workflows** (`experimental_workflow`), and the deployer's responsible-use obligations.
* `references/eve-docs-coverage.md` — a **map of every eve docs page → where this skill covers it** (keep it in sync when eve adds pages; the intentionally out-of-scope pages are the non-Next frontends and the raw TS-API/tutorials).

## Bundled scripts

* `scripts/check_eve_state.py <project-root>` — reports whether the agent is scaffolded, lists existing tools/skills/channels/connections/schedules/subagents/hooks/evals, reads `meta.json#stack.agent`, and proposes the next step. Run it first.
