# eve docs coverage map

Every page of <https://eve.dev/docs> mapped to where this skill covers it. Purpose: prove and *maintain* full coverage — when eve adds a docs page, add a row and point it at a reference. The golden rule still holds: this skill encodes the **workflow + conventions**, not a frozen copy — always `[VERIFY]` against `node_modules/eve/docs/` — the published package ships its full docs **and a CHANGELOG**, which is the only place the breaking-change history exists (eve.dev has no changelog page). `npm pack eve@<version>` is enough; you do not need to install it.

> **Verification pass 2026-08-12 against eve@0.31.3.** All 15 cited subpaths and all 16 cited exports exist; `eve add` / `eve registry` / `eve extension build` / `eve channels list` confirmed (and no `eve channels add`, as documented). The Slack hook set and `ctx.*` surface match. **One table was wrong**: the channel-kind list — `channel/linear` does not exist (it is `channel/linear-agent`, or the `eve add linear` bundle), `teams`/`telegram`/`twilio` are hand-authored rather than registry items, and `twilio` was missing entirely.
>
> **Verification pass 2026-08-16 against eve@0.38.3** (eve shipped 0.32.0 through 0.38.3 in the four
> days since the last pass — pulled `npm pack eve@0.38.3` and read `CHANGELOG.md` + `docs/`, same
> technique). CLI surface, auth fallback, and channel-kind list from the previous pass all still hold.
> **Four things had drifted**: ① **eve's own scaffold default model changed in 0.36.0** from
> `anthropic/claude-sonnet-5` to `zai/glm-5.2` — this skill's *recommendation* is unchanged, but three
> files described it as "the scaffold default," which stopped being true; ② **`defineDynamic` dropped
> `fallback`** in 0.33.0 — every matching handler must now return a concrete model/tool/instruction,
> no compiled fallback; ③ **frontend agent bindings renamed `stop()` → `cancel()`** in 0.38.0; ④
> separately (not itself a change this pass — shipped 0.33.0, just never logged before), the `eve`
> channel's default `turnPolicy` (**`"steer"`**, cancel-and-replace on an overlapping send) was
> documented backwards as a hard reject/queue in two files. All four fixed, across six files:
> `eve-scaffold.md`, `eve-conventions.md`, `eve-concepts.md`, `SKILL.md`, `ai-elements.md`, and
> `eve-web-integration.md`. Not re-verified this pass (logged for the next one): the 0.31.0
> session/channel API surface already covered by the 08-12 pass, and the newer 0.37.x background-tasks
> / MCP-channel-route / Vercel-Sandbox-Drives surfaces, which this skill doesn't document yet.
>
> **Rebase note, 2026-08-16, landing the standalone `eve-channels.md`** (per-surface Telegram /
> Discord / Teams / WhatsApp guides, proposed 2026-08-06, predates the 08-12 channel-table fix
> above). Its three section headers claimed `eve add channel/telegram` and `eve add channel/teams`
> and `eve add channel/chat-sdk-whatsapp` — checked against `eve@0.38.3`'s own docs (`telegram.mdx`
> / `teams.mdx` show hand-authored setup only, `channel/discord` is the one of the three that is
> real and documented, `chat-sdk.mdx` confirms WhatsApp rides the Chat SDK with no registry item
> of its own) and corrected to match §Channel's already-verified table instead of re-diverging
> from it. The Linear §Channel subsection this branch predates was kept in place rather than
> dropped by the merge.
>
> **Verification pass 2026-09-01 against eve@0.47.6** (eve shipped 0.45.1 → 0.47.6 in the six days
> since the 08-26 pass; `npm pack eve@0.47.6`, then `CHANGELOG.md` + `docs/` + the `exports` map and
> `.d.ts`, same technique). Mechanical checks first: **38 of the 39 `eve/…` subpaths this skill cites
> still exist** — the one absent is `eve/tools/defaults`, which this skill already documents as removed
> in 0.45.0 — and **63 of the 69 eve-owned identifiers** it names resolve. The six that do not are all
> correct as written: `createGithubTools` and `createRedisState` belong to third-party packages,
> `addToolApprovalResponse` is the AI SDK's, `onTurnEnd` is phrased as "-style", and `isLoopbackRequest`
> and `resolveActiveSession` are documented here *as removed*. `DynamicResolveContext` still carries no
> `clientContext`; `failoverRegions`, `EveMessagePart` and the Telegram identifiers all survive;
> `experimental.subagentPersistentSessions` is gone from the types, which is what this skill already says.
>
> **Two capabilities were missing entirely.** ① **Memory** (`agent/memory/<slot>.ts`, `defineMemory` on
> `eve/memory`, `fileMemory()` on `eve/memory/file`, `byPrincipal` on `eve/memory/scope`) shipped across
> 0.45.1–0.47.5 and is the only way to hold context **across** sessions — everything this skill documented
> under State is per-session. Four new subpaths, a new docs page, and a fifth pattern page. Now
> `eve-capabilities.md` §Memory, with the parts that fail closed spelled out: a `scope` resolver returning
> `null` disables the slot rather than sharing one, providers must partition on `memory.scope.key` and not
> the raw value, and `fileMemory()` **errors** rather than guessing a backend outside Vercel and `eve dev`.
> ② **The MCP channel** (`mcpChannel` on `eve/channels/mcp`) — the agent published *as* an MCP server so a
> client like Claude Code can delegate to it, auth mandatory even in development. It is the mirror image of
> the MCP *connection* this skill already covered, and the two are easy to confuse by name alone.
>
> **Three things this skill asserted are now false:**
>
> ① **eve's scaffold default model moved again**, `zai/glm-5.2` → **`openai/gpt-5.6-luna-fast`** in 0.47.2.
> It is one constant, `DEFAULT_AGENT_MODEL_ID`, used for `eve init`, for a config-less agent and for the
> setup picker's pre-selection. Three files said `glm-5.2`; at 0.47.6 that string survives only in the
> CHANGELOG and one guide example. Twice in eleven minor versions is the argument for this skill's own
> rule — pin explicitly, never inherit.
> ② **The scaffold does not pin `zod 4.4.3`**, or any literal: `eve init` substitutes a
> `__EVE_INIT_ZOD_VERSION__` token whose default tracks eve's own dependency (**4.5.4** at 0.47.6), the
> same mechanism that pins `ai` `^7.0.82`, `@vercel/connect` `1.0.0` and the Node engine. The durable
> instruction is to read the generated `package.json`, not to memorise a number.
> ③ **The auth-fallback line still said "still current at 0.38.3 — current npm `latest`"**, three releases
> after that stopped being true. The claim itself held; its stamp had rotted.
>
> **Three additions to surfaces already covered**: Slack gained `onSlashCommand` and `onShortcut` in
> 0.47.4 — both acknowledged immediately with the handler kept alive, so the ack is not the reply — and
> the 0.47.6 docs are now explicit that `onEvent` sees **only** JSON `event_callback` deliveries, never
> slash commands or interactive payloads. Sandbox handles gained `delete()` in 0.47.0, which drops the
> session's sandbox without retiring the session, with per-backend caveats. Eval contexts gained
> `transcript`, which is what a multi-turn judge should be pointed at instead of `t.reply`.
>
> **Not re-verified this pass** (logged for the next one): `ai-elements.md`, whose claims are about the
> *mapping* between eve and `ai` — `ai` is at `7.0.87` and eve no longer declares it as a dependency, so
> the two drift independently and both need re-packing; and the behavioural detail in `eve-channels.md`,
> where every identifier was re-confirmed mechanically but the prose was last read in full at 0.45.0.
> Also unread: the stream protocol's move to version 24 (0.46.1, `action.input.appended` and the new
> `message.completed` ordering), instrumentation `tracePolicy` superseding `capture`, and
> `defineDynamic` for `connections/` (0.47.4) — three surfaces this skill does not document yet.

