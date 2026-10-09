# eve concepts — config, context, durability, HITL, dynamic capabilities

The cross-cutting concepts behind every capability. This complements `eve-conventions.md` (rules) and `eve-capabilities.md` (per-file how-to). Live docs: <https://eve.dev/docs/concepts/…>, `/docs/agent-config`, `/docs/instructions`, `/docs/human-in-the-loop`, `/docs/guides/{state,dynamic-capabilities,dynamic-workflows}`. **Read `node_modules/eve/docs/` first.** Last verified end-to-end against **`eve@0.47.6`** (2026-09-01), spot-checked against **`eve@0.63.0`** (2026-09-22) for the `auto`/`evaluate` rename, `t.judge`, and instrumentation changes below; treat every identifier as `[VERIFY]` again on upgrade.

## Agent config — `agent/agent.ts` (`defineAgent`)

Root-only. Fields:
- `model` — gateway id (this skill pins `"anthropic/claude-sonnet-5"`; **eve's own scaffold default is now `spacexai/grok-4.7`** — `DEFAULT_AGENT_MODEL_ID` read off `eve@0.64.0`'s `dist`, changed in 0.63.0 from the `openai/gpt-5.6-luna-fast` of 0.47.2, itself from the `zai/glm-5.2` of 0.36.0, and used for all three of `eve init`, a config-less agent, and the setup picker's pre-selection. **Three moves in twenty-seven minor versions**, so pin explicitly and never inherit it
  - **Or `auto()` — a model picked per turn by an evaluation model** (`import { auto } from "eve/models"`; renamed from `autoModel`/`eve/experimental/evaluate` in **eve 0.60.0** — the old import path is gone, not deprecated, as of eve@0.63.0. Depends on `ai@^7.0.105`; the bundled `docs/guides/evaluate.md` is the source). ⚠️ **Renamed again in 0.72.0, and this one has no alias.** The standalone question-asking function is **`decide` from `eve/ai`**: `eve/ai` exports no `evaluate` whatsoever — verified in 0.75.1's own `.d.ts` — so unlike the AI SDK, which keeps `@deprecated` aliases for the same rename, an import of `evaluate` **fails to resolve**. *Still experimental: its API can change between eve releases, and the AI SDK evaluation-model spec can change in patch releases* — pin eve and re-read the page on upgrade.
    ```ts
    import { defineAgent } from "eve";
    import { auto } from "eve/models";

    export default defineAgent({
      reasoning: "medium",
      model: auto({
        // model: typeSafeAi.decisionModel("jev-latest"),   // optional; default evaluator is "typesafe-ai/jev" via AI Gateway
        options: {
          "openai/gpt-5.6-sol": "Difficult reasoning and engineering tasks",   // key = Gateway id, value = description
          routine: { model: anthropic("sonnet-5"), description: "Routine work", reasoning: "low" },  // object form: provider instance / alias / reasoning override
        },
      }),
    });
    ```
    **Runtime, as documented:** it evaluates at the first `step.started` of a turn and reuses the choice for the tool-loop steps of that turn; a new turn chooses again and child sessions route from their own prompts. The evaluator sees **option keys, descriptions and up to eight recent user/assistant text messages capped at 16,000 characters** — never credentials or model instances. A request with no user text, or whose latest messages exceed the cap, **fails before provider I/O**. `reasoning` per option: `"provider-default"` · `"none"` · `"minimal"` · `"low"` · `"medium"` · `"high"` · `"xhigh"`; omitted inherits the agent's. Gateway auth is the ordinary AI SDK one (in `eve dev` the `/login` connection); the TUI footer shows `dynamic model`.
    **What this skill adds before you reach for it:** (1) it costs **one extra evaluation call per turn** and adds a model we never pinned — this skill's default stays a single pinned model; use `auto` when the agent genuinely spans cheap routine turns and hard ones. (2) **The evaluator is a processor**: recent conversation text goes to TypeSafe AI through the Gateway (or to whichever `Experimental_EvaluationModel` provider you pass) — under `stack.data_residency = "eu"`/`"eu-sovereign"` record it with `data_residency.py add` and check `dev-flow/references/eu-data-sovereignty.md` §4.10 before enabling; the Gateway's `zeroDataRetention` option applies to evaluation requests (Vercel changelog, 2026-09-16). (3) Every option must be a model the tools and instructions already work with — image support and tool-calling are not negotiated by the evaluator. (4) **Naming collision to watch**: `auto` also exists at `eve/tools/approval` for tool-approval decisions — a different function with a different signature; import from `eve/models` for model selection.
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
- **Opt in** — the framework tools that are *not* registered by default are one re-export each: `export { glob as default } from "eve/tools/glob"` (same for `grep`), `workflow()` from `eve/tools/workflow` (**lowercase since 0.64 — `experimental_workflow` and the uppercase `Workflow` framework tool were removed**), `sleep()` from `eve/tools/sleep`. **The filename is what names the tool**, not the export.
- **Disable** — `agent/tools/bash.ts` → `export default disableTool();` (from `eve/tools`).
- **Extend** — new tools with fresh slugs join the built-ins.

## Sandbox — the agent's isolated `/workspace`

Every agent has exactly one sandbox: an isolated bash filesystem rooted at `/workspace`, where `bash`/`read_file`/`write_file` (and the opt-in `glob`/`grep`) run and which custom code reaches via `ctx.getSandbox()`. It **never touches your app runtime** (authored tools keep full `process.env`; only sandbox-targeted tools run inside). Providers: **Vercel Sandbox** (hosted, snapshot-backed), **Docker** (local containers), **microsandbox** (local VM, Apple Silicon/Linux KVM), **just-bash** (pure-JS interpreter, no isolation — the cheap fallback), and `DefaultSandbox`, which picks Vercel on Vercel and otherwise tries Docker → microsandbox → just-bash.

⚠️ **Rewritten in 0.64 — the object form is gone.** *"Replace object-form sandbox definitions with exported provider environments whose `open()` method starts and returns the current eve session's persistent live sandbox"* (CHANGELOG 0.64.0, `49971b7`). A module now **exports an environment** and returns a sandbox from a `defineSandbox()` selector. The environment export is required because `eve build` prepares immutable inputs before any session exists.

```ts title="agent/sandbox.ts"   // shorthand; agent/sandbox/sandbox.ts (folder) wins
import { defineSandbox } from "eve/sandbox";
import { VercelSandbox } from "eve/sandbox/vercel";   // DefaultSandbox from eve/sandbox · DockerSandbox · MicrosandboxSandbox · JustBashSandbox

export const environment = VercelSandbox.environment({
  prepare: async (sandbox) => {                        // was `bootstrap` — runs once per environment generation, not per session
    const r = await sandbox.run({ command: "pnpm install --frozen-lockfile" });
    if (r.exitCode !== 0) throw new Error(r.stderr);   // run() does not throw on a nonzero exit
  },
});

export default defineSandbox(async ({ session }) => {  // was `onSession` — per durable session, after open()
  const sandbox = await environment.open({ networkPolicy: "deny-all", resources: { vcpus: 2 } });
  await sandbox.writeTextFile({ path: ".eve/session", content: session.id });
  return sandbox;
});
```

- **Old → new**: `defineSandbox({ backend, bootstrap, onSession, revalidationKey })` → `environment.open()` inside a `defineSandbox(selector)`; `backend: vercel()` → `VercelSandbox.environment()`; `defaultBackend()` → `DefaultSandbox.environment()`; `bootstrap` → the environment's `prepare`; `onSession` → code after `open()` in the selector; the generation is derived (sandbox source, preparation code, Dockerfile, environment options, workspace resources, skills), so **there is no `revalidationKey` to set**. Custom providers: `defineSandboxProvider()` from `eve/sandbox/provider`.
- **The selector runs until initialization succeeds, then never again**: eve checkpoints the provider and its state, and later steps and restarts call `resume()` directly. If initialization throws, eve deletes the newly started sandbox and retries on the next access. So post-`open()` code is *session* setup, not per-turn setup.
- **`prepare` builds an artifact, runtime never rebuilds it**: Vercel captures a snapshot, Docker an image, microsandbox a VM snapshot, just-bash a filesystem template. A missing artifact fails with rebuild/redeploy guidance instead of being repaired at runtime — which is why `eve build --skip-sandbox-prewarm` output is explicitly *not deployable*.
- **Seeding:** files under `agent/sandbox/workspace/` seed writable `/workspace` when eve prepares a new environment generation; existing live state is **not** overwritten by later seed changes. Skills are a separate read-only tree at `$HOME/.agents/skills`. Refer to those two paths only — `/eve/resources` is provider-internal staging.
- **Network policy** goes to `open()` (`"allow-all"` · `"deny-all"` · `{ allow: { "api.example.com": [...] } }`) and applies to the live sandbox, not the environment; Docker supports only the two coarse forms. `sandbox.setNetworkPolicy(...)` updates it afterwards (the Vercel environment returns a session where it is always available).
- **⚠️ Custom-provider handle hooks were renamed in 0.75.0**, because the old names said *session*
  about something that is a *sandbox*: **`onSessionStop()` → `onSandboxStop()`** and
  **`onSessionDelete()` → `onSandboxDelete()`** (verified in 0.75.1's `dist`). And 0.75.0 **adds
  `onSessionEnd()`**, which is genuinely about the session: eve calls it when a durable session
  completes, expires or fails, so a provider can release session-owned resources straight from
  persisted state. Only `defineSandboxProvider()` implementations are affected — a project that uses
  `VercelSandbox` / `DockerSandbox` / `JustBashSandbox` / `MicrosandboxSandbox` has nothing to change.
- **Lifecycle:** `sandbox.stop()` stops compute and keeps state; `sandbox.delete()` clears provider state so the next `ctx.getSandbox()` reruns the selector on a fresh sandbox (`ctx.reset()` retires the whole session instead).
- **Credential brokering:** secrets **never enter the sandbox** — a per-domain `transform` injects an auth header at the firewall, so egress authenticates while the secret stays out of the sandbox process.
- **Sharing:** a declared subagent can inherit its dispatching parent's sandbox with `defineParentSandbox()` — and then cannot declare its own workspace or skill files. Built-in environments do **not** share resources across sessions; a session-specific path is not an isolation boundary.
- The default sandbox is **not** a substitute for configuring network policy, credentials, retention, or deletion (see Responsible use).

## Execution model & durability

Three nested levels: **session** (durable, days/weeks) → **turn** (one user message + all work until the reply) → **step** (a durable checkpoint: one model call + its tool calls). **Every turn is a durable workflow on the Workflow SDK**; state serializes at each step boundary. On crash/redeploy, the run resumes from the **last completed step** — completed steps never re-run (recorded result replayed), but a **step interrupted mid-execution re-runs** → non-idempotent side effects (charge, email, external write) **must be made idempotent or approval-gated**. Work **parks** (holds no compute) while awaiting approval, OAuth, input, or a subagent, and resumes exactly where it paused. Nothing to configure — sessions are durable by default; history is append-only, turns land in order.

## Tasks — which entry point you export *is* the design decision (0.71)

Read against `node_modules/eve/docs/tools/tasks.md` on 2026-10-03. A **task** is a tool call that
returns a receipt at once and keeps working while the conversation continues; its result reaches the
model later as a `task.result` message. A workflow tool defines **exactly one** of three entry
points, and defining none or more than one **throws at definition time**:

| Body | Runs as | Result | A new message mid-call |
|---|---|---|---|
| `execute(input, ctx)` | tool call — **the turn waits** | the tool result | **aborts** `ctx.abortSignal` |
| `task(input, ctx)` | a task | a receipt, then `task.result` | nothing |
| `serve(receive, ctx)` | a **resumable** task | a receipt, then one `task.result` per reply | nothing |

**The question the three answer is not "is this slow?" — it is "should the conversation continue
while this works?"** That distinction is the whole section, because the instinct is wrong in a
specific way: **waiting does not need a task.** A question, a `sleep` or an approval inside an
`execute` body parks the turn *durably and holds no compute* — the same property §Execution model
describes — and a new message stops the wait. Reach for `task` when the model should keep talking
(a twenty-minute deploy, research it may not need yet), or when **a question must survive new
messages**: in an `execute` call the question lapses when the conversation moves on, resolving
`{ status: "cancelled" }`, which is what the built-in `ask_question` does and is usually right.

**Agents have no choice to make**: every agent tool is a `serve` tool, so every delegation is a
resumable task — only the model can tell from the conversation whether it needs the answer now. The
turn rule below is what keeps that safe.

**No turn ends while a task is working.** If the model stops talking with tasks outstanding, eve
parks the turn exactly as `task_wait` does, appends the results and calls the model again *in the
same turn*. `turn.waiting` marks each park (`on: "input"` when a person must act, else `"tasks"`); a
`step.started` with the same `turnId` means it resumed; `turn.completed` and `session.waiting` come
only when the turn really ends. **No result ever starts a turn on its own.** In a root session the
text before the wait completes as an ordinary message; in **child and schedule sessions the held
step reports `finishReason: "tool-calls"`**, which is how channels know to post only the final reply.
An idle resumable task isn't working and doesn't hold anything.

### What this changes in how we write the agent

- **An instruction is not an ordering guarantee.** "Publish only after the review approves" holds
  exactly as long as the model chooses to follow it, because the review is a task the model decides
  when to wait for. When an order *must* hold, it is a **single workflow tool** that calls
  `ctx.agent("reviewer")`, reads the result and only then acts — and **the side effect is not
  exposed as a tool of its own**, with `tool: false` on the subagent so the model cannot route round
  it. This is the same reasoning as `eve-patterns.md` §2 (gate every side effect) applied to
  sequencing rather than permission; it is written up as a pattern there.
- **Task output is budgeted: 50 KB and 2,000 lines shared by every result in one message**, then cut
  and marked `[truncated]`. A task that returns a document returns an **id**, not the document —
  which is already §7's handoff rule, now with a number behind it.
- **32 working tasks per session** (`TOO_MANY_TASKS`), idle resumable ones excluded. **No task
  timeout exists**: the only bound is `limits.sessionTimeoutMs`, 30 days by default, so a body that
  needs a deadline **races `sleep` against its own work**. A cancel gives the body **30 seconds** to
  unwind; a `serve` body that hasn't returned to `receive()` by then ends and the task finishes.
- **Instruct the model to use `task_wait` sparingly.** Results arrive without it; it exists for the
  case where the model deliberately withholds a message from the person while waiting. In child and
  schedule sessions the built-in prompt tells the model to wait rather than reply, because only the
  final reply reaches the caller.
- `task_cancel` stops one task's current work; `session.cancel()` cancels the turn, the `execute`
  calls it waits on and **every working task**. A steering message ends a `task_wait` and aborts the
  `abortSignal` of an awaited `execute` call, but **never interrupts a task** — the model reads the
  message and decides per task whether to keep, correct (call again with its `taskId`) or cancel.

### ⚠️ A task has no owner — a tenancy hole, of which 0.72.0 closed half

> **Update 2026-10-09 (eve 0.72.0).** Half of what follows was fixed upstream, and the half that
> remains is the half that matters to us. **Approvals without a `response` policy can now be
> approved or cancelled only by the principal whose turn requested the call** — so a shared thread
> no longer lets another person run a tool under the requester's turn, which is exactly the leak
> this section was written about. Calls from unauthenticated or anonymous callers are unchanged, and
> a tool that genuinely needs other approvers declares `approval.response`, which replaces the
> default. 0.75.0 extends the same reasoning to subagents: a subagent's approval stays open on the
> parent until the subagent settles it, and a typed `approve` answers it on text-only channels.
>
> **What is not fixed: reading and continuing.** The ownership check landed on *approvals*, not on
> the tasks themselves — eve still does not check which caller started a task, so the paragraphs
> below stand for `task_wait`, `task_cancel`, the `[Tasks]` note, and a continued `serve` task that
> keeps the state its body built for an earlier caller. Approving under someone else's turn is now
> refused; *resuming their work* is not.

**eve does not check which caller started a task.** Tasks belong to the session's open turn, not to
the caller that created them, so in a session several people share — **a Slack thread is the normal
case** — the model working for one person can read, continue or `task_cancel` a task another person
started. Worse for `serve`: a continued resumable task **keeps the state its body built for earlier
calls**, and the continuing call runs with *its own* caller's auth. Anonymous callers share one
identity.

So the rule from `eve-patterns.md` §1 applies inside the task body too: **key per-caller data on the
principal and enforce per-person access in the tool**, never on the assumption that whoever reaches
a task is whoever created it. A shared channel plus a `serve` tool that caches per-person state is
the concrete leak, and it is ours to close — eve states plainly that it does not.

## Sessions, runs & streaming (HTTP contract)

**One handle: the `sessionId`.** ⚠️ 0.31.0 replaced the continuation-token model with fixed, ID-addressed handles — there is no token to keep current and none to go stale. Lifecycle:
- `POST /eve/v1/session` (message) → `sessionId`, in the body **and** the `x-eve-session-id` header.
- `GET /eve/v1/session/<id>/stream` → **NDJSON** event stream; reconnect from any point with `startIndex` (negative reads from the tail, `-1` = latest).
- `POST /eve/v1/session/<id>` (message) → continue.
- `POST /eve/v1/session/<id>/{clear,compact,reset}` → session control.
- `GET /eve/v1/health` — public health route.

Accepted async work returns **202**; a follow-up on an inactive session returns **409** with `code: "session_not_active"`. **"Continuation" survives in one place only** — a *custom channel* still owns a channel-local continuation **address** (`from(address)`, `channel.continuation?.rekey(rawToken)`); the framework derives nothing for you there. That is a channel address, not a client session cursor: don't conflate the two.

Event types: lifecycle (`session.started`, `turn.started/completed`, `session.waiting`), content (`message.received/appended/completed`, `reasoning.appended` — incremental), processing (`step.started/completed`, `actions.requested`, `action.result`), control (`turn.cancelled/failed`, `input.requested`, `turn.waiting`), delegation (`task.started`, `task.settled`, `agent.started` — the `subagent.*` events were removed in 0.71). **A turn no longer ends while its tasks work**: a question or a sign-in from inside a running call emits `input.requested` then `turn.waiting` and resumes under the same `turnId`, so `turn.completed` and `session.waiting` now mean the turn really ended, and a client that closes a response on the first completed message shows the text written *before* the wait instead of the reply. The message stream version is **26** (the TypeScript client accepts 21–26). The web app never hand-rolls this — `withEve()` + `useEveAgent()` own it (see `eve-web-integration.md`).

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

Resolve **model, tools, skills, and instructions** at runtime from a session event instead of declaring them up front. Events + precedence: `step.started` overrides `turn.started` overrides `session.started` overrides the static default. Use it when the right capability depends on **who's calling** (tenant, team, plan, feature flags, external data): per-tenant tools built at `session.started`, feature-flagged tools, per-team playbooks/skills, or resolving the model at `session.started` to keep prompt caches warm. **Two rules, and the second is the one that bites.**

1. A dynamic tool's `execute` must be an **inline** function (expression/arrow/method-shorthand) placed directly as the property value, so it survives workflow replay across steps.

2. ⚠️ **Every value that executor closes over must be JSON-serializable.** Module-level *function* references are fine; a runtime closure is not, and neither is a class instance. The classic shape this rule forbids is also the most natural one to write:

   ```ts
   // ✗ every executor now captures `ctx`, a runtime arrow
   function shopTools(session: unknown) {
     const ctx = () => shopperContext(session as never);
     return { search: defineTool({ …, async execute({ q }) { return api.search(ctx(), q); } }) };
   }

   // ✓ the factory captures nothing; each executor reads its caller from the
   //   ToolContext eve already passes as the second argument
   function shopTools() {
     return { search: defineTool({ …, async execute({ q }, tool) {
       return api.search(shopperContext(tool.session), q);
     } }) };
   }
   ```

   `ToolContext` extends `SessionContext`, so `tool.session` carries `{ id, auth, turn, parent? }` — everything a per-caller context needs.

   **Why this rule is worth a paragraph: it fails silently and totally.** eve logs `Dynamic tool "<name>" callback "execute" has a non-serializable capture` and then *skips the complete resolver result* — not the one offending tool, all of them. The agent starts, answers, and behaves like an agent that was never given any tools: in the reference implementation it began guessing at `load_skill("shop")`, `load_skill("catalog")`, and finally told the shopper it had no way to search. Nothing throws, no request 500s, and the only evidence is one line in the dev server log. **When an eve agent behaves as though its tools do not exist, read the server log for this message before debugging the model.**

## Dynamic workflows — `workflow()` (model-orchestrated subagents)

Let the **model write JavaScript** that coordinates the agent's own subagents as **one durable step** — programmatic fan-out where the program decides how many subagents to run, which output feeds which call, and how to combine results.

```ts title="agent/tools/workflow.ts"
import { workflow } from "eve/tools/workflow";   // 0.45.0: was eve/tools · 0.64: lowercase factory
export default workflow({ maxSubagents: 20 });   // default 100, integer 1–128
```

⚠️ **Renamed in 0.60.0, and the old name is gone.** `experimental_workflow` and the uppercase `Workflow`
framework tool *"and its exports have been removed"* (CHANGELOG 0.60.0, `8bc931f`) — the replacement is the
lowercase `workflow()` factory from the same subpath, and the file name still gives the tool its model-facing
name (`tools/workflows.mdx`, re-read on `eve@0.64.0`, 2026-09-23). eve no longer discovers or injects an agent
catalog for it: the generated program resolves targets exactly like `ctx.agent` elsewhere.

It's a **coordination layer only** — the program's single host capability is
`ctx.agent(name, { message, taskId?, outputSchema? })`, with no workflow context, session state,
credentials, imports or ordinary tools, and it must return a JSON-serializable value. It **can** call
subagents that are hidden from the model (`tool: false`, or a same-named `disableTool()` file), so name
those in the tool description or the instructions when you want them used. The whole orchestration is one
step, so it resumes after a restart even if a child is long-running or human-gated. One scheduling rule
decides the shapes that work: the sandbox resumes only after **every pending call in the current batch
settles**, so `Promise.all` fan-out → fan-in is supported and **`Promise.race` does not resume on the
first child**. A child failure is thrown at its `ctx.agent` call, so generated code can catch it.

### The general form: model-written code, and what makes it safe

`workflow()` is eve's narrow version of a broader idea — **let the model write a program instead of emitting one tool call at a time**. The general mechanism is [`run`](https://github.com/vercel-labs/run) (`run@2.0.1`, *"secure QuickJS-backed JavaScript runtime with host functions and continuations"*), which is also what powers **code-mode tool execution in the AI SDK**. Worth understanding even if you only ever use eve's version, because it names the three properties that make model-written code safe at all:

- **Isolation is in-process, not OS-level.** The code runs in a QuickJS context inside a worker thread — `eval` with the plug pulled, not a VM. Cheap enough to run per tool call; **not** a substitute for Vercel Sandbox when you need OS-level isolation, and the blog says so itself.
- **`hostFunctions` is the entire egress surface.** The sandboxed program can reach exactly what you hand it and nothing else — no ambient secrets, no internal services, no `fetch` you didn't pass in. This is #6's read-vs-egress boundary expressed as a *mechanism* rather than a policy: not "the agent shouldn't call that", but "there is nothing to call".
- **A host function can interrupt, and resumption replays.** Settled host-function calls return their **recorded** results when the program resumes, so a pause for human approval mid-program is durable rather than a re-run. Same replay contract as eve's own step boundaries — which is why `workflow()` can be one durable step at all.

Config is `run({ source, hostFunctions, limits: { timeoutMs, memoryLimitBytes } })`, or `createRunner()` for a shared budget. Node 22.13+ / Bun. `[VERIFY]` before wiring it directly into an eve agent — eve exposes the workflow tool, not `run`, and whether you should reach past it is a design decision, not a default.

## Workflow tools — `defineWorkflowTool` (durable waits, not model-orchestrated fan-out)

Landed **0.48.0–0.52.0**; a different mechanism from `workflow()` above, and easy to conflate by name alone: `workflow()` (until 0.64, `experimental_workflow`) lets **the model** write the coordination code as one durable step; `defineWorkflowTool` lets **you** write an ordinary static tool whose executor is *itself* a durable Workflow run — for a tool that must wait on a person, a webhook, or a timer without holding compute, not for model-orchestrated multi-agent fan-out.

```ts title="agent/tools/deploy.ts"
import { defineWorkflowTool } from "eve/tools";
import { z } from "zod";

export default defineWorkflowTool({
  description: "Deploy a service to production. Pauses for a human to approve the plan.",
  inputSchema: z.object({ service: z.string() }),
  async execute({ service }, ctx) {
    "use workflow";                       // required, first statement, or the build fails
    const plan = await planDeploy(service);            // "use step" function — side effects go here
    const answer = await ctx.ask({ prompt: `Deploy ${service}?`, display: "confirmation",
      options: [{ id: "approve", label: "Deploy", style: "primary" }, { id: "cancel", label: "Cancel" }] });
    if (answer.optionId !== "approve") return { deployed: false, reason: "rejected" };
    return { deployed: true, url: await applyDeploy(plan) };
  },
});
```

- **`"use workflow"` must open the executor**, inline or as a top-level `async function` in the same module or an imported one — a missing directive is a build error. Side effects, the clock, randomness and `process.env` belong in a separate `"use step"` function; the workflow body itself is replayed and must stay deterministic.
- `ctx` inside the body is `WorkflowToolContext`, not the ordinary `ToolContext`: `session`, `callId`, `toolName`, `abortSignal`, plus the workflow-only `ask`, `agent` and (since 0.64) `agents`.
  - **`ctx.agent(name)` returns a session (0.71)**, it no longer returns the child's output: `const r = await ctx.agent("reviewer").send(plan, { signal: ctx.abortSignal }); const { message, status } = await r.result();` — and a `status === "failed"` has to be handled, because nothing throws for you. The argument is the **model-visible subagent name**, not a key; **eve assigns the replay-stable invocation identity itself**, including repeated and parallel calls; **`agentId` is removed** — each `ctx.agent(name)` call opens a *new* session and later `send`s on the same handle continue that conversation until the run finishes. The generated programs of the `workflow` tool keep the old `ctx.agent(name, { message, outputSchema? })` form.
  - **`ctx.ask(request)`** — ask the human on the session's channel (`prompt`, `display`, `options`); awaiting it suspends the run. It composes with `approval`, which gates the call *before* `execute` runs and can only show the model's input.
  - **`ctx.agents`** (0.60.1; the root copy target lands at `ctx.agents.agent` in 0.61.0) — the effective callable-agent descriptions, including subagents hidden from the parent model, for a body that decides where to delegate. Reading it **in a step throws** (0.61.1), with the same rule for `ctx.agent()`/`ctx.ask()`.
  - `getSandbox` is unavailable anywhere, and **`getSkill` no longer exists at all** (removed in 0.71 with `SkillHandle` and `SkillFile`). **`getToken`/`requireAuth` live on the step context**: a `"use step"` helper that takes `ctx` directly receives a restricted `WorkflowStepToolContext` (`session`, `callId`, `toolName`, `abortSignal`, `getToken`, `requireAuth`). Read `ctx.agents`, call `ctx.agent()` and `ctx.ask()` in the body; pass a step only the serializable values it needs.
- **`yield` reports progress, `await` suspends — and background mode publishes nothing.** A body may be an async generator. In **default** execution `yield value` emits an `action.partial` snapshot for the pending call (last-write-wins per tool-call id, never entering model history as an intermediate result). In **background** execution the value is *consumed without publishing progress or requesting a parent turn*: 0.63 removed background execution from `defineTool` and dynamic tools altogether, along with the `TaskExec` and `postMessage` authoring APIs, and delivers each cohort's completed/failed/cancelled outcomes in one automatic report. **`yield task.postMessage(...)` no longer exists** — do not write it. `return value` settles the call; with no return, the last yield becomes the output (or `null`). Prefer an explicit return when progress and result have different shapes.
- **`ctx.abortSignal` is durable** — it survives replay, aborts on a steered turn, `task_cancel` or the session ending, and a step that receives it observes the abort. Pass it into the steps that should stop and clean up in `try/finally`.
- **Two independent axes, and since 0.71 the second one is which function you export.** Durable suspension (`ctx.ask`, an awaited `createHook`/`createWebhook`, `sleep` — all from the vendored `workflow` package) is orthogonal to *how the call runs*, and `execution: "background"` is **gone**: you rename `execute` to **`task(input, ctx)`** and drop the option (the body is unchanged; `defineWorkflowTool` rejects `execution` with an error that says exactly this). `execute` is an ordinary tool call and the turn waits for its result; `task` runs as a task and its result arrives as a `task.result` message at a step boundary; **`serve(receive, ctx)`** is the third form, for work the model should be able to send more input to while it runs. One behaviour changed for *every* `execute` tool: **a steering message now aborts its `ctx.abortSignal`**, which is why `dismissible` was dropped from `ctx.ask` — a new message withdraws the open questions of the calls the turn waits on (a withdrawn question now resolves `{ status: "cancelled" }`, and the `input.resolved` outcome `"dismissed"` is now `"cancelled"`). A question that must survive new messages is asked from a `task`.
- Input must be a plain JSON object, and the tool must live under `agent/tools/` — a `defineDynamic` resolver cannot return a workflow tool.
- The workflow's identity derives from the executor's module path and function name; renaming or moving it starts a *new* workflow lineage, and a run resumed on a deployment that no longer has it fails naming the missing workflow.

This is the general form of the `deploy`/`refund_order`/`render_video` shapes `eve-patterns.md` and `eve-scaffold.md` describe by hand today with `approval` + a webhook route — `defineWorkflowTool` is now the first-party way to write that as one function instead of gluing a route handler to a resumed session. **It is also the *only* way**: durable background execution was removed from `defineTool` and dynamic tools in 0.63.0, so a `task`/`serve` body requires `defineWorkflowTool`. `[VERIFY]` against `node_modules/eve/docs/tools/workflows.mdx` before relying on a detail not repeated here — this section summarizes, it does not reproduce the full page (background/waiting semantics table, cancellation grace period, retry-and-idempotency notes).

## Responsible use (deployer obligations — do this before production)

### Remove the defaults you did not ask for — before the first run

eve gives **every** agent `bash`, `read_file`, `write_file`, `web_fetch`, `web_search`, `todo` and (in the root session) `agent`. Authoring your own tools **adds** to that set; `defineDynamic` adds to it too. Nothing in the scaffold narrows it, so a storefront assistant ships holding a shell unless you take it away.

This is not hypothetical. The reference implementation's shopping assistant, asked *"a waterproof shell for commuting, under 150"*, opened its first turn with `bash` running `env | grep`. It was reaching for the environment because it had no catalog tool (see the serialization trap above) — but it could only reach at all because the default was there.

So for any agent facing a user who is not the operator, write the sentinels **when you scaffold**, not when you harden:

```ts
// agent/tools/bash.ts — and read_file, write_file, web_fetch, web_search, agent
import { disableTool } from "eve/tools";
export default disableTool();
```

Keep the ones the product actually needs and say in the file *why* it is kept. The test is one line and belongs in the eval suite from the start: assert each sentinel file contains `disableTool()`, so a later `eve add` cannot quietly restore a shell.

eve's defaults are **permissive** (unsupervised tools, unrestricted egress). As the deployer you must configure: **approval policies, tool restrictions, connection scopes, route/session authorization, sandbox controls, telemetry exports**, and ensure legal compliance. Before shipping with sensitive data, review the full action surface (default/custom/MCP tools, shell/file/web tools, connected services, subagents, schedules, external actions). **Require human approval** for sensitive/irreversible/regulated/financial/healthcare/employment/housing/legal/safety- or user-impacting/external-side-effecting actions. **Never rely on model behavior alone** to prevent them.
