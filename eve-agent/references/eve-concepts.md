# eve concepts — config, context, durability, HITL, dynamic capabilities

The cross-cutting concepts behind every capability. This complements `eve-conventions.md` (rules) and `eve-capabilities.md` (per-file how-to). Live docs: <https://eve.dev/docs/concepts/…>, `/docs/agent-config`, `/docs/instructions`, `/docs/human-in-the-loop`, `/docs/guides/{state,dynamic-capabilities,dynamic-workflows}`. **Read `node_modules/eve/docs/` first.** Last verified end-to-end against **`eve@0.45.0`** (2026-08-26); treat every identifier as `[VERIFY]` again on upgrade.

## Agent config — `agent/agent.ts` (`defineAgent`)

Root-only. Fields:
- `model` — gateway id (this skill pins `"anthropic/claude-sonnet-5"`; **eve's own scaffold default is `zai/glm-5.2`** since 0.36.0, still true at 0.45.0 and also the default of `eve init --model` — and **GLM 5.2 takes no image input**, so an agent that will ever see a screenshot needs a vision-capable model or an image route to one) or a `LanguageModel`; may be a `defineDynamic({ events })` for per-session/turn/step model choice — since 0.33.0 there is no `fallback`, every matching handler must return a concrete model.
- `reasoning` — `"provider-default" | "none" | "minimal" | "low" | "medium" | "high" | "xhigh"` (availability is model/provider-dependent).
- `compaction` — summarizes older turns near the window; **on by default**, `thresholdPercent` default `0.9` (lower = compact sooner).
- `limits` — `{ maxInputTokensPerSession (default 40_000_000 for root), maxOutputTokensPerSession (unset) }`; set either to `false` to remove a cap. Size tight for public demos (+ Vercel Firewall rate-limit), looser for internal tools.
- `modelOptions` — provider option overrides; `outputSchema` — structured return for task-mode runs.
- `experimental.workflow.world` — the Workflow world package (e.g. `"@workflow/world-postgres"`); `build.externalDependencies` — keep packages external in hosted builds.

## Instructions — `agent/instructions.md` (static) vs dynamic

Instructions are the **always-on identity**, prepended every turn. Keep `instructions.md` short and stable. Organization: a single root file, an `agent/instructions/` directory (`.md` + `.ts`, non-recursive, alphabetical), or a hybrid (root first). You **cannot** have both `.md` and `.ts` at root (build error). Dynamic instructions resolve at runtime from session context:

```ts
import { defineDynamic, defineInstructions } from "eve/instructions";
export default defineDynamic({ events: { "turn.started": (_e, ctx) =>
  defineInstructions({ markdown: `…per-caller context from ctx.session.auth…` }) } });
```

Instructions vs skills: **same context, different timing** — instructions load always; skills load on demand via `load_skill`. Long procedures belong in `skills/`, not instructions.

## Context control — what the model sees

Layered visibility, not everything-in-the-prompt: `instructions.md` (always) + dynamic instructions (per-caller) + on-demand `skills/` (advertised, loaded via `load_skill`) + runtime tools for file/workspace inspection (a shallow workspace hint, not inlined contents). This keeps prompts compact and defers non-essential info. Manage growth by putting identity in `instructions.md`, procedures in `skills/`, integrations in `tools/`, specialization in subagents, and files behind sandbox/workspace tools — not the prompt. `compaction` handles overflow automatically.

## Default harness — the built-in tools + loop

eve runs the agent loop (model calls, tool execution, compaction) and ships built-ins:
- Sandbox: `bash`, `read_file` (line-numbered, read-before-write), `write_file` (stale-read detection). **`glob` and `grep` are no longer default** — dropped from the set in **0.39.0**; opt in with a one-line file (below).
- Network: `web_fetch` (app runtime), `web_search` (**provider-managed, model-dependent** — which model you route to decides whether you get search at all, and how good it is).

  **eve already solved this, and it's one line.** `web_search` has no local executor — the provider runs it — and on **AI Gateway models eve defaults to Exa**, with no separate account. Switch providers by exporting the config helper, not by writing a tool:

  ```ts title="agent/tools/web_search.ts"
  import { webSearch } from "eve/tools/web_search";
  export default webSearch({ provider: "parallel" });   // "exa" (Gateway default) | "parallel"
  ```

  Direct provider models keep their own native search instead. So the older worry — *which model you route to decides whether you get search* — holds for direct providers and **not** for the Gateway, where search is a property of the gateway. Only reach for `defineTool()` when you want your own implementation; the provider's own built-in search (one `tools/web_search.ts` per provider, as shadcn's `chatbot-template` does) is the pattern for the non-Gateway case.
- Session: `ask_question` (mid-turn input), `todo` (durable per-session list), `load_skill`, `connection_search` (discover/call connection tools), `agent` (delegate to a fresh instance, root-only).

