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

## The chat UI itself — use the shadcn chat primitives, not hand-rolled divs

`useEveAgent()` gives you the data (`data.messages`, `status`, `send`); it does NOT dictate
the UI. Build that UI with the **official shadcn chat components** (`MessageScroller` /
`Message` / `Bubble` / `Marker`, Jun 2026) — you get autoscroll, a scroll-to-bottom button
and scroll-fade for free instead of a hand-rolled `useRef`+`scrollTop`. The agent emits
**markdown**, so render assistant turns through `streamdown` wrapped in `.typeset`
(shadcn/typeset, Jul 2026) — never `whitespace-pre-wrap`, which leaves `**bold**` and lists
literal. Use `<Marker className="shimmer">` for the "agent is working" state, not a spinner.
Full recipe: `design-md-to-app/references/chat-and-typeset.md`. In a monorepo the primitives
live in the shared `packages/ui` (`@workspace/ui`), imported by `apps/web`.

**Option — Vercel AI Elements.** [AI Elements](https://ai-sdk.dev/elements) is Vercel's prebuilt
component kit for AI chat surfaces (message list, prompt input, reasoning/tool blocks, etc.),
installed via the shadcn CLI. It's a legitimate alternative when you want a batteries-included
AI-chat look out of the box — but it is **not** the default here: the **best practice stays the
shadcn chat components + `shadcn/typeset`** above, which stay consistent with the rest of the
app's design system and DESIGN.md tokens. Reach for AI Elements only when the user explicitly
wants that kit; bind it to `useEveAgent()`'s `data.messages`/`status`/`send` the same way.
(Seen in the wild in the `trycompai/crm` reference monorepo's `.agents/skills/ai-elements`.)

## Rich UI from agent output — the widget protocol

When the agent should render **structured cards** (a match, a chart, a data table), don't make
it emit HTML or JSON for the client to parse, and don't stuff the data into the model's context.
Use the **widget protocol**: the agent writes a fenced code block whose **language is the widget
name** and whose **body is only an identifier**; the client routes that fence to a React component
that **fetches its own data**. This is how `roprgm/worldcup-eve` renders every card.

````text
Argentina plays Friday.
```match
today
```
````

Why this beats emitting markup or data:

* **Cheap, deterministic tokens.** The model outputs a name + an id, not a payload — so it can't
  hallucinate the numbers, and short output is faster and within tighter `limits`.
* **Fresh data, owned by the UI.** The widget self-fetches (TanStack Query), so it shows live
  data from your API, not a snapshot frozen into the turn. Agent and UI stay decoupled.
* **The instructions ARE the contract.** `agent/instructions.md` carries a *question → tool →
  widget* table telling the model which fence to write; the client carries the matching renderers.

Client side, route the fences with `streamdown`'s custom renderers (`plugins.renderers`), keyed by
the widget languages. Render **nothing while `isIncomplete`** so a half-streamed fence never
flashes, and parse the body leniently (drop a stray `team:` label, tolerate casing/spacing):

```tsx
// components/chat/rich-markdown.tsx
import type { CustomRenderer, CustomRendererProps } from "streamdown";

const WIDGET_LANGUAGES = ["match", "group", "chances", "bracket"]; // = the fence names in instructions.md

function WidgetBlock({ language, code, isIncomplete }: CustomRendererProps) {
  if (isIncomplete) return null;                 // no partial-block flash mid-stream
  return renderWidget(language, code.trim());    // switch on language → a self-fetching <Widget/>
}

const WIDGET_RENDERERS: CustomRenderer[] = [{ language: WIDGET_LANGUAGES, component: WidgetBlock }];
// <Markdown plugins={{ renderers: WIDGET_RENDERERS }}>{assistantText}</Markdown>
```

Keep widget components **pure presentation fed by their own query** — they take an id, fetch, and
render; they never receive data through the agent. The seam is: model → fence name + id → your API.

## Passing browser context to the agent (`prepareSend` → `clientContext` → `defineDynamic`)

Per-request browser state (time zone, locale, viewport, the entity the user is looking at) reaches
the agent through **`prepareSend`**, which merges fields into every outgoing turn. The agent reads
them back in a **dynamic instruction** (or a tool) on `turn.started`. This is the client→agent
bridge — distinct from `defineDynamic` reading `ctx.session.auth` (verified identity, server-side).

```tsx
// client — inject context on every send
const agent = useEveAgent({
  prepareSend: (input) => ({
    ...input,
    clientContext: { timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone },
  }),
});
```

```ts
// agent/instructions/time.ts — read it fresh each turn
import { defineDynamic, defineInstructions } from "eve/instructions";
export default defineDynamic({
  events: {
    "turn.started": (ctx) => defineInstructions({
      markdown: `The user's IANA time zone is in the client context; state kickoffs in it.`,
      // ctx exposes the turn's clientContext — [VERIFY] the exact accessor against installed docs.
    }),
  },
});
```

Only send **non-sensitive** UI context this way (it is client-asserted, not verified) — never derive
tenant/user from it. Identity stays `ctx.session.auth.current`.

## Resumable chats — persist the event log, restore with `initialEvents`

`useEveAgent` exposes `session` (the `SessionState` cursor) and `events` (the raw stream log).
To make a conversation survive a reload with **no backend**, persist `events` (keyed by a chat id
in the URL, e.g. `/chat/<id>`) and rehydrate via `initialSession` / `initialEvents`:

```tsx
const agent = useEveAgent({ initialSession: saved?.session, initialEvents: saved?.events });
useEffect(() => {
  if (agent.events.length)
    save(id, { session: { ...(agent.session), streamIndex: agent.events.length }, events: agent.events });
}, [id, agent.session, agent.events]);
```

Gotchas worldcup-eve hit (encode these):

* **Pin `streamIndex` to the log length, not the live cursor.** eve's `session` cursor lags
  mid-turn and **resets when a stream aborts** (reload, `stop()`); saving the bare cursor over a
  good one loses resumability. Persist `streamIndex: events.length`.
* **Before the first turn boundary there is no `sessionId`** — you can only restart from the
  pending first message, not resume. After eve mints the cursor, mount as-is and the next `send`
  backfills the tail.
* **Gate reads on hydration.** The server has no restored events; reporting `messages` before
  hydration mismatches the server-rendered markup. Return `[]` until hydrated.
* **Detect terminal failure from the log.** A session that hits its token budget ends with a
  `session.failed` event carrying `SESSION_TOKEN_LIMIT_REACHED`; `status`/`error` don't survive a
  refresh but the event does — read the failure from the persisted log to keep a "limit reached"
  state sticky.

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
