# The eve template catalogue — go here before inventing a shape

Thirteen reference implementations published at <https://eve.dev/templates>. This file is a
**lookup table, not a review**: it says which one already solved the problem you have, so the work
starts from a read instead of from a blank file. Surveyed 2026-10-05.

Use it the way `dev-flow/references/resources.md` is used — consult it *before* a `WebSearch` and
before designing a channel, a memory slot, a multi-agent split or an approval flow from scratch.

## ⚠️ Read the shape, not the API

**Every standalone template pins an eve older than the one we target, and some by a lot.** Read from
the `package.json` of each repo, not from its README:

| Template | eve pinned | Minors behind 0.71 |
|---|---|---|
| `eve-software-factory-template` | `^0.67.2` | 4 |
| `OpenInstinct` | `0.66.3` | 5 |
| `mux-video-agent` | `0.46.1` | 25 |
| `eve-sre-agent-template` | `0.44.4` | 27 |
| `marketing-team` · `kody` · `sanity-copilot` · `typefully` | `^0.39.3` | 32 |
| `eve-design-template` | `0.27.3` | **44** |

So the catalogue is a **museum of eve API generations**, and we know exactly what broke in between,
because `eve-docs-coverage.md` records the 0.64 → 0.71 sweep: `execution: "background"` is refused
and the body is `task(input, ctx)`, `taskDeliveryPolicy` and the delivery cohorts are gone, the
`subagent.*` events no longer exist, `agentId` is `taskId`, `ctx.agent(name)` returns a session
rather than an output, and `ctx.getSkill` was removed. **A template's architecture is still worth
reading; its call sites are not worth copying.** OpenInstinct's own page says as much in its way —
*"do not move an Eve 0.69 session onto this 0.66.3 deployment"*.

