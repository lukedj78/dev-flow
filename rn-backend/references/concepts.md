> Sources: expo-secure-store docs, supabase auth docs, firebase auth docs, OWASP mobile guide.

# Concepts — backend integration in mobile

## Mobile auth ≠ web auth

| Concern | Web | Mobile |
|---|---|---|
| Token storage | httpOnly cookie | Secure storage (Keychain/Keystore) — no cookies in native fetch |
| CSRF | Real concern (cross-site) | Not a concern (no cookies, no browser) |
| Session duration | Hours / days | Weeks / months (rotating refresh tokens) |
| Sign-out on close | Sometimes (session cookie) | Almost never (persistent token, "stay signed in") |
| Biometric re-auth | Rare | Common (Touch ID / Face ID on re-open) |

The implication: on mobile, the user expects to open the app and BE SIGNED IN. Even after weeks. The token persists; only the user explicitly signing out (or the refresh failing) ends the session.

## Token kinds

- **Access token (short-lived, 5-60 min)**: included in `Authorization: Bearer <token>`. Server validates per request.
- **Refresh token (long-lived, weeks-months)**: stored securely; presented to the auth endpoint to mint a new access token when the current one expires.
- **ID token (JWT, optional)**: contains user claims (id, email, role). Useful to avoid a `/me` call on cold start.

The refresh-on-401 dance:
1. Client sends request with access token.
2. Server returns 401 (token expired).
3. Client intercepts in `api()` wrapper. Sends refresh token to `/auth/refresh`.
4. Server returns new access + refresh.
5. Client stores both, retries original request.
6. If refresh ALSO returns 401 → sign out (refresh token revoked or expired).

## Where the token lives

```
expo-secure-store     ← persistent encrypted (token survives app restart)
        ↓ on app start
Zustand store         ← in-memory, synchronous reads
        ↓ on sign-in / refresh
TanStack Query cache  ← ["auth", "session"] mirror, drives refetch-on-focus + invalidation
        ↓ pass to api()
Authorization header  ← every protected request
```

The Zustand store is the SINGLE source of truth at runtime. Secure-store is the persistence layer. TanStack Query lets us treat the session like any other piece of server state — invalidate it, refetch it, show loading states.

## Server-side auth models — RLS vs API-auth

Two patterns. The skill teaches both because they imply different client code:

### RLS (Row Level Security) — Supabase, PostgreSQL direct

- Client calls the database DIRECTLY (over HTTPS, with the access token).
- Server enforces "which rows can this user read/write" via SQL policies.
- No custom API endpoints needed for CRUD.
- Pro: less server code; con: complex policies, hard to test, vendor-specific syntax.

### API-auth — custom REST / tRPC / GraphQL

- Client calls YOUR API endpoints.
- Server verifies the token, then queries the DB on behalf of the user.
- Authorization logic in TypeScript/Python/Ruby, not SQL.
- Pro: portable, easy to test; con: more code.

The CLIENT-SIDE code is similar either way: `api()` wrapper, secure-store, Zustand store, refresh-on-401. Only the URL of `api()` and the shape of `signIn` change between models.

## Auth flow on app launch (cold start)

```
1. App boots → app/_layout.tsx renders.
2. Read accessToken + refreshToken from expo-secure-store.
3. If both present:
   a. Hydrate Zustand store with tokens.
   b. Fire useQuery(["auth", "me"]) → /me endpoint.
   c. If /me returns 200 → store user, render protected routes.
   d. If /me returns 401 → try refresh once. On success retry /me. On failure → sign out (clear tokens, redirect to /(auth)/sign-in).
4. If no tokens → render (auth)/sign-in via the (app)/_layout.tsx redirect.
```

Pattern in `app/(app)/_layout.tsx`:

```tsx
import { Redirect, Stack } from "expo-router";
import { useAuthStore } from "@/store/auth";
import { useMe } from "@/lib/queries/useMe";

export default function ProtectedLayout() {
  const token = useAuthStore((s) => s.accessToken);
  const { isLoading, data: user, isError } = useMe(!!token);

  if (isLoading) return null; // splash
  if (!token || isError || !user) return <Redirect href="/(auth)/sign-in" />;
  return <Stack />;
}
```

## Sources

- https://docs.expo.dev/versions/latest/sdk/securestore/
- https://supabase.com/docs/guides/auth
- https://firebase.google.com/docs/auth
- https://owasp.org/www-project-mobile-app-security/
