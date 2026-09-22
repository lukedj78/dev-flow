# module-add → `auth` (better-auth)

Wire **better-auth** as the auth layer of an existing scaffold. Defaults: email/password + a passwordless email sign-in — **email OTP** (`emailOTP` plugin) when the product is a PWA or will be installed to the home screen, magic-link otherwise (see *Magic link or email OTP* below). Database adapter: Drizzle (assumes `module-db` already ran).

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

// ⚠️ `db` (the lazy Proxy from `module-add db`), not `getDb()`. `auth` is built at
// module scope, so `getDb()` here opens the database on import — in every parallel
// `next build` worker. With PGlite that aborts the build (`RuntimeError: Aborted()`);
// the Proxy defers the connection to the adapter's first query.
export const auth = betterAuth({
  database: drizzleAdapter(db, { provider: "pg" }),
  emailAndPassword: {
    enabled: true,
    requireEmailVerification: false,
  },
  // Passwordless sign-in — wire after `module-add email` is run. PWA: emailOTP
  // (see below); plain web app: magicLink({ sendMagicLink: ... }).
  // plugins: [emailOTP({ sendVerificationOTP: ... })],
});

export type Session = typeof auth.$Infer.Session;
```

### Magic link or email OTP

Both are passwordless and both need `module-add email`. They differ in **where the link opens**:

- A **magic link** is opened by the mail app, which hands it to the system browser. On iOS an
  installed PWA is a separate web-app container: the link signs in **Safari**, not the home-screen
  app, and the user is still signed out where they started. (Android behaves the same unless the
  PWA's scope captures links.) This is the whole problem for a mobile-first PWA.
- An **email OTP** is a 6-digit code the user types into the screen they are already on, so the
  session cookie lands in the right container. Default for PWAs and for anything installed to the
  home screen.

Verified with better-auth 1.7.5 (FITROOM, 2026-09):

```typescript
// lib/auth.ts
import { emailOTP } from "better-auth/plugins";

plugins: [
  emailOTP({
    otpLength: 6,
    expiresIn: 600,          // seconds
    allowedAttempts: 5,      // then the code is burnt: TOO_MANY_ATTEMPTS
    storeOTP: "hashed",      // never keep usable codes in the verification table
    async sendVerificationOTP({ email, otp, type }) { /* send via lib/email */ },
  }),
  nextCookies(),             // from "better-auth/next-js" — keep it LAST
],
```

```typescript
// lib/auth-client.ts
import { emailOTPClient } from "better-auth/client/plugins";
// createAuthClient({ plugins: [emailOTPClient()] })

