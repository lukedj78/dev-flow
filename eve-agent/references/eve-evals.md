# eve evals — the full reference

An eval is a **scored check that runs the agent against a real session and grades the result** — it boots a real agent server, drives sessions through the TypeScript client over the actual HTTP surface, and asserts on outcomes. It's the deploy gate. Live docs: <https://eve.dev/docs/evals/…>. Last verified end-to-end against **`eve@0.47.6`** (2026-09-01): `defineEval`, `defineEvalConfig`, `mockModel` and all five `eve/evals/expect` matchers exist as written, and `t.transcript` was added in 0.47.0. Re-`[VERIFY]` on upgrade against `node_modules/eve/docs/` — the eval API is young.

## Layout & config

```
my-agent/
├─ agent/
├─ evals/
│  ├─ evals.config.ts              # required, exactly one, at evals/ root
│  ├─ smoke.eval.ts                # id = "smoke"
│  └─ weather/brooklyn.eval.ts     # id = "weather/brooklyn"  (path IS the id)
└─ package.json
```

`evals/` is a **sibling of `agent/`**, never inside it. Each `*.eval.ts` is auto-discovered; sibling non-eval files hold shared helpers.

```ts
// evals/evals.config.ts — declares shared defaults (judge model, reporters, concurrency, timeouts)
import { defineEvalConfig } from "eve/evals";
export default defineEvalConfig({});
```

**Shared resources: `setup` / `teardown`** (0.64). `setup` runs **once per `eve eval` invocation**, after
discovery and before the target starts — the place to start a test database or run migrations. What it
returns becomes `t.context`, typed by passing the config's type to `defineEval`:

```ts
// evals/evals.config.ts
export default defineEvalConfig({
  async setup() { return { database: await startTestDatabase() }; },
  async teardown(context) { await context?.database.close(); },   // `undefined` when setup returned nothing or threw
});

// evals/database.eval.ts
import type config from "./evals.config.js";
export default defineEval<typeof config>({
  async test(t) { await t.require((await t.context.database.query("SELECT 1 AS value")).rows[0]?.value, equals(1)); },
});
```

The context object is **shared in the runner process, never serialized and never sent to the agent
server** — class instances and functions keep their identity, and **concurrent evals share it**, so
isolate any rows they modify. `teardown` runs after the local server and its sandbox handles shut down,
including after a failed setup or startup, and a cleanup failure fails the command. The per-eval
`timeoutMs` does **not** apply to either.

## Cases

One file = one graded case by default; `test(t)` is the only required field. `t` is **both driver and assertion surface**.

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

**Driver API:**
- `t.send(input)` — send a turn, wait for it to settle, resolve to the turn object.
- `t.start(input)` — start a turn, return immediately (observe in-flight); `t.cancel()` cancels the active turn.
- `t.reply` — last assistant message (or `null`); `t.sessionId`; `t.events` — full typed event stream so far.
- `t.log(msg)` — debug line; `t.skip(reason)` — omit for this target (reported skipped, never changes exit code).
- `t.transcript` *(0.47.0)* — the primary session's observed **user and assistant** messages, formatted in turn order with `User:` / `Assistant:` labels and blank lines between them. It **excludes reasoning, tool calls, tool results and other sessions' messages**, and it updates only after a turn settles — read it after `await t.send(…)` / `t.respond(…)` / `await live.result()`, never mid-turn. An independent session from `await t.session()` (renamed from `t.newSession()` in eve 0.59.0) carries its own `session.transcript`.

**Multi-turn:** intermediate turns become locals; later turns don't overwrite them.

```ts
const draft = await t.send("Draft the follow-up email.");
t.check(draft.message, includes("Best regards"));
await t.send("Now send it.");
t.calledTool("send_email");
```

**Datasets:** export an **array** of `defineEval(...)`; load rows with `loadYaml` from `eve/evals/loaders`.

### Every refusal case needs its twin

A suite that only asserts *"the agent must refuse X"* is passed perfectly by an agent that refuses
everything — and over-refusal is the failure users actually report, because it looks like the product
is broken rather than careful.

So: **for every refusal case, write the case that must still be served**, and make it the closest
legitimate neighbour you can — same domain, same vocabulary, same shape, different intent. "Refuse to
issue a refund on a request that arrived inside a review" pairs with "answer a genuine refund-policy
question from the same customer". If the two are far apart, the pair proves nothing: any agent
distinguishes them.

