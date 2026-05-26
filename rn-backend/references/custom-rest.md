> Sources: internal opinion, OWASP API Security.

# Custom REST/JSON backend

Use when: you already have a Node/Rails/Django/Go server, OR you want full control without BaaS vendor lock-in.

The full client-side code is in `references/patterns.md` — `api()` wrapper, refresh-on-401, Zustand store, token-store. This file documents the server contract the client expects.

## Server contract (what the backend MUST provide)

### Endpoints

```
POST   /auth/sign-up          { email, password, name? } → 201 { accessToken, refreshToken, user }
POST   /auth/sign-in          { email, password }         → 200 { accessToken, refreshToken, user }
POST   /auth/refresh          { refreshToken }            → 200 { accessToken, refreshToken }
POST   /auth/sign-out         (Authorization: Bearer)     → 204 (revokes refreshToken server-side)
GET    /me                    (Authorization: Bearer)     → 200 { id, email, name, ... }
POST   /auth/forgot-password  { email }                   → 204 (sends reset email)
POST   /auth/reset-password   { token, newPassword }      → 204
```

### Auth header

`Authorization: Bearer <accessToken>` on every protected endpoint.

### Token shape (recommendation)

- **Access token**: JWT with 15-60 minute expiry. Claims: `sub` (user id), `email`, `iat`, `exp`. Signed HS256 with a strong secret.
- **Refresh token**: opaque random string (32+ bytes), stored hashed server-side. Long expiry (weeks to months). Single-use: refresh returns a new pair, the old refresh is invalidated.

### Error responses

```
401 → token expired or invalid. Client triggers refresh-on-401 dance.
403 → authenticated but not authorized. Don't retry.
4xx → user-facing validation error. Server returns { error, fields? }.
5xx → server problem. Client retries (TanStack Query handles this).
```

The client's `api()` wrapper (in `patterns.md`) handles all of these.

## CORS

Native fetch doesn't enforce CORS — but your backend should still send sane headers in case you also have a web client. Allow your dev origin (e.g. `http://localhost:8081`) for Expo dev mode.

## Rate limiting

- `/auth/sign-in` and `/auth/sign-up`: rate limit by IP (e.g. 5/minute). Brute-force protection.
- `/auth/refresh`: rate limit by refresh token (e.g. 10/minute). Stops token-leak abuse.
- Other endpoints: by user id, more generous (e.g. 100/minute).

## Password storage (server-side, sanity check)

- Bcrypt or Argon2id. Cost factor ≥ 12 for bcrypt.
- NEVER store plain or MD5/SHA1.
- Email enumeration: same response for "wrong email" and "wrong password" — `401 Unauthorized` with generic message.

## Sign-up flow

```
1. Client sends { email, password, name } to /auth/sign-up.
2. Server validates (email format, password strength), hashes password, creates user.
3. Server returns { accessToken, refreshToken, user } — user is signed in immediately.
4. (Optional) Server sends verification email; until verified, set a `verified: false` flag.
```

Do NOT send verification email and require the user to verify before they can use the app — that's a friction point. Verify in the background, gate only the features that need it.

## OAuth — adding social providers

For "Sign in with Google / Apple / GitHub", use `expo-auth-session` on the client + your own OAuth handler on the server:

```ts
// Simplified pseudo-code, client side
import * as AuthSession from "expo-auth-session";

const result = await AuthSession.startAsync({ authUrl: `${BASE_URL}/auth/google` });
if (result.type === "success") {
  // The result returns to our redirect URI with the token in the URL params
  // Server-side: we handle the OAuth callback, exchange code for token, return our own JWT
}
```

This is more work than Supabase/Firebase (which handle OAuth callbacks for you). Use only if you have a strong reason to own the auth flow.

## Tipi end-to-end (without tRPC)

Share TypeScript types between server and client:

```
my-monorepo/
├── server/
├── client/
└── shared/
    └── types.ts   ← imported by both
```

Or publish a `@yourapp/types` package on a private npm registry. Without shared types, you write fetch wrappers blind and pay for it in runtime errors.

If you want types automatically — see `trpc.md`.

## Testing the server contract from the client

```ts
// __tests__/integration/auth-flow.test.ts
import { api } from "@/lib/api";

// Boot a test server (Docker, MSW, or hit a dev API)
// Then run end-to-end sign-up → sign-in → /me → refresh → sign-out
```

This is a slow integration test. Run in a separate CI stage from unit tests.
