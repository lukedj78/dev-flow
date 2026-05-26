---
name: rn-module-add
description: 'Use to wire a backend/infra module (auth, db, storage, realtime, push, payments) into a scaffolded Expo + RN app. Reads .workflow/meta.json with stack.framework="expo-rn" and the user-chosen provider for each module (Supabase, Firebase, custom REST, tRPC, RevenueCat). Installs deps, generates the wiring code (lib/auth.ts, lib/supabase.ts, etc.), updates meta.json#stack to record the choice. Always idempotent. Triggers on: "add auth", "wire up db", "set up Supabase", "set up Firebase", "add payments", "add push" (the server-side part), "aggiungi modulo X". Not for: building UI for the module (rn-add-screen does the login screen, etc.), client-side knowledge only (rn-backend, rn-push-notifications), scaffolding (rn-bootstrap).'
---

# rn-module-add — wire a backend/infra module into a scaffolded RN app

## Contract

See `references/contracts.md` (vendored from `dev-flow`). Key facts:
- Reads `<project-root>/.workflow/meta.json#stack.framework` — must be `"expo-rn"`.
- Requires `meta.json#phase ≥ "scaffolded"`.
- Each module updates a specific key in `meta.json#stack`:
  - `auth` module → `meta.json#stack.auth`
  - `db` module → `meta.json#stack.db`
  - `storage` module → `meta.json#stack.storage` (new sub-key)
  - `realtime` module → `meta.json#stack.realtime` (new sub-key)
  - `push` module → `meta.json#stack.push` (new sub-key)
  - `payments` module → `meta.json#stack.payments`
- Sets `meta.json#phase = "module-added"` after the first module, then leaves it.
- Always idempotent: re-running with same provider detects existing wiring and exits 0.

## When this skill applies

- Phase is `scaffolded` or `page_generated` or `module-added`.
- User asks to add ONE module by name. (To add multiple, run the skill multiple times.)
- Orchestrator routes here from `dev-flow`.

## Knowledge dependencies (read these first)

- `~/my-skills/rn-fundamentals/SKILL.md` — TypeScript strict, modern primitives.
- `~/my-skills/rn-backend/SKILL.md` — provider-agnostic client-auth architecture.
- `~/my-skills/rn-backend/references/<provider>.md` — provider-specific wiring (supabase.md / firebase.md / custom-rest.md / trpc.md).
- `~/my-skills/rn-push-notifications/references/setup.md` — for the push module.
- `~/my-skills/rn-publishing-payments/references/revenuecat.md` — for the payments module.

## Workflow

### Step 1 — Verify preconditions

Read `.workflow/meta.json`. Abort if `stack.framework != "expo-rn"` or `phase < "scaffolded"`.

### Step 2 — Identify the module + provider

Module the user requested: one of `auth | db | storage | realtime | push | payments`.

If the user didn't specify a provider, default to:
- `auth`, `db`, `storage`, `realtime` → **Supabase** (the default in `rn-backend/references/decision-tree.md`).
- `push` → **expo-notifications + Expo push service** (the default).
- `payments` → **RevenueCat** (the default).

If the user specifies a non-default provider, accept it: Firebase / custom-rest / tRPC for backend; Stripe for non-digital payments.

### Step 3 — Idempotency check

Read `meta.json#stack.<module-key>`. If non-null:
- Same provider as requested → "Already wired with X, exiting." Phase stays.
- Different provider → REFUSE unless user passed an explicit "swap" intent. Removing one provider's code + installing another's is a multi-file change that needs explicit user confirmation. Report and stop.

### Step 4 — Install deps

Use `npx expo install ... -- --legacy-peer-deps` for any package that touches native (auth, db SDKs, payments). Use `npm install --legacy-peer-deps` for JS-only packages.

Provider matrix:

| Module | Supabase | Firebase | Custom REST | tRPC |
|---|---|---|---|---|
| auth | `@supabase/supabase-js`, `react-native-url-polyfill`, `expo-secure-store` | `@react-native-firebase/{app,auth}`, `expo-build-properties` | (uses existing `lib/api.ts`) + `expo-secure-store` | `@trpc/client`, `@trpc/react-query`, `superjson` |
| db | (same as auth) | `@react-native-firebase/firestore` | (uses `lib/api.ts`) | (uses tRPC) |
| storage | (uses `@supabase/supabase-js`) | `@react-native-firebase/storage` | `expo-file-system` + custom upload | (uses tRPC or REST) |
| realtime | (uses `@supabase/supabase-js`) | (uses `@react-native-firebase/firestore`) | (WebSocket of your choice) | (tRPC subscriptions) |
| push | `expo-notifications`, `expo-device` | (same + `@react-native-firebase/messaging`) | (same; server-side uses your backend) | (same) |
| payments | `react-native-purchases` (RevenueCat) | (same) | (same) | (same) |