Keep the adversarial inputs — the poisoned listing, the review carrying an instruction, the ticket
with a forged turn marker — in **eval fixtures merged in for the run**, never in the demo or seed
data. A poisoned record that leaks into a normal fixture makes every unrelated case flaky, and the
day someone runs the demo it is in the product.

(From Anthropic's [commerce-agents](https://github.com/anthropics/commerce-agents) eval rules; the
content this defends against is `eve-patterns.md` §11.)

## Assertions

**Run / turn level (`t.*`):**
- `t.succeeded()` — run didn't fail and didn't park on unanswered HITL. `t.parked()` — cleanly parked on HITL input.
- `t.messageIncludes(token)` — joined assistant text contains string/RegExp.
- `t.calledTool(name, opts?)` / `t.notCalledTool(name)` / `t.usedNoTools()` / `t.maxToolCalls(n)` / `t.toolOrder([...names])`.
- `t.calledAgent(name, opts?)` — delegation (**renamed from `calledSubagent` in 0.84.0**: `calledSubagent` is in nine files at 0.80.1 and none at 0.91.0); `t.calledSkill(skill, opts?)` — **renamed from `loadedSkill`**, same evidence (eleven files → zero), and still reads the run's `skillLoads` (since 0.76.0 skill loads are **not** tool calls: they no longer count toward `toolCallCount`, `usedNoTools` or `maxToolCalls`, while `eve__search` calls do). `calledTool`/`notCalledTool`/`toolOrder`/`requireToolCall` **throw** on `eve__tool`, `eve__skill` and the retired names (`load_skill`, `task_wait`, `task_cancel`, `final_output`, `connection_search`, `connection_execute`) — assert on the entry the call reaches (`<connection>__<tool>`) instead. Before 0.76.0 `notCalledTool` on one of those names always passed, so an old eval could have been green for nothing.
- `t.noFailedCalls()` — no tool/agent/skill failure. **Renamed from `noFailedActions` in 0.84.0** (seven files → zero), part of the same wave that moved `calledSubagent` → `calledAgent` and `loadedSkill` → `calledSkill`: the vocabulary went from *actions* to *calls* across the eval surface, so an eval written before 0.84 fails to compile rather than silently passing — which is the good outcome.
- `t.event(type, opts?)` / `t.notEvent(type, opts?)` / `t.eventOrder([...matchers])` / `t.eventsSatisfy(label, predicate)` — event-stream escape hatches.
- `turn.outputEquals(value)` / `turn.outputMatches(schema)` — structured output.
- Preconditions: `await t.require(value, matcher)` (records a gate, returns the value on pass), `turn.requireToolCall(name)`, `session.requireInputRequest({ toolName })`.

**Matchers for `t.check` / `t.require`** (from `eve/evals/expect`):
`includes(v)` · `equals(v)` (deep) · `matches(schema)` (Standard Schema) — all **gate by default**; `similarity(expected)` (normalized Levenshtein, 1=identical) — **soft**; `satisfies(fn, label)` — custom predicate (gate).

**Matcher mini-language** for `calledTool`/`calledAgent`: a literal (partial-deep-match), a RegExp, or a predicate; props `input`/`output`/`status`/`count` (agents also `callId`/`childSessionId`). ⚠️ **`remoteUrl` is gone** — at 0.91.0 the only occurrences left in the package are inside a vendored third-party SDK, none on eve's own eval surface, so an assertion carrying it does not fail loudly, it simply never matches what it meant to.

**New matchers at 0.91.0 worth knowing, none of which existed at 0.80.1**: `t.waitForToolCall(name)` and `t.awaitingInput()` (assert on a turn *parked* rather than finished — the shape every HITL agent needs and the reason these assertions used to be written as sleeps), `t.requireInteraction(...)`, `t.noFailedCalls()`, `t.dispatchSchedule(...)`, `t.compact()` / `t.nextTurn()` / `t.startRespond(...)` / `t.respondAll(...)` / `t.sendFile(...)`. Read them off `dist/src/evals/types.d.ts`, which lists the whole surface in one place.

