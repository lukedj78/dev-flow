# The eve template catalogue — go here before inventing a shape

**Twenty-two** reference implementations listed at <https://vercel.com/templates/eve> (the old
`eve.dev/templates` now 308-redirects there). This file is a **lookup table, not a review**: it says
which one already solved the problem you have, so the work starts from a read instead of from a
blank file. Re-surveyed **2026-11-24** against eve **1.4.0** (`vercel/eve@518473f`); the first
survey was 2026-10-05.

Use it the way `dev-flow/references/resources.md` is used — consult it *before* a `WebSearch` and
before designing a channel, a memory slot, a multi-agent split or an approval flow from scratch.

## ⚠️ Read the shape, not the API — but most of the catalogue is on 1.x now

The October survey found a **museum of eve API generations** (pins from 0.27 to 0.67). The 1.0
release (2026-11-15) moved almost all of it: **every template inside the monorepo pins `eve` 1.2.0**
(25 directories under [`vercel/eve/apps/templates`](https://github.com/vercel/eve/tree/main/apps/templates)),
and the standalone repos were bumped on 2026-11-20. Read from each `package.json`, not the README
(checked 2026-11-24 with `gh api`):

| Template | eve pinned | Read the code for current API? |
|---|---|---|
| everything in `vercel/eve/apps/templates` | `1.2.0` | ✅ moves with eve itself |
| `eve-software-factory-template` · `eve-data-analyst-template` · `kody-eve-template` | `^1.0.0` | ✅ |
| `marketing-team-eve-template` · `personal-agent-template` · `sanity-copilot-eve-template` | `1.0.0` | ✅ |
| `OpenInstinct` | `1.0.0-rc.1` | ⚠️ release candidate — check against 1.x before copying |
| `eve-design-template` | `1.0.0-rc.0` | ⚠️ same |
| **`eve-sre-agent-template`** (upstream repo) | **`0.83.0`** | ❌ pre-1.0 — the in-monorepo copy is on 1.2.0, read that one instead |
| `eve-chat-template` · `eve-slack-agent-template` (upstream repos) | `^0.31.3` · `^0.24.0` | ❌ **archived** 2026-08 — the monorepo copies replaced them |
| `typefully-eve-template` | `^0.83.0` | ❌ **archived** 2026-11-13 |
| `mux-video-agent` | (not re-checked) | ❌ last push 2026-08-27, no licence |

**Rule that still holds:** a 1.x template's call sites are safe to read; anything below 1.0 is shape
only. `eve-docs-coverage.md` records what broke between 0.64 and 0.71, and the 1.0 CHANGELOG what
broke after — a pre-1.0 call site is wrong more often than right.

**Licences.** The standalone repos are MIT (Mem0 is Apache-2.0). The monorepo templates mostly ship
no `LICENSE` file of their own — `eve-chat`, `eve-coding-agent`, `eve-computer-use`, `eve-data-agent`,
`eve-discord-agent`, `eve-slack-agent`, `eve-voice`, `slack-company-brain` — and none declares a
`license` in `package.json`, so they fall under **the eve repository's root licence, Apache-2.0**.
That is the reading `registry-intake` K8 needs before copying text: a missing per-template file is
**not** "all rights reserved" inside a licensed monorepo. `[VERIFY]` if a template ever moves out to
its own repo.

## Need → template

| When you need | Go to | Licence | Read it for |
|---|---|---|---|
| **A persisted web chat** with per-user long-term memory | `eve-chat-template` (in-repo) | Apache-2.0 (repo root) | The baseline we scaffold *against*: password access first, then Sign in with Vercel + Better Auth + Drizzle + Neon + Upstash Redis for multi-user production. Current API. |
| **A starter Slack agent** | `eve-slack-agent-template` (in-repo) | Apache-2.0 (repo root) | Webhook handling and Vercel Connect wiring, minimal. Current API. |
| **A company-wide assistant in Slack** | `slack-company-brain-template` (in-repo; gallery name "Company Brain") | Apache-2.0 (repo root) | Mention-or-DM in Slack, answer in thread. **Slack only, no web UI**, and "out of the box it knows nothing about your company" — the knowledge sources are yours to wire. |
| **The smallest honest eve app** | `apps/fixtures/weather-agent` (in-repo; moved from `weather-agent-fixture`) | Apache-2.0 (repo root) | Agent config, instructions, one typed tool, one markdown skill. The thing to diff against when a scaffold feels bloated. |
| **A multi-agent team** | [`marketing-team-eve-template`](https://github.com/vercel-labs/marketing-team-eve-template) · 459★ | MIT | **Already mined**: five architecture patterns are in `eve-patterns.md` §7 (depth-1 routing, boundaries by craft, one writer, handoff artifacts by id, `description` as the routing contract). Go back only for the 20 agent-skills. |
| **An agent with no UI at all** | [`kody-eve-template`](https://github.com/vercel-labs/kody-eve-template) · 19★ (gallery: "GitHub Maintainer") | MIT | The canonical **topology ③**: `agent/` at the repo root, surfaces are GitHub, Linear and **email**. Cited in the contract's `agent` key for exactly this. |
| **A pipeline with stations and a reviewed output** | [`eve-software-factory-template`](https://github.com/vercel-labs/eve-software-factory-template) · **1186★** ("Foreman") | MIT | The most-starred of the set and the closest to `eve-patterns.md` §8 (autonomous pipeline): classifier → analyst → implementer → reviewer, ending in a **draft** PR. Read it before designing any station pipeline of ours. |
| **An agent that investigates rather than builds** | `eve-sre-agent-template` — in-repo copy on 1.2.0; [upstream](https://github.com/vercel-labs/eve-sre-agent-template) · 14★ on 0.83.0 (gallery: "Incident Response Agent") | MIT | §9 (investigation) in the wild: alerts from Slack or webhooks, live Datadog + GitHub + Vercel evidence, **read-only by default** — which is the §6 read-vs-egress boundary chosen as a default rather than argued for. |
| **Questions answered from a database** | [`eve-data-analyst-template`](https://github.com/vercel-labs/eve-data-analyst-template) · 8★ (Slack + Postgres); `eve-data-agent-template` (in-repo, dbt + DuckDB, not in the gallery) | MIT · Apache-2.0 | The data-agent variant reads dbt model docs **before** querying — documentation as a precondition of SQL, not an afterthought. |
| **A personal assistant with its own auth** | [`personal-agent-template`](https://github.com/vercel-labs/personal-agent-template) · 499★ | MIT | ⚠️ **Nuxt 4 + Better Auth, not Next.js** — read it for the agent side, not the app shell. |
| **An agent answering from an approved corpus** | [`eve-design-template`](https://github.com/vercel-labs/eve-design-template) · 55★ | MIT | A reviewed, **versioned** corpus of org-approved guidance as the only source — the grounding half of §11. ⚠️ eve `1.0.0-rc.0`. |
| **Memory that survives conversations** | [`OpenInstinct`](https://github.com/Merit-Systems/OpenInstinct) · 497★; also the in-repo `eve-memory-agent-template` and `eve-mem0-template` | MIT · Apache-2.0 | OpenInstinct's `agent/memory/workstreams.ts` + `db/services/workstreams.ts` are still the best-specified memory slot in the catalogue — see below. |
| **A multi-tenant product on eve** | `eve-commerce-platform-template` (in-repo, gallery: "Commerce Platform") | has its own LICENSE | Its `package.json` says "self-hosted, multi-tenant", its README says "deployable to your own Vercel project" — read it for tenancy, and check the self-hosting claim yourself. `[VERIFY]` |
| **A CMS copilot** | [`sanity-copilot-eve-template`](https://github.com/vercel-labs/sanity-copilot-eve-template) · 5★ | MIT | GROQ queries and edits, schema inspection, drafts and releases — the reference if `module-add cms` ever needs an agent side. |
| **Scheduled social publishing** | [`typefully-eve-template`](https://github.com/vercel-labs/typefully-eve-template) · 8★ — **archived** | MIT | A publishing **queue** the agent manages, with briefs pulled from Notion: the shape for "the agent drafts, a human releases". Shape only. |
| **Media processing with approval** | [`mux-video-agent`](https://github.com/muxinc/mux-video-agent) · 4★ | ⛔ **none** | Durable asset work with **human approval on write actions** — the one row where the approval gate is in the product rather than in a doc. Ideas only, no text. |

**Not covered above, listed in the gallery:** Coding Agent, Web Chat, BELL Stack, Discord, Slack
Starter, Voice, Vercel Drives, TanStack (Start), Contentful, Content Agent, Agent with Python. Open the
gallery for those; none changes a decision this file routes. **Gone since October:**
`eve-llm-council-template` (no longer in the monorepo or the gallery).

**Every template assumes Vercel somewhere** — a Deploy button, Blob-backed memory, Sign in with
Vercel, Vercel Cron, `@vercel/connect`. Before reusing one in a self-hosted project, read
`eve-concepts.md` §Self-hosting for what each of those becomes off Vercel.

## The one worth reading today: OpenInstinct's `workstreams`

A memory slot specified far past what `eve-capabilities.md` §Memory describes, and the design
decisions are the valuable part. ⚠️ Read on eve 0.66.3; the repo is on `1.0.0-rc.1` since then, so
the design decisions below stand but the file paths are `[VERIFY]`. Read 2026-10-05 from its page and confirmed against the file list
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

(Checked 2026-10-05, before the repo moved to eve 1.0 — re-read its `package.json` before relying on the numbers.)
OpenInstinct pinned `next 16.3.3`, five patches below our floor of `16.3.8`. Per the contract's own
rule — name the CVEs that apply to *this* project — the applicable set is **empty**: it uses no
`next/og` or `ImageResponse` (the September critical), configures no `images.remotePatterns` (the
high SSRF is conditional on it), and sets no `cacheComponents` (the two `use cache` leaks need it).
Still worth bumping, since patches are cheap; not an alarm. The same check belongs on any template
before a deploy — `vercel-deploy` §Also check the Next.js security floor.
