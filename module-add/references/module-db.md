# module-add → `db` (Drizzle ORM + Neon Postgres)

Wire **Drizzle ORM** with a **Neon** Postgres database into an existing scaffold. Defaults: Neon serverless driver, `drizzle-kit` for migrations, schema in `lib/db/schema.ts`.

## ⚠ Read before running

**`drizzle-kit push` is for development only.** It compares your schema to the live DB and applies the diff directly — fast, but **destructive on column drops/renames** (no rollback, no migration history). For anything that touches real user data:

- Local dev: `pnpm db:push` is fine.
- Pre-production / production: switch to the migration workflow — `pnpm db:generate` produces a numbered SQL file, you review it, commit it to git, then `pnpm db:migrate` applies it. This gives you rollback-by-revert and a clear changelog of what shipped when.

Both scripts ship below. State this distinction in the hand-off message so the user doesn't `db:push` against prod by accident.

## Idempotency check

Before doing anything, check whether the db is already wired:

1. `<project-root>/package.json` contains `"drizzle-orm"` and `"drizzle-kit"` in dependencies.
2. `<project-root>/drizzle.config.ts` exists.
3. `<project-root>/lib/db/index.ts` exists.
4. `<project-root>/.env.local.example` contains `DATABASE_URL`.

If all four: tell the user it's installed, offer to regenerate the reference schema or add a new table example. Don't double-install.

## Prerequisites

None. `module-add db` is typically the first module added.

## Install

```bash
cd <project-root>
npm install drizzle-orm @neondatabase/serverless
npm install --save-dev drizzle-kit dotenv tsx
```

## Files to write

### `drizzle.config.ts` (project root of the app)

⚠️ **Mirror the runtime's driver choice here, or `db:push` fails on a clean
checkout.** The client below falls back to PGlite when `DATABASE_URL` is unset —
but a config that only reads `dbCredentials.url` exits with *"Either connection
'url' or 'host', 'database' are required"*, so the very first `pnpm db:push`
cannot run without the infrastructure the fallback exists to avoid. Branch the
config the same way the client branches (`driver: "pglite"` is one of the five
this version accepts — verified at `drizzle-kit@0.31.10`):

```typescript
import { defineConfig } from "drizzle-kit";
import "dotenv/config";

const url = process.env.DATABASE_URL;

export default defineConfig(
  url
    ? {
        dialect: "postgresql",
        schema: "./lib/db/schema.ts",
        out: "./lib/db/migrations",
        dbCredentials: { url },
      }
    : {
        dialect: "postgresql",
        driver: "pglite",
        schema: "./lib/db/schema.ts",
        out: "./lib/db/migrations",
        dbCredentials: { url: process.env.PGLITE_DATA_DIR ?? "./.data/pglite" },
      },
);
```

### `lib/db/index.ts`

**Recommended: driver-switch by URL** (field-verified). One client that picks the driver
from `DATABASE_URL`: Neon over HTTP in prod/preview, node-postgres for a local Postgres,
and **embedded PGlite when no URL is set** — so `pnpm dev` and CI run with zero infra and
the *same* Drizzle schema, and prod is a one-env-var swap. This removes the "manually swap
neon-http for node-postgres" caveat entirely. `pg`/`pglite` are `require`d lazily so
serverless bundlers (and eve/nitro) don't trace them into the Neon build.

```typescript
import { drizzle as drizzleNeon, type NeonHttpDatabase } from "drizzle-orm/neon-http";
import { neon } from "@neondatabase/serverless";
import { createRequire } from "node:module";
import * as schema from "./schema";

const nodeRequire = createRequire(import.meta.url);
export type Database = NeonHttpDatabase<typeof schema>;

export function createDb(url?: string): Database {
  if (url && /neon\.tech/.test(url)) return drizzleNeon(neon(url), { schema });
  if (url) {
    const { Pool } = nodeRequire("pg") as typeof import("pg");
    const { drizzle } = nodeRequire("drizzle-orm/node-postgres") as typeof import("drizzle-orm/node-postgres");
    return drizzle(new Pool({ connectionString: url, max: 4 }), { schema }) as unknown as Database;
  }
  const { PGlite } = nodeRequire("@electric-sql/pglite") as typeof import("@electric-sql/pglite");
  const { drizzle } = nodeRequire("drizzle-orm/pglite") as typeof import("drizzle-orm/pglite");
  const { resolve } = nodeRequire("node:path") as typeof import("node:path");
  return drizzle(new PGlite(process.env.PGLITE_DATA_DIR ?? resolve(process.cwd(), ".data/pglite")), { schema }) as unknown as Database;
}

// HMR-safe singleton (Next re-evaluates modules; PGlite is single-process).
const g = globalThis as unknown as { __db?: Database };
export function getDb(): Database { return (g.__db ??= createDb(process.env.DATABASE_URL)); }
```

Add dev deps for the fallback branches: `pnpm add -D @electric-sql/pglite pg @types/pg`.
**Gotcha (Turbopack):** never build the PGlite dataDir with `new URL(..., import.meta.url)`
(Turbopack treats it as a build-time asset and fails) — use `resolve(process.cwd(), …)`,
and add `serverExternalPackages: ["@electric-sql/pglite", "pg"]` to `next.config.ts` so the
WASM/native drivers aren't bundled. **Multi-process dev (e.g. Next + a separate agent):**
PGlite is single-process — either point both at one Neon dev branch, or expose PGlite over
the Postgres wire protocol with `@electric-sql/pglite-socket` (`PGLiteSocketServer`,
`maxConnections ≥ 2`) and set `DATABASE_URL=postgresql://…@127.0.0.1:5434/postgres`.

