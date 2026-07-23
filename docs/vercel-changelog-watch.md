# Vercel changelog watch

eve is in **beta** and Vercel ships to the changelog frequently. This file tracks changelog
items that affect our skills, so the skills stay current. It is a living watchlist —
periodically fetch <https://vercel.com/changelog>, add new relevant rows here, and apply the
change to the affected skill.

## Skills that track Vercel (check these when a relevant item ships)

| Skill | Vercel surface it depends on |
|---|---|
| `eve-agent` | eve framework + CLI, Vercel AI Gateway (models, service tiers), `eve deploy` |
| `module-add` (voice / realtime / deploy) | AI Gateway audio + realtime, `stack.deploy = "vercel"` |
| `design-md-to-app` | `stack.deploy = "vercel"` |
| `monorepo-bootstrap` | Vercel deploy for `apps/web` |
| `setup-deploy` | Vercel project setup |

## How to run a watch pass

1. Fetch <https://vercel.com/changelog> — read the newest entries since the last dated pass below.
2. For each entry, classify: **relevant** (touches a skill above) vs **not relevant** (a model id, an unrelated product).
3. For relevant items, edit the affected skill (mark new/unstable API `[VERIFY]` against the installed docs — eve is beta), and add a row to the log below with status `applied`.
4. Update the "Last pass" date. For anything ambiguous or out of scope, ask the user.

**Last pass: 2026-07-23** (entries through 2026-07-22).

## Log

| Date | Changelog item | Relevant to | Status |
|---|---|---|---|
| 2026-07-22 | **eve extensions** — installable packages bundling tools/connections/skills/instructions/hooks (`npx eve extension init`, `agent/extensions/<name>.ts`, `eve extension build`, `defineExtension`, `disableTool`, `toolResultFrom`) | `eve-agent` | ✅ applied — new **Extension** capability in `eve-capabilities.md` + SKILL.md + CLI ref |
| 2026-07-22 | **AI Gateway streaming transcription** — AI SDK `streamTranscribe` for incremental transcripts | `module-add` voice/realtime | ✅ applied — note in `module-voice.md` STT step |
| 2026-07-21 | **AI Gateway service tiers** — `providerOptions.gateway.serviceTier` (`default`/`priority`/`flex`), OpenAI+Gemini only | `eve-agent`, `module-add` voice | ✅ applied earlier (`eve-scaffold.md §3`, `module-voice.md` caveat) |
| 2026-07-21 | Gemini 3.6 Flash / 3.5 Flash-Lite, Laguna S 2.1 on AI Gateway | — | ⏭️ not relevant — our skills don't pin model ids (default `anthropic/claude-sonnet-5` is documented, model choice is per-project) |
| 2026-07-21 | Vercel Connect: 90+ preset connectors | — (watch) | ⏭️ not applied — possible future tie-in with eve `connections`; revisit if it exposes an eve-facing API |
| 2026-07-21 | Vercel MCP supports purchases; Python bytecode bundles | — | ⏭️ not relevant to our skills |

> Convention: `[VERIFY]` any eve/AI-SDK identifier added from a changelog against `node_modules/eve/docs/` or the installed `@ai-sdk/*` before relying on it — beta surfaces move between the changelog announcement and the shipped API.
