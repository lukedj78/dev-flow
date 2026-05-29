> Sources: internal spec docs/superpowers/specs/2026-05-16-rn-expo-skills-set-design.md

# Stack: expo-rn

Identifier in `meta.json#stack.framework`: **`"expo-rn"`**

## What it means

The project targets mobile (iOS + Android) using **Expo + React Native** with the opinionated stack defined by the `rn-*` skill family.

## `meta.json#stack` shape for this stack

```json
{
  "stack": {
    "framework": "expo-rn",
    "ui": "nativewind",
    "auth": null,
    "db": null,
    "payments": null,
    "deploy": null
  },
  "stack_config": {
    "expo_sdk": "55",
    "state_lib": "zustand",
    "data_lib": "tanstack-query"
  }
}
```

The `stack` object follows the existing contract (see `contracts.md`). `framework`, `ui`, and the four backend slots (`auth`, `db`, `payments`, `deploy`) are populated incrementally — `rn-bootstrap` sets `framework` + `ui`; `rn-module-add` (Wave 3) fills the rest.

`stack_config` is a free-form sub-object specific to this stack — version of Expo SDK, choice of state/data libs, etc. Not used by the contract, only by the `rn-*` skills.

## Routing — which skill for which phase

| Phase | Skill |
|---|---|
| `prd_drafted` or `design_extracted` | `rn-bootstrap` |
| `scaffolded` or `page_generated` or `module_added` | `rn-add-screen` (UI), `rn-write-tests` (tests), `rn-module-add` (auth/db/storage/realtime/push/payments) |
| `feature_complete` | `rn-eas-deploy` |
| `deployed` | maintenance loop: `rn-add-screen` for new features, `rn-eas-build-submit-update` for OTA hotfixes |

All skills shipped — Wave 3 complete as of 2026-05-22.

## Knowledge skills available (auto-invoked when context matches)

Wave 1:
- `rn-fundamentals` — foundational rules (Expo / TS / New Architecture)
- `rn-styling` — NativeWind v4, safe area, dark mode
- `rn-expo-router` — file-based routing, typed routes, modals

Wave 2:
- `rn-components-apis` — core RN components + platform APIs (Pressable / expo-image / FlashList / KeyboardAvoidingView / Linking)
- `rn-data-fetching` — TanStack Query, mutations, optimistic updates, infinite scroll

Wave 3:
- `rn-animations-gestures` — Reanimated 4, Gesture Handler 2, worklets, layout animations
- `rn-push-notifications` — expo-notifications, permissions, 3 entry paths, deep linking from notification
- `rn-backend` — provider-agnostic auth/db patterns (sub-references: Supabase default, Firebase, custom REST, tRPC)
- `rn-eas-build-submit-update` — eas.json profiles, credentials, OTA channels, EAS Workflows CI
- `rn-publishing-payments` — App Store + Play Store, IAP via RevenueCat, store assets, review guidelines

## Family membership

Operative skills in this stack (all shipped):
- `rn-bootstrap` — scaffold an Expo app from PRD + DESIGN
- `rn-add-screen` — add a route to a scaffolded app (5 canonical templates)
- `rn-write-tests` — Jest + RNTL + Maestro setup + tests
- `rn-module-add` — wire auth/db/storage/realtime/push/payments (provider-agnostic)
- `rn-eas-deploy` — end-to-end deploy orchestration (init → preview → production → submit → channels)

## NEVER use these skills on this stack

- `design-md-to-app` — Next.js scaffolder, would produce a web app.
- `module-add` — Next.js module wirer.
- `screenshot-to-page` — Next.js screen generator.
- `setup-deploy` — Vercel/Render/Fly, not EAS.

(These are reserved for `stack.framework="next"` and other web stacks.)
