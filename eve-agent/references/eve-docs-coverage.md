# eve docs coverage map

Every page of <https://eve.dev/docs> mapped to where this skill covers it. Purpose: prove and *maintain* full coverage — when eve adds a docs page, add a row and point it at a reference. The golden rule still holds: this skill encodes the **workflow + conventions**, not a frozen copy — always `[VERIFY]` against `node_modules/eve/docs/`.

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
| `/docs/channels/overview` · `/eve` · `/slack` · `/discord` · `/github` · `/linear` · `/teams` · `/telegram` · `/twilio` | `eve-capabilities.md` §Channel (all kinds + Vercel Connect; Slack `onMessage`/`onEvent` hooks + `ctx.cancel()`/`ctx.reset()` session controls) | ✅ |
| `/docs/channels/custom` | `eve-capabilities.md` §Channel (`defineChannel`) | ↪ |
| `/docs/channels/chat-sdk` | `eve-capabilities.md` §Channel — Vercel Chat SDK adapter for Slack/Discord/Telegram/WhatsApp/email | ↪ |

## Schedules, extensions, hooks, state
| Page | Covered in | |
|---|---|---|
| `/docs/schedules` | `eve-capabilities.md` §Schedule + `eve-patterns.md` §4 (dynamic) | ✅ |
| `/docs/extensions` | `eve-capabilities.md` §Extension | ✅ |
| `/docs/guides/hooks` | `eve-capabilities.md` §Hook (+ observability-sink pattern) | ✅ |
| `/docs/guides/state` | `eve-concepts.md` §State (`defineState`) | ✅ |

## Dynamic & advanced guides
| Page | Covered in | |
|---|---|---|
| `/docs/guides/dynamic-capabilities` | `eve-concepts.md` §Dynamic capabilities | ✅ |
| `/docs/guides/dynamic-workflows` | `eve-concepts.md` §Dynamic workflows (`experimental_workflow`) | ✅ |
| `/docs/guides/session-context` | `eve-conventions.md` + `eve-concepts.md` + `eve-patterns.md` (`ctx.session.auth`) | ✅ |
| `/docs/guides/auth-and-route-protection` | `eve-scaffold.md` §4 + `eve-conventions.md` (fail-closed) + `eve-patterns.md` §1 | ✅ |
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
| `/docs/install-integrations` | `eve-capabilities.md` §Install from the registry FIRST (`eve add` / `eve registry list/search/view/add`, third-party shadcn-format sources) + `SKILL.md` ecosystem-first + `eve-registry-porting` sourcing priority | ✅ |
| `/docs/reference/typescript-api` | read the installed `.d.ts` / `node_modules/eve/docs/` — never mirror types | ⛔ |
| `/docs/tutorial/*` (9-part series) | a learning tutorial, not API surface — this skill encodes the workflow, not tutorials | ⛔ |

**Result:** every non-tutorial, non-type-reference eve docs page has a home. The two intentional `⛔` are the multi-framework frontends (we're Next-only for web) and the raw TypeScript-API/tutorial pages (read the installed source).
