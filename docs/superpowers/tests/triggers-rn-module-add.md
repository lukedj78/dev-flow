# Trigger acceptance list — rn-module-add

## Should trigger (3+)
1. "Aggiungi auth con Supabase / Firebase / il mio backend"
2. "Wire up the database for this app"
3. "Setup push notification + token upload al server"

## Should NOT trigger (3+)
1. "Crea una nuova schermata" → expect rn-add-screen
2. "Scrivi i test" → expect rn-write-tests
3. "Build production EAS" → expect rn-eas-build-submit-update

## Idempotency contract
1. Adding the same module twice MUST detect existing wiring and report "already installed".
2. Re-running with a DIFFERENT provider for the same module (e.g. auth Supabase → Firebase) requires explicit `--swap` flag; otherwise refuse.
3. Module installation MUST update `meta.json#stack.<key>` so future runs know what's wired.
4. Removing a module is NOT supported in v1 — user reverts via git.

## Modules in v1
- `auth`: provider-agnostic (Supabase / Firebase / custom REST / tRPC)
- `db`: same providers
- `storage`: Supabase Storage / Firebase Storage / custom REST + expo-file-system
- `realtime`: Supabase Realtime / Firebase onSnapshot
- `push`: expo-notifications + provider-of-choice for server-side send
- `payments`: RevenueCat (default) / Stripe (non-digital only)
