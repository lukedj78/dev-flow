---
name: rn-fundamentals
description: 'Use at the start of any React Native or Expo task to lock in foundational choices: Expo managed workflow as default, latest Expo SDK with New Architecture ON, TypeScript, npm. Triggers on: "starting a new RN/Expo project", "what is the right architecture for an Expo app", "managed vs bare workflow", questions about Fabric/Hermes/JSI/New Architecture, "differences between RN and React web". Also triggers as a precondition when any other rn-* skill is selected and project setup is unclear. Not for: styling (rn-styling), navigation (rn-expo-router), data (rn-data-fetching).'
---

# rn-fundamentals — foundational rules for React Native + Expo

This skill is the prerequisite read for any RN/Expo work. It sets the four non-negotiables and points you to deeper concept material when needed.

## The 4 non-negotiables

1. **Expo managed workflow** is the default. Bare workflow / `react-native init` only if there is a documented native dependency Expo cannot wrap.
2. **Latest stable Expo SDK** at bootstrap time, with **New Architecture ON** (`newArchEnabled: true` in `app.json`). Hermes is the default JS engine — leave it on.
3. **TypeScript** is mandatory. Template `blank-typescript`. `tsconfig.json` extends `expo/tsconfig.base`.
4. **npm** is the package manager (matches Expo defaults and `npx create-expo-app`). No Yarn, no pnpm in this set.

## Quick decision tree

- "Should I use Expo or bare RN?" → `references/decision-tree.md`
- "What versions am I targeting?" → `references/stack-defaults.md`
- "Why does X behave differently than React on the web?" → `references/concepts.md`
- "Is this an OK pattern at the foundational level?" → `references/patterns.md`

## Common anti-patterns (NEVER do)

- ❌ `npx react-native init` when Expo managed would have worked — Expo is the default.
- ❌ Leaving New Architecture OFF on a new project — opt out only with a written reason.
- ❌ Mixing `yarn` and `npm install` in the same project.
- ❌ Pinning Expo SDK to a version older than the current stable without justification.

## Sources

- Course: codewithbeto.dev/rnCourse — lessons 1, 2, 3, 5, 6, 12 + "Introduction" module (free).
- Official: https://reactnative.dev/architecture/landing-page
- Official: https://docs.expo.dev/get-started/introduction/
