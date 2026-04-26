# module-add → `auth` (better-auth)

Wire **better-auth** as the auth layer of an existing scaffold. Defaults: email/password + magic-link. Database adapter: Drizzle (assumes `module-db` already ran).

## Idempotency check

Before doing anything, check whether better-auth is already wired:

1. `<project-root>/package.json` contains `"better-auth"` in `dependencies`.
2. `<project-root>/lib/auth.ts` exists.
3. `<project-root>/.env.local.example` contains `BETTER_AUTH_SECRET`.

If all three: tell the user it's installed, offer to regenerate the reference UI or rotate the secret. Don't double-install.

## Prerequisites

- `meta.json#stack.db` must be set (Drizzle is the assumed adapter). If null, stop and ask the user to run `module-add db` first.
- Framework: Next App Router or Vite + React. Other frameworks are not yet supported in this variant.

## Install

```bash
cd <project-root>
npm install better-auth
npm install --save-dev @types/node     # only if not already installed
```

## Files to write

### `lib/auth.ts`

```typescript
import { betterAuth } from "better-auth";
import { drizzleAdapter } from "better-auth/adapters/drizzle";
import { db } from "@/lib/db";

export const auth = betterAuth({
  database: drizzleAdapter(db, { provider: "pg" }),
  emailAndPassword: {
    enabled: true,
    requireEmailVerification: false,
  },
  // Magic-link via email — wire after `module-add email` is run.
  // plugins: [magicLink({ sendMagicLink: ... })],
});

export type Session = typeof auth.$Infer.Session;
```

### `lib/auth-client.ts`

```typescript
import { createAuthClient } from "better-auth/react";

export const authClient = createAuthClient({
  baseURL: process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000",
});

export const { signIn, signUp, signOut, useSession } = authClient;
```

### `app/api/auth/[...all]/route.ts` (Next App Router)

```typescript
import { auth } from "@/lib/auth";
import { toNextJsHandler } from "better-auth/next-js";

export const { GET, POST } = toNextJsHandler(auth.handler);
```

### Reference UI: `app/sign-in/page.tsx`

A minimal sign-in page using shadcn primitives (or MUI `TextField`/`Button` if `stack.ui = "mui"`). The page should:
- Render Email + Password inputs and a submit button.
- Call `signIn.email({ email, password })` from `@/lib/auth-client`.
- On error, surface the message in a `<p className="text-error">` (or MUI `<Alert>`).
- On success, redirect to `/`.

Templates live alongside this reference file when fleshed out — for v1, write a short, idiomatic implementation that matches the project's UI library (read `meta.json#stack.ui` to decide).

### Schema additions for Drizzle

better-auth needs `user`, `session`, `account`, and `verification` tables. Append the schema definitions to `lib/db/schema.ts` (created by `module-add db`). Use the official better-auth Drizzle schema generator:

```bash
npx @better-auth/cli generate
```

Then run a Drizzle migration (`npm run db:push` or `drizzle-kit migrate`).

## Environment variables

Append to `.env.local.example`:

```
BETTER_AUTH_SECRET=<generate-with-openssl-rand-base64-32>
BETTER_AUTH_URL=http://localhost:3000
NEXT_PUBLIC_APP_URL=http://localhost:3000
```

Tell the user to:
1. Generate the secret: `openssl rand -base64 32`.
2. Copy `.env.local.example` to `.env.local` and fill in.

## Update meta.json

```json
{
  "stack": {
    "auth": "better-auth"
  }
}
```

## Known caveats

- better-auth's Drizzle adapter requires the schema to be in a specific shape. The `@better-auth/cli generate` tool handles this — don't hand-write the auth tables.
- Magic-link requires `module-add email` (Resend is the default). Don't enable magic-link before email is wired — better-auth will throw at runtime.
- For social login (Google/GitHub/etc.), the user has to register OAuth apps with each provider and add `BETTER_AUTH_GOOGLE_CLIENT_ID` etc. to env. This is out of scope for v1 — leave a comment in `auth.ts` showing how to add them.
