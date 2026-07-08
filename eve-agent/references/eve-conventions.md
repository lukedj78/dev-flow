# eve-conventions — cross-cutting rules, import map, and best practices

These are the rules that apply across every mode. They come from the eve.dev docs
(2026-06); always re-confirm exact signatures against `node_modules/eve/docs/` and the
TypeScript types of the **installed** version — names and defaults can drift.

## Import map (each capability has its own subpath)

Only `defineAgent` / `defineRemoteAgent` come from bare `eve`. Everything else is namespaced:

| Helper | Module |
|---|---|
| `defineAgent`, `defineRemoteAgent` | `eve` |
| `defineTool`, `disableTool`, `ExperimentalWorkflow` | `eve/tools` |
| approval policies `always` / `once` / `never` | `eve/tools/approval` |
| built-in tool defaults (`bash`, `readFile`, …) | `eve/tools/defaults` |
| `defineSkill` | `eve/skills` |
| `defineInstructions` | `eve/instructions` |
| `defineDynamic` | `eve/tools` · `eve/skills` · `eve/instructions` |
| `defineChannel` + route verbs `GET/POST/PUT/PATCH/DELETE/WS` | `eve/channels` |
| `chatSdkChannel` (messaging surfaces via adapters) | `eve/channels/chat-sdk` |
| `defineMcpClientConnection`, `defineOpenAPIConnection` | `eve/connections` |
| `defineHook` | `eve/hooks` |
| `defineSchedule` | `eve/schedules` |
| `defineState` | `eve/context` |
| `defineSandbox` + backends `vercel()`/`docker()`/… | `eve/sandbox` |
| `defineInstrumentation` | `eve/instrumentation` |
| `defineEval`, `defineEvalConfig` | `eve/evals` |
| value matchers `includes`/`equals`/`matches`/`similarity`/`satisfies` | `eve/evals/expect` |
| `Client` (typed client) | `eve/client` |
| `withEve` (Next.js config wrapper) | `eve/next` |
| `useEveAgent` (React hook) | `eve/react` (also `eve/vue`, `eve/svelte`) |
| outbound auth `vercelOidc`/`bearer`/`basic` | `eve/agents/auth` |

**There is no `defineSubagent`.** A local subagent is a directory `agent/subagents/<id>/`
with an `agent.ts` that exports a description; a remote subagent uses `defineRemoteAgent`.

## Identity is the file path

`agent/tools/get_weather.ts` → tool `get_weather`; `agent/connections/linear.ts` →
connection `linear`; `agent/schedules/billing/sweep.ts` → `billing/sweep`. No `id`/`name`
field is authored. The **root agent name comes from `package.json` `name`**. A wrong
filename fails resolution rather than silently no-op'ing, and a subagent dir colliding with
a tool name fails the build.

## Root-only vs subagent-local slots

Root-only: `agent.ts`, `instrumentation.ts`, `channels/`, `schedules/`. Subagent-capable:
`tools/`, `skills/`, `connections/`, `hooks/`, `sandbox/`, `lib/`, nested `subagents/`.
`instructions.md` is required at root, optional per subagent. **Never author both
`instructions.md` and `instructions.ts` at the root** — it is a build error.

## Durability & idempotency (the rule scaffolds get wrong)

Every turn runs as a **durable workflow** on the Workflow SDK: Session → Turn → Step, where
a Step is a checkpoint (one model call + its tool calls). Completed steps replay their
recorded result; **an interrupted step re-runs**. Therefore any tool with a non-idempotent
side effect (payment, delete, email, external write) MUST be either made idempotent or
**approval-gated** — gating a side effect on approval is also what makes it replay-safe.

```ts
import { defineTool } from "eve/tools";
import { always } from "eve/tools/approval";   // or once() / never() (default)
export default defineTool({
  approval: always(),
  inputSchema: z.object({ /* … */ }),
  async execute(input, ctx) { /* … */ },
});
```

HITL surfaces as `input.requested` / `authorization.required` stream events; the run parks
durably at `session.waiting` and resumes when the client answers via `inputResponses` keyed
by `requestId`. The built-in `ask_question` tool (`{ prompt, options?, allowFreeform? }`)
is the other HITL path.

## Security model

Two trust zones: the **app runtime** (trusted — has `process.env`/secrets, runs tool
`execute` and durable execution) and the **sandbox** (isolated — own `/workspace`, no
`process.env`, no secrets; only shell/`bash` runs there). Rules:

* Secrets live in `process.env` only — never in `agent.ts`, the compiled manifest, or the
  sandbox. The model sees only a tool's returned value, never the key.
