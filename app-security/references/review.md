# The review checklist

The scan finds patterns. This file is how you decide whether a pattern is a hole. It is ordered by the
[OWASP Top 10:2025](https://owasp.org/Top10/2025/) and written for a dev-flow stack: Next.js 16 App
Router, better-auth with the helpers in `lib/auth-server.ts`, Drizzle, Zod.

Read the code each time. A flagged line is a reason to open a file, never a finding by itself.

## A01 — Broken access control

This is where real apps leak. **Every Server Action and every mutating route checks two things in its own
body: who is calling, and that the object belongs to them or to their tenant.**

Why both, and why in the body: an exported Server Action is a public POST endpoint. Anyone can call it
with any arguments, without ever loading the page that renders the form. A check in the page, the layout
or `proxy.ts` does not run for that call. [Next.js, *Data Security*](https://nextjs.org/docs/app/guides/data-security)
says this directly, and CVE-2025-29927 showed that middleware is not a security boundary.

Wrong — the session is checked, ownership is not (an IDOR, OWASP API1:
[Broken Object Level Authorization](https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/)):

```ts
"use server";
export async function deleteNote(id: string) {
  await getCurrentUserId();                            // any logged-in user…
  await db.delete(notes).where(eq(notes.id, id));      // …deletes anyone's note
}
```

Right — the owner is part of the query, so another user's id matches nothing:

```ts
"use server";
export async function deleteNote(input: unknown) {
  const { id } = z.object({ id: z.string().uuid() }).parse(input);
  const userId = await getCurrentUserId();
  await db.delete(notes).where(and(eq(notes.id, id), eq(notes.userId, userId)));
}
```

What to look at:

- the scan's `server-action-unauthenticated`, `route-handler-unauthenticated` and `query-by-id-unscoped`;
- **every action that takes an id**, even when it is not flagged: a session call satisfies the scan and
  proves nothing about ownership;
- multi-tenant apps: the filter is the tenant (`getCurrentTenantId()`), and a role check comes after it;
- a helper that does the check is fine, if it really receives the user and filters by them. Follow it.

The pattern that makes this hard to get wrong is a **Data Access Layer**: every query lives in
`lib/server/<domain>.ts`, starts with `import "server-only"`, gets the user from the session itself and
never takes a `userId` argument from the caller. Actions call the DAL and nothing else.

## A02 — Security misconfiguration

- **Headers.** A `Content-Security-Policy`, `X-Content-Type-Options: nosniff`, `Referrer-Policy` and
  `frame-ancestors` (or `X-Frame-Options`), set in `next.config.ts` `headers()` or in `proxy.ts`. The scan
  reports `security-headers-missing`; the fix is `vercel-deploy`'s.
- **better-auth.** `trustedOrigins` lists only the app's own origins; cookies are `secure` in production;
  `BETTER_AUTH_SECRET` is long, random and only on the server.
- **Errors.** Production errors do not return stack traces or database messages to the client.

## A03 — Software supply chain failures

- The scan's `dependencies` check. A vulnerable package that the app does not reach can be accepted, with
  the reason recorded in `meta.json#security.findings.accepted`.
- Third-party registry components go through `registry-intake`, never straight into `components/`.

## A05 — Injection

Validate every input the server receives, with Zod, before using it: FormData, `params`, `searchParams`,
headers, and the arguments of every Server Action. TypeScript types disappear at runtime; a caller can
send anything.

Wrong:

```ts
const rows = await db.execute(sql.raw(`select * from orders where status = '${status}'`));
```

Right — a Drizzle query builder, or the `sql` template with values as parameters:

```ts
const rows = await db.select().from(orders).where(eq(orders.status, status));
const rows = await db.execute(sql`select * from orders where status = ${status}`);
```

What to look at: the scan's `raw-sql`; `dangerouslySetInnerHTML` fed by user content; URLs built from
input and passed to `fetch`, `redirect()` or `rewrites()` (SSRF and open redirects).

## A07 — Authentication failures

- Sign-in, sign-up and password reset are rate-limited (better-auth `rateLimit`, or the platform's).
- A password reset token is single-use and expires; a reset invalidates the user's other sessions.
- Sign-in errors do not reveal whether an email exists.

## Data over-exposure

What leaves the server is part of the attack surface:

- **Action results.** Return the fields the UI needs, never a full row or the result of `.returning()`.
  A user row carries a password hash or provider tokens more often than anyone remembers. The scan reports
  `action-returns-row`.
- **Props to `"use client"` components.** Everything passed is serialized into the page. Pass a minimal
  object, not the database record.
- **Public variables.** `NEXT_PUBLIC_*` is inlined into the client bundle. Some keys are public by design:
  Supabase anon, Stripe publishable, a PostHog project key, a reCAPTCHA site key, any `_URL`. A secret,
  private key, token or password never is. The scan reports `public-env-secret`.
- **`server-only`.** Every module under `lib/server/` and `lib/db/` starts with `import "server-only"`, so
  importing it from a client component fails the build instead of shipping it. The scan reports
  `server-only-missing`.

## Mobile (Expo)

- Session and refresh tokens live in `expo-secure-store`. AsyncStorage is plain text on the device.
- `EXPO_PUBLIC_*` is in the bundle in plain text; anything secret stays on a server the app calls.
- The backend enforces authorization as if the app did not exist: a phone can be made to send any request.
  With Supabase, that means Row Level Security on every table the app reaches.

## eve agents

The agent's identity, approvals and guards are `eve-agent`'s (`eve-agent/references/eve-patterns.md`
§1–2). Check one thing here: the tools the agent calls go through the same owner-scoped DAL as the app.
A tool that takes a `userId` from the model's arguments is A01.

## One more pass, on a branch

Claude Code's built-in `/security-review` reads the current branch's diff against the main branch. It
needs an `origin` remote. Run it on a pull request when you want a second reading of what changed; it
does not replace the whole-app review above.

## Sources

- Next.js, *Data Security*: https://nextjs.org/docs/app/guides/data-security
- OWASP Top 10:2025: https://owasp.org/Top10/2025/
- OWASP API Security Top 10 2023, API1 BOLA: https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/
- OWASP ASVS 5.0.0: https://owasp.org/www-project-application-security-verification-standard/