> **Verification pass 2026-08-26 against eve@0.45.0** (eve shipped 0.39.0 → 0.45.0 in the ten days
> since the 08-16 pass; `npm pack eve@0.45.0`, then `CHANGELOG.md` + `docs/` + the `exports` map and
> `.d.ts`, same technique). Mechanical checks first: **28 of the 29 `eve/…` subpaths this skill cites
> still exist**, and every export named in the module table resolves. **Three things this skill
> asserted are now false:**
>
> ① **`eve/tools/defaults` was removed in 0.45.0.** Every built-in definition moved to its own
> subpath named after the *tool* (`eve/tools/write_file`, `/read_file`, `/bash`, `/todo`,
> `/web_fetch`, `/load_skill`) while the export keeps camelCase. Four files carried the old path,
> including the override recipe — the one line a reader would actually copy.
> ② **`glob` and `grep` left the default tool set in 0.39.0.** Two files listed them as built-ins and
> one claimed "~12 tools with zero code". The real set is at most ten, and half of it is
> *conditional* on the session — `agent` is root-only, `ask_question` needs a session that can
> request input, `web_search` needs a supporting provider, `load_skill`/`connection_search` appear
> only when those resources are declared.
> ③ **`experimental_workflow` moved off `eve/tools` to `eve/tools/workflow`** — the import in the
> Dynamic-workflows example would not have resolved.
>
> **Also closed a `[VERIFY]` that had an answer all along:** `web_search` has no local executor, and
> **on AI Gateway models eve already defaults to Exa**, switchable with
> `webSearch({ provider: "parallel" })` from `eve/tools/web_search`. The note had been speculating
> about wrapping a Gateway tool in `defineTool()` when the framework ships the config helper.
>
> **Four gaps filled** from the changelog, each verified in the types before writing: persistent
> subagent sessions are the **default** since 0.45.0 (`experimental.subagentPersistentSessions` is
> gone and `false` is no longer an opt-out); `useEveAgent({ resume: true })` + `resume()` (0.44.1)
> resume a *still-running* turn, which the hand-rolled event-log pattern cannot; a child may return
> `parent.sandbox` to share the parent's live sandbox (0.39.0); and `ctx.isDMOrPrivateChannel()`
> (0.39.1) — async, and **fails closed to `true`**. Plus `respond()`'s 0.42.0 strictness
> (`parseInputResponses()` from `eve/client` for anything widened to `InputResponse[]`), the new
> **Linq** channel (iMessage *and* SMS, `eve add channel/linq`), and Telegram/Chat-SDK authorization
> challenges.
>
> **The map itself had rotted**: eight rows pointed at paths that have moved
> (`/docs/tools` → `/tools/overview`, `/docs/human-in-the-loop` → `/tools/human-in-the-loop`,
> `/docs/guides/state` → `/concepts/state`, `/docs/guides/acp` → `/protocols/acp`,
> `/docs/connections` → `/connections/overview`, and `guides/dynamic-workflows`,
> `reference/project-layout`, `introduction` no longer exist as pages in the shipped set). Four pages
> were uncovered: `concepts/built-in-tools`, `channels/linq`, `protocols/ucp` (↪ — agentic commerce,
> a `/.well-known/ucp` profile off a custom channel), and
> `patterns/durable-cross-channel-notifications`, which became **`eve-patterns.md` §10**. Coverage is
> back to 82/82.
>
> **Method note for the next pass:** the package's `docs/` folder is the set to diff against, and it
> is *not* identical to eve.dev — `docs/README.md` plays the role of `/docs/introduction`. Treat a
> page missing from the package as "not in the shipped set", not as proof the website deleted it.
>
> **Spot check 2026-08-26 against eve@0.45.0 — sandbox surface only, superseded by the pass above.** Closed the
> `eve-conventions.md` `[VERIFY]` on Vercel Sandbox regions. Answer: eve's `vercel()` options are a
> structural passthrough of the SDK's create params minus a fixed exclusion list (`region` is not on
> it), but eve compiles in `@vercel/sandbox` **2.8.0**, and `region`/`failoverRegions` only exist from
> **3.x** — so the region is a project-level setting today, and it will start working through
> `vercel()` the moment eve revendors, with nothing to announce it. **One table was wrong**: the module
> map put `vercel()`/`docker()` on `eve/sandbox`; each backend has **its own subpath**
> (`eve/sandbox/vercel`, `/docker`, `/just-bash`, `/microsandbox`), and only `defineSandbox` +
> `defaultBackend` come from `eve/sandbox` itself. The `just-bash` `[VERIFY]` is confirmed and dropped.
> **Note for the next full pass: eve is at 0.45.0**, seven minors past the 08-16 pass; everything in
> this skill outside the sandbox surface is still only verified against 0.38.3.