Customize:
- **Override** — `agent/tools/<slug>.ts` spreading the default: `import { writeFile } from "eve/tools/write_file"; export default defineTool({ ...writeFile, async execute(i, ctx) {…} });` — **`eve/tools/defaults` was removed in 0.45.0**; every built-in now lives on its own subpath, named after the *tool* (`eve/tools/read_file`, `/write_file`, `/web_fetch`, `/load_skill`, `/todo`, `/bash`) while the export keeps camelCase (`readFile`, `writeFile`, `webFetch`, `loadSkill`).
- **Opt in** — the framework tools that are *not* registered by default are one re-export each: `export { glob as default } from "eve/tools/glob"` (same for `grep`), `experimental_workflow()` from `eve/tools/workflow`, `sleep()` from `eve/tools/sleep`. **The filename is what names the tool**, not the export.
- **Disable** — `agent/tools/bash.ts` → `export default disableTool();` (from `eve/tools`).
- **Extend** — new tools with fresh slugs join the built-ins.

## Sandbox — the agent's isolated `/workspace`

Every agent has exactly one sandbox: an isolated bash filesystem rooted at `/workspace`, where `bash`/`read_file`/`write_file` (and the opt-in `glob`/`grep`) run and which custom code reaches via `ctx.getSandbox()`. It **never touches your app runtime** (authored tools keep full `process.env`; only sandbox-targeted tools run inside). Backends (`defaultBackend()` picks best-available): **Vercel Sandbox** (hosted), **Docker** (local containers), **microsandbox** (local VM, Apple Silicon/Linux KVM), **just-bash** (pure-JS interpreter, no isolation — the cheap fallback).

```ts
import { defineSandbox } from "eve/sandbox";
import { vercel } from "eve/sandbox/vercel";
export default defineSandbox({           // agent/sandbox.ts (shorthand) OR agent/sandbox/sandbox.ts (folder wins)
  backend: vercel({ resources: { vcpus: 2 } }),
  revalidationKey: () => "repo-bootstrap-v1",
  async bootstrap({ use }) {/* template-scoped, runs once — clone/install/seed */},
  async onSession({ use, ctx }) {/* per-session — network policy, resources, per-user creds */},
});
```

- **Seeding:** files under `agent/sandbox/workspace/` mirror into `/workspace` at session start (structure intact; top-level entries are advertised to the model).
- **Network policy** (three forms): `"allow-all"` (default) · `"deny-all"` · `{ allow: ["*.github.com"], subnets: { deny: [...] } }`. Set on the backend (pre-bootstrap), in `onSession`'s `use()`, or mid-turn via `sandbox.setNetworkPolicy(...)`.
- **Credential brokering:** secrets **never enter the sandbox** — a per-domain `transform` injects an auth header at the firewall (supported by `vercel()`/`microsandbox()`), so egress authenticates while the secret stays out of the sandbox process.
- The default sandbox is **not** a substitute for configuring network policy, credentials, retention, or deletion (see Responsible use).

## Execution model & durability

Three nested levels: **session** (durable, days/weeks) → **turn** (one user message + all work until the reply) → **step** (a durable checkpoint: one model call + its tool calls). **Every turn is a durable workflow on the Workflow SDK**; state serializes at each step boundary. On crash/redeploy, the run resumes from the **last completed step** — completed steps never re-run (recorded result replayed), but a **step interrupted mid-execution re-runs** → non-idempotent side effects (charge, email, external write) **must be made idempotent or approval-gated**. Work **parks** (holds no compute) while awaiting approval, OAuth, input, or a subagent, and resumes exactly where it paused. Nothing to configure — sessions are durable by default; history is append-only, turns land in order.

## Sessions, runs & streaming (HTTP contract)

**One handle: the `sessionId`.** ⚠️ 0.31.0 replaced the continuation-token model with fixed, ID-addressed handles — there is no token to keep current and none to go stale. Lifecycle:
- `POST /eve/v1/session` (message) → `sessionId`, in the body **and** the `x-eve-session-id` header.
- `GET /eve/v1/session/<id>/stream` → **NDJSON** event stream; reconnect from any point with `startIndex` (negative reads from the tail, `-1` = latest).
- `POST /eve/v1/session/<id>` (message) → continue.
- `POST /eve/v1/session/<id>/{clear,compact,reset}` → session control.
- `GET /eve/v1/health` — public health route.

Accepted async work returns **202**; a follow-up on an inactive session returns **409** with `code: "session_not_active"`. **"Continuation" survives in one place only** — a *custom channel* still owns a channel-local continuation **address** (`from(address)`, `channel.continuation?.rekey(rawToken)`); the framework derives nothing for you there. That is a channel address, not a client session cursor: don't conflate the two.

Event types: lifecycle (`session.started`, `turn.started/completed`, `session.waiting`), content (`message.received/appended/completed`, `reasoning.appended` — incremental), processing (`step.started/completed`, `actions.requested`, `action.result`), control (`turn.cancelled/failed`, `input.requested`), delegation (`subagent.called/completed`). The web app never hand-rolls this — `withEve()` + `useEveAgent()` own it (see `eve-web-integration.md`).

## Human-in-the-loop (HITL)

