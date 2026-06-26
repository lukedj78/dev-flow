# eve-web-integration — how the Next.js app consumes the agent

The web app is the **client**; the eve agent is the **engine**. Wire them with eve's
**official** Next.js integration, not by hand-rolling HTTP.

> Confirm exact API names, the hook return shape, and routes against `node_modules/eve/docs/`
> (live: <https://eve.dev/docs/guides/frontend/nextjs> and `.../client/*`). Package subpaths
> below are from the docs but should be verified against the **installed** eve version.

## The official pattern (use this)

eve ships a first-class Next.js integration so you do **not** write fetch/stream code:

* **`withEve()` — from `eve/next`** — wrap the Next.js config so eve's routes are mounted
  **same-origin** in the web app. The browser only ever talks to the Next.js origin; no CORS,
  no agent host named in client code.

  ```ts
  // next.config.ts
  import { withEve } from "eve/next";
  const nextConfig = {};
  export default withEve(nextConfig);
  // separate agent dir: withEve(nextConfig, { eveRoot: "../agent" })
  ```

  Options: `eveRoot` (default = Next app root), `eveBuildCommand` (default `"eve build"`),
  `servicePrefix` (default `"/_eve_internal/eve"`), `devServerTimeoutMs` (default `180000`).
  `eve channels add web` (or `eve init --channel-web-nextjs`) generates a `next.config.ts`
  already wrapped with `withEve`.

* **`useEveAgent()` — from `eve/react`** — a hook that opens a session, streams events, and
  exposes UI state. (Also `eve/vue`, `eve/svelte`; Nuxt/SvelteKit have their own config plugins.)

  ```tsx
  import { useEveAgent } from "eve/react";

  const agent = useEveAgent({
    headers: async () => ({ authorization: `Bearer ${await getAccessToken()}` }),
  });
  ```

  The bearer token is matched by an authenticator in `agent/channels/eve.ts` — which ships
  as `placeholderAuth()` and **rejects production traffic** until you replace it with real
  auth (Clerk / Auth.js / OIDC-JWT / API keys / custom `AuthFn`). eve fails closed.

### `useEveAgent()` return shape (what the UI binds to)

| Field | Meaning |
|---|---|
| `data` | projected UI state from the reducer; defaults to `{ messages }` |
| `status` | `"ready" \| "submitted" \| "streaming" \| "error"` — drives the composer |
| `error` | last `Error`, if any |
| `events` | raw eve stream events |
| `session` | `SessionState` cursor: `sessionId`, `continuationToken`, `streamIndex` |
| `send(input)` | send text or a full turn payload |
| `stop()` | abort the active request |
| `reset()` | clear events/data/errors + the local session cursor |

Useful options: `reducer`, `initialSession`, `initialEvents`, `host`, `auth`, `prepareSend`,
`onEvent`/`onError`/`onFinish`, `optimistic` (default `true`), `maxReconnectAttempts` (default `3`).

### Env vars (production)

* `EVE_NEXT_PRODUCTION_PORT` — port for a local production build (default `4274`).
* `EVE_NEXT_PRODUCTION_ORIGIN` — point the same-origin proxy at a **separately-deployed**
  agent on another origin. This is the seam that keeps `apps/agent` independently deployable
  while the browser still talks only to the web origin.

Do **not** introduce an ad-hoc `AGENT_BASE_URL` + manual `fetch` — `withEve()` handles routing.

## Message discipline (one turn at a time)

eve has no durable inbound queue. Send one turn per session and wait for the turn to settle
(`status === "ready"`, i.e. the `session.waiting` stream event) before the next `send`; if
the UI can burst, hold your own per-session queue. A session has one active
`continuationToken` at a time — a stale token is rejected. For raw `eve/client` use,
`await response.result()` before the next `session.send()`.

HITL: on `input.requested` / `authorization.required`, pause the composer and answer via
`inputResponses` keyed by `requestId`. Reconnect to a live stream with the `SessionState`
cursor (`sessionId` + `streamIndex`) rather than restarting it.

## The underlying HTTP contract (non-Next clients / debugging only)

`withEve()` proxies to eve's stable HTTP API. You normally never call it directly from the
Next app, but it is the contract for non-Next consumers and `curl` verification:

* `POST /eve/v1/session` — start a session (body has `continuationToken`; header `x-eve-session-id`).
* `POST /eve/v1/session/:sessionId` — continue (next turn).
* `GET  /eve/v1/session/:sessionId/stream` — stream events as **NDJSON** (`?startIndex=<n>` to replay).
* `GET  /eve/v1/info` — agent inspection · `GET /eve/v1/health` — public health check.

The typed client is `Client` from `eve/client` (`client.session().send(...)`, `result()`,
async-iterate for live events).

## Shared types (`packages/types`)

Re-export eve's own types so the wire contract is defined once — do **not** redefine them.
The relevant exports include `SessionState`, the stream-event type (`HandleMessageStreamEvent`),
and `EveMessage` (AI-SDK `UIMessage` convention). Verify the exact export surface against the
installed eve version.

## Boundary smells to avoid

* Importing agent internals as a library, or hand-rolling `fetch`/NDJSON parsing / an
  `AGENT_BASE_URL` instead of `withEve()` + `useEveAgent()`.
* Firing concurrent `send`s without gating on `status === "ready"` (turns get rejected).
* Redefining session/event types per app instead of re-exporting eve's via `packages/types`.
* Shipping a production channel still on `placeholderAuth()` (eve fails closed → rejected).