⚠️ **This is not a theoretical caveat, and `module-add auth` is what usually
triggers it** — an agent channel that needs to know who is calling imports
`lib/auth` → `lib/db` and opens the directory a second time. Two observed
symptoms: the engine aborts with `RuntimeError: Aborted()`, and the data
directory is left corrupt, so every later `drizzle-kit push` fails until you
`rm -rf` it. **The dev server also holds the lock**, so CLI tools must be run
with it stopped. Prefer resolving sessions over HTTP from the second process to
having two of them on one directory.

**Simpler alternative** (Neon-only — fine when you always have a Neon URL, incl. dev):

```typescript
import { drizzle } from "drizzle-orm/neon-http";
import { neon } from "@neondatabase/serverless";
export const db = drizzle({ client: neon(process.env.DATABASE_URL!) });
```

### `lib/db/schema.ts`

```typescript
import { pgTable, serial, text, timestamp, index, uniqueIndex } from "drizzle-orm/pg-core";

// Reference example — replace/extend with real tables as features land.
//
// Conventions to follow when adding new tables:
//   1. Every multi-tenant table has `tenantId` as the first column after `id`,
//      with an index on (tenantId, createdAt) for list queries.
//   2. Every "owned" record has `userId` (the creator) — also indexed.
//   3. Soft delete via `archivedAt: timestamp("archived_at")` (nullable) instead
//      of DELETE. Reads filter `WHERE archivedAt IS NULL`.
//   4. `createdAt` / `updatedAt` are non-null with defaults. Update the latter
//      in your server action with `set({ updatedAt: new Date() })`.
//   5. Slugs / external identifiers go in a `uniqueIndex` so the DB rejects
//      duplicates — never rely on app-level uniqueness checks (race conditions).
export const posts = pgTable(
  "posts",
  {
    id: serial("id").primaryKey(),
    slug: text("slug").notNull(),
    title: text("title").notNull(),
    body: text("body"),
    createdAt: timestamp("created_at").defaultNow().notNull(),
    updatedAt: timestamp("updated_at").defaultNow().notNull(),
    archivedAt: timestamp("archived_at"),
  },
  (table) => ({
    slugUnique: uniqueIndex("posts_slug_unique").on(table.slug),
    createdAtIdx: index("posts_created_at_idx").on(table.createdAt),
  })
);

// `module-add auth` will append user/session/account/verification tables here.
```

#### A note on indexes

A schema without indexes is a schema that will be slow as soon as the app has more than a handful of rows. Every column you `WHERE` or `ORDER BY` in a query needs an index — and Postgres won't tell you when one is missing, you'll just discover it when a query takes 4 seconds. The conventions above bake the common ones (`tenantId`, `createdAt`, slugs) in by default. When you add a new query pattern (e.g., a search by `customerEmail`), add the matching index in the same change.

#### Row-Level Security (RLS) — Postgres-native multi-tenancy

The `lib/server/<domain>.ts` template enforces tenant scoping in **app code** (`eq(table.tenantId, tenantId)` in every WHERE clause). That's the first line of defense and it's enough for most projects.

If you're going to be processing PII at scale, or if a regulator/auditor asks for "defense in depth", you can add **Postgres RLS** as a second line: the database itself refuses to return cross-tenant rows even if a buggy query forgets the WHERE clause. Setup:

1. Add a `current_tenant_id` GUC (session variable) — your auth middleware sets it on every request via `SET LOCAL current_tenant_id = '...'`.
2. Enable RLS per table: `ALTER TABLE practices ENABLE ROW LEVEL SECURITY;`
3. Define a policy: `CREATE POLICY tenant_isolation ON practices FOR ALL USING (tenant_id = current_setting('current_tenant_id')::uuid);`

Drizzle doesn't manage RLS policies natively (yet) — you write them in raw SQL migration files. Worth doing if your threat model demands it; overkill if you're shipping a small B2B tool.

### `package.json` script additions

Append to `scripts`:

```json
{
  "db:push": "drizzle-kit push",
  "db:migrate": "drizzle-kit migrate",
  "db:studio": "drizzle-kit studio",
  "db:generate": "drizzle-kit generate"
}
```

## Environment variables

Append to `.env.local.example`:

```
DATABASE_URL=postgresql://user:password@ep-xxx.region.neon.tech/dbname?sslmode=require
```

Tell the user to:
1. Create a Neon project at https://neon.tech (free tier is fine for dev).
2. Copy the connection string from the Neon dashboard (use the "pooled" URL for serverless).
3. Paste into `.env.local`.

## Verification

After install + write:

```bash
npx drizzle-kit check
```

This validates the schema syntax without needing a real database. If it fails, the schema has a syntax error — fix and retry.

To verify against a real DB later (user's responsibility):

```bash
npm run db:push
```

This pushes the schema to the connected Neon DB. The user runs this after they've put the real `DATABASE_URL` in `.env.local`.

## Update meta.json

```json
{
  "stack": {
    "db": "neon-drizzle"
  }
}
```

## Known caveats

- Neon's serverless driver works only over HTTP, not TCP. The **driver-switch `lib/db/index.ts`** above handles this automatically (node-postgres for a local TCP Postgres, PGlite when no URL) — prefer it over the Neon-only version precisely to avoid a manual swap. If you used the simpler Neon-only client, local dev against Docker Postgres needs the manual `neon-http` → `node-postgres` swap.
- Drizzle's `drizzle-kit push` is destructive on column drops. For production, the user should switch to `drizzle-kit generate` + `drizzle-kit migrate` workflow. Mention this in the report — `push` is fine for dev only.
- The `posts` example table is throwaway — invite the user to replace it once their schema starts taking shape.