**Severity (chain on any assertion):**
- `.gate(threshold?)` — hard; a miss marks the eval `failed` and `eve eval` exits non-zero.
- `.soft(threshold?)` / `.atLeast(threshold)` — tracked; a below-threshold miss marks the eval `scored` (only blocks under `--strict`).
- **`t.score(evaluation)`** (0.79.0) records a 0–1 score you computed yourself — name it with `.label(key)`, gate it with `.gate()` / `.atLeast()`. `eve eval` warns when two soft assertions in one eval share a name with different scores.

## LLM judge

⚠️ **`t.judge.autoevals.*` was removed in eve 0.62.0.** The `factuality`/`summarizes`/`closedQA`/`sql` graders and
the `autoevals` namespace are gone; `t.judge(...)` is now called directly, calls `decide` from `eve/ai` (`evaluate` until 0.72.0; it takes an `Experimental_DecisionModel` such as `provider.decisionModel(...)`) under
the hood, and defaults to `typesafe-ai/jev` (`docs/evals/judge.mdx`).

Soft by default (tracked, never fails unless gated). `t.judge` accepts a criteria string (becomes a `boolean`
question), one typed question (`boolean` / `score` / `choice`), or a batch of named questions:

```ts
t.judge("The response uses no math beyond arithmetic.").atLeast(0.8);

t.judge({
  type: "score",
  instructions: "Grade the response's clarity.",
  criteria: ["Unclear", "Mostly clear", "Clear and concise"],
}).label("clarity").atLeast(0.75);
```

| Question | Assertion score |
|---|---|
| Criteria string or `boolean` | the returned probability of true, 0–1 |
| `score` | the returned rubric position divided by the highest level index |
| `choice` | 1 when the selected option equals `expected`; otherwise 0 |

By default the judge grades `{ input, output }` — the latest prompt and reply of the session whose turn most
recently settled. Pass `{ on: value }` to grade another output (e.g. `session.transcript` for a multi-turn case —
grading the default output on a multi-turn case scores only the last message). A **batch** call takes `state`
instead of `on`, replacing the default entirely:

```ts
const judgments = t.judge({
  state: { response: turn.message ?? "", reference },
  questions: {
    accurate: { type: "boolean", instructions: "Is the response consistent with the reference?" },
    outcome: { type: "choice", instructions: "Classify the response.", criteria: { answered: "…", declined: "…" }, expected: "answered" },
  },
});
```

Choice questions require an `expected` option key, used locally for scoring and never sent to the evaluator. Gate/soften with `.gate(t)` / `.atLeast(t)`; a boolean probability rarely reaches exactly 1 even for a good response, so give it an explicit gate rather than relying on the default.

**Judge model** resolves innermost-wins: per-call `{ model, modelOptions }` → per-eval `defineEval({ judge: {…} })` → project `defineEvalConfig({ judge: {…} })`. It is resolved once when `t` is built and is **never** the model under test.

## Targets

A target is always an **HTTP URL**. `eve eval` boots a local dev server automatically; `eve eval --url <url>` runs against a deployment — the same files work as CI/CD end-to-end tests. Inside a case, `t.target` gives:
- `t.target.fetch(path, init)` — authenticated request for channel/webhook ingress.
- `t.target.dispatchSchedule(id)` — trigger a schedule (dev-mode only).
- `t.target.attachSession(sessionId)` — consume an externally-created session for assertions.

**Remote auth:** eve uses Vercel OIDC/trusted-IDP when `VERCEL_ORG_ID`/`VERCEL_PROJECT_ID` (or `.vercel/project.json`) match; also `VERCEL_AUTOMATION_BYPASS_SECRET` (protection bypass) or `EVE_EVAL_AUTH_TOKEN` for non-Vercel targets.

## Deterministic fixtures — `mockModel` (and the trap in it)

`mockModel` from `eve/evals` replaces the provider entirely, so an eval can exercise eve's runtime —
the tool loop, HITL parking, channel ingress — **without a model call**. That is what makes a
runtime-shaped eval cheap enough to run on every push, and non-flaky enough to gate on.

```ts title="agent/agent.ts"
import { mockModel } from "eve/evals";
export default defineAgent({ model: mockModel("A deterministic reply") });
```