await authClient.emailOtp.sendVerificationOtp({ email, type: "sign-in" });
await authClient.signIn.emailOtp({ email, otp });
```

Set `emailAndPassword: { enabled: false }` when OTP is the only method. The code input is the
`InputOTP` primitive from `components/ui/` (golden rule 3), not six hand-rolled `<input>`s. Give
it `autoComplete="one-time-code"` and `inputMode="numeric"` so iOS offers the code from Mail.

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

**Don't branch on shadcn vs MUI only — read `stack.ui` for its actual value.** The project may be on `"base-ui"` (standalone Base UI, no shadcn CLI — use plain `<input>`/`<button>` with Tailwind classes and Base UI's own primitives, e.g. `Field`/`Input` from `@base-ui/react`) or `"coss"` (Coss/UI, the Cal.com design system on Base UI, installed via the shadcn CLI's `@coss/*` registry — its inputs/buttons come from `@coss/ui`, not `components/ui/` shadcn defaults). Both are Base-UI-family, not MUI, so treat `stack.ui = "mui"` as the only branch that needs the MUI-specific components; everything else (`shadcn`, `base-ui`, `coss`) uses HTML-native form elements/primitives styled with Tailwind, just sourced from a different component library per `stack.ui`.

### Schema additions for Drizzle

better-auth needs `user`, `session`, `account`, and `verification` tables. Generate them — never hand-write them, the adapter expects an exact shape:

```bash
npx auth@latest generate --config lib/auth.ts --output lib/db/auth-schema.ts
```

⚠️ **Not `npx @better-auth/cli generate`.** That package is stuck at **0.1.0**
and generates for a much older better-auth: against `better-auth@1.7.2` its
output is missing `account.issuer`, and sign-up fails at runtime with *"The field
\"issuer\" does not exist in the \"account\" Drizzle schema"*. The library's own
error message names the replacement, and `auth@latest` tracks better-auth's
version (1.7.2 at the time of writing).

⚠️ **The generator cannot load a config that imports through a path alias.**
`lib/auth.ts` normally does `import { db } from "@/lib/db"`, and the CLI
resolves the file outside Next's module resolution, so it exits `MODULE_NOT_FOUND`
on the alias. Two ways out, in order: run it against a config whose imports are
relative, or — when the schema is otherwise correct and one field is missing —
transcribe that field from better-auth's own declaration
(`@better-auth/core/dist/db/schema/<table>.mjs`) with a comment saying where it
came from and why. Never invent a column.

Then wire it into the schema `module-add db` created:

```typescript
// lib/db/schema.ts
export * from "./auth-schema";
```

and apply it (`pnpm db:push` in dev, `db:generate` + `db:migrate` for anything real).

### Two things the generator gets wrong on Postgres, and the only fix that survives regeneration

Field-verified against `auth@1.7.5` (Hostitaly, 2026-09-16). Both are in the generator, so **editing
the generated file by hand is not a fix** — the next `generate` silently reverts it.

1. **Every instant is `timestamp without time zone`.** The generator hard-codes
   `` `timestamp('${name}')` `` for the `pg` provider (`auth/dist/index.mjs`, the `date` field map);
   there is no adapter option. A naive column stores the *writing process's* wall clock while Postgres
   compares in the *server's* zone, so `session.expires_at`, `verification.expires_at` and any invitation
   expiry drift by the client/server offset, and at the DST fold two instants an hour apart collapse into
   one. Seventeen columns across `user`, `session`, `account`, `verification`, `two_factor`,
   `organization`, `member`, `invitation`.
2. **Anything you add to a table's extras array is dropped**, including the
   `UNIQUE (organization_id, id)` a multi-tenant schema needs so child tables can carry a composite
   foreign key `(organization_id, <parent>_id) → parent(organization_id, id)`.

The fix is a **post-generation patch script chained into the generate command**, so the file stays
generated and the correction cannot be forgotten:

```jsonc
// package.json
"auth:generate": "dotenv -e .env.local -- auth generate --config lib/auth/cli.ts --output lib/db/schema/auth.ts --yes && node scripts/patch-auth-schema.mjs lib/db/schema/auth.ts"
```

The script rewrites `timestamp("x")` → `timestamp("x", { withTimezone: true })`, injects the `unique(...)`
entries, and **exits non-zero** if a column or a table's extras array is not where it expects — so a
future better-auth version cannot drop either quietly. Then generate the migration and **add an explicit
`USING "<col>" AT TIME ZONE 'UTC'`** to each `SET DATA TYPE timestamptz`: without it Postgres converts
using the session's TimeZone, so the result depends on who runs the migration. State in the migration
header how existing rows are interpreted — the zone of the process that wrote them is not recorded.

Pair it with a test that reads `information_schema.columns` and fails when a naive instant or a missing
composite unique reappears; an exact-set assertion catches both a new offender and a fixed one.

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

## Wiring server actions

Once better-auth is installed, the `lib/server/<domain>.ts` template's `getCurrentTenantId()` / `getCurrentUserId()` stubs (which throw `AUTH_NOT_WIRED`) need to be replaced with real implementations. Drop in **one shared helper** at `lib/auth-server.ts` and have every server action import from it:

### `lib/auth-server.ts`

```typescript
import { headers } from "next/headers";
import { auth } from "@/lib/auth";

/**
 * Resolve the current session inside a server action or RSC.
 *
 * - Returns `null` if the request is unauthenticated.
 * - Throws nothing on its own — let the caller decide whether unauth is fatal.
 * - Memoize with `cache()` from `react` if you call this many times per request.
 */
export async function getSession() {
  return await auth.api.getSession({ headers: await headers() });
}

