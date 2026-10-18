# module-add → `observability` (errors · logs · uptime)

Without this module, a dev-flow app does not know when production breaks. The error a user sees stays in their
browser (`error.tsx` only `console.error`s), a Server Action's exception lives in Vercel's runtime logs (one hour
on Hobby), and nothing says when the site is down. Users find out first.

The module wires one **level** at a time, and skips a level that is already on:

| Level | What it gives | With | New sub-processor |
|---|---|---|---|
| `errors` | every client and server exception, with the release that introduced it | `@sentry/nextjs` 11.8.0 (MIT): Sentry EU, or GlitchTip for `eu-sovereign` | one, registered |
| `logs` | structured lines tied to a request, and kept beyond Vercel's window | `lib/log.ts`; a Vercel log drain to Axiom (EU) or Better Stack (`germany`) on Pro | one when drained |
| `uptime` | an email when the app stops answering | `app/api/health/route.ts` and a monitor: Sentry Uptime or Better Stack | the monitor's provider |

Versions and facts were checked on 2026-10-18 against npm and the providers' docs:
- Sentry's EU region costs the same as the US one, is available on the free Developer plan, and is chosen when the
  organization is created; it cannot be changed later.
- Sentry's server is FSL 1.1, not OSI. GlitchTip is MIT. Both speak the same SDK, so changing provider means
  changing the DSN.
- The provider table is `dev-flow/references/eu-data-sovereignty.md` §4.9.

## Before anything

1. **Choose the levels.** Read `meta.json#stack.observability`, a list where absent means none yet, and ask which
   levels to add. Before the first production deploy, `errors` is the minimum dev-flow proposes.
2. **Choose the provider by region.** Read `stack.data_residency`:

   | `data_residency` | errors | logs (drain) |
   |---|---|---|
   | `eu` | Sentry, with an organization in **Frankfurt** (`*.ingest.de.sentry.io`) | Axiom EU dataset, or Better Stack `germany` |
   | `eu-sovereign` | GlitchTip, self-hosted in the EU (MIT) | Better Stack `germany`, or none |
   | `none` | Sentry, either region | either |

3. **Never create the account.** The user creates it. The DSN and `SENTRY_AUTH_TOKEN` (for source maps) go into
   Vercel's env through `project-infra-setup`, never through chat.
4. **Register the provider** with `dev-flow/scripts/data_residency.py add`. `compliance-audit` reads it as a
   sub-processor.

## Level `errors`

```bash
pnpm add @sentry/nextjs@11.8.0
```

**`lib/observability/options.ts`** holds the one set of options every runtime shares:

```ts
import type { ErrorEvent } from "@sentry/nextjs"

const EMAIL = /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g

/** Nothing personal leaves the app: no cookies, no auth headers, no bodies, no emails, no tokens in URLs. */
export function scrub(event: ErrorEvent): ErrorEvent {
  if (event.request) {
    delete event.request.cookies
    delete event.request.data
    if (event.request.headers) {
      delete event.request.headers.cookie
      delete event.request.headers.authorization
    }
    if (event.request.url) event.request.url = event.request.url.replace(/([?&](token|code|key)=)[^&]+/gi, "$1[redacted]")
  }
  if (event.user) event.user = { id: event.user.id }
  return JSON.parse(JSON.stringify(event).replace(EMAIL, "[email]"))
}

export const options = {
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  release: process.env.NEXT_PUBLIC_VERCEL_GIT_COMMIT_SHA ?? process.env.VERCEL_GIT_COMMIT_SHA,
  environment: process.env.NEXT_PUBLIC_VERCEL_ENV ?? process.env.VERCEL_ENV ?? "development",
  sendDefaultPii: false,
  tracesSampleRate: 0,      // errors only; tracing is a later decision
  beforeSend: scrub,
}
```

**`sentry.server.config.ts`** and **`sentry.edge.config.ts`**, which are the same file:

```ts
import * as Sentry from "@sentry/nextjs"
import { options } from "./lib/observability/options"

Sentry.init(options)
```

