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
- `t.transcript` *(0.47.0)* — the primary session's observed **user and assistant** messages, formatted in turn order with `User:` / `Assistant:` labels and blank lines between them. It **excludes reasoning, tool calls, tool results and other sessions' messages**, and it updates only after a turn settles — read it after `await t.send(…)` / `t.respond(…)` / `await live.result()`, never mid-turn. An independent session from `t.newSession()` carries its own `session.transcript`.

**Multi-turn:** intermediate turns become locals; later turns don't overwrite them.

```ts
const draft = await t.send("Draft the follow-up email.");
t.check(draft.message, includes("Best regards"));
await t.send("Now send it.");
t.calledTool("send_email");
```

**Datasets:** export an **array** of `defineEval(...)`; load rows with `loadYaml` from `eve/evals/loaders`.

## Assertions

**Run / turn level (`t.*`):**
- `t.succeeded()` — run didn't fail and didn't park on unanswered HITL. `t.parked()` — cleanly parked on HITL input.
- `t.messageIncludes(token)` — joined assistant text contains string/RegExp.
- `t.calledTool(name, opts?)` / `t.notCalledTool(name)` / `t.usedNoTools()` / `t.maxToolCalls(n)` / `t.toolOrder([...names])`.
- `t.calledSubagent(name, opts?)` — delegation; `t.loadedSkill(skill, opts?)` — sugar for `calledTool("load_skill", { input: { skill } })`.
- `t.noFailedActions()` — no tool/subagent/skill failure.
- `t.event(type, opts?)` / `t.notEvent(type, opts?)` / `t.eventOrder([...matchers])` / `t.eventsSatisfy(label, predicate)` — event-stream escape hatches.
- `turn.outputEquals(value)` / `turn.outputMatches(schema)` — structured output.
- Preconditions: `await t.require(value, matcher)` (records a gate, returns the value on pass), `turn.requireToolCall(name)`, `session.requireInputRequest({ toolName })`.

**Matchers for `t.check` / `t.require`** (from `eve/evals/expect`):
`includes(v)` · `equals(v)` (deep) · `matches(schema)` (Standard Schema) — all **gate by default**; `similarity(expected)` (normalized Levenshtein, 1=identical) — **soft**; `satisfies(fn, label)` — custom predicate (gate).

**Matcher mini-language** for `calledTool`/`calledSubagent`: a literal (partial-deep-match), a RegExp, or a predicate; props `input`/`output`/`status`/`count` (subagents also `callId`/`childSessionId`/`remoteUrl`).

**Severity (chain on any assertion):**
- `.gate(threshold?)` — hard; a miss marks the eval `failed` and `eve eval` exits non-zero.
- `.soft(threshold?)` / `.atLeast(threshold)` — tracked; a below-threshold miss marks the eval `scored` (only blocks under `--strict`).

## LLM judge

Soft by default (tracked, never fails unless gated). Graders under `t.judge.autoevals`:

| Grader | What it scores |
|---|---|
| `factuality(expected)` | factual consistency vs an expected answer (A–E buckets) |
| `summarizes(expected)` | how well the reply summarizes the expected text |
| `closedQA(criteria)` | reply satisfies a free-form yes/no criterion |
| `sql(expected)` | semantic equivalence of two SQL statements |

Each scores `t.reply` by default; pass `{ on: value }` to grade another output. **To grade a whole conversation rather than the last reply, pass `{ on: t.transcript }`** — that is what it exists for; grading `t.reply` on a multi-turn case scores the last message and silently ignores everything that led to it. Gate/soften with `.gate(t)` / `.atLeast(t)`:

```ts
t.judge.autoevals.closedQA("cites a source").atLeast(0.6);
```

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

## Reporters

- **Console** (default) — one line per eval, failed assertions shown.
- **JUnit** — XML for CI annotations. Prefer the CLI flag so the pipeline owns the path: `eve eval --junit .eve/junit.xml`.
- **Braintrust** — uploads to experiments (needs the `braintrust` package + `BRAINTRUST_API_KEY`). Configure in `defineEvalConfig({ reporters: [Braintrust({ projectName })] })` or per-eval. Gate assertions log as `gate:`-prefixed binary scores for diffing.

Disable configured reporters with `--skip-report`. Custom reporters implement `onRunStart` / `onEvalComplete` / `onRunComplete`.

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
