---
name: rn-fundamentals
description: 'Use at the start of any React Native or Expo task to lock in foundational choices: Expo managed workflow as default, latest Expo SDK with New Architecture ON, TypeScript, npm. Triggers on: "starting a new RN/Expo project", "what is the right architecture for an Expo app", "managed vs bare workflow", questions about Fabric/Hermes/JSI/New Architecture, "differences between RN and React web". Also triggers as a precondition when any other rn-* skill is selected and project setup is unclear. Not for: styling (rn-styling), navigation (rn-expo-router), data (rn-data-fetching).'
---

# rn-fundamentals — foundational rules for React Native + Expo

This skill is the prerequisite read for any RN/Expo work. It sets the four non-negotiables and points you to deeper concept material when needed.

## The 4 non-negotiables

1. **Expo managed workflow** is the default. Bare workflow / `react-native init` only if there is a documented native dependency Expo cannot wrap.
2. **Latest stable Expo SDK** — `57.0.16` on 2026-08-26 (`npm view expo dist-tags`); `[VERIFY]` at bootstrap time, quarterly cadence. **New Architecture is on and not optional** from SDK 55 onward — do *not* set `newArchEnabled`: it is ignored, and **confirmed absent from `@expo/config-types@57.0.2`'s `ExpoConfig` schema** (zero occurrences), so it is not merely discouraged — there is no key to set. Hermes is the engine.
3. **TypeScript** is mandatory. `tsconfig.json` extends **`expo/tsconfig.base`** — confirmed shipping at the root of `expo@57.0.16`, and it sets `moduleResolution: "bundler"` (which is why relative imports here need no `.js` extension).
   ⚠️ **`blank-typescript` is our choice, not the CLI's default.** From `create-expo-app@4.0.0`'s own help: *"NPM template to use: default, blank, blank-typescript, tabs, bare-minimum. **Default: default**"* — and `default` is the one it labels *"recommended for most app developers"*. Pass `-t blank-typescript` explicitly or you get something else.
4. **npm** is the package manager. ⚠️ This is a **house rule**, not the CLI's preference: `create-expo-app@4.0.0` *resolves* the package manager from your environment — the `--use-npm` / `--use-yarn` / `--use-pnpm` flags are **gone** (zero occurrences in the package). Invoking it with `npx` gets you npm because npx *is* npm, not because the CLI prefers it. No Yarn, no pnpm in this set.
5. ⚠️ **`create-expo-app@4` writes agent files by default** — `AGENTS.md`, `CLAUDE.md` and `.claude/settings.json`, opt out with `--no-agents-md`. On a dev-flow project decide deliberately: a scaffolded `CLAUDE.md` sitting next to `.workflow/` is a second set of instructions nobody reconciled.

## Source of truth (Expo)

This skill set (rn-fundamentals + its 6 siblings: rn-data-fetching, rn-expo-router, rn-backend, rn-push-notifications, rn-publishing-payments, rn-animations-gestures) encodes the **workflow and opinionated stack choices** — Expo managed, New Architecture on, TanStack Query, Reanimated 4, and so on. It is NOT a frozen copy of the Expo/RN API, and it goes stale every time a new SDK ships.

For anything sensitive to the current Expo SDK — exact API shapes, CLI commands and flags, config-plugin options, deprecations, EAS behavior — do not trust this skill's wording blindly. In priority order, the authoritative source is:

1. **Live Expo docs** — https://docs.expo.dev/ (always current for the installed SDK).
2. **Expo MCP server** — `https://mcp.expo.dev/mcp` — live docs/CLI/EAS reference exposed as MCP tools. **If it is connected in this session, prefer it** over anything written across this skill set for current-version details.
3. **Official `expo/skills`** — installable as a Claude Code plugin, or via `npx skills add expo/skills` — maintained by Expo directly against the SDK release cadence.

Last swept **2026-08-26** against `expo@57.0.16`, `create-expo-app@4.0.0`, `@expo/config-types@57.0.2` and `zustand@5.0.15`. Any version number, CLI command, or config key in this skill set marked `[VERIFY]` above is a candidate to have drifted since — check it against the sources above before relying on it, the same way `eve-agent` defers to `node_modules/eve/docs` instead of guessing the eve API.

## Quick decision tree

- "Should I use Expo or bare RN?" → `references/decision-tree.md`
- "What versions am I targeting?" → `references/stack-defaults.md`
- "Why does X behave differently than React on the web?" → `references/concepts.md`
- "Is this an OK pattern at the foundational level?" → `references/patterns.md`
- "Where does this piece of state live?" → `references/zustand-rn.md` (Zustand as the client-state store: selectors + `useShallow`, slices, `persist` with AsyncStorage, ⚠️ the async-hydration race — and the table for what does **not** belong in it: server data → TanStack Query, form fields → the form lib, ephemeral UI → `useState`)

## Common anti-patterns (NEVER do)

- ❌ `npx react-native init` when Expo managed would have worked — Expo is the default.
- ❌ Leaving New Architecture OFF on a new project — opt out only with a written reason.
- ❌ Mixing `yarn` and `npm install` in the same project.
- ❌ Pinning Expo SDK to a version older than the current stable without justification.

## Sources

- Course: codewithbeto.dev/rnCourse — lessons 1, 2, 3, 5, 6, 12 + "Introduction" module (free).
- Official: https://reactnative.dev/architecture/landing-page
- Official: https://docs.expo.dev/get-started/introduction/
