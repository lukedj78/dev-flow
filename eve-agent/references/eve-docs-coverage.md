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

Legend: **✅ deep** (written up here) · **↪ pointer** (named + where to read) · **⛔ out of scope** (with reason).

## Foundational & getting started
| eve docs page | Covered in | |
|---|---|---|
| `/docs/introduction` | `SKILL.md` (what eve is, the two layouts) | ✅ |
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
| `/docs/concepts/security-model` | `eve-conventions.md` §Security + `eve-patterns.md` | ✅ |
| `/docs/concepts/sessions-runs-and-streaming` | `eve-concepts.md` §Sessions + `eve-web-integration.md` | ✅ |

## Building blocks
| Page | Covered in | |
|---|---|---|
| `/docs/tools` | `eve-capabilities.md` §Tool + `eve-conventions.md` (idempotency/approval) | ✅ |
| `/docs/skills` | `eve-capabilities.md` §Skill + `eve-concepts.md` (context) | ✅ |
| `/docs/subagents` | `eve-capabilities.md` §Subagent | ✅ |
| `/docs/sandbox` | `eve-concepts.md` §Sandbox (backends, seeding, network policy, credential brokering) | ✅ |
| `/docs/human-in-the-loop` | `eve-concepts.md` §HITL + `eve-conventions.md` (approval) | ✅ |

## Connections & channels
| Page | Covered in | |
|---|---|---|
| `/docs/connections` · `/mcp` · `/openapi` | `eve-capabilities.md` §Connection (`defineMcpClientConnection` / `defineOpenAPIConnection`) | ✅ |
| `/docs/channels/overview` · `/eve` · `/slack` · `/github` · `/linear` · `/twilio` | `eve-capabilities.md` §Channel (all kinds + Vercel Connect; Slack `onMessage`/`onEvent` hooks + `ctx.cancel()`/`ctx.reset()` session controls) | ✅ |
| `/docs/channels/telegram` · `/discord` · `/teams` | `eve-channels.md` — per-surface guides: webhook registration, group dispatch, `onMessage` gate + the two send paths (Telegram); 3s ACK + command propagation (Discord); `onInputResponse` authorization bypass + file opt-in (Teams) | ✅ |
| `/docs/channels/custom` | `eve-capabilities.md` §Channel (`defineChannel`) | ↪ |
| `/docs/channels/chat-sdk` | `eve-capabilities.md` §Channel — `chatSdkChannel()` shape + the Resend worked example (official code); `eve-channels.md` — WhatsApp adapter + when an adapter's thread model doesn't fit your domain | ✅ |

## Schedules, extensions, hooks, state
| Page | Covered in | |
|---|---|---|
| `/docs/schedules` | `eve-capabilities.md` §Schedule + `eve-patterns.md` §4 (dynamic) | ✅ |
| `/docs/extensions` | `eve-capabilities.md` §Extension | ✅ |
| `/docs/guides/hooks` | `eve-capabilities.md` §Hook (+ observability-sink pattern) | ✅ |
| `/docs/guides/state` | `eve-concepts.md` §State (`defineState` — session-scoped) + `eve-patterns.md` §3 (the external store it explicitly defers to) | ✅ |

## Dynamic & advanced guides
| Page | Covered in | |
|---|---|---|
| `/docs/guides/dynamic-capabilities` | `eve-concepts.md` §Dynamic capabilities | ✅ |
| `/docs/guides/dynamic-workflows` | `eve-concepts.md` §Dynamic workflows (`experimental_workflow`) | ✅ |
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
| `/docs/reference/cli` | `eve-scaffold.md` §CLI quick reference + `eve-evals.md` (`eve eval` flags) | ↪ |
| `/docs/reference/project-layout` | `eve-scaffold.md` + `SKILL.md` layout | ✅ |
| `/integrations` (directory) | `eve-capabilities.md` §Connection/Channel/Extension + `SKILL.md` (ecosystem-first) — adopt prebuilt connections/channels/extensions before hand-rolling | ✅ |
| `/docs/channels/photon` | `eve-capabilities.md` §Channel — `photonIMessageChannel` (`eve/channels/photon`), `eve add channel/photon-imessage`, `connectPhotonCredentials`, route `/eve/v1/photon` (new in 0.29.3) | ✅ |
| `/docs/guides/acp` | `eve-scaffold.md` §CLI — `eve acp [url]` (Agent Client Protocol v1 over stdio, `--scope` / `EVE_VERCEL_SCOPE`, new in 0.29.4) | ✅ |
| `/docs/install-integrations` | `eve-capabilities.md` §Install from the registry FIRST (`eve add` / `eve registry list/search/view/add`, third-party shadcn-format sources) + `SKILL.md` ecosystem-first + `eve-registry-porting` sourcing priority | ✅ |
| `/docs/reference/typescript-api` | read the installed `.d.ts` / `node_modules/eve/docs/` — never mirror types | ⛔ |
| `/docs/tutorial/*` (9-part series) | a learning tutorial, not API surface — this skill encodes the workflow, not tutorials | ⛔ |

**Result:** every non-tutorial, non-type-reference eve docs page has a home. The two intentional `⛔` are the multi-framework frontends (we're Next-only for web) and the raw TypeScript-API/tutorial pages (read the installed source).
