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
| `scaffolded` | `rn-add-screen` (Wave 2) for UI work, `rn-module-add` (Wave 3) for auth/db/payments |
| `feature_complete` | `rn-eas-deploy` (Wave 3) |

Skills marked "Wave 2/3" are not yet implemented as of this snapshot — they exist as design entries in the spec.

## Knowledge skills available (auto-invoked when context matches)

- `rn-fundamentals` — foundational rules (Expo / TS / New Architecture)
- `rn-styling` — NativeWind v4, safe area, dark mode
- `rn-expo-router` — file-based routing, typed routes, modals

Wave 2/3 additions: `rn-components-apis`, `rn-data-fetching`, `rn-animations-gestures`, `rn-push-notifications`, `rn-backend-supabase`, `rn-eas-build-submit-update`, `rn-publishing-payments`.

## Family membership

Operative skills in this stack: `rn-bootstrap` (Wave 1), `rn-add-screen` (Wave 2), `rn-module-add` (Wave 3), `rn-write-tests` (Wave 2), `rn-eas-deploy` (Wave 3).

## NEVER use these skills on this stack

- `design-md-to-app` — Next.js scaffolder, would produce a web app.
- `module-add` — Next.js module wirer.
- `screenshot-to-page` — Next.js screen generator.
- `setup-deploy` — Vercel/Render/Fly, not EAS.

(These are reserved for `stack.framework="next"` and other web stacks.)
