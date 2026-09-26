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
| [`mattpocock/skills`](https://github.com/mattpocock/skills) — `resolving-merge-conflicts` | Resolves an in-progress merge/rebase hunk by hunk from each side's **primary sources** (commits, PRs, issues), keeps both intents where compatible, names what it dropped, runs the repo's checks, finishes the operation | A merge or rebase stops on conflicts — typically when parallel sessions or worktrees land back | **Free** — MIT, no account, no network beyond git (read 2026-09-15) | `references/merge-conflicts.md` covers what the skill cannot know about a dev-flow project — derived files to regenerate, `meta.json` by field, the gates to rerun — and overrides its last step: stage by name, commit only a merge the user asked for. It does not restate the method |
| [`Rizzo-AI-Academy/rizzo-flow`](https://github.com/Rizzo-AI-Academy/rizzo-flow) — `skills/rizzo-flow` | Drives **Rizzo Flow**, a local decision engine with a Jev/TypeSafe-compatible HTTP API: typed answers (yes-no, one of ≤ 26 options, a score, a number with anchors) with probabilities and zero generated tokens, ≈ 50 ms each on a local GPU. The skill carries the parts that matter — when *not* to use it, how to write the questions, and how to read uncalibrated probabilities. | A project that must classify, route or triage text **without sending it outside its perimeter** (professional secrecy, special-category data, an `eu-sovereign` residency decision), or that wants the same typed decisions free in dev, CI and evals. Read `eve-agent/references/eve-patterns.md` §13 first: it owns the choice between this and hosted Jev, and the wiring. | Free — Apache-2.0, weights included. The cost is the hardware: an always-on EU GPU (Scaleway `L4-1-24G` ≈ €575/month, verified 2026-09-26) or your own machine. Vercel has no GPU, so it is always a separate service. | Nothing: dev-flow has no local decision engine. The hosted path is Jev through AI Gateway (`eve-patterns.md` §13), which costs $0.042 per million input tokens and sends the text to a US-hosted service. |

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