Legend: **✅ deep** (written up here) · **↪ pointer** (named + where to read) · **⛔ out of scope** (with reason).

## Foundational & getting started
| eve docs page | Covered in | |
|---|---|---|
| `/docs/introduction` (the shipped set's entry point is `docs/README.md`) | `SKILL.md` (what eve is, the two layouts) | ✅ |
| `/docs/getting-started` | `eve-scaffold.md` (init, first tool, local dev, HTTP API) | ✅ |
| `/docs/agent-config` | `eve-concepts.md` §Agent config (+ `eve-scaffold.md` §3 model/limits/service-tier) | ✅ |
| `/docs/instructions` | `eve-concepts.md` §Instructions | ✅ |
| `/docs/responsible-use` | `eve-concepts.md` §Responsible use (+ `eve-conventions.md` security) | ✅ |

## Concepts
| Page | Covered in | |
|---|---|---|
| `/docs/concepts/context-control` | `eve-concepts.md` §Context control | ✅ |
| `/docs/concepts/default-harness` | `eve-concepts.md` §Default harness | ✅ |
| `/docs/concepts/execution-model-and-durability` | `eve-concepts.md` §Execution model + `eve-conventions.md` durability | ✅ |
| `/docs/concepts/built-in-tools` | `eve-conventions.md` §Built-in default harness + `eve-concepts.md` §Default harness — the ten defaults and which are conditional, the per-tool subpaths, `glob`/`grep` as opt-ins, `webSearch({ provider })` | ✅ |
| `/docs/concepts/security-model` | `eve-conventions.md` §Security + `eve-patterns.md` | ✅ |
| `/docs/concepts/sessions-runs-and-streaming` | `eve-concepts.md` §Sessions + `eve-web-integration.md` | ✅ |

## Building blocks
| Page | Covered in | |
|---|---|---|
| `/docs/tools/overview` | `eve-capabilities.md` §Tool + `eve-conventions.md` (idempotency/approval) | ✅ |
| `/docs/skills` | `eve-capabilities.md` §Skill + `eve-concepts.md` (context) | ✅ |
| `/docs/subagents` | `eve-capabilities.md` §Subagent | ✅ |
| `/docs/sandbox` | `eve-concepts.md` §Sandbox (backends, seeding, network policy, credential brokering) | ✅ |
| `/docs/tools/human-in-the-loop` | `eve-concepts.md` §HITL + `eve-conventions.md` (approval) + `eve-capabilities.md` (`respond()` / `parseInputResponses`) | ✅ |

## Connections & channels
| Page | Covered in | |
|---|---|---|
| `/docs/connections/overview` · `/mcp` · `/openapi` | `eve-capabilities.md` §Connection (`defineMcpClientConnection` / `defineOpenAPIConnection`) | ✅ |
| `/docs/channels/overview` · `/eve` · `/slack` · `/github` · `/linear` · `/twilio` | `eve-capabilities.md` §Channel (all kinds + Vercel Connect; Slack `onMessage`/`onEvent` hooks + `ctx.cancel()`/`ctx.reset()` session controls) | ✅ |
| `/docs/channels/telegram` · `/discord` · `/teams` | `eve-channels.md` — per-surface guides: webhook registration, group dispatch, `onMessage` gate + the two send paths (Telegram); 3s ACK + command propagation (Discord); `onInputResponse` authorization bypass + file opt-in (Teams) | ✅ |
| `/docs/channels/linq` | `eve-capabilities.md` §Channel — `eve add channel/linq`, Connect vs portable credentials, iMessage **and** SMS (Photon stays iMessage-only) | ✅ |
| `/docs/channels/mcp` | `eve-capabilities.md` §Channel — `mcpChannel()` on `eve/channels/mcp`: the agent published **as** an MCP server (`agent_start` / `agent_get` / `agent_update` / `agent_cancel`), auth mandatory even in dev. Distinct from `/docs/connections/mcp`, which is the agent *calling* one. | ✅ |
| `/docs/channels/custom` | `eve-capabilities.md` §Channel (`defineChannel`) | ↪ |
| `/docs/channels/chat-sdk` | `eve-capabilities.md` §Channel — `chatSdkChannel()` shape + the Resend worked example (official code); `eve-channels.md` — WhatsApp adapter + when an adapter's thread model doesn't fit your domain | ✅ |

## Schedules, extensions, hooks, state
| Page | Covered in | |
|---|---|---|
| `/docs/schedules` | `eve-capabilities.md` §Schedule + `eve-patterns.md` §4 (dynamic) | ✅ |
| `/docs/memory` · `/docs/patterns/multi-tenant-memory` | `eve-capabilities.md` §Memory — slots, `defineMemory`, `fileMemory()` + backends, scope/visibility/namespace, `eve add memory/supermemory` | ✅ |
| `/docs/extensions` | `eve-capabilities.md` §Extension | ✅ |
| `/docs/guides/hooks` | `eve-capabilities.md` §Hook (+ observability-sink pattern) | ✅ |
| `/docs/concepts/state` | `eve-concepts.md` §State (`defineState` — session-scoped) + `eve-patterns.md` §3 (the external store it explicitly defers to) | ✅ |

## Dynamic & advanced guides
| Page | Covered in | |
|---|---|---|
| `/docs/guides/dynamic-capabilities` | `eve-concepts.md` §Dynamic capabilities | ✅ |
| the `Workflow` tool (now inside `/docs/concepts/built-in-tools`; there is no `guides/dynamic-workflows` page) | `eve-concepts.md` §Dynamic workflows (`experimental_workflow()` from `eve/tools/workflow`) | ✅ |
| `/docs/guides/session-context` | `eve-conventions.md` + `eve-concepts.md` + `eve-patterns.md` (`ctx.session.auth`) | ✅ |
| `/docs/guides/auth-and-route-protection` | `eve-scaffold.md` §4 (helpers `jwtHmac`/`jwtEcdsa`/`httpBasic`/`oidc`, `ForbiddenError`/`UnauthenticatedError`, `withAuthChallenges`) + `eve-conventions.md` (fail-closed) + `eve-patterns.md` §1 | ✅ |
| `/docs/guides/remote-agents` | `eve-capabilities.md` §Subagent (`defineRemoteAgent`) | ↪ |
| `/docs/guides/instrumentation` | `eve-conventions.md` §Observability + `eve-scaffold.md` (`instrumentation.ts`) | ✅ |
| `/docs/guides/dev-tui` | `eve-scaffold.md` / `eve-conventions.md` (`eve dev` / `eve dev <url>`) | ↪ |

## Client, frontend, deployment
| Page | Covered in | |
|---|---|---|
| `/docs/guides/client/{overview,messages,streaming,continuations}` | `eve-web-integration.md` + `eve-concepts.md` §Sessions | ✅ |
| `/docs/guides/client/output-schema` | `eve-concepts.md` §Agent config (`outputSchema`) + evals structured-output | ↪ |
| `/docs/guides/frontend/{overview,nextjs}` | `eve-web-integration.md` (`withEve()` + `useEveAgent()`) | ✅ |
| `/docs/guides/frontend/{nuxt,sveltekit,use-eve-agent-svelte,use-eve-agent-vue}` | dev-flow web is **Next-only**; RN consumes over HTTP (`eve/client`) | ⛔ |
| `/docs/guides/deployment/{overview,vercel,self-hosting}` | `eve-scaffold.md` §Deploy + `eve-conventions.md` §self-host | ✅ |

## Evals, patterns, reference
| Page | Covered in | |
|---|---|---|
| `/docs/evals/{overview,cases,assertions,judge,targets,reporters,running}` | `eve-evals.md` (full) + `eve-capabilities.md` §Eval | ✅ |
| `/docs/patterns/{multi-tenant-auth,multi-tenant-approvals,multi-tenant-memory,dynamic-scheduling}` | `eve-patterns.md` | ✅ |
| `/docs/patterns/durable-cross-channel-notifications` | `eve-patterns.md` §10 — `to()` starts a turn, so a notification goes through the platform API plus an app-owned outbox; at-least-once and what that costs | ✅ |
| `/docs/protocols/ucp` | `eve-capabilities.md` §Channel (`defineChannel` + route verbs) — a UCP profile is a JSON document served from `/.well-known/ucp` on a custom channel; the protocol itself is agentic commerce, out of dev-flow's remit | ↪ |
| `/docs/reference/cli` | `eve-scaffold.md` §CLI quick reference + `eve-evals.md` (`eve eval` flags) | ↪ |
| project layout (folded into `/docs/getting-started`; no standalone `reference/project-layout` page in the shipped set) | `eve-scaffold.md` + `SKILL.md` layout | ✅ |
| `/integrations` (directory) | `eve-capabilities.md` §Connection/Channel/Extension + `SKILL.md` (ecosystem-first) — adopt prebuilt connections/channels/extensions before hand-rolling | ✅ |
| `/docs/channels/photon` | `eve-capabilities.md` §Channel — `photonIMessageChannel` (`eve/channels/photon`), `eve add channel/photon-imessage`, `connectPhotonCredentials`, route `/eve/v1/photon` (new in 0.29.3) | ✅ |
| `/docs/protocols/acp` | `eve-scaffold.md` §CLI — `eve acp [url]` (Agent Client Protocol v1 over stdio, `--scope` / `EVE_VERCEL_SCOPE`, new in 0.29.4) | ✅ |
| `/docs/install-integrations` | `eve-capabilities.md` §Install from the registry FIRST (`eve add` / `eve registry list/search/view/add`, third-party shadcn-format sources) + `SKILL.md` ecosystem-first + `eve-registry-porting` sourcing priority | ✅ |
| `/docs/reference/typescript-api` | read the installed `.d.ts` / `node_modules/eve/docs/` — never mirror types | ⛔ |
| `/docs/tutorial/*` (9-part series) | a learning tutorial, not API surface — this skill encodes the workflow, not tutorials | ⛔ |

**Result:** every non-tutorial, non-type-reference eve docs page has a home. The two intentional `⛔` are the multi-framework frontends (we're Next-only for web) and the raw TypeScript-API/tutorial pages (read the installed source).
