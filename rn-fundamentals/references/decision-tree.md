> Sources: docs.expo.dev/workflow/overview, docs.expo.dev/development-builds, https://expo.dev/changelog/expo-go-and-app-store-may-2026, https://expo.dev/go, internal opinion.

# Decision tree — fundamentals

## Q1: Expo managed or bare?

```
Need a native library Expo cannot wrap?
├── NO  → MANAGED. Always start here.
└── YES → Check expo-modules registry first. Still NO?
         ├── Library is a one-off (e.g. legacy SDK) → BARE
         └── Library is broadly useful → write a config plugin instead, stay MANAGED
```

**Default: managed. 95% of apps stay here.**

## Q2: Expo Go or dev client?

```
Do you need the app on a physical iPhone?
├── YES → DEV BUILD (expo-dev-client). The App Store Expo Go can't load SDK 57.
└── NO  → Android device, or iOS simulator? Expo Go is still fine for a quick spin.
         Adding a custom native module / config plugin / custom build flag?
         └── YES → DEV BUILD anyway.
```

**Default for a brand-new app: a development build (`expo-dev-client`).**

This flipped in 2026. The App Store build of Expo Go is **frozen at SDK 54** — SDK 55, 56 and 57 were never approved by App Review, and Expo has no approved timeline. We ship **SDK 57**, so the Expo Go you install from the App Store simply cannot open our project.

What still works:
- **Android** — Expo Go is unaffected; the Play Store build tracks current SDKs.
- **iOS simulator** — current-SDK Expo Go is installed by Expo CLI (or from https://expo.dev/go), bypassing App Review entirely.
- **iOS physical device** — you need either a dev build, or `eas go` (builds *your own* copy of Expo Go and delivers it via TestFlight; requires a paid Apple Developer membership).

Expo now positions Expo Go as an educational tool for beginners' first steps and recommends development builds for real work. Treat Expo Go as a demo convenience, not the team's daily driver: one `eas build --profile development` per native change buys you a client that matches the app you actually ship.

## Q3: New Architecture ON or OFF?

```
ON, unless: a critical library is still incompatible (very rare in 2026).
```

If you turn it OFF: write the reason in `app.json` as a comment-equivalent (a `// reason` in README) and add a TODO to flip ON later.

## Q4: TypeScript strict mode?

```
ALWAYS strict: true in tsconfig.json. extends "expo/tsconfig.base".
```

## Q5: Monorepo?

Out of scope for Wave 1. If asked, defer with: "single-package Expo app for now; if you need a monorepo, that's a separate setup (pnpm workspaces or bun workspaces) outside this skill set."
