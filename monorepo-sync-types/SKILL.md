---
name: monorepo-sync-types
description: 'Regenerate backend types and re-export them via packages/shared/types/ in a turborepo monorepo so both apps/web/ and apps/mobile/ consume a single typed surface. Supports Supabase (via supabase gen types typescript), neon-drizzle (via drizzle-kit introspect/pull + InferSelectModel/InferInsertModel re-exports — the default DB stack), tRPC (via inference from the server router import), and custom REST (via a manual or zod-derived schema). Reads .workflow/meta.json with stack.framework="monorepo" and stack.{auth,db} populated. Use when "rigenera i tipi da Supabase", "sync DB schema to packages/shared/types", "il backend è cambiato, aggiorna i tipi", "sync types from tRPC", "sync Drizzle types after a schema change". Not for: creating shared packages from scratch (use monorepo-add-shared-package), wiring the backend client itself (use module-add or rn-module-add).'
---

# monorepo-sync-types — regenerate + propagate backend types across the monorepo

## Contract

See `references/contracts.md` (vendored from `dev-flow`). Key facts:
- Reads `<project-root>/.workflow/meta.json#stack.framework` — must be `"monorepo"`.
- Reads `meta.json#stack.db` and `stack.auth` to determine the source of truth:
  - `"supabase"` → run `supabase gen types typescript` against the linked project.
  - `"neon-drizzle"` → introspect/pull via `drizzle-kit` and re-export `InferSelectModel`/`InferInsertModel` from the Drizzle schema (this is the default DB for most projects — see `module-add/references/module-db.md`).
  - `"trpc"` → re-import the server router type and re-export it.
  - `"firebase"` → no auto-gen, but normalize fixed types from Firestore rules (limited).
  - `"custom-rest"` → ask the user where the schema lives (Zod / OpenAPI / TS source).
- Writes generated types into `packages/shared/src/types/` (NOT into `packages/api/`, because `packages/shared` is consumed by BOTH apps including for non-backend code).
- Idempotent: regenerating overwrites; no-diff prints "already in sync".
- Does NOT modify `phase`.

## When this skill applies

- User says: "rigenera i tipi", "sync DB schema", "supabase types update", "the backend changed, update types".
- Orchestrator does NOT route here automatically — invoked on demand (e.g., after a backend migration).

## Knowledge dependencies

- `monorepo-bootstrap/references/structure.md` — for `packages/shared/src/types/` location.
- `rn-backend/references/<provider>.md` — for provider-specific gen commands.
- `module-add/references/module-db.md` — for the web side conventions.

## Workflow

### Step 1 — Verify preconditions

Read `.workflow/meta.json`. Abort if:
- `stack.framework != "monorepo"`.
- `stack.db == null` AND `stack.auth == null` → "No backend configured yet. Run `module-add db` or `rn-module-add db` first."

Read `meta.json#stack_config.supabase_project_ref` (or equivalent) for the gen command target.

### Step 2 — Branch by provider

#### Supabase

Run the canonical gen command:

```bash
npx supabase gen types typescript --project-id <ref> > packages/shared/src/types/database.ts
```

(or `--linked` if `supabase login` + `supabase link` already done.)

Add to `packages/shared/src/index.ts`:
```ts
export type { Database } from './types/database';
```

Add a typed Supabase client wrapper in `packages/api/src/client.ts`:
```ts
import { createClient } from '@supabase/supabase-js';
import type { Database } from '@<slug>/shared/types/database';

export const supabase = createClient<Database>(
  process.env.EXPO_PUBLIC_SUPABASE_URL!, // or NEXT_PUBLIC_ on web side — see decision-tree
  process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY!,
);
```

Both web and mobile apps now import `supabase` from `@<slug>/api/client` and get full type safety: `supabase.from('posts').select(...)` is fully typed.

#### neon-drizzle

This is the default DB stack for most projects (see `module-add/references/module-db.md`). Drizzle's schema file is already the source of truth for types — there's no separate "gen types" command — so syncing means two things: (1) make sure the schema file matches the live DB, and (2) re-export row types to `packages/shared/`.

1. If drift with the live database is suspected (someone ran DDL outside Drizzle, or this is the first sync), refresh the schema from the database:
   ```bash
   npx drizzle-kit pull
   ```
   This introspects the Neon database and (re)writes the schema file. Confirm the target path against `module-add/references/module-db.md` — by default `apps/web/lib/db/schema.ts`.
