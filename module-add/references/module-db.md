# module-add → `db` (Drizzle ORM + Neon Postgres)

Wire **Drizzle ORM** with a **Neon** Postgres database into an existing scaffold. Defaults: Neon serverless driver, `drizzle-kit` for migrations, schema in `src/lib/db/schema.ts`.

## Idempotency check

Before doing anything, check whether the db is already wired:

1. `<root>/<project-root>/package.json` contains `"drizzle-orm"` and `"drizzle-kit"` in dependencies.
2. `<root>/<project-root>/drizzle.config.ts` exists.
3. `<root>/<project-root>/src/lib/db/index.ts` exists.
4. `<root>/<project-root>/.env.local.example` contains `DATABASE_URL`.

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

```typescript
import { defineConfig } from "drizzle-kit";
import "dotenv/config";

export default defineConfig({
  dialect: "postgresql",
  schema: "./src/lib/db/schema.ts",
  out: "./src/lib/db/migrations",
  dbCredentials: {
    url: process.env.DATABASE_URL!,
  },
});
```

### `src/lib/db/index.ts`

```typescript
import { drizzle } from "drizzle-orm/neon-http";
import { neon } from "@neondatabase/serverless";

const sql = neon(process.env.DATABASE_URL!);
export const db = drizzle({ client: sql });
```

### `src/lib/db/schema.ts`

```typescript
import { pgTable, serial, text, timestamp } from "drizzle-orm/pg-core";

// Reference example — replace/extend with real tables as features land.
export const posts = pgTable("posts", {
  id: serial("id").primaryKey(),
  title: text("title").notNull(),
  body: text("body"),
  createdAt: timestamp("created_at").defaultNow().notNull(),
});

// `module-add auth` will append user/session/account/verification tables here.
```

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

- Neon's serverless driver works only over HTTP, not TCP. For local dev with a different Postgres (e.g., Docker), the user has to swap `neon-http` for `node-postgres` in `src/lib/db/index.ts`. Note this in the report.
- Drizzle's `drizzle-kit push` is destructive on column drops. For production, the user should switch to `drizzle-kit generate` + `drizzle-kit migrate` workflow. Mention this in the report — `push` is fine for dev only.
- The `posts` example table is throwaway — invite the user to replace it once their schema starts taking shape.