Two ways to durably pause for a person: **approvals** (tool sign-off — `never()`/`once()`/`always()` or a custom policy `({ session, toolName, toolInput, approvedTools, callId }) => "approved" | "user-approval" | "denied" | "not-applicable"`, from `eve/tools/approval`) and **questions** (built-in `ask_question` with `prompt`/`options`/`allowFreeform`). Both emit `input.requested`, park the turn at `session.waiting` durably (seconds or days), and resume when the client answers via **`respond(inputResponses, …)`** keyed by `requestId` — since 0.31.0 a **separate call** from `send`, and mutually exclusive with it (for approvals a plain follow-up message like "approve" also works). For approvals, unrelated follow-up text doesn't deny — eve holds it and replays it after the approval resolves.

## Session state — `defineState` (short-term, session-scoped)

```ts
import { defineState } from "eve/context";
const budget = defineState("my-agent.budget", () => ({ count: 0, cap: 25 }));
// in a tool/hook: budget.get(); budget.update(s => ({ ...s, count: s.count + 1 }));
```

Durable **per-session** working memory (survives turns/crashes/redeploys), `get()` / `update(fn)`, throws outside tools/hooks. **Lives and dies with the session; never crosses the parent/child subagent boundary.** For anything that must outlive the session, be shared across users, or be independently queryable → external storage (see the tenant-scoped memory recipe in `eve-patterns.md` §3). **Never** use `defineState` for long-term memory.

## Dynamic capabilities — `defineDynamic`

Resolve **model, tools, skills, and instructions** at runtime from a session event instead of declaring them up front. Events + precedence: `step.started` overrides `turn.started` overrides `session.started` overrides the static default. Use it when the right capability depends on **who's calling** (tenant, team, plan, feature flags, external data): per-tenant tools built at `session.started`, feature-flagged tools, per-team playbooks/skills, or resolving the model at `session.started` to keep prompt caches warm. **Rule:** a dynamic tool's `execute` must be an **inline** function (expression/arrow/method-shorthand) placed directly as the property value, so it survives workflow replay across steps.

## Dynamic workflows — `experimental_workflow` (model-orchestrated subagents)

Let the **model write JavaScript** that coordinates the agent's own subagents as **one durable step** — programmatic fan-out where the program decides how many subagents to run, which output feeds which call, and how to combine results.

```ts
import { experimental_workflow } from "eve/tools/workflow";   // 0.45.0: era eve/tools
export default experimental_workflow({ maxSubagents: 4 });   // WORKFLOW_SUBAGENT_LIMIT_REACHED past the budget
```

It's a **coordination layer only** — no filesystem/network/shell, only calls to the built-in `agent`, declared subagents, and remote agents. The whole orchestration is one step, so it resumes after a restart even if a child is long-running or human-gated.

### The general form: model-written code, and what makes it safe

`experimental_workflow` is eve's narrow version of a broader idea — **let the model write a program instead of emitting one tool call at a time**. The general mechanism is [`run`](https://github.com/vercel-labs/run) (`run@2.0.1`, *"secure QuickJS-backed JavaScript runtime with host functions and continuations"*), which is also what powers **code-mode tool execution in the AI SDK**. Worth understanding even if you only ever use eve's version, because it names the three properties that make model-written code safe at all:

- **Isolation is in-process, not OS-level.** The code runs in a QuickJS context inside a worker thread — `eval` with the plug pulled, not a VM. Cheap enough to run per tool call; **not** a substitute for Vercel Sandbox when you need OS-level isolation, and the blog says so itself.
- **`hostFunctions` is the entire egress surface.** The sandboxed program can reach exactly what you hand it and nothing else — no ambient secrets, no internal services, no `fetch` you didn't pass in. This is #6's read-vs-egress boundary expressed as a *mechanism* rather than a policy: not "the agent shouldn't call that", but "there is nothing to call".
- **A host function can interrupt, and resumption replays.** Settled host-function calls return their **recorded** results when the program resumes, so a pause for human approval mid-program is durable rather than a re-run. Same replay contract as eve's own step boundaries — which is why `experimental_workflow` can be one durable step at all.

Config is `run({ source, hostFunctions, limits: { timeoutMs, memoryLimitBytes } })`, or `createRunner()` for a shared budget. Node 22.13+ / Bun. `[VERIFY]` before wiring it directly into an eve agent — eve exposes the workflow tool, not `run`, and whether you should reach past it is a design decision, not a default.

## Responsible use (deployer obligations — do this before production)

eve's defaults are **permissive** (unsupervised tools, unrestricted egress). As the deployer you must configure: **approval policies, tool restrictions, connection scopes, route/session authorization, sandbox controls, telemetry exports**, and ensure legal compliance. Before shipping with sensitive data, review the full action surface (default/custom/MCP tools, shell/file/web tools, connected services, subagents, schedules, external actions). **Require human approval** for sensitive/irreversible/regulated/financial/healthcare/employment/housing/legal/safety- or user-impacting/external-side-effecting actions. **Never rely on model behavior alone** to prevent them.
