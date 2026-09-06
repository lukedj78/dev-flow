# External skills — what dev-flow can point you at, and never installs

dev-flow ships its skills free and offline-capable. It is also allowed to
**tell you that somebody else's skill exists** when your project reaches a point
where one would help.

That is all this file is: a short list of third-party agent skills, what each one
is for, and the one moment in a dev-flow project when mentioning it is useful.

## The rules, so this never turns dev-flow into a paid product

1. **dev-flow suggests. The user installs.** Never run an install command for one
   of these on the user's behalf, never add one to `install.sh`, never make a
   dev-flow skill import or require one.
2. **Say the price in the same breath.** If a skill needs a paid account, the
   suggestion states what it costs *before* the user goes anywhere near a signup
   page. A payment step must never arrive as a surprise.
3. **Name what dev-flow already does for free.** Every row below has a "what we do
   instead" column. If the free path covers the need, say so and let the user
   decide — the suggestion is an option, not a recommendation.
4. **Only when the project actually asks.** These come up when the work reaches
   them, not in a menu of possibilities at kickoff.
5. **Nothing here is a dependency.** Remove every row and dev-flow still does
   everything it did before.

## The list

| Skill | What it does | When to mention it | Cost | What dev-flow does instead |
|---|---|---|---|---|
| [`sleekdotdesign/agent-skills`](https://github.com/sleekdotdesign/agent-skills) — `sleek-design-mobile-apps` | Designs mobile screens through [sleek.design](https://sleek.design)'s API and returns them rendered, with HTML / React Native / SwiftUI implementation notes | A mobile project (`stack.framework = "expo-rn"`) at `prd_drafted` → `design_extracted`, when the user has **no** design and does not want to write a DESIGN.md by hand | Free trial ≈ one design run; sustained use needs Pro, **$49.99/mo** ($30/mo billed yearly) | `design-md-to-app`'s DESIGN.md path: extract a style from a reference (e.g. [styles.refero.design](https://styles.refero.design)) or write the block by hand, then materialise it. Free, and the tokens stay in the repo. |
| [`rorkai/app-store-connect-cli-skills`](https://github.com/rorkai/app-store-connect-cli-skills) — 25 skills over the `asc` CLI | Drives the App Store Connect API from the terminal: release flow, TestFlight orchestration, metadata and screenshot sync, crash triage, submission health, signing, ASO audit, RevenueCat catalog sync. Installed by the CLI itself (`asc install-skills`), which pins a reviewed commit, verifies every file and rolls back on failure — `git` only, no Node or npx | A mobile project at `feature_complete` → `deployed` that is going to the **App Store**, when the release is repeated often enough that the dashboard is the bottleneck — or the moment someone wants TestFlight crashes and tester feedback as text an agent can read | **Free** — CLI and skills both MIT. Costs an App Store Connect API key (`.p8`), which is a production credential. Telemetry is on by default and honours `DO_NOT_TRACK=1` (checked 2026-09-06) | `rn-eas-deploy` ships the release without it: EAS builds and submits the artifact, and the human finishes in the dashboard. That path stays documented and stays the default. What dev-flow has no free equivalent for is the read side — review blockers, TestFlight crashes, metadata and screenshot upload — and `rn-eas-deploy/references/asc-cli.md` says so, plus who may run what |

Install, when the user wants one:

```bash
npx skills add <owner>/<repo>
```

That is the [`skills`](https://www.npmjs.com/package/skills) CLI (the open agent-skills
ecosystem). It writes to `.agents/skills/` in the working directory. Verified at
`skills@1.5.23`.

## Adding a row

Before adding one, check it earns its place:

- It does something **no dev-flow skill does**. An external skill that duplicates
  `design-md-to-app` or `rn-bootstrap` is not an option, it is a fork.
- You have **read its SKILL.md**, not just its README — including what it sends
  where, and which host it talks to.
- Its licence and its price are **stated as facts you checked**, with the date.
- The "what dev-flow does instead" column is filled in honestly. If dev-flow has
  no free equivalent, say that plainly too — that is the strongest reason for a
  row to exist.

## What this is not

Not a plugin system, not a registry, not a tier of skill. dev-flow does not load,
validate, version or update anything listed here. It knows these exist, the way a
good colleague knows which tool down the hall does the thing you just asked about.