**`instrumentation.ts`.** If the file already exists, keep what it does (for example `@vercel/otel`, or eve's
setup) and add to it:

```ts
import * as Sentry from "@sentry/nextjs"

export async function register() {
  if (process.env.NEXT_RUNTIME === "nodejs") await import("./sentry.server.config")
  if (process.env.NEXT_RUNTIME === "edge") await import("./sentry.edge.config")
}

// Next.js 16 calls this for every uncaught server error: Server Actions, RSC, route handlers.
export const onRequestError = Sentry.captureRequestError
```

**`instrumentation-client.ts`:**

```ts
import * as Sentry from "@sentry/nextjs"
import { options } from "./lib/observability/options"

Sentry.init(options)   // no replayIntegration: Session Replay stays off (privacy)

export const onRouterTransitionStart = Sentry.captureRouterTransitionStart
```

**`app/error.tsx`** (or `app/[locale]/error.tsx` when next-intl owns the root segment). Replace the scaffold's
`console.error` with
`Sentry.captureException(error)` inside a `useEffect`. Keep the `digest` on screen: it is the key to the server
event.

**`app/global-error.tsx`.** The scaffold writes it from `design-md-to-app/references/global-error.template.tsx`;
here, add `Sentry.captureException(error)` the same way.

**`next.config.ts`:**

```ts
import { withSentryConfig } from "@sentry/nextjs/config"   // not the package root: v11 exports it here only

export default withSentryConfig(nextConfig, {
  org: "<org>", project: "<project>",
  authToken: process.env.SENTRY_AUTH_TOKEN,   // source maps; set in Vercel by project-infra-setup
  sentryUrl: "https://de.sentry.io/",         // the EU org's API host; omit for a US org, use the GlitchTip URL for GlitchTip
  silent: !process.env.CI,
})
```

