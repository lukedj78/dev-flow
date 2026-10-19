---
name: monorepo-add-shared-package
description: 'Extract logic from apps/web/ or apps/mobile/ into a new or existing shared package under packages/ in a turborepo monorepo, OR create a fresh empty shared package skeleton. Reads .workflow/meta.json with stack.framework="monorepo". Adds the package to pnpm-workspace.yaml (already covered by the wildcard), updates packages/typescript-config/base.json path aliases, registers as workspace:* in both apps. Use to "estrai questa logica in shared", "spostala in packages/shared", "create a shared @<slug>/foo package", "factor X out of the apps". Not for: scaffolding the whole monorepo (use monorepo-bootstrap), backend modules (use module-add or rn-module-add — they install into packages/api/ automatically), generating types from a backend schema (use monorepo-sync-types).'
---

# monorepo-add-shared-package — factor shared logic into packages/

## Contract

See `references/contracts.md` (vendored from `dev-flow`). Key facts:
- Reads `<project-root>/.workflow/meta.json#stack.framework` — must be `"monorepo"`.
- Requires `meta.json#phase ≥ "scaffolded"`.
- Adds entries to:
  - `packages/typescript-config/base.json#paths` (new alias `@<slug>/<pkg-name>/*`) — **not** a root
    `tsconfig.base.json`, which `monorepo-bootstrap` never creates (Turborepo's official pattern
    is a workspace package extended by name; see `monorepo-bootstrap/references/structure.md`)
  - `apps/web/package.json#dependencies` AND `apps/mobile/package.json#dependencies` (as `workspace:*`)
  - `meta.json#stack_config.shared_packages` array
- Does NOT modify `phase`.

## When this skill applies

- User says: "estrai questa logica in shared", "create a shared @<slug>/foo package", "spostala in packages/shared", "factor X out of the apps".
- Orchestrator does NOT route here automatically — invoked on demand.

## Knowledge dependencies

- `monorepo-bootstrap/references/structure.md` — for the canonical layout.
- `monorepo-bootstrap/references/patterns.md` — for the workspace protocol + import conventions.

## Workflow

### Step 1 — Verify preconditions

Read `.workflow/meta.json`. Abort with clear message if:
- `stack.framework != "monorepo"` → "This skill is monorepo-only. For non-monorepo projects use plain TS path aliases inside the app."
- `phase < "scaffolded"` → "Need at least scaffolded — run monorepo-bootstrap first."

Read `meta.json#project_slug` for the namespace.

### Step 2 — Determine the package name

Ask the user (one round-trip):

> "Package name (without namespace)? E.g. 'shared', 'design', 'api', 'ui', 'config-eslint'. Or a topic-specific one like 'forms', 'analytics', 'payments-client'."

Validate:
- kebab-case only (lowercase a-z, 0-9, hyphens).
- Reject reserved names: `web`, `mobile`, `root` (those are app names, not packages).
- If the user picks `shared`, `design`, or `api` and the package already exists, route to that existing package (add files there instead of creating a new one).

Resulting package: `@<slug>/<name>` lives at `packages/<name>/`.

### Step 3 — Decide the source mode

Two flows:

**(a) Create-empty mode** — user wants a fresh skeleton.
- Create `packages/<name>/src/index.ts` (empty barrel export).
- Create `packages/<name>/package.json` with name `@<slug>/<name>`, main `./src/index.ts`.
- Create `packages/<name>/tsconfig.json` extending `@<slug>/typescript-config/base.json`.

**(b) Extract-from-app mode** — user wants to move existing files out of an app.
- Ask user: "Which file(s) or folder(s) to extract? E.g. `apps/web/lib/format.ts` or `apps/mobile/types/Post.ts`."
- Create the package skeleton (same as mode A).
- `mv` the listed files into `packages/<name>/src/`.
- Run a codebase-wide find-replace:
  - `from "@<slug>/web/lib/format"` → `from "@<slug>/<name>/format"`
  - Same for any import that referenced the moved files.
- Update both `apps/web/tsconfig.json` and `apps/mobile/tsconfig.json` so the find-replace patterns are picked up.

### Step 4 — Update root configs

Patch `packages/typescript-config/base.json`:
- Add path alias `@<slug>/<name>/*: ["packages/<name>/src/*"]`.

Patch both `apps/web/package.json` and `apps/mobile/package.json`:
- Add `"@<slug>/<name>": "workspace:*"` to dependencies.

### Step 5 — Run `pnpm install`

```bash
pnpm install
```

This wires the workspace properly. Without it, imports from the new package fail.

### Step 6 — Verify

Run `npx tsc --noEmit` from both `apps/web/` and `apps/mobile/`. Must pass.

If extract mode was used, also verify the moved files compile inside their new home: `cd packages/<name> && npx tsc --noEmit`.

### Step 7 — Update meta.json + commit

```json
{
  "stack_config": {
    "shared_packages": ["@<slug>/shared", "@<slug>/design", "@<slug>/api", "@<slug>/<name>"]
  },
  "history": [
    ...,
    { "skill": "monorepo-add-shared-package", "ran_at": "<iso>", "inputs": {"name": "<name>", "mode": "create|extract", "files_moved": [...]}, "phase_before": "...", "phase_after": "..." }
  ]
}
```

If git repo: commit with `feat(packages/<name>): create shared package` or `refactor: extract <files> into @<slug>/<name>`.

## Common anti-patterns (NEVER do)

- ❌ Create a package without adding it to BOTH apps' package.json as `workspace:*` — imports will silently fail at runtime.
- ❌ Skip the `packages/typescript-config/base.json#paths` update — TS won't resolve the alias.
- ❌ Move files without grep-ing the entire codebase for imports — broken references everywhere.
- ❌ Use the package name `web`, `mobile`, or `root` — collision with app/root names.
- ❌ Create circular dependencies (`packages/foo` importing from `packages/bar` while `bar` imports from `foo`) — turborepo will complain but it's avoidable upfront.
- ❌ Use `file:../packages/<name>` style instead of `workspace:*` — pnpm won't deduplicate.

## Updating meta.json (recommended pattern)

When this skill modifies state (artifact written, phase advanced, history appended), use the canonical script when available:

```bash
python3 .../dev-flow/scripts/update_meta.py <project-root> append-history \
    --skill 'monorepo-add-shared-package' --inputs '{"name": "<name>"}' --outputs '{"files": [...]}'
```

## Sources

- Spec: `docs/superpowers/specs/2026-05-29-monorepo-set-design.md`
- `monorepo-bootstrap/references/structure.md` — canonical layout
- `monorepo-bootstrap/references/patterns.md` — workspace + import conventions
