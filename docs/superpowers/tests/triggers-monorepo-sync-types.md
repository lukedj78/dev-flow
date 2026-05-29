# Trigger acceptance list — monorepo-sync-types

## Should trigger (3+)
1. "Rigenera i tipi da Supabase"
2. "Il backend è cambiato, aggiorna i tipi"
3. "Sync DB schema to packages/shared/types"

## Should NOT trigger (3+)
1. "Aggiungi modulo auth" → expect module-add or rn-module-add (the wiring, not the type sync)
2. "Estrai questa funzione in shared" → expect monorepo-add-shared-package
3. "Scaffolda il monorepo" → expect monorepo-bootstrap

## Idempotency contract
1. Re-running with no schema changes → reports "already in sync, no diff" and exits 0.
2. Generated file goes to `packages/shared/src/types/<backend>.ts` (never `packages/api/`).
3. `packages/shared/src/index.ts` is updated only if the export line is missing.

## End-state after success
1. `packages/shared/src/types/database.ts` (Supabase) OR `firestore.ts` (Firebase) OR `api.ts` (REST/Zod) updated to match the current backend schema.
2. `packages/shared/src/index.ts` re-exports the canonical type (`Database`, etc.).
3. `pnpm tsc --noEmit` in both apps passes.
4. `meta.json#stack_config.types_last_synced_at` updated to current ISO timestamp.