2. Re-export typed rows via `InferSelectModel` / `InferInsertModel` (from `drizzle-orm`) into `packages/shared/src/types/db.ts`:
   ```ts
   import type { InferSelectModel, InferInsertModel } from 'drizzle-orm';
   import { users, posts } from '../../../../apps/web/lib/db/schema'; // adjust relative path to the real schema location

   export type User = InferSelectModel<typeof users>;
   export type NewUser = InferInsertModel<typeof users>;
   export type Post = InferSelectModel<typeof posts>;
   export type NewPost = InferInsertModel<typeof posts>;
   ```
3. Add to `packages/shared/src/index.ts`:
   ```ts
   export * from './types/db';
   ```

If the schema file was hand-edited to add tables/columns that haven't reached the database yet, don't `pull` (it would overwrite the new columns) — instead run the migration first (`drizzle-kit generate` + `drizzle-kit migrate`; `drizzle-kit push` is dev-only and destructive on column drops, per `module-add/references/module-db.md`), then re-export types from the now-current schema.

#### tRPC

The types flow automatically via TS inference — no gen step. The skill verifies the wiring is correct:

1. `packages/api/src/client.ts` imports the server's `AppRouter` type:
   ```ts
   import type { AppRouter } from '../../../server/src/router';
   export const trpc = createTRPCReact<AppRouter>();
   ```
2. (Optional) Re-export Zod-derived input/output types from `packages/shared/src/types/`:
   ```ts
   import type { inferRouterOutputs } from '@trpc/server';
   import type { AppRouter } from '../../api/src/router-type'; // a re-export
   export type RouterOutputs = inferRouterOutputs<AppRouter>;
   ```

If the server lives outside the monorepo: import via a published `@<scope>/types` package OR copy the router types file into `packages/shared/src/types/router.d.ts` and tell the user to keep it in sync.

#### Firebase

No auto-gen. The skill creates skeleton types from Firestore rules + user input:

1. Ask the user for the collections in use (or parse `firestore.rules`).
2. For each collection, ask the user for the document shape OR generate a placeholder.
3. Write `packages/shared/src/types/firestore.ts` with the shapes.

This is a manual-maintenance scenario — Firebase doesn't ship a type-gen tool the way Supabase does.

#### Custom REST

Ask the user where the schema lives:

- **Zod schemas** in the server: ask for the path, generate `packages/shared/src/types/api.ts` via `z.infer<typeof Schema>` for each.
- **OpenAPI spec**: ask for the YAML/JSON path, run `npx openapi-typescript <spec> -o packages/shared/src/types/api.d.ts`.
- **TS source** in a separate repo: copy the relevant types into `packages/shared/src/types/api.ts` and instruct the user to keep in sync.

### Step 3 — Verify

Run `pnpm tsc --noEmit` from `apps/web`, `apps/mobile`, and `packages/shared`. Must pass.

If types changed in ways that broke existing code, report each error — the user fixes the consumers (the skill doesn't auto-fix arbitrary call sites).

### Step 4 — Update meta.json + commit

```json
{
  "stack_config": {
    "types_last_synced_at": "<iso>",
    "types_source": "supabase" // or "neon-drizzle" / "trpc" / "firebase" / "custom-rest"
  },
  "history": [
    ...,
    { "skill": "monorepo-sync-types", "ran_at": "<iso>", "outputs": [...] }
  ]
}
```

If git repo: commit with `chore(types): sync from <provider>`.

## Common anti-patterns (NEVER do)

- ❌ Generate types into `packages/api/` — types are general-purpose, both apps consume them; they live in `packages/shared/`.
- ❌ Hand-edit generated type files — they will be overwritten next sync.
- ❌ Skip the `packages/shared/src/index.ts` re-export — apps would need deep import paths.
- ❌ Forget the `--project-id` flag on `supabase gen types` — it will fail or generate the wrong schema.
- ❌ Run gen without verifying the user is logged into the right project (`supabase status`).
- ❌ For tRPC: import the server router via a brittle relative path (`../../../../server/src/router`). Instead use a workspace import if the server is in the monorepo, or a `.d.ts` shim file if not.

## Updating meta.json (recommended pattern)

```bash
python3 .../dev-flow/scripts/update_meta.py <project-root> record-artifact \
    --path packages/shared/src/types/database.ts --produced-by 'monorepo-sync-types'
python3 .../dev-flow/scripts/update_meta.py <project-root> append-history \
    --skill 'monorepo-sync-types' --inputs '{"source": "supabase"}' --outputs '{"types": "packages/shared/src/types/database.ts"}'
```

## Sources

- Spec: `docs/superpowers/specs/2026-05-29-monorepo-set-design.md`
- Official: https://supabase.com/docs/guides/api/rest/generating-types
- Official: https://trpc.io/docs/quickstart#using-trpcs-types-on-the-client
- `monorepo-bootstrap/references/structure.md`
