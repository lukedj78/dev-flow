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
* `ctx` gives `ctx.session` (id, turn, `auth.current`/`auth.initiator`, `parent`),
  `ctx.getSandbox()`, `ctx.getSkill(id)`.
* `execute` runs in the **trusted app runtime** — read secrets from `process.env` here; the
  model only sees the returned value.
* **Idempotency:** an interrupted step re-runs. Any non-idempotent side effect must be made
  idempotent or gated with `approval: always()` / `once()` from `eve/tools/approval`.
* Optional: `outputSchema` (return typing / task mode), `toModelOutput(output)` to project
  what the model sees vs what channels receive.
* Override a built-in tool by re-importing from `eve/tools/defaults`; disable via `disableTool()`.

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
surface. Platform channels read secrets from env vars (`DISCORD_*`, `GITHUB_*`, `LINEAR_*`,
`MICROSOFT_*`, `TELEGRAM_*`, `TWILIO_*`); **Slack is the exception** (Vercel Connect, no
`SLACK_*` env vars). Most need a one-time out-of-band registration (Discord command PUT,
Telegram `setWebhook`, GitHub App events, Linear OAuth `actor=app`, Slack `--triggers`).

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
is the deploy gate; new capabilities without evals erode it.

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
