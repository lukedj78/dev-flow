# eve-scaffold — full scaffold procedure

Goal: a runnable eve agent at `apps/agent`, wired into the Turborepo/pnpm monorepo, exposing its HTTP API, with a baseline eval and a shared types package the web app re-exports.

**Reminder:** confirm every eve-specific command and path against `node_modules/eve/docs/` (live: <https://eve.dev/docs>) and `eve info` / `npx eve --help` before running. The steps below are the workflow; the exact flags belong to the installed eve version.

## eve CLI quick reference (verify against your version)

* `eve init [target]` — scaffold a new agent, or add one to an existing directory.
* `eve dev` — local dev server + terminal UI. `eve dev --no-ui` = headless/controllable background mode (use for verification). `eve dev <url>` — attach the UI to a remote deployment.
* `eve info` — print the resolved app: discovered tools, skills, subagents, schedules, channels, routes, artifact paths, discovery diagnostics.
* `eve build` — compile `.eve/` artifacts and the host output.
* `eve start` — serve the built output; prints the listening URL.
* `eve eval` — run evals against the local app or a remote target.
* `eve channels add web|slack` / `eve channels list` — scaffold / list channels.
* `eve link` — link to a Vercel project and pull AI Gateway credentials.
* `eve deploy` — deploy to Vercel production (links first if needed).

See `eve-conventions.md` for the import map, durability/idempotency, security model, and
deploy rules referenced throughout.

## 1. Preconditions

* **Node ≥ 24** and npm. A monorepo already exists (Turborepo + pnpm). If not, stop and ask the user to run the monorepo bootstrap first (`apps/` + `packages/` + `turbo.json` + `pnpm-workspace.yaml`).
* `apps/agent` does not yet contain an eve agent (otherwise switch to Capability mode).

## 2. Initialize eve inside apps/agent

* Read `node_modules/eve/docs/` for the current init flow, then run `npx eve@latest init apps/agent` (or `eve init .` from within `apps/agent`).
* Keep the default HTTP channel (`agent/channels/eve.ts`) — the web app consumes it. The Next.js app supplies the UI via `useEveAgent()`, so you do not need eve's own starter chat UI.
* Confirm the generated layout against the docs. Expect under `agent/`:
  * `agent.ts` — model & runtime config,
  * `instructions.md` — system prompt,
  * `tools/` — one file per tool, auto-registered by filename,
  * `channels/eve.ts` — the default HTTP channel + auth policy,
  * plus optional `skills/`, `connections/`, `schedules/`, `subagents/`, `hooks/`, `sandbox/`, `lib/`, `instrumentation.ts`,
  * and an `evals/` directory at the app root — a **sibling of `agent/`**, not inside it.

## 3. Pin the model and write instructions

* Set the model explicitly in `agent/agent.ts` rather than relying on an implicit default, so the choice is reviewable in Git. The eve scaffold default is `anthropic/claude-sonnet-5`, routed through the Vercel AI Gateway; keep it unless the user asked for something specific. Document the choice in a comment.
* **Service tiers (AI Gateway).** For an **OpenAI or Gemini** model you can trade latency/throughput/cost per request via `providerOptions: { gateway: { serviceTier: 'priority' | 'flex' | 'default' } }`: `priority` = faster at higher cost (interactive/voice paths), `flex` = cheaper at possibly higher latency (batch schedules / low-urgency subagents), `default` = baseline. It is **best-effort** — an unavailable tier silently falls back to `default` and only an *invalid* value fails the request — and the tier that actually served the request is echoed back in the provider metadata, so log it if you depend on it. At launch this covers **OpenAI and Gemini only**: with the default `anthropic/claude-sonnet-5` it is a **no-op**, so reach for it only when you've pinned an OpenAI/Gemini model. `[VERIFY]` that your installed eve version forwards `providerOptions` (from `agent/agent.ts` or per-generation) through to the Gateway before relying on this. Ref: <https://vercel.com/changelog/service-tiers-now-available-on-ai-gateway>.
* Write a real `agent/instructions.md` (system prompt) that states the agent's purpose and boundaries — the baseline eval will assert against it.

## 4. Set the channel auth (fail closed)

* The scaffolded `agent/channels/eve.ts` ships `placeholderAuth()`, which **rejects production traffic** so an unauthenticated app can't go live by accident. The auth fallback `[vercelOidc(), localDev()]` also does not admit browser users in production. To accept browser traffic, replace it with real auth (Clerk / Auth.js / OIDC-JWT / API keys / a custom `AuthFn`), typically wired via `agent/lib/auth.ts`, and put `tenantId` + identity attributes on the principal. Never hardcode secrets; use env vars. (`jwtHmac`/`httpBasic` were not confirmed as exports — verify any specific helper against the installed docs.)

## 5. Wire into the monorepo

* Add `apps/agent` to `pnpm-workspace.yaml` (if it uses an `apps/*` glob this is automatic).
* Add tasks to `turbo.json` so these run for the agent: `dev`, `build`, `lint`, `typecheck`, and an `eval` task that runs `eve eval`. `eve build` emits Nitro output under `.output/` and workflow state under `.workflow-data` — list both as the agent's Turbo `outputs` and add them to `.gitignore` (alongside `.eve/`).
* Make sure `pnpm install` at the root resolves the agent's deps.
* If `apps/web` fronts the agent (proxy/rewrites), forward **both** `/eve/` **and** `/.well-known/workflow/`.

## 6. Baseline eval

* Add at least one real eval case in `evals/` (sibling of `agent/`, file `*.eval.ts`) plus an `evals.config.ts`, using `defineEval` from `eve/evals`:

  ```ts
  import { defineEval } from "eve/evals";
  import { includes } from "eve/evals/expect";
  export default defineEval({
    description: "Agent responds and stays on its declared purpose.",
    async test(t) {
      await t.send("Hello — what do you do?");
      t.succeeded();
      t.check(t.reply, includes("..."));   // assert something true of your instructions
    },
  });
  ```

  CI gate: `eve eval --strict --junit .eve/junit.xml`. See `eve-capabilities.md` (Eval section) for assertions and the LLM judge.

## 7. Shared types package

* Create or update `packages/types` so it **re-exports eve's** session request shape and stream-event union (see `eve-web-integration.md`). Both `apps/web` and `apps/agent` import from here so the contract is single-sourced — do not redefine a parallel set of types.

## 8. Verify (Definition of Done)

```bash
eve info                                      # app resolves; routes + tools discovered
pnpm --filter agent lint typecheck build
pnpm --filter agent eval                      # runs `eve eval`
```

Then prove the HTTP API works end-to-end. Start the agent headless (`eve dev --no-ui`), open a session and read the stream:

```bash
# POST /eve/v1/session  -> body has continuationToken, header x-eve-session-id
# GET  /eve/v1/session/:sessionId/stream  -> NDJSON (application/x-ndjson)
```

Record the exact commands used. (`GET /eve/v1/health` is the public health route for load balancers.)

## 9. Update the workflow contract

If `.workflow/meta.json` exists:

* Set `stack.agent = "eve"`.
* Append to `history`:

```json
{ "skill": "eve-agent", "action": "scaffold", "ran_at": "<ISO8601>" }
```

If there is no `.workflow/`, skip this and tell the user the agent is scaffolded but not tracked in a dev-flow workflow.

## Deploy (when asked)

* `eve link` to attach the Vercel project + pull AI Gateway credentials, then `eve deploy` for production. Model usage bills through the Vercel AI Gateway.

## Common pitfalls

* Adding the agent at the repo root instead of `apps/agent` (breaks the monorepo).
* Putting `evals/` inside `agent/` — it must be a sibling of `agent/`.
* Letting `apps/web` import the agent as a library, or hand-rolling fetch/NDJSON parsing instead of using `withEve()` + `useEveAgent()`.
* Hardcoding secrets in `agent.ts` or `channels/eve.ts` — always use env vars.
* Forgetting the `eval` task in `turbo.json`, which silently removes the quality gate.
* Shipping a prod channel with no real authenticator — eve fails closed, so the agent will reject traffic.