### Step 5 — Generate the wiring

For each (module, provider) combination, write to `<project-root>/lib/`:

- `auth/Supabase` → `lib/supabase.ts` (client) + `lib/auth.ts` (sign-in/out hooks). See `~/my-skills/rn-backend/references/supabase.md`.
- `auth/Firebase` → `lib/firebase.ts` + `lib/auth.ts`. See `~/my-skills/rn-backend/references/firebase.md`.
- `auth/custom-rest` → `lib/api.ts` (already exists from rn-bootstrap, extend with refresh-on-401) + `lib/auth.ts`. See `~/my-skills/rn-backend/references/custom-rest.md`.
- `auth/tRPC` → `lib/trpc.ts` + `lib/auth.ts`. See `~/my-skills/rn-backend/references/trpc.md`.
- `payments/RevenueCat` → `lib/purchases.ts` + `hooks/usePro.ts`. See `~/my-skills/rn-publishing-payments/references/revenuecat.md`.
- `push/expo-notifications` → `lib/push.ts` + edits to `app/_layout.tsx` (handlers + permissions). See `~/my-skills/rn-push-notifications/references/patterns.md`.

ALWAYS also create `store/auth.ts` (Zustand) and ensure `app/(app)/_layout.tsx` redirects when unauthenticated — see `~/my-skills/rn-backend/references/patterns.md`.

### Step 6 — Update `.env.example` + `app.json`

Per provider, add the env vars to `.env.example`:

- Supabase: `EXPO_PUBLIC_SUPABASE_URL=`, `EXPO_PUBLIC_SUPABASE_ANON_KEY=`
- Firebase: requires `GoogleService-Info.plist` + `google-services.json` at root (manual download from Firebase console).
- Custom REST: `EXPO_PUBLIC_API_URL=`
- tRPC: `EXPO_PUBLIC_API_URL=`
- RevenueCat: `EXPO_PUBLIC_REVENUECAT_IOS_KEY=`, `EXPO_PUBLIC_REVENUECAT_ANDROID_KEY=`

For Firebase or RevenueCat or push notifications, add the relevant `app.json` config plugin entries (see provider-specific reference).

### Step 7 — Verify

Run `npx tsc --noEmit`. Must pass. If not, fix the wiring before reporting.

For modules with native config plugin changes (Firebase, push), the next build will require a new `eas build --profile development`. Print a reminder.

### Step 8 — Update meta.json + commit

Update `meta.json`:
- `stack.<module>`: set to the provider name (e.g. `"supabase"`, `"firebase"`, `"custom-rest"`, `"trpc"`, `"revenuecat"`, `"stripe"`, `"expo-notifications"`).
- `phase`: if currently `"scaffolded"` or `"page_generated"`, set to `"module-added"`. Otherwise leave.
- `history`: append `{ skill: "rn-module-add", ran_at: <iso>, inputs: { module, provider }, outputs: [<files>], phase_before, phase_after }`.

If git repo: `git add` the new files + `git commit -m "feat(<module>): wire <provider>"`.

## Common anti-patterns (NEVER do)

- ❌ Wire two providers for the same module simultaneously (e.g. Supabase + Firebase auth) — pick one.
- ❌ Skip the `stack.<module>` update in meta.json — future re-runs will re-install.
- ❌ Hardcode secrets in `lib/*.ts` — read from `process.env.EXPO_PUBLIC_*`.
- ❌ Generate wiring without running `tsc --noEmit` — broken project shipped to user.
- ❌ Add a module that requires a new dev build without printing the "rebuild required" reminder.
- ❌ Use `npm install` without `--legacy-peer-deps` — fails on Expo SDK 54 (see `rn-bootstrap` lessons-learned).

## Sources

- Course: codewithbeto.dev/rnCourse — Backend Basics + Supabase + Publishing/Payments modules (paid).
- Knowledge skills consumed (see above).