/**
 * Get the current user's id, throwing if unauthenticated.
 *
 * Use this in server actions that REQUIRE a logged-in user. The thrown error
 * propagates to Next's error boundary as an HTTP 500 — clients see the generic
 * fallback in `app/error.tsx`, never the raw message.
 */
export async function getCurrentUserId(): Promise<string> {
  const session = await getSession();
  if (!session?.user?.id) {
    throw new Error("UNAUTHORIZED");
  }
  return session.user.id;
}

/**
 * Get the current user's tenant id.
 *
 * For single-tenant projects, return `getCurrentUserId()` — the user IS the tenant.
 * For B2B / multi-tenant: read from a `users.tenantId` column or a session claim.
 * Customize the implementation here, then every server action picks it up.
 */
export async function getCurrentTenantId(): Promise<string> {
  // Single-tenant default: tenant === user.
  return await getCurrentUserId();
  //
  // Multi-tenant variant (uncomment + adapt when you add a `users.tenantId` column):
  // const session = await getSession();
  // if (!session?.user?.tenantId) throw new Error("UNAUTHORIZED");
  // return session.user.tenantId;
}
```

### Updating `lib/server/<domain>.ts`

The action template ships with placeholder stubs at the top of the file:

```typescript
async function getCurrentTenantId(): Promise<string> {
  throw new Error("AUTH_NOT_WIRED — run `module-add auth` to enable.");
}
```

Replace those two stubs with imports:

```typescript
import { getCurrentTenantId, getCurrentUserId } from "@/lib/auth-server";
```

Run `pnpm typecheck` to confirm — every action that called the stub now resolves to the real helper, no other changes needed. The `ActionResult<T>` shape stays identical.

### Why `throw` instead of `return { ok: false }` for unauth

The actions in the template **return** `{ ok: false }` for **business** errors (validation, "title too short", "this practice is archived"). They **throw** for **system** errors (DB down, auth not wired, request unauthorized). The reason: a logged-out user submitting a form is a system-level state — the form should never have been rendered in the first place — so it's a 500, not a 4xx-style field error. The thrown error hits `app/error.tsx`, the user gets the clean fallback, and your logs show the real cause.

If you want to gate the form at render time instead of catching the throw, do an `await getSession()` check in the parent RSC and `redirect("/sign-in")` if null — that's the right place to handle "user not logged in", not deep inside the action. **With `cacheComponents: true` (Next 16), do it the way the next section says** — a top-level session read in a layout breaks instant navigation.

### Next 16 `cacheComponents`: protecting routes without breaking instant navigation

With `cacheComponents: true`, a layout that awaits the session at its top level and calls
`redirect()` fails instant-navigation validation. In dev the overlay reports **"Could not validate
instant"** for every protected route: a request read cannot be prerendered into the static shell.
Reading `cookies()`/`headers()` outside a `<Suspense>` boundary is a build error. The pattern that
satisfies it, from `node_modules/next/dist/docs/01-app/02-guides/authentication-with-cache-components.md`
(verified on Next 16.3.4 + better-auth 1.7.5), has **three parts, and all three are needed**:

**1. `proxy.ts`: an optimistic cookie check.** Next's `authentication.md` §Optimistic checks with
Proxy. It only asks whether a session cookie is present, with no DB lookup, so signed-out visitors
are redirected before render and prefetches never hit a redirect mid-tree:

```typescript
// proxy.ts (Next 16 renamed middleware.ts; runs on Node — do not set `runtime`)
import { getSessionCookie } from "better-auth/cookies";
import { type NextRequest, NextResponse } from "next/server";

const PROTECTED = ["/dashboard", "/settings"];

export default function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  if (PROTECTED.some((p) => pathname === p || pathname.startsWith(`${p}/`)) && !getSessionCookie(request)) {
    return NextResponse.redirect(new URL("/sign-in", request.url));
  }
  return NextResponse.next(); // or the next-intl middleware: `return intl(request)`
}
```

A cookie that is present can still be expired or forged, so this is never the authorization check.

**2. `getCurrentUser()` with `"use cache: private"`.** This is the real check. The directive may
read `headers()`/`cookies()`, keeps the result in the browser only, and lets authenticated routes
prefetch per session. `redirect()` throws, so a redirect is never cached; only a resolved user is:

```typescript
// lib/auth/session.ts
import "server-only";
import { headers } from "next/headers";
import { redirect } from "next/navigation";
import { auth } from "./auth";