* Sandbox network policy defaults to `allow-all`; set `deny-all` or an allow-list (on the
  backend factory or `onSession`) for sensitive/regulated/production workloads.
* Connection tokens come from `auth.getToken()` → `{ token, expiresAt? }`, are cached per
  step, never serialized to durable state, and never reach the model.

## Auth fails closed

The default eve HTTP channel ships `placeholderAuth()`, which **rejects production traffic**
so an unauthenticated app can't go live by accident. The auth fallback `[vercelOidc(),
localDev()]` also does not admit browser users in production. To accept browser traffic,
replace it with real auth (Clerk / Auth.js / OIDC-JWT / API keys / a custom `AuthFn`) in
`agent/channels/eve.ts`, and put a `tenantId` (and other identity attributes) on the
principal. **Never derive tenant/user from model input** — only from verified
`ctx.session.auth.current`.

## Built-in default harness

The model already has ~12 tools with zero code: `bash`, `read_file`, `write_file`, `glob`,
`grep`, `web_fetch`, `web_search`, `todo`, `ask_question`, `agent` (subagents), `load_skill`
(only when skills are declared), `connection_search` (only when connections are declared).
Override a default by creating `agent/tools/<name>.ts` re-importing from `eve/tools/defaults`;
disable one with the `disableTool()` sentinel. Don't re-implement what the harness gives you.

## State & per-session context

`defineState("namespaced.key", () => initial)` from `eve/context` is durable **per session**,
survives step/redeploy boundaries, does **not** reset per turn (reset via a `turn.started`
hook), and does **not** cross the parent↔subagent boundary (subagents get fresh instances).
Per-session/per-caller context that must resolve at runtime belongs in `defineDynamic`
(reading `ctx.session.auth`), not in `instructions.ts` (which runs once at build time and is
baked into the manifest). Write `execute`/resolvers as **inline** function expressions — the
bundler does not capture `execute: someFn` and it fails on replay.

## Deploy & monorepo wiring

* `eve build` emits Nitro output under `.output/` and writes workflow state under
  `.workflow-data`. Gitignore both, and list them as Turbo task `outputs` for `apps/agent`.
* Deploy with `eve link` (pulls Vercel AI Gateway credentials) + `eve deploy`, or
  `vercel deploy` (not `--prebuilt` when skipping prewarming).
* When `apps/web` fronts the agent, the proxy/rewrites must forward **both** `/eve/` **and**
  `/.well-known/workflow/`.
* Model credentials via env: `AI_GATEWAY_API_KEY` (gateway) or a provider key
  (`ANTHROPIC_API_KEY`, …) plus the matching `@ai-sdk/*` package for direct routing.
* Prereqs: **Node ≥ 24** and npm. Default scaffold model: `anthropic/claude-sonnet-4.6`.
* Self-host: `eve build` + `PORT=3000 eve start --host 0.0.0.0`, persistent `.workflow-data`,
  Nitro scheduled-task runner if schedules exist, and a real authenticator replacing
  `vercelOidc()`.

## Observability — inspecting deployed runs

Deployed on Vercel, every eve project gets an **Agent Runs** tab (trigger, duration, token
usage per session) automatically. To debug from the terminal or from a coding agent, use the
`vercel agent-runs` CLI (needs `npm i -g vercel@latest`):

```bash
vercel agent-runs projects              # projects with runs
vercel agent-runs list                  # recent runs for a project
vercel agent-runs inspect <runId>       # metadata, lifecycle, usage, subagents
vercel agent-runs trace <runId>         # turns, messages, reasoning, tokens (markdown when piped)
```

Add `--json` for programmatic output. The same four operations exist as Vercel MCP tools
(`list_agent_run_projects`, `list_agent_runs`, `get_agent_run`, `get_agent_run_trace`) via
`npx add-mcp https://mcp.vercel.com` — so an autonomous loop can debug a failed run without a
human. ([VERIFY] against current Vercel CLI/MCP.)

## Workspace seeding

Only two sources reach the sandbox `/workspace`: `agent/skills/` → `/workspace/skills/…`,
and `agent/sandbox/workspace/**` → `/workspace/…` at bootstrap. **`agent/lib/` is
import-only and never reaches the workspace** — don't assume helper code there is available
to shell tools at runtime. Don't seed skills via `sandbox/workspace/skills/`; use `agent/skills/`.

## Responsible use (default to safe)

eve's defaults are permissive: tools can execute without approval and sandbox egress is not
deny-all. For any action that is irreversible, regulated (financial/health/employment/
housing/legal), safety-impacting, or has external side effects, default to an approval gate
or other protective control. **Do not rely on model behavior alone** to prevent sensitive
actions.