A callback form gets an eve-owned view of the prompt (`lastUserMessage`, `userMessages`,
`userMessageCount`, `tools`, `toolResults`) and may return `{ text, toolCalls, usage }` — which is
how you script a deterministic **tool loop**: return a `toolCalls` entry while `toolResults` is
empty, return text once it isn't. The options form (`{ modelId, provider, respond }`) exists only
when a fixture also needs a model identity. With no argument at all it answers `"Mock response"`.

⚠️ **`mockModel` lives in the agent definition, not in the eval.** So it belongs to a *dedicated
fixture agent* — and it **stays mocked when that agent is deployed as an eval target**. Reach for it
on an agent you built to be a fixture; put it in the real agent's `agent.ts` and the mock is what
ships. The behaviour you actually want to gate on still needs a real model somewhere.

## Tool stubs — fix what a tool returns, without deploying a mock

`mockModel` above replaces the **model**. Tool stubs replace what a **tool returns**, and they are the
other half of a deterministic eval: `mockModel` makes the agent's decisions predictable, stubs make the
world it decides against predictable. They work *"against local and deployed agents, with no mock code to
deploy"* — so unlike `mockModel`, nothing fixture-shaped ships in the agent.

```ts
const session = await t.session({
  stubs: [
    { id: "milk", tool: "complete_task",
      match: { task_id: { const: "milk" } },
      outcome: { response: { success: true } } },
    { id: "other", tool: "complete_task", outcome: { response: { success: false } } },
  ],
});
```

A rule is `{ id, tool, match?, outcome | outcomes }`. `id` is a name unique in the session that tracks
the rule's place in its sequence (traces never show it); `tool` is an **existing** tool's name;
`match` is a JSON-Schema-subset constraint on the input, and omitting it matches any valid input.
`outcome` repeats forever, `outcomes` is a non-empty array consumed in order whose **last entry then
repeats** — use exactly one of the two. Each outcome holds exactly one of `response` (the JSON the tool
returns) or `throw`. Stubs are plain JSON, so they live in a fixture file typed
`satisfies readonly ToolStub[]` and are shared across evals; `ToolStub` and `ToolStubOutcome` are
exported from **both** `eve/evals` and `eve/client`, and they check the JSON's shape without inferring
your tool's response type.

**Four behaviours decide whether an eval means anything.** All four are easy to get backwards:

1. **First match wins, top to bottom.** Put the specific rule before the unconditional fallback. Written
   the other way round, the fallback answers everything and the specific rule never fires — and nothing
   errors.
2. **No rule matches → eve runs the real tool.** The default is not "fail" and not "return nothing". A
   typo in `tool` therefore produces a *passing* eval that silently exercised production behaviour. eve
   warns after the run about rules that matched no calls, and **does not fail the eval for it**, so read
   the warning. When a call must happen, assert it: `turn.calledTool(name, { count: 1 })`.
3. **The sequence is not a database.** `outcomes` returns entry two on the second matching call whether or
   not anything else happened in between. An eval that stubs a read *and* a write is asserting that the
   agent asked for the write, never that the write took effect. To test a real update, use the real tool.
4. **A broken stub fails the eval even when the agent recovers** — as does a failure while processing its
   response, and neither falls back to the real tool. A deliberate `throw` is the opposite: an ordinary
   tool failure the eval can assert on.

⚠️ **Stubs are refused by default, including in development, and the grant is a deployment decision.**
The target must permit tool replacement for the eval's caller: with Vercel OIDC that means `eveVercelOidc`
(not `vercelOidc` — see `eve-conventions.md`) with `allowToolStubs: true` on the runner's `vercelSubject`.
Only the target's **server configuration** grants it, after token verification: a request cannot grant it
and a user never inherits a project's grant. The symptom when it is missing is a `403` with
*"Tool stubbing is not permitted for this caller."*

🔴 **And the grant has a scope we must not repeat as "the eval runner can stub":** eve checks the
permission **only when it creates the session**. Afterwards the session is an ordinary session, so
**anyone the channel admits to it can use its stubs** — i.e. anyone who can reach a stubbed session can
make its tools return whatever those rules say. eve's own guidance is to isolate such sessions with the
session-access policy, or to run evals against **a separate deployment of the same agent code**. For a
multi-tenant product the second is the honest answer: the grant is deployment-wide in effect, not
caller-wide.

