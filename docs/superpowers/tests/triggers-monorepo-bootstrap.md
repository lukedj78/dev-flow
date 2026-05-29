# Trigger acceptance list — monorepo-bootstrap

## Should trigger (3+)
1. "Scaffolda il monorepo da PRD + DESIGN.md"
2. orchestrator routes here from `dev-flow` when `meta.json#stack.framework == "monorepo"` and `phase ∈ {prd_drafted, design_extracted}`
3. "Bootstrap turborepo with web + mobile"

## Should NOT trigger (3+)
1. "Scaffolda app web" → expect design-md-to-app (framework=next)
2. "Scaffolda app mobile" → expect rn-bootstrap (framework=expo-rn)
3. "Aggiungi modulo auth" → expect module-add or rn-module-add (not bootstrap)

## Idempotency contract
1. Running on a project with `pnpm-workspace.yaml + apps + packages` already → reports "already initialized" and skips root scaffold (but may still run scaffold-{web,mobile}.sh --patch if needed).
2. Re-running scaffold-web.sh on already-scaffolded apps/web/ → reports "already scaffolded" and skips.
3. Re-running scaffold-mobile.sh same.
4. Re-running with --patch on already-patched configs → reports "already wired" and skips.

## End-state after success
1. Root: `pnpm-workspace.yaml`, `turbo.json`, `package.json`, `tsconfig.base.json`, `.gitignore`, `.npmrc`, `README.md`.
2. `apps/web/` scaffolded by design-md-to-app, tailwind preset wired.
3. `apps/mobile/` scaffolded by rn-bootstrap, tailwind + metro configs wired.
4. `packages/{shared,design,api}/` skeletons.
5. `meta.json#stack.framework = "monorepo"` + `stack.monorepo.{web,mobile}` populated.
6. `meta.json#phase = "scaffolded"`.
7. `pnpm install` from root succeeds; `pnpm turbo dev --dry-run` lists all workspaces.
