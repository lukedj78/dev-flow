# Trigger acceptance list — monorepo-add-shared-package

## Should trigger (3+)
1. "Estrai questa logica in shared"
2. "Spostala in packages/shared/utils"
3. "Crea un package @<slug>/forms condiviso tra le due app"

## Should NOT trigger (3+)
1. "Aggiungi modulo auth" → expect module-add or rn-module-add (backend wiring, not packaging)
2. "Scaffolda il monorepo" → expect monorepo-bootstrap
3. "Sync types from Supabase" → expect monorepo-sync-types

## Idempotency contract
1. Running with an existing package name → adds files there, doesn't recreate.
2. Adding a workspace dependency already present in apps/web/package.json → skipped.
3. Path alias already in tsconfig.base.json → skipped.

## End-state after success
1. `packages/<name>/` exists with package.json, tsconfig.json, src/index.ts.
2. `tsconfig.base.json#paths` includes the new alias.
3. Both `apps/web/package.json` and `apps/mobile/package.json` list `@<slug>/<name>: workspace:*`.
4. (Extract mode) imports in apps/ refactored to use the new package.
5. `pnpm install` + `pnpm tsc --noEmit` pass.
6. `meta.json#stack_config.shared_packages` updated.