**Injecting errors.** `throw` takes a required `message` and an optional `name` (default `"Error"`), and
eve raises a plain `Error`. `name: "TimeoutError"` fails the call immediately instead of waiting for a
deadline. Ordinary tools and connection operations show the model only the message, so put what the model
needs **in `message`**; workflow task errors keep the name. `{ response: { error: "timeout" } }` is just
JSON — only `throw` raises. Note `noFailedCalls()` fails on an injected error, which is correct and often
surprising: assert the failure explicitly instead, with `calledTool(name, { status: "failed" })`.

**Subagents and connections.** Prefix with the subagent path to replace only that subagent's tool —
`researcher/list_tasks`, `researcher/assistant/list_tasks`, and `agent/list_tasks` for the built-in
`agent` — while a bare `researcher` replaces the whole subagent and a **root rule never matches a
subagent's tool of the same name**. Persistent tools implemented with `serve`, the built-in `agent`
among them, require an **unconditional** stub (no `match`, or `{}`), and real and stubbed calls to the
same persistent tool cannot be mixed. Connections use the qualified name (`linear__list_issues`), and
⚠️ **a stubbed connection must still be reachable**, because eve lists its tools to validate the
operation and its arguments — a stub does not take the connection offline. A call routed through
`eve__tool` matches by the name and input of the tool it *reaches*; `eve__search`, `eve__tool` and
`eve__skill` cannot be stubbed, and neither can provider-hosted tools such as the provider's own web
search (your own search tool can).

**Limits, since hitting one fails setup rather than degrading:** 100 rules, 20,000 JSON nodes, nesting
depth 32, about one million characters, and **10,000 tool calls per session** (split the eval when you
reach it). `__proto__` is a reserved property name. Unsupported JSON Schema — `patternProperties`,
`$ref`, formats, `multipleOf`, `minContains`/`maxContains`, `uniqueItems`, dependencies, and object or
array values in `const`/`enum` — fails setup too, as do unknown tool names, invalid subagent paths and
paths into remote agents. Remote agents receive no rules at all: replace the whole remote agent tool.

## Reporters

- **Console** (default) — one line per eval, failed assertions shown.
- **JUnit** — XML for CI annotations. Prefer the CLI flag so the pipeline owns the path: `eve eval --junit .eve/junit.xml`.
- **Braintrust** — uploads to experiments (needs the `braintrust` package + `BRAINTRUST_API_KEY`). Configure in `defineEvalConfig({ reporters: [Braintrust({ projectName })] })` or per-eval. Gate assertions log as `gate:`-prefixed binary scores for diffing.

Disable configured reporters with `--skip-report`. Custom reporters implement `onRunStart` / `onEvalComplete` / `onRunComplete`. ⚠️ **Since 0.79.0 `AssertionResult.score`, `threshold` and `passed` are optional** (`score` is absent when the scorer threw; `threshold`/`passed` when no rule applies) and a `key` was added — **a custom reporter must treat `passed === false` as the failure signal**, never `!passed`, or every ungated assertion reads as a failure. Labeled assertions now report to Braintrust and Datadog under the bare label (`grounding`, not `score [grounding]`), so labeled metrics start a new series after the upgrade.

## Running

`eve eval` discovers every `*.eval.ts`, boots (or targets) a server, runs concurrently, prints a per-eval summary.

| Flag | Effect |
|---|---|
| `eve eval weather smoke` | run selected evals by id / directory prefix |
| `--url https://<app>` | target a remote deployment |
| `--tag fast` | filter to tagged evals |
| `--timeout 60000` | per-eval timeout (ms) |
| `--max-concurrency 4` | cap concurrency (default 8) |
| `--strict` | soft threshold misses block the exit code |
| `--junit <path>` | JUnit XML output |
| `--json` | machine-readable output |
| `--verbose` | stream per-eval logs |
| `--list` | print discovered evals without running |
| `--skip-report` | disable configured reporters |

**Exit codes:** `0` pass · `1` failures/execution errors · `2` config problems. `t.skip` → skipped, never changes the code.

**CI gate (the one to wire in `turbo.json`):**

```bash
eve eval --strict --junit .eve/junit.xml
```

This blocks a merge on score regressions and emits per-eval CI annotations — the deploy gate for every dev-flow eve agent.
