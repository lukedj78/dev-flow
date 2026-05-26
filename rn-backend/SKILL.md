---
name: rn-backend
description: 'Use to connect an Expo + RN app to a backend (auth, database, storage, realtime), agnostic of the provider. Teaches the shared patterns: secure-store for tokens, auth state via Zustand + TanStack Query, refresh-on-401 middleware, auth-gate routing via Expo Router (app)/_layout.tsx, row-level security vs API-auth concepts. Provider-specific details live in sub-references: Supabase (default, matches the course), Firebase, custom REST/JSON, tRPC. Triggers on: "setup backend", "setup auth with X", "connect Supabase/Firebase/my API", "secure token storage", "refresh token flow", "row level security". Not for: building the login UI (rn-add-screen — uses Form template), push notifications (rn-push-notifications), payments (rn-publishing-payments).'
---

# rn-backend — provider-agnostic backend integration for RN/Expo

## The 5 rules (non-negotiable, regardless of provider)

1. **Tokens in `expo-secure-store`**, never `AsyncStorage` or plain in-memory. Tokens are bearer credentials — they go in Keychain (iOS) / Keystore (Android) encrypted at rest.
2. **Auth state in a Zustand store + replicated in TanStack Query** with key `["auth", "session"]`. Zustand for synchronous reads in components and `_layout.tsx` redirect logic; TanStack Query for refetch-on-focus and revalidation.
3. **`api()` wrapper owns auth headers + refresh-on-401**. Every fetch goes through it. Refresh flow is centralized — no per-call retry logic.
4. **Auth gate via Expo Router groups**: `(auth)/` for public screens, `(app)/` for protected; the `(app)/_layout.tsx` checks the store and `<Redirect />` if no user.
5. **Sign-out clears EVERYTHING**: secure-store token, Zustand store, TanStack Query cache (`queryClient.clear()`). No "user signed out but still see old data" bugs.

## Quick decision tree

- "Which provider? Supabase / Firebase / custom REST / tRPC?" → `references/decision-tree.md`
- "What's the shared client-auth architecture?" → `references/concepts.md`
- "How do I wire it up — store, middleware, gate?" → `references/patterns.md`
- "I picked Supabase. Specifics?" → `references/supabase.md`
- "I picked Firebase." → `references/firebase.md`
- "I'm bringing my own REST/JSON backend." → `references/custom-rest.md`
- "I want tRPC end-to-end typed." → `references/trpc.md`

## Common anti-patterns (NEVER do)

- ❌ `AsyncStorage.setItem("token", token)` — use `SecureStore.setItemAsync("token", token)`.
- ❌ Reading the token inside every `api()` call from secure-store synchronously — cache it in the Zustand store, refresh from secure-store only on app start.
- ❌ Stored "logged in" boolean in the client that drifts from the server token's actual validity — single source of truth is the token + a `/me` query.
- ❌ Calling `signOut()` and forgetting to `queryClient.clear()` — next user sees previous user's posts in cache.
- ❌ Hardcoding `Authorization: Bearer xxx` in a single screen — wrap in `api()`.
- ❌ Vendor lock-in code scattered (`supabase.auth.signIn(...)` in 12 components) — wrap in `lib/auth.ts` so swapping providers touches one file.

## Sources

- Course: codewithbeto.dev/rnCourse — "Backend Basics" + "Supabase" modules (paid).
- Official Supabase: https://supabase.com/docs/reference/javascript/auth-signinwithpassword
- Official Firebase: https://firebase.google.com/docs/auth/web/start
- Official tRPC: https://trpc.io/docs/client/react/server-components
- Official secure-store: https://docs.expo.dev/versions/latest/sdk/securestore/