export async function getCurrentUser() {
  "use cache: private";
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) redirect("/sign-in"); // next-intl: getPathname({ href, locale: await locale() }) from next/root-params
  return { id: session.user.id, email: session.user.email, name: session.user.name };
}
```

Return a small serialisable object, not the whole session. Server Actions still use a plain
`getSession()` and throw on null, as above. Never read the session inside a plain `"use cache"`
function: it throws.

**3. Call it inside `<Suspense>`, never at the layout's top level.** Put the user menu, the
role-dependent nav, and the page body that needs the user in a component that awaits
`getCurrentUser()`, wrapped in a `<Suspense fallback={<Skeleton />}>`. The chrome outside the
boundary stays in the static shell.

To migrate one route at a time, `export const instant = false` on a page or layout lets it keep
blocking on the server (same guide, §Migrating an existing app).

## When the product **is** an MCP server — OAuth for coding agents

Everything above builds an app that signs *people* in. If the product exposes an MCP server,
a coding agent has to get a token for it, and the MCP spec settles how: OAuth 2.1 with PKCE,
RFC 9728 protected-resource metadata for discovery, and clients that register themselves
because you will never have met them.

better-auth ships this. It is **not** part of the core package.

> **Checked 2026-09-11** against the shipped declarations (`npm pack`, then the `.d.mts`) —
> `better-auth@1.7.4`, `@better-auth/oauth-provider@1.7.4`, `@better-auth/mcp@1.7.4`,
> `@better-auth/cimd` — all MIT.

### The package is `oauth-provider`, not `oidc-provider`

`@better-auth/oidc-provider` **does not exist on npm** (404, checked today). The plugin is
**`@better-auth/oauth-provider`**, and the old name is still what circulates in blog posts and
half-remembered notes. Installing the one you remember gets you nothing; installing the one
that exists gets you an OAuth 2.1 **and** OIDC provider — it serves
`/.well-known/openid-configuration` alongside `/.well-known/oauth-authorization-server`.

### `mcp()` *is* the provider — do not wire both

```bash
npm install @better-auth/mcp @better-auth/cimd
```

`@better-auth/mcp` depends on `@better-auth/oauth-provider`; you do not install it separately.
And from the plugin's own doc comment: *"Because it is the OAuth provider, it cannot be
combined with a separate `oauthProvider()`."* Wiring both — the obvious reading of "I need the
OIDC provider plugin **and** the MCP plugin" — is the first way this goes wrong.

```ts
// lib/auth.ts
import { betterAuth } from "better-auth";
import { jwt } from "better-auth/plugins";
import { mcp } from "@better-auth/mcp";
import { cimd } from "@better-auth/cimd";