**The four exceptions** live inside the eve monorepo at
[`vercel/eve/apps/templates`](https://github.com/vercel/eve/tree/main/apps/templates) — `eve-chat-template`,
`eve-llm-council-template`, `eve-slack-agent-template`, `personal-agent-template`. They move with
eve itself, so they are the only ones whose **code** is safe to read for current API shape.

## Need → template

Licences verified on 2026-10-05. ⛔ marks the one with no licence, which by `registry-intake`'s K8
means all rights reserved: read it for ideas, never copy its text.

| When you need | Go to | Licence | Read it for |
|---|---|---|---|
| **A persisted web chat** with per-user long-term memory | `eve-chat-template` (in-repo) | eve's own | The baseline we scaffold *against*: Better Auth + Drizzle + Neon + Upstash Redis, web chat **and** Slack from one agent. Current API. |
| **A starter Slack agent** | `eve-slack-agent-template` (in-repo) | eve's own | Webhook handling and Vercel Connect wiring, minimal. Current API. |
| **Several models answering one prompt, then a judge** | `eve-llm-council-template` (in-repo) | eve's own | Parallel fan-out to four models, streamed, with a judge producing per-model agreement scores. The cheap version of our §12 adversary. Current API. |
| **The smallest honest eve app** | `weather-agent-fixture` (in-repo) | eve's own | Agent config, instructions, one typed tool, one markdown skill. The thing to diff against when a scaffold feels bloated. |
| **A multi-agent team** | [`marketing-team-eve-template`](https://github.com/vercel-labs/marketing-team-eve-template) · 447★ | MIT | **Already mined**: five architecture patterns are in `eve-patterns.md` §7 (depth-1 routing, boundaries by craft, one writer, handoff artifacts by id, `description` as the routing contract). Go back only for the 20 agent-skills. |
| **An agent with no UI at all** | [`kody-eve-template`](https://github.com/vercel-labs/kody-eve-template) · 11★ | MIT | The canonical **topology ③**: `agent/` at the repo root, surfaces are GitHub, Linear and **email**. Cited in the contract's `agent` key for exactly this. |
| **A pipeline with stations and a reviewed output** | [`eve-software-factory-template`](https://github.com/vercel-labs/eve-software-factory-template) · **1151★** | MIT | The most-starred of the set and the closest to `eve-patterns.md` §8 (autonomous pipeline): classifier → analyst → implementer → reviewer, ending in a **draft** PR. Read it before designing any station pipeline of ours. |
| **An agent that investigates rather than builds** | [`eve-sre-agent-template`](https://github.com/vercel-labs/eve-sre-agent-template) · 12★ | MIT | §9 (investigation) in the wild: alerts from Slack or webhooks, live Datadog + GitHub + Vercel evidence, **read-only by default** — which is the §6 read-vs-egress boundary chosen as a default rather than argued for. |
| **An agent answering from an approved corpus** | [`eve-design-template`](https://github.com/vercel-labs/eve-design-template) · 47★ | MIT | A reviewed, **versioned** corpus of org-approved guidance as the only source — the grounding half of §11. ⚠️ eve `0.27.3`: shape only. |
| **Memory that survives conversations** | [`OpenInstinct`](https://github.com/Merit-Systems/OpenInstinct) · 390★ | MIT | Its `agent/memory/workstreams.ts` + `db/services/workstreams.ts` are the best-specified memory slot in the catalogue — see below. |
| **A CMS copilot** | [`sanity-copilot-eve-template`](https://github.com/vercel-labs/sanity-copilot-eve-template) · 5★ | MIT | GROQ queries and edits, schema inspection, drafts and releases — the reference if `module-add cms` ever needs an agent side. |
| **Scheduled social publishing** | [`typefully-eve-template`](https://github.com/vercel-labs/typefully-eve-template) · 8★ | MIT | A publishing **queue** the agent manages, with briefs pulled from Notion: the shape for "the agent drafts, a human releases". |
| **Media processing with approval** | [`mux-video-agent`](https://github.com/muxinc/mux-video-agent) · 4★ | ⛔ **none** | Durable asset work with **human approval on write actions** — the one row where the approval gate is in the product rather than in a doc. Ideas only, no text. |

## The one worth reading today: OpenInstinct's `workstreams`

A memory slot specified far past what `eve-capabilities.md` §Memory describes, and the design
decisions are the valuable part. Read 2026-10-05 from its page and confirmed against the file list
(`agent/memory/workstreams.ts`, `db/schema/workstreams.ts`, `db/services/workstreams.ts`, plus an
eval and a 14 KB test):

- **Scoped** to the authenticated workspace *and* eve's deployment-aware memory key — two axes, not one.
- **Capacity 100 per scope, 8 recalled.** The eight most recently updated *active or waiting*
  records come back first; older ones stay searchable rather than being deleted.
- **Updates require the current revision** — optimistic concurrency on a memory record, which is the
  thing hand-rolled agent memory always forgets.
- **At capacity the agent asks which record to forget.** It does not evict silently, which is the
  difference between a memory the user trusts and one that loses things.
- **Forgetting leaves a tombstone** against interrupted saves, and does not touch chat history.
- **Saving is explicitly not an action**: *"does not start a job, create a schedule, or authorize an
  action."* Memory and side effects are separate verbs — the same separation §2 asks for.
- Available **only in interactive root turns**, so a scheduled run cannot quietly rewrite memory.

### And three decisions from it worth copying, with one that is not

✅ **Vault secrets are encrypted before they reach the database**, and **browser autofill keeps saved
passwords out of the model's context** — the same shape as eve-code's firewall token exchange in
`eve-capabilities.md` §Extension: the credential is used without ever entering the place that could
leak it.

✅ **Gmail is scoped to `gmail.modify`, deliberately not `mail.google.com`** — the permanent-delete
scope is declined on purpose. Scope minimisation stated as a decision rather than left to a default.

⚠️ **But: *"Payment credentials can appear in stored Eve tool results; the bundled skills instruct
the agent not to repeat them in chat."*** An instruction in a skill is **not a control** — that is
the whole argument of §11. Recorded here as a counter-example, not a pattern.

⚠️ **Two side effects with no approval gate**: *"Spend requests do not have an additional Eve
approval step"* and *"user-requested email and calendar operations run without an extra Eve tool
approval. Calendar events with attendees send Google invitations."* Defensible for a **personal**
agent with one user and Link's own consent screen in the path; forbidden by §2 in a multi-tenant
product. **The distinction — personal agent versus product — is the lesson**, and it is the question
to ask before copying any approval design from this catalogue.

## Two operational numbers worth having before a plan

- **OpenInstinct requires Vercel Pro**, because it polls for scheduled work **every minute** and the
  Hobby plan allows one cron per day. Exactly the kind of ceiling `dev-flow/references/before-you-build.md`
  step 2 asks to write into the plan beside the capability.
- **A Google OAuth app in Testing mode only works for listed test users, and those grants expire
  after seven days.** Restricted Gmail scopes need Google's verification and may need a security
  assessment. Anyone wiring Gmail hits this on day eight, not day one.

## Next.js floor, checked rather than assumed

OpenInstinct pins `next 16.3.3`, five patches below our floor of `16.3.8`. Per the contract's own
rule — name the CVEs that apply to *this* project — the applicable set is **empty**: it uses no
`next/og` or `ImageResponse` (the September critical), configures no `images.remotePatterns` (the
high SSRF is conditional on it), and sets no `cacheComponents` (the two `use cache` leaks need it).
Still worth bumping, since patches are cheap; not an alarm. The same check belongs on any template
before a deploy — `vercel-deploy` §Also check the Next.js security floor.
