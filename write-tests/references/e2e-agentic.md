# write-tests → e2e (agentic end-to-end, web **and** mobile)

**Status: read, not adopted** (`dev-flow/references/resources.md` §Mobile). Nothing routes here by
default, `stack.test` does not gain the layer on its own, and no project uses it today. This file
exists so that a project that *chooses* it starts from the decisions already taken, instead of
discovering them one failed run at a time.

[e2e](https://e2e.tester.army/docs) (tester-army, **Apache-2.0**, `e2e@0.19.0`) writes end-to-end
tests where each step is either exact (`screen`, `expect` — Playwright underneath on web) or a goal
handed to an agent (`agent.act('upgrade to the Pro plan')`). The mobile engine is **agent-device**
(callstack, MIT): a native accessibility tree, not screenshots.

## Why this is a reference and not a skill

Our skills own a **stage**; our references own a **technique**. Playwright and Maestro are already
techniques inside a skill, and e2e is a third — the first one that spans web and mobile. A skill of
its own would create a second authority over "write an end-to-end test", which is the mistake we
avoided when we merged emilkowalski's animation skills into `transitions` instead of installing
them. `rn-write-tests` points here for the mobile half; there is one copy of this text.

## Three gates before the first test

1. **`registry-intake`, twice.** `npx e2e init` writes a third-party `SKILL.md` into
   `.agents/skills/e2e/` (symlinked into `.claude/skills/`) **and** registers an MCP server in
   `.mcp.json` and `.cursor/mcp.json`. Both are instructions this agent would then obey. The user
   runs `init`; the agent runs `skill-review` and `mcp-review`, shows the report, and pins with
   `skill-approve` / `mcp-approve`. Reviewed 2026-10-10 at 0.19.0: the skill was clean apart from
   **K8** (no `license:` in the frontmatter, Apache-2.0 LICENSE present in the package) and two
   **K4** false positives, both the documented `--yes` flag. The MCP entry takes **M3** — `npx e2e
   mcp` is unpinned.
2. **`stack.test` gains the layer**, as a string: `vitest+playwright+e2e` on web,
   `jest-expo+rntl+e2e` on mobile. Unit layer first, end-to-end last.
3. **A model.** Agent steps need one, and **Claude Pro carries no API credits**: on Max or Team you
   link a Claude Console organization and use the plan's monthly credits (`ANTHROPIC_API_KEY`), or
   you bring a paid key or a local endpoint. `e2e` does not read `.env` files — export it in the
   shell and in CI. Tests with no agent step need no model at all.

## The cost rule — deterministic by default

An agent step costs money **every time it runs that is not a cache replay**, and `prd-to-tasks`
generates a test per feature: a suite is a recurring bill that grows with coverage. Two rules, and
they are not style preferences:

- **A locator first.** `agent.act` is for a goal whose path may change ("book the first free slot
  on Tuesday"); a known field, an exact value and a visible outcome are `screen` and `expect`. A
  test written entirely in goals is a test that pays to re-derive what a selector already knows.
- **`--strict-cache` in CI.** Without it a stale recording quietly falls back to a live agent run,
  and the bill is the first thing that tells you. With it the step fails `REPLAY_STALE`, makes no
  model call, and someone re-records deliberately.

**What the cache spares, and what it never spares.** A verified `agent.act` replays its recorded
actions with no model call. **`agent.assert`, `agent.waitFor` and `agent.extract` always call the
model** — every run, cache or not. So the cheap shape is *agent does, locator checks*: the judgment
is the expensive half.

A miss costs a full agent run: changing the instruction, a param, the agent, its context or the
engine invalidates the entry; changing the model does not. Wrap timestamps and other moving values
in `unique()` or every run is a miss. Entries live in `.e2e/cache/`, gitignored by `init` — commit
them only after reading them, because typed values are stored verbatim.

## The canonical shape

```ts
// tests/booking.e2e.ts
import { describe, test } from '@e2e-dev/web'
import { expect } from 'e2e'

describe('booking', () => {
  test('books the first free slot', async ({ app, agent, screen }) => {
    await app.open('/prenota')

    // The goal: the path through the week strip is allowed to change.
    await agent.act('book the first free slot on {day}', { params: { day: 'mercoledì' } })

    // The check: exact, cheap, and it is what lets the step replay later.
    await expect(screen.getByRole('status')).toHaveText('Prenotazione confermata')
    await expect(screen.getByRole('listitem')).toHaveCount(1)
  })
})
```

Every `agent.act` is followed by an `expect` — not only to assert, but because **a verified step is
what the cache records**. An `act` nobody checks is an `act` that pays full price forever.

## Config, and the one trap that bites Next.js 16

`e2e.config.ts` at the project root, default-exporting an object that ends in `satisfies E2EConfig`;
an unknown key is `INVALID_CONFIG` at load.

⚠️ **A Next 16 dev server blocks cross-origin requests to its dev resources.** A target that opens
`127.0.0.1` or `[::1]` while `next dev` identifies as `localhost` **never hydrates** — the page
loads and nothing works. Either point the target at `http://localhost:<port>`, or add the host to
`allowedDevOrigins` in `next.config.ts`. This is the first thing to check when a test sees a dead
page.

## What it does not replace

- **Playwright stays.** The web engine *is* Playwright, the two run side by side, and their docs
  document migrating one file at a time. Keep the existing specs; do not rewrite a suite that works.
- **Directory names: do not rename either.** Our Playwright specs live in `e2e/<slug>.spec.ts`
  (`test-page-e2e.md`) and the tool's default glob is `tests/**/*.e2e.ts`. They coexist. The word
  "e2e" then means two things in one repo — the directory and the tool — which is survivable only
  because each has a fixed home. Moving either to "tidy up" breaks both globs.
- **Maestro keeps the two-user flow.** `rn-write-tests` uses Maestro for the check that finds
  authorization bugs between identities: user A takes the slot, user B must see it taken — two
  `runFlow` sign-ins in one file with `clearState` between them. e2e on mobile has **no session
  save/restore** (`test.setup` is unsupported there), so the same flow means signing in inside each
  test: expressible, but it pays a sign-in per test and loses what Maestro gives for free.

## Secrets, and the boundary they do not cross

`credentials.user(name)` and `secrets` hand the runner a **handle with no plaintext accessor**: the
model sees a name and a purpose, the runner types the value, and after a secret fill the attempt
takes no further screenshots. Their own docs state the holes, and they are ours to respect:
redaction matches strings, so a transformed value (last four characters, base64) passes through;
video and binary downloads are not masked; `command.log` records the app's stdout verbatim.

⚠️ **There is no origin allowlist.** The agent may follow the app to another site and use the
step's secrets there. Nothing is sandboxed, and cache entries are unsigned and replay with your
permissions. On a project with real credentials this belongs in the `compliance-audit` notes, not
only here.

Telemetry goes to `eu.i.posthog.com` with a published field list (never URLs, instructions, page
content or screenshots). Turn it off per project: `E2E_TELEMETRY_DISABLED=1` or the cross-tool
`DO_NOT_TRACK=1`.

## Reading a failure

Each failing test writes `.e2e/results/<test>/trace.md` — the failing line, every step, console
errors, failed requests and the screen at failure, written to be read by an agent. Use
`.e2e/report.json` for scripts. `--ai-trace` dumps the model calls; it is large, so read it with a
tool rather than loading it into context.