export const auth = betterAuth({
  // …database, emailAndPassword, etc. as above
  plugins: [
    jwt(),
    mcp({
      loginPage: "/login",
      consentPage: "/consent",
      resource: "https://api.example.com/mcp",
    }),
    cimd({ fetchClientMetadataResource, metadataProfile: "mcp-2026-07-28" }),
  ],
});
```

`resource` is the canonical protected-resource identifier (RFC 8707 / RFC 9728). Issued tokens
are **audience-bound** to it and it is published in the protected-resource metadata. It must be
an **HTTPS URL with no query, fragment or credentials**; HTTP is accepted only on loopback, for
local development.

Mounted once the plugin is in: `/.well-known/oauth-authorization-server`,
`/.well-known/oauth-protected-resource`, `/.well-known/openid-configuration`, and the
`/oauth2/*` endpoints (`authorize`, `token`, `consent`, `register`, `create-client`, …).

### Dynamic client registration is opt-in, and the mode is a security decision

The reflex — "MCP needs dynamic registration, so it must be on" — is wrong twice. It is
**`allowDynamicClientRegistration: false` by default**, and enabling it only opens
`POST /oauth2/register`; *who may register* is a second choice, with three modes:

| Mode | How it is authorized | Turned on by |
|---|---|---|
| **session-backed** | a logged-in user with client-create privileges | `allowDynamicClientRegistration: true` alone |
| **token-backed** | an RFC 7591 initial access token in `Authorization: Bearer` | defining `validateInitialAccessToken` |
| **open** | nobody — unauthenticated | `allowUnauthenticatedClientRegistration: true` |

Open registration means **anyone on the internet can create a client on your authorization
server**. Sometimes that is the requirement; it is never a default you drift into. Say it out
loud before enabling it, and prefer what MCP itself recommends: **`@better-auth/cimd`**, Client
ID Metadata Documents, which verify client identity through *domain ownership* instead of
letting the registration endpoint stand open. MCP 2026-07-28 pins CIMD draft-00 — hence
`metadataProfile: "mcp-2026-07-28"` plus an application-owned metadata-resource transport.

### PKCE is per client, not a global switch

There is no `requirePKCE: true` on the plugin. `requirePKCE` is a **field on the OAuth
application record** (the `oauthApplication` schema, `type: "boolean"`, not required), so it is
set per registered client. Do not go looking for a plugin option that does not exist, and do
not assume every client that registered has it on.

### Guarding the MCP route

`@better-auth/mcp` exports `requireMcpAuth` and `createMcpProtectedRequestHandler` for the
resource-server side — the token has to be checked against the **audience** (`resource`) and
the required scopes, not merely be a valid token. `RequireMcpAuthOptions` carries `resource`,
`issuer`, `jwksUrl`, `challengeScopes`, `requiredScopes`, a custom `isScopeSatisfied`, and a
`dpop` block with `proofMaxAgeSeconds`.

One behavioural difference worth knowing: `mcp()` sets **`refreshTokenReuseInterval` to 30
seconds** for its clients so a retried refresh recovers the rotated response. The OAuth
provider on its own stays strict. Set it to `0` to get strict handling back.

### What this is not

This is the **authorization** half. Writing the MCP server itself — tools, resources,
transport — is product work. And do not confuse it with `product-to-agent-skill`, which
documents an API *for* coding agents: that one writes the runbook, this one issues the token.

## Update meta.json

```json
{
  "stack": {
    "auth": "better-auth"
  }
}
```

## Known caveats

- ⚠️ **Wiring auth into a second process is what makes `module-add db`'s PGlite
  warning bite.** That reference says the embedded fallback is single-process and
  safe "as long as only one process touches the database". Auth is the thing that
  usually breaks that: an agent sidecar, a worker or a queue consumer that needs
  to know who is calling will import `lib/auth` → `lib/db` and open the same data
  directory a second time. On a real project this aborted the engine and left the
  directory unreadable — recoverable only by deleting it. **Resolve the session
  over HTTP from the other process** (`GET /api/auth/get-session`, forwarding the
  caller's `cookie` header) rather than sharing the database: one component holds
  the session store, and the sidecar never needs database credentials at all.
- better-auth's Drizzle adapter requires the schema to be in a specific shape. The `@better-auth/cli generate` tool handles this — don't hand-write the auth tables.
- Magic-link **and email OTP** require `module-add email` (Resend is the default). Don't enable either before email is wired — better-auth will throw at runtime. In dev, `sendVerificationOTP` can log the code to the server console until email lands.
- **PWA → email OTP, not magic link**: on iOS a mail link opens Safari, not the installed app (see *Magic link or email OTP*).
- **`cacheComponents: true` → proxy cookie check + `"use cache: private"` `getCurrentUser()` inside `<Suspense>`.** A top-level session `redirect()` in a layout triggers "Could not validate instant" in dev.
- **Pass the lazy `db` to `drizzleAdapter`, never `getDb()`.** `auth` is built at import time, and an eager client aborts `next build` under PGlite.
- For social login (Google/GitHub/etc.), the user has to register OAuth apps with each provider and add `BETTER_AUTH_GOOGLE_CLIENT_ID` etc. to env. This is out of scope for v1 — leave a comment in `auth.ts` showing how to add them.
