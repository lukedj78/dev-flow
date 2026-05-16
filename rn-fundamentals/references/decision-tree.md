> Sources: docs.expo.dev/workflow/overview, docs.expo.dev/development-builds, internal opinion.

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
Adding any of: custom native module, config plugin, custom build flag?
├── NO  → EXPO GO. Faster onboarding for the team.
└── YES → DEV CLIENT (expo-dev-client). Build once per native change.
```

**Default for a brand-new app: Expo Go. Switch to dev client the day you add Reanimated 3 + native config OR any expo-* module that needs prebuild (very few do).**

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
