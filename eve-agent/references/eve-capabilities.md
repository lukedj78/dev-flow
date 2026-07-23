# eve-capabilities — adding one capability at a time

Add exactly ONE capability per invocation, idempotently. Read the matching section of
`node_modules/eve/docs/` (live: <https://eve.dev/docs>) first, and see
`eve-conventions.md` for the import map, identity-by-path, durability/idempotency, and
security rules that apply to all of these.

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

## Skill — `agent/skills/<name>.md`

An on-demand procedure the framework-owned `load_skill` tool pulls into the active turn when
the request matches the skill's description (or the user names it). Three shapes: flat
`agent/skills/<name>.md`, packaged `agent/skills/<name>/SKILL.md` (with sibling `references/`,
`assets/`, `scripts/`), or TypeScript via `defineSkill` from `eve/skills`. Write the
description as a **task trigger, not a label**. Skills are per-agent scoped — a subagent's
skills are invisible to the root.

## Channel — `eve channels add web|slack`

A new entrypoint. Run `eve channels add <kind>` (kinds: `web`, `slack`, `discord`, `github`,
`linear`, `teams`, `telegram`, `twilio`); `eve channels list` shows user-authored channels.
The file stem is the channel id and the channel is the module's **default export**
(`defineChannel` from `eve/channels` for custom ones). The default HTTP channel
(`agent/channels/eve.ts`) already exists from scaffold — only add a channel for another
surface. Platform channels read secrets from env vars (`DISCORD_*`, `LINEAR_*`, `MICROSOFT_*`,
`TELEGRAM_*`, `TWILIO_*`); **Slack and GitHub go through Vercel Connect** (no `SLACK_*` env
vars — credentials via `connectSlackCredentials`/`connectGitHubCredentials` from
`@vercel/connect/eve`). Most need a one-time out-of-band registration (Discord command PUT,
Telegram `setWebhook`, GitHub App events, Linear OAuth `actor=app`).

Slack concretely ([VERIFY] against installed docs — the Connect flow has changed before):

```ts
// agent/channels/slack.ts   (scaffolded by `eve channels add slack`)
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

A realtime **voice** surface (AI Gateway `gpt-realtime-2` / STT / TTS, built web-side via the
`module-add voice` stub) should treat the agent as the brain and voice as an I/O channel
(STT → agent → TTS) — never run the speech-to-speech model's own tool loop *and* eve's
durable loop in parallel; two control loops compete and fragment the logic.

### Chat SDK channel — messaging surfaces via adapters

For **messaging platforms** (Facebook Messenger, WhatsApp, email via Resend, Liveblocks, and
any surface with an adapter), use the **Chat SDK channel** instead of a bespoke `defineChannel`.
It's `chatSdkChannel()` from `eve/channels/chat-sdk`, in a channel file named after the surface
(e.g. `agent/channels/resend.ts`). One channel reaches many platforms through pluggable adapters:

```ts
// agent/channels/resend.ts   ([VERIFY] names against installed eve/@chat-adapter versions)
import { chatSdkChannel } from "eve/channels/chat-sdk";
import { stateMemory } from "@chat-adapter/state-memory";
import { resendAdapter } from "@resend/chat-sdk-adapter";

export default chatSdkChannel({
  adapters: [resendAdapter({ /* creds from env */ })],
  state: stateMemory(),
  handler: (bot) => {
    // register handlers on `bot` like a standalone Chat SDK app, then route to the agent:
    bot.on("message", async (message, { send, thread }) => {
      await send(message.text, { thread });
    });
  },
});
```

It gives you out of the box: a **webhook route per adapter**, typing indicators + automatic
reply posting, **HITL input requests rendered as cards with buttons**, **thread persistence
across sessions**, and in-conversation error reporting. Adapter creds go in env vars;
`@chat-adapter/state-memory` is the default (swap for a durable store in production). Use this
for reach across chat platforms; keep the default HTTP channel (`agent/channels/eve.ts`) for
the Next.js web app via `withEve()`/`useEveAgent()`.

## Connection — `agent/connections/<service>.ts`

Auth + access to an external service via **MCP** or **OpenAPI**. The filename is the
connection id; tools surface to the model as `<connection>__<tool>` and are discoverable via
the built-in `connection_search`. The model never sees the URL or credentials.

```ts
// MCP
import { defineMcpClientConnection } from "eve/connections";
export default defineMcpClientConnection({
  url: "https://mcp.linear.app/sse",
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

* A markdown schedule runs as the bare app principal — in a multi-tenant agent whose tools
  require a tenant id, it can't call anything. Use the handler form: enumerate tenants in
  code, then `receive(channel, { message, target, auth })` one session per tenant with the
  tenant id stamped onto `auth.attributes` (eve's "dynamic scheduling" pattern — full recipe, incl. the atomic-lease `ScheduleStore` and at-least-once idempotency, in `references/eve-patterns.md` §4).
* **The default eve HTTP channel does not implement `receive()`** — it cannot be a handoff
  target. Author a minimal internal channel (`defineChannel` with a `receive` hook that
  calls `send(message, { auth, mode: "task", continuationToken: <fresh unique> })`).
* **Give that channel at least one (inert) route.** `receive()` resolves its target by
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

**Consume an installed extension** (the common case) — add ONE file under `agent/extensions/`:

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
