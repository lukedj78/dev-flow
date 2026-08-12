# eve-capabilities — adding one capability at a time

Add exactly ONE capability per invocation, idempotently. Read the matching section of
`node_modules/eve/docs/` (live: <https://eve.dev/docs>) first, and see
`eve-conventions.md` for the import map, identity-by-path, durability/idempotency, and
security rules that apply to all of these.

## Install from the registry FIRST — `eve add` / `eve registry` ([VERIFY])

Before hand-authoring any capability below, check whether the ecosystem already ships it — the
same ecosystem-first rule as everywhere in dev-flow, now with a **first-class CLI** (source: eve.dev/docs/install-integrations). An **integration** is the umbrella term: it writes files
straight into your project and can add *anything an agent uses* — a single tool, a channel, a
connection, or a whole extension (an extension is one *kind* of integration).

```bash
# Discover (official eve catalog + any configured third-party sources)
eve registry list                       # all available integrations
eve registry search browser             # find a capability
eve registry view extension/agent-browser   # inspect before installing

# Install (kind/name, or a direct registry URL)
eve add extension/agent-browser
eve add channel/slack
eve add connection/linear
eve add instrumentation/braintrust
eve add https://registry.acme.com/r/analytics.json
#   flags: --skip-install (defer dep install)   --overwrite (replace existing files)

# Third-party registries (shadcn registry format; stored in package.json#registries)
eve registry add @acme=https://registry.acme.com/r/{name}.json
```

Where files land: **extensions** → a mount under `agent/extensions/`; **connections** →
`agent/connections/` (+ installs `@vercel/connect` when required); **instrumentation** →
`agent/instrumentation.ts` (agents have **one** instrumentation file — compose multiple
exporters by hand). After any install: **review the generated files and add required config
(env vars, Connect provisioning) before running the agent.** The full catalog is the
integrations directory (<https://eve.dev/integrations>). Only fall through to hand-authoring the
sections below when nothing in the registry fits (or you must own/modify the source — then see
`eve-registry-porting`). `[VERIFY]` command syntax against `node_modules/eve/docs/`.

## Tool — `agent/tools/<name>.ts`

The most common operation, and the most loop-friendly. The filename slug becomes the tool
name and eve auto-registers it (`agent/tools/get_weather.ts` → `get_weather`).

```ts
import { defineTool } from "eve/tools";
import { z } from "zod";

export default defineTool({
  description: "Get the current weather for a city.",
  inputSchema: z.object({ city: z.string().min(1) }),   // z.object({}) for no input
  async execute({ city }, ctx) {
    return { city, condition: "Sunny", temperatureF: 72 };
  },
});
```

* `inputSchema` is required (Zod / any Standard Schema / a plain JSON Schema object).
* **Return plain JSON.** The runtime rejects non-JSON-serializable tool outputs at call
  time ("returned a non-JSON-serializable result") — returning raw ORM rows (Drizzle rows
  carry `Date` objects) fails on real runs while passing typecheck and mock evals. Project
  to plain objects (dates → ISO strings) in a shared `lib/` helper so every copy of the
  tool gets the fix.
* `ctx` gives `ctx.session` (id, turn, `auth.current`/`auth.initiator`, `parent`),
  `ctx.getSandbox()`, `ctx.getSkill(id)`.
* `execute` runs in the **trusted app runtime** — read secrets from `process.env` here; the
  model only sees the returned value.
* **Idempotency:** an interrupted step re-runs. Any non-idempotent side effect must be made
  idempotent or gated with `approval: always()` / `once()` from `eve/tools/approval` — or a
  **custom policy** `({ session, toolName, toolInput, … }) => "user-approval" |
  "not-applicable" | "approved" | "denied"` when the decision depends on input or caller
  (threshold amounts, cross-tenant guards). See eve-conventions.md for the full shape.
* Optional: `outputSchema` (return typing / task mode), `toModelOutput(output)` to project
  what the model sees vs what channels receive.
* Override a built-in tool by re-importing from `eve/tools/defaults`; disable via `disableTool()`.

### Prebuilt toolsets (don't hand-write what a preset already gives)

Before hand-writing many tools for a well-known service, check for a **prebuilt toolset** — a
single file in `agent/tools/` that exposes a whole family of tools. The first is **GitHub
Tools**: `createGithubTools` from `@github-tools/sdk/eve` ([VERIFY] against the installed
package). One file covers pull requests, code review, issues, commits, and repo management:

```ts
// agent/tools/github.ts
import { createGithubTools } from "@github-tools/sdk/eve";
export default createGithubTools({ preset: "maintainer" });
```

Five presets scope the surface — `code-review`, `issue-triage`, `repo-explorer`, `ci-ops`,
`maintainer` — usable alone or merged. **Safe by default**: write tools (`mergePullRequest`)
require approval; read tools (`listPullRequestFiles`, `getCommit`) trim what the model sees.
Prefer a toolset + preset over reinventing per-tool files for that service.

More prebuilt capabilities ship as **extensions** in the eve integrations directory (<https://eve.dev/integrations>) — GitHub Tools, **agent-browser**, **Browserbase**, **Browser Use**, **KERNEL**, **Jetty**. Install one per the **Extension** section below instead of hand-writing its tools.

## Skill — `agent/skills/<name>.md`

An on-demand procedure the framework-owned `load_skill` tool pulls into the active turn when
the request matches the skill's description (or the user names it). Three shapes: flat
`agent/skills/<name>.md`, packaged `agent/skills/<name>/SKILL.md` (with sibling `references/`,
`assets/`, `scripts/`), or TypeScript via `defineSkill` from `eve/skills`. Write the
description as a **task trigger, not a label**. Skills are per-agent scoped — a subagent's
skills are invisible to the root.

## Channel — `eve add channel/<kind>`

A new entrypoint. Install from the registry: **`eve add channel/<kind>`** (kinds: `web`, `slack`,
`discord`, `github`, `linear`, `teams`, `telegram`, `photon-imessage`) — or the `/add` browser in the
dev TUI. ⚠️ **`eve channels add` was removed in eve 0.29.0**; only `eve channels list` (user-authored
channels) survives. `[VERIFY]` the kind list against `eve registry list`.
The file stem is the channel id and the channel is the module's **default export**
(`defineChannel` from `eve/channels` for custom ones). The default HTTP channel
(`agent/channels/eve.ts`) already exists from scaffold — only add a channel for another
surface. Platform channels read secrets from env vars (`DISCORD_*`, `LINEAR_*`, `MICROSOFT_*`,
`TELEGRAM_*`, `TWILIO_*`); **Slack and GitHub go through Vercel Connect** (no `SLACK_*` env
vars — credentials via `connectSlackCredentials`/`connectGitHubCredentials` from
`@vercel/connect/eve`). Most need a one-time out-of-band registration (Discord command PUT,
Telegram `setWebhook`, GitHub App events, Linear OAuth `actor=app`). For messaging surfaces not in that list — WhatsApp, email, or a unified adapter — use the **Vercel Chat SDK** channel (`/docs/channels/chat-sdk`); for a bespoke HTTP/WebSocket surface (CORS, file uploads), author a **custom channel** with `defineChannel` (`/docs/channels/custom`). `[VERIFY]` both against the installed docs. The **eve integrations directory** (<https://eve.dev/integrations>) is the full channel catalog — Google Chat, WhatsApp, X, Messenger, Resend/email, and provider-official adapters beyond the CLI kinds.

Slack concretely ([VERIFY] against installed docs — the Connect flow has changed before):

```ts
// agent/channels/slack.ts   (scaffolded by `eve add channel/slack`)
import { connectSlackCredentials } from "@vercel/connect/eve";
import { slackChannel } from "eve/channels/slack";
export default slackChannel({ credentials: connectSlackCredentials("slack/<agent-name>") });
```

```bash
vercel connect create slack --triggers                                  # provision + enable Event Subscriptions
vercel connect attach <uid> --triggers --trigger-path /eve/v1/slack --yes   # point triggers at eve's route
```

Gotchas: `--triggers` is needed on BOTH create (connector) and attach (destination) — a bot
that appears in Slack but never replies is almost always missing one of the two; the trigger
path must be `/eve/v1/slack`, not Connect's default `/slack`; re-running `create` installs a
duplicate Slack app. Slack delivers over the public internet, so it cannot be tested on
localhost — deploy first, then smoke-test with `eve dev <url>`.

**Slack event hooks + session controls** ([VERIFY] against installed docs) — configured on the
`slackChannel({ … })` options in `agent/channels/slack.ts`:
- **`onMessage(ctx)`** — intercept an incoming message before it starts/continues a turn. Helpers on `ctx`: `ctx.isBotMentioned()` (explicit @-mention), `ctx.isSubscribed()` (the thread already owns an active eve session), `ctx.thread.listParticipants()` (unique human Slack user ids, first-appearance order). Use it to gate *when* the agent replies (e.g. only on mention, or always inside a subscribed thread).
- **`onAppMention(ctx)`** / **`onDirectMessage(ctx)`** — the mention- and DM-specific hooks. Don't hand-roll that gating inside `onMessage`: eve already routes it. (`onInteraction(ctx)` handles interactive components.) All the message hooks receive the same `ctx` helpers and the session controls below.
- **`onEvent(ctx)`** — the **raw fallback after the message hooks**: Slack **Events API** callbacks that aren't messages (`reaction_added`, `team_join`, `channel_created`, …). It can still **fan one event out to multiple targets** (e.g. greet every new member), but ⚠️ **`ctx.receive` was removed in 0.31.0**: for generic events the target is now passed **in each operation's options** — `ctx.send(message, { target, auth })`. `resolveActiveSession` is gone too; use `ctx.resolveSession(address)`.
- **Session controls** (thread-bound, callable from the hooks) — ⚠️ **the two take different options**: **`ctx.cancel({ turnId? })`** stops the current turn but **keeps the session** (for mid-turn corrections; new input queues onto the same session) — from `onEvent` it needs the thread explicitly: `ctx.cancel({ channelId, threadTs, turnId? })`. **`ctx.reset({ reason? })`** **terminally retires** the session owning the thread — the next message starts a fresh session (new history, state, and sandbox). `reason` belongs to `reset` only. These are the messaging-channel surface of the runtime's turn-cancel / session-lifecycle model (see `eve-concepts.md` §Sessions/HITL).

A realtime **voice** surface (AI Gateway `gpt-realtime-2` / STT / TTS, built web-side via the
`module-add voice` stub) should treat the agent as the brain and voice as an I/O channel
(STT → agent → TTS) — never run the speech-to-speech model's own tool loop *and* eve's
durable loop in parallel; two control loops compete and fragment the logic.

### Chat SDK channel — messaging surfaces via adapters

For **messaging platforms** (Facebook Messenger, WhatsApp, email via Resend, Liveblocks, and
any surface with an adapter), use the **Chat SDK channel** instead of a bespoke `defineChannel`.
It's `chatSdkChannel()` from `eve/channels/chat-sdk`, in a channel file named after the surface
(e.g. `agent/channels/resend.ts`). One channel reaches many platforms through pluggable adapters:

Shape verified against Vercel Labs' [`kody-eve-template`](https://github.com/vercel-labs/kody-eve-template)
(`agent/channels/resend.ts`, MIT) — an earlier version of this reference guessed it and got four
things wrong, so copy this, don't improvise:

```ts
// agent/channels/resend.ts — email in and out
import { createRedisState } from "@chat-adapter/state-redis";
import { createResendAdapter } from "@resend/chat-sdk-adapter";
import type { Message, Thread } from "chat";
import { chatSdkChannel } from "eve/channels/chat-sdk";

export const { bot, channel, send } = chatSdkChannel({
  adapters: {                                   // an OBJECT keyed by name, not an array
    resend: createResendAdapter({
      fromAddress: requireEnv("RESEND_FROM_ADDRESS", "kody@yourdomain.com"),
      fromName: process.env.RESEND_FROM_NAME ?? "Kody",
    }),
  },
  state: createRedisState(),                    // durable thread state
  streaming: false,                             // email has no incremental rendering
  userName: "Kody Agent",
});

bot.onNewMention(async (thread: Thread, message: Message) => {
  await thread.subscribe();                     // opt this thread into follow-ups
  await send(message.text, { thread });
});

bot.onSubscribedMessage(async (thread: Thread, message: Message) => {
  await send(message.text, { thread });
});

export default channel;                          // the channel is the default export
```

The four things worth reading twice:

1. **`adapters` is an object keyed by name**, not an array — the key is how the adapter is addressed.
2. **Factories are `create*`**: `createResendAdapter`, `createRedisState`. There is no `handler:`
   callback — you **destructure `{ bot, channel, send }`** from the call and register hooks on `bot`,
   then `export default channel` separately.
3. **`bot.onNewMention` / `bot.onSubscribedMessage`** are the two hooks. The mention handler calls
   `thread.subscribe()` first — without it the agent answers once and never hears the reply.
4. **`streaming: false` for email.** There is nothing to render incrementally in an inbox; each reply is
   delivered as one message. Leaving streaming on is a silent-quality bug, not an error.

Set `fromAddress` from the **same env var the system prompt and any digest task use**, so channel
replies and agent-sent mail share one identity — otherwise the agent answers from two addresses.

It gives you out of the box: a **webhook route per adapter**, typing indicators + automatic
reply posting, **HITL input requests rendered as cards with buttons**, **thread persistence
across sessions**, and in-conversation error reporting. Adapter creds go in env vars; state has
pluggable backends (`@chat-adapter/state-redis` for durability, `state-memory` only for local
dev — memory state loses every thread on redeploy). Use this for reach across chat platforms;
keep the default HTTP channel (`agent/channels/eve.ts`) for the Next.js web app via
`withEve()`/`useEveAgent()`.

**Email is a first-class inbound surface, not just an outbox.** The template's whole loop is a
scheduled digest emailed out, a human replying in natural language ("create Linear issues for #1
and #2"), and the agent acting and confirming by email. If a product already has an email
relationship with its users, that is a channel — don't build a web UI to get a conversation you
already have.

## Session API — fixed, ID-addressed handles (0.31.0)

⚠️ **eve 0.31.0 was a breaking migration of this whole surface.** Continuation tokens are gone from the
client: a session is addressed by its **`sessionId`** and nothing else. Code written against 0.30.x will
not compile or will fail at runtime. `[VERIFY]` against the installed version — eve is beta and this
moved twice in a month.

**Inside a channel**, three entry points and one cross-channel handoff:

| Call | What it gives you |
|---|---|
| `from(address)` | operations bound to a **channel-local continuation address**; the first `send()` creates a session if the address is unowned |
| `resolveSession(address)` | a fixed `Session` handle pinned to whichever session **currently owns** that address (a snapshot, not a live pointer) |
| `attachSession(sessionId)` | an **I/O-free** handle pinned to one durable id — no lookup; the first operation reports whether the id is still active |
| `to(channel, target)` | hand work to **another authored channel**; chain `.send(message, options)` |

```ts
const source = from(threadId);
const session = await source.send("Hello", { auth });   // positional message, then options
await source.respond(inputResponses, { auth });          // HITL answers — a SEPARATE call
await source.cancel({ turnId });
await source.reset({ reason: "Start over" });

const s = attachSession(sessionId);
await s.getEventStream({ startIndex: 12 });
```

**Four traps in the migration:**

1. **`send` is positional.** `send(message, options)` — not one options bag. And `message` and
   `inputResponses` are **mutually exclusive**: a HITL reply goes through `respond()`, so you can no
   longer smuggle one inside a send.
2. **`receive()`, `ctx.receive` and `resolveActiveSession` are removed.** Handoff is
   `to(channel, target).send(...)`; for generic Slack events the target rides **in each operation's
   options**. Channel event identity is now `ctx.session.id`.
3. **`onMessage` can no longer veto by returning `null`.** A canonical eve `onMessage` hook cannot drop
   an otherwise authorized delivery — if you relied on that for authorization, it is now a hole. Move the
   check into auth.
4. **"Continuation" still exists, but only as a channel address.** A custom channel owns its own token
   format (`channel.continuation?.rekey(rawToken)`) — "the framework derives nothing for you". That is
   not the old client session cursor; don't reintroduce one.

Client-side the same shape applies: `client.sessions.create(input)` and
`client.sessions.attach(sessionId)` replace `client.session(...)`. See `eve-web-integration.md`.

## Connection — `agent/connections/<service>.ts`

Auth + access to an external service via **MCP** or **OpenAPI**. The filename is the
connection id; tools surface to the model as `<connection>__<tool>` and are discoverable via
the built-in `connection_search`. The model never sees the URL or credentials.

**Check the eve integrations directory first** — <https://eve.dev/integrations> lists **50+ prebuilt MCP/OpenAPI connections** (Stripe, Supabase, Notion, Linear, Sentry, PostHog, Vercel, PlanetScale, Datadog, Airtable, Cloudinary, Mixpanel, Zapier, …). Adopt the official/prebuilt one over hand-authoring a `defineMcpClientConnection` / `defineOpenAPIConnection` when it exists — same ecosystem-first rule as everywhere in dev-flow.

```ts
// MCP
import { defineMcpClientConnection } from "eve/connections";
export default defineMcpClientConnection({
  url: "https://mcp.linear.app/mcp",   // [VERIFY] Streamable HTTP endpoint; the /sse transport is deprecated
  description: "Linear workspace: issues, projects, comments.",
  auth: { getToken: async () => ({ token: process.env.LINEAR_API_TOKEN! }) },
  tools: { allow: ["list_issues", "create_issue"] },   // set exactly one of allow / block
});
```

`defineOpenAPIConnection` takes `spec` (HTTPS URL or inline OpenAPI 3.x), `description`,
`auth.getToken`, and `operations: { allow|block }` by `operationId`. Prefer `allow` when
write operations are involved. Keep a Linear *connection* (agent reads/updates issues at
runtime) distinct from the build loop's own Linear access.

## Schedule — `agent/schedules/<name>.ts` (root-only)

```ts
import { defineSchedule } from "eve/schedules";
export default defineSchedule({
  cron: "0 9 * * 1-5",                  // 5-field, minute granularity, UTC
  markdown: "Post the morning standup summary.",   // OR a run() handler — exactly one
});
```

`eve dev` does **not** fire schedules on cadence; trigger manually in dev via
`POST /eve/v1/dev/schedules/<name>`. On Vercel they become Cron Jobs; self-hosted needs the
Nitro task runner under `eve start`.

Handler-form gotchas (`run({ receive, waitUntil, appAuth })`), learned the hard way:

⚠️ **`receive()` was removed in eve 0.31.0** — see §Session API above. Schedules now hand off with
`to(channel, target).send(message, { auth })`.

* A markdown schedule runs as the bare app principal — in a multi-tenant agent whose tools
  require a tenant id, it can't call anything. Use the handler form: enumerate tenants in
  code, then `to(channel, target).send(message, { auth })` one session per tenant with the
  tenant id stamped onto `auth.attributes` (eve's "dynamic scheduling" pattern — full recipe, incl. the atomic-lease `ScheduleStore` and at-least-once idempotency, in `references/eve-patterns.md` §4).
* **Give the handoff channel at least one (inert) route.** The target is resolved by
  module reference, falling back to a route fingerprint — and a channel with `routes: []`
  has no fingerprint, so cross-bundle module duplication makes it unresolvable at runtime
  ("channel is not registered in this agent's channels/").

## Subagent — local dir or remote

* **Local:** `agent/subagents/<name>/agent.ts` exporting a description, mirroring the
  `agent/` layout (own `tools/`, `skills/`, `instructions.md`, `sandbox/`). It **cannot**
  have `channels/` or `schedules/` (root-only). The dir name becomes the delegation tool;
  it must not collide with a tool name. The child sees none of the parent's history/state.
* **Remote:** `agent/subagents/<name>.ts` with `defineRemoteAgent` from `eve` (`url`,
  `description`, `auth` from `eve/agents/auth`) to call a separately-deployed eve agent as
  if it were a local subagent.

Prefer a **skill** when a subagent would be overkill (a skill is lighter).

**Building a whole team of them?** The mechanics above are one subagent; the *architecture* — a lead that routes depth-1 to non-overlapping specialists, boundaries drawn by job rather than artifact, shared state with exactly one writer, handoff artifacts passed **by id** so documents never enter the lead's context, and the subagent `description` written as a routing contract — is **`eve-patterns.md` §7**. Read it before adding the second subagent, not the fifth.

## Hook — `agent/hooks/<name>.ts` (lifecycle subscriber)

```ts
import { defineHook } from "eve/hooks";
export default defineHook({
  events: {
    async "session.started"(event, ctx) { /* audit / metrics / persist */ },
    async "message.completed"(event) { /* … */ },
  },
});
```

Events include `session.started`, `turn.completed`, `message.completed`, `action.result`,
and `*`. Handlers run after each event is durably recorded — use for audit logging, metrics,
persisting sessions to your own DB. Not a place for behavior the model should invoke (use a tool).

**Observability sink (external), the way worldcup-eve does it** — `turn.completed` + `session.failed`
posting to an external store. Two rules learned the hard way:

* **`await` the request.** The workflow runtime **suspends once the handler resolves**, so a
  dangling (un-awaited) `fetch` never completes. Since the user's reply is already delivered by
  then, awaiting adds no visible latency.
* **Observability must never fail a turn.** No-op when the sink's env vars are unset, bound the
  request with `AbortSignal.timeout(...)`, and swallow errors to a `console.warn` — never throw.

```ts
export default defineHook({
  events: { "turn.completed": notifyObs, "session.failed": notifyObs },
});
async function notifyObs(_event: unknown, ctx: HookContext) {
  const { OBS_URL, OBS_TOKEN } = process.env;
  if (!OBS_URL || !OBS_TOKEN) return;                       // no-op unless configured
  try {
    await fetch(OBS_URL, { method: "POST", signal: AbortSignal.timeout(15_000),
      headers: { authorization: `Bearer ${OBS_TOKEN}` },
      body: JSON.stringify({ sessionIds: [ctx.session.id] }) });
  } catch (e) { console.warn("[obs]", e); }                 // never fail the turn
}
```

(For deployed runs you also get Vercel's Agent Runs tab + `vercel agent-runs` CLI for free — see
eve-conventions.md → Observability. Use a custom sink only when you need the data in your own store.)

## Eval — `evals/<...>.eval.ts` (sibling of `agent/`)

```ts
import { defineEval } from "eve/evals";
import { includes } from "eve/evals/expect";

export default defineEval({
  description: "Weather agent answers and calls the right tool.",
  async test(t) {
    await t.send("What is the weather in Brooklyn?");
    t.succeeded();
    t.calledTool("get_weather");
    t.check(t.reply, includes("Sunny"));
  },
});
```

Files live in `evals/` at the **app root, a sibling of `agent/`**, named `*.eval.ts`; the
path is the id; `evals.config.ts` holds project config (default judge model, reporters).
Add a negative case (`t.notCalledTool` / `t.usedNoTools` / `t.maxToolCalls`). Deterministic
assertions are hard gates; LLM-judge graders (`t.judge.autoevals.{factuality,summarizes,
closedQA,sql}`) are soft by default — enforce with `.atLeast()` or `.gate()`. The eval suite
is the deploy gate; new capabilities without evals erode it. **Full API** — the complete
assertion set (`toolOrder` / `eventOrder` / `calledSubagent` / `loadedSkill` / `noFailedActions`
/ structured-output / preconditions), the matchers, judge model resolution, targets
(`t.target.fetch` / `dispatchSchedule` / `attachSession`), reporters (Console / JUnit /
Braintrust), and every `eve eval` flag + exit code — is in **`references/eve-evals.md`**.

## Extension — `agent/extensions/<name>.ts` (installable capability bundle)

An **extension** is a *package* of eve capabilities — tools, connections, skills, instructions, and hooks — published to a package registry and installed like any other dependency, then versioned/upgraded with the project. Reach for one when a whole capability family (a CRM integration, browser-use tools, a memory / self-improvement layer) should be **reused across agents** instead of hand-copied. (Shipped 2026-07-22; `[VERIFY]` every identifier below against `node_modules/eve/docs/` — this surface is new.)

**Consume an installed extension** (the common case) — `eve add extension/<name>` (from the registry — see the "Install from the registry FIRST" section at the top; it writes the mount + installs the package), or add the ONE file under `agent/extensions/` by hand:

```ts
// agent/extensions/crm.ts
import crm from "@acme/crm";
export default crm({ apiKey: process.env.CRM_API_KEY! });   // config validated by the extension's schema
```

* The **filename sets the namespace**: an extension tool `search` mounted via `agent/extensions/crm.ts` runs as `crm__search` (filename + `__` + tool name). Renaming the file re-namespaces its tools.
* The extension declares a **config schema** (Zod / any Standard Schema); pass config as the default-export call argument. Read secrets from `process.env` in this trusted runtime — never hardcode.
* Tune what it exposes without forking it: `disableTool()` to approval-gate / replace / remove a bundled tool, and `toolResultFrom` inside a hook to narrow a bundled tool's result type. `[VERIFY]` both against the installed docs.

**Author a new extension** (a bigger, separate operation) — scaffold with `npx eve@latest extension init <name>`, which lays out the package:

```
@acme/crm/
  package.json
  extension/
    extension.ts        # defineExtension + config schema
    tools/  connections/  skills/  instructions.md  hooks/  lib/
```

Build with `eve extension build`, publish to a registry, then consume it from agents as above. `defineExtension` and the exact layout are `[VERIFY]` against `node_modules/eve/docs/`.

**Extension vs. the other capabilities:** a tool/skill/connection/hook is a *single local file* in this agent; an extension is a *versioned package* that bundles several of them and is shared across agents. **Extension vs. `eve-registry-porting`:** porting *copies* a component into your repo (vendored, tenant-hardened by hand); an extension *installs* a package (a dependency you upgrade). Prefer an extension when a maintained package exists and the reuse-across-agents payoff justifies it; port when you need to own/modify the source or the source isn't packaged.

## After any add

```bash
eve info                                   # confirm the new file was discovered
pnpm --filter agent lint typecheck build
pnpm --filter agent eval                   # `eve eval`; CI: eve eval --strict --junit .eve/junit.xml
```

Then update `.workflow/meta.json` history:

```json
{ "skill": "eve-agent", "action": "add-tool", "inputs": { "name": "<name>" } }
```

(Use `add-skill` / `add-channel` / `add-connection` / `add-schedule` / `add-subagent` /
`add-hook` / `add-eval` as appropriate.)

## Idempotency

Before creating a file, check whether it already exists (and run `eve info`). If it exists
and matches intent, report "already present, skipping" instead of overwriting. Only modify
on explicit request.