`sentryUrl` is the build option for the API host (also read from `SENTRY_URL`), checked in 11.8.0's types. When
`next.config.ts` already wraps other plugins (`withNextIntl`, eve's), `withSentryConfig` goes outermost.

**Content-Security-Policy.** If the app sends one, its `connect-src` must let the browser reach the ingest:
`https:` already does; a list of hosts needs `https://*.ingest.de.sentry.io` (or the GlitchTip host). The other way
is `tunnelRoute: "/monitoring"` in `withSentryConfig`, which posts through the app itself, so `'self'` is enough.

**`NEXT_PUBLIC_VERCEL_GIT_COMMIT_SHA`** has to be exposed to the client so that browser events carry the release.
On Vercel, enable "Automatically expose System Environment Variables".

**GlitchTip** uses the same files and options. `NEXT_PUBLIC_SENTRY_DSN` is the GlitchTip project's DSN, and
`sentryUrl` is the GlitchTip host, which accepts the source-map upload through the same API.

## Level `logs`

**`lib/log.ts`** writes one JSON line per event to stdout, which Vercel's runtime logs keep as is:

```ts
import "server-only"
import { headers } from "next/headers"

type Level = "info" | "warn" | "error"

async function write(level: Level, event: string, fields: Record<string, unknown> = {}) {
  let requestId: string | undefined
  try { requestId = (await headers()).get("x-request-id") ?? undefined } catch { /* outside a request: cron, build */ }
  const line = { ts: new Date().toISOString(), level, event, requestId, ...fields }
  ;(level === "error" ? console.error : console.log)(JSON.stringify(line))
}

export const log = {
  info: (event: string, fields?: Record<string, unknown>) => write("info", event, fields),
  warn: (event: string, fields?: Record<string, unknown>) => write("warn", event, fields),
  error: (event: string, fields?: Record<string, unknown>) => write("error", event, fields),
}
```

- **Never log secrets or personal data.** Log the id, not the email; log the outcome, not the request body.
- **`x-request-id`** is set in `proxy.ts`, on every request that does not already carry one:

  ```ts
  const requestHeaders = new Headers(request.headers)
  if (!requestHeaders.has("x-request-id")) requestHeaders.set("x-request-id", crypto.randomUUID())
  return NextResponse.next({ request: { headers: requestHeaders } })
  ```

  With `errors` on, tag it on the event as well (`Sentry.setTag("request_id", id)` in the server config's
  `beforeSend`, read from the headers), so a user's report, the event and the log line share one id.
- **Use it where failures disappear today:**
  - an email that returns `{ ok: false }`: `log.warn("email_failed", { template, reason })`;
  - a `track()` that fails;
  - each cron run's outcome.
- **Drain.** On Vercel **Pro**, a log drain sends the runtime logs to Axiom (an EU dataset) or Better Stack
  (`data_region: germany`). `project-infra-setup` configures it, and the provider is registered. On **Hobby**
  there is no drain and the logs last **one hour**: say so; do not pretend otherwise.

## Level `uptime`

**`app/api/health/route.ts`** answers 200 when the app and its database respond, and 503 otherwise. It returns no
personal data:

```ts
import { sql } from "drizzle-orm"
import { db } from "@/lib/db"

export const dynamic = "force-dynamic"

export async function GET() {
  let dbOk = false
  try { await db.execute(sql`select 1`); dbOk = true } catch { /* reported below */ }
  const release = process.env.VERCEL_GIT_COMMIT_SHA ?? null
  return Response.json({ ok: dbOk, db: dbOk, release }, { status: dbOk ? 200 : 503 })
}
```

Without a database (`stack.db` null), drop the database ping: `ok` then means "the app answers".

**The monitor.** Sentry Uptime (same provider, set up in the Sentry project) or Better Stack, on
`https://<domain>/api/health` every minute, alerting the project's email when the check fails. The user creates the
monitor. The module prints the steps and the URL, and creates no account.

## The proof, without an account

A configuration is not "done" until an event has been seen arriving. Before the user's DSN exists, prove it against
the local fake ingest:

```bash
python3 <skills>/module-add/scripts/fake_ingest.py serve --port 9010 --out .verification/ingest &
NEXT_PUBLIC_SENTRY_DSN=http://public@127.0.0.1:9010/1 pnpm dev -p 3313
# provoke one error in a Server Action and one in a client component, then:
python3 <skills>/module-add/scripts/fake_ingest.py summary .verification/ingest
```

The fake ingest is plain `http`: a CSP whose `connect-src` has only `'self' https:` blocks the browser's event.
Allow `http://127.0.0.1:9010` in development only (`process.env.NODE_ENV === "production" ? "" : " http://127.0.0.1:9010"`).
Use `127.0.0.1`, not `localhost`: a browser may resolve `localhost` to `::1`, where the ingest does not listen.

Expected:
- two or more events, carrying the release;
- `"emails": false` and `"authorization": false`.

Then stop exactly what you started. With the user's account, only the DSN changes.

## The check

```bash
python3 <skills>/module-add/scripts/observability_check.py <root>          # the levels in stack.observability
python3 <skills>/module-add/scripts/observability_check.py <root> --all    # every level
```

| Level | What is checked |
|---|---|
| `errors` | `onRequestError` in `instrumentation.ts`; the client init; `global-error.tsx` and `error.tsx` (or `app/[locale]/error.tsx`) reporting; a `release`; `sendDefaultPii` not true; no Replay; `withSentryConfig` from `@sentry/nextjs/config`; a CSP `connect-src` that lets the DSN host through; the DSN host matching `stack.data_residency` |
| `logs` | `lib/log.ts`; `x-request-id` |
| `uptime` | the health route |

A DSN read from an env var with no value in the env files reads **not checked**, never ok. So does privacy hidden
behind a spread. An Expo app is not applicable: use `rn-module-add observability`.

## Record

- `meta.json#stack.observability`: the active levels, for example `["errors", "logs"]`.
- `stack.observability_provider`, for example `{ "errors": "sentry", "logs": "axiom", "uptime": "sentry" }`.
- A history entry. Never `phase`.
