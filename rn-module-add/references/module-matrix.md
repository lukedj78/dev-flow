> Sources: synthesized from rn-backend, rn-push-notifications, rn-publishing-payments references.

# Module matrix — what gets wired per (module, provider)

This is the operational lookup for `rn-module-add`. For each row, the skill consumes the indicated knowledge skill's references and generates the listed files.

## `auth`

| Provider | Knowledge ref | Files generated | Native rebuild needed? |
|---|---|---|---|
| Supabase | `rn-backend/references/supabase.md` | `lib/supabase.ts`, `lib/auth.ts`, `store/auth.ts`, `app/(app)/_layout.tsx` patch | No (JS-only SDK) |
| Firebase | `rn-backend/references/firebase.md` | `lib/firebase.ts`, `lib/auth.ts`, `store/auth.ts`, `app/(app)/_layout.tsx` patch, `app.json` plugin entry | **YES** (native SDK) |
| Custom REST | `rn-backend/references/custom-rest.md` | `lib/api.ts` extended (refresh-on-401), `lib/auth.ts`, `store/auth.ts`, `lib/token-store.ts`, `app/(app)/_layout.tsx` patch | No |
| tRPC | `rn-backend/references/trpc.md` | `lib/trpc.ts`, `lib/auth.ts`, `store/auth.ts`, `app/_layout.tsx` patch (provider) | No |

## `db`

| Provider | Knowledge ref | Files generated | Notes |
|---|---|---|---|
| Supabase | `rn-backend/references/supabase.md` | (no new file — uses `lib/supabase.ts` from auth) + `lib/queries/` templates | Run `npx supabase gen types typescript` to generate `types/database.ts` |
| Firebase | `rn-backend/references/firebase.md` | (uses `lib/firebase.ts`) + `lib/queries/` templates | Firestore is schemaless; no type-gen step |
| Custom REST | `rn-backend/references/custom-rest.md` | (uses `lib/api.ts`) + `lib/queries/` templates | Shared types in `types/api.ts` (manual) |
| tRPC | `rn-backend/references/trpc.md` | (uses `lib/trpc.ts`) | Types auto-flow from server router |

## `storage`

| Provider | Files generated | Native rebuild? |
|---|---|---|
| Supabase | `lib/storage.ts` (wrapper over `supabase.storage`) | No |
| Firebase | `lib/storage.ts` (`@react-native-firebase/storage` wrapper) | **YES** |
| Custom REST + `expo-file-system` | `lib/storage.ts` (multipart upload to your API), `expo-file-system` install | No (Expo handles file system) |

## `realtime`

| Provider | Files generated | Native rebuild? |
|---|---|---|
| Supabase | `lib/realtime.ts` (channel helper) | No |
| Firebase | (via `onSnapshot` in queries, no new file) | No |
| Custom REST | Recommend WebSocket lib of choice (e.g. native `WebSocket` + reconnect helper) | No |
| tRPC | (via subscriptions in `lib/trpc.ts`, ws link) | No |

## `push`

| Provider | Files generated | Native rebuild? |
|---|---|---|
| expo-notifications + Expo push service | `lib/push.ts`, `app/_layout.tsx` (handlers + setNotificationHandler), `app.json` plugin entry | **YES** (after plugin add) |
| expo-notifications + APNs/FCM direct | Same as above + server-side change (out of scope of this skill) | **YES** |

The skill ALWAYS configures `expo-notifications`. The "provider" choice only changes whether your server uses Expo push API or APNs/FCM direct — that's a server concern, not a client concern.

## `payments`

| Provider | Files generated | Native rebuild? |
|---|---|---|
| RevenueCat | `lib/purchases.ts`, `hooks/usePro.ts`, `app/_layout.tsx` patch (configure on sign-in) | **YES** (`react-native-purchases` native SDK) |
| Stripe (non-digital only) | `lib/stripe.ts` (Checkout session URL handler via expo-web-browser), `expo-web-browser` install | No (WebView only) |

## Wiring conventions (regardless of provider)

- All client code goes in `lib/`.
- All Zustand stores go in `store/`.
- All TanStack Query hooks go in `lib/queries/` or `lib/mutations/`.
- All custom hooks go in `hooks/`.
- `app/_layout.tsx` patches are surgical (add the provider, the subscription, the handler — don't restructure).
- `.env.example` is updated with the provider's required env vars.

## When a module requires a native rebuild

After installation:
1. Print to the user: "This module added a native dependency. Run `eas build --profile development --platform all` before testing on a device."
2. Update `meta.json#stack_config.requires_native_rebuild = true` so downstream operations know.
3. Do NOT auto-trigger the build — let the user do it (it takes minutes and they might want to batch with other changes).
