# module-add → `realtime` (Vercel Functions WebSockets)

Wire **app-level realtime over WebSockets** — multi-user chat, presence, live counters, collaborative cursors — using **Vercel Functions WebSockets** in a Next.js App Router app.

Goal: a working `wss://…/api/ws` endpoint plus a typed client hook with reconnect/backoff, so the app can push and receive messages in realtime. **Not for agent streaming** — an eve agent already streams its responses (NDJSON via `useEveAgent`); use this only for realtime the agent does not own.

> The WebSocket API on Vercel is `experimental_*` and requires **Fluid compute**. Pin `@vercel/functions` and re-verify the surface against the installed version + <https://vercel.com/docs/functions/websockets>.

## Idempotency check

Before doing anything, check whether this is already wired:

1. `package.json` contains `"@vercel/functions"` in `dependencies`.
2. `app/api/ws/route.ts` exists.
3. `lib/realtime/use-socket.ts` exists.

If all three: tell the user it's installed, offer to regenerate the demo or extend the message protocol. Don't double-install.

## Prerequisites

- `meta.json#stack.framework` is `"next"` (or `"monorepo"` → operate in `apps/web/`). Next.js App Router only; Pages Router not supported.
- **Fluid compute must be enabled** on the Vercel project (default for projects created on/after 2025-04-23). Without it, WebSockets are rejected.
- For anything beyond a single instance (broadcast, rooms, presence shared across users), an **external store / pub-sub is required** — see "Shared state" below. A pure echo works with no store.

**When to NOT run this module:**
- You only need to stream the *agent's* output → use eve's stream (`useEveAgent`), not raw WS.
- One-way server-push notifications → SSE (`text/event-stream`) is simpler and survives reconnect better.

## Install

```bash
cd <project-root>            # or <project-root>/apps/web for monorepo
npm install @vercel/functions
```

The client uses the browser-native `WebSocket` — no package. If you need cross-instance broadcast/presence, also install a Redis client (see "Shared state").

## Files to write

### `app/api/ws/route.ts`

Next.js has no native WS upgrade API, so use the `@vercel/functions` workaround. A single connection is pinned to one function instance; this handler echoes and broadcasts to the connections *on the same instance*. Cross-instance broadcast needs external pub-sub (documented below).

```ts
import {
  experimental_upgradeWebSocket,
  type WebSocketData,
} from "@vercel/functions";

// Connections served by THIS instance. Not shared across instances/deployments.
const peers = new Set<WebSocket>();

export async function GET() {
  return experimental_upgradeWebSocket((ws) => {
    peers.add(ws as unknown as WebSocket);

    ws.on("message", (data: WebSocketData) => {
      // Broadcast to peers on this instance. For app-wide broadcast,
      // publish to Redis here and fan out on the subscriber (see below).
      for (const peer of peers) {
        try {
          (peer as unknown as { send: (d: WebSocketData) => void }).send(data);
        } catch {
          /* peer gone */
        }
      }
    });

    ws.on("close", () => {
      peers.delete(ws as unknown as WebSocket);
    });
  });
}
```

### `lib/realtime/use-socket.ts`

Typed client hook with reconnect + exponential backoff. The socket lifecycle is the sanctioned `useEffect` case (subscribing to an external system) — `state-discipline` allows it here; the connection `status` is honest UI state.

```ts
"use client";

import { useEffect, useRef, useState, useCallback } from "react";

export type SocketStatus = "connecting" | "open" | "closed";

/**
 * Connect to the app's WebSocket endpoint with reconnect/backoff.
 * `url` defaults to the same-origin /api/ws (wss in prod, ws in dev).
 */
export function useSocket(onMessage?: (data: string) => void) {
  const [status, setStatus] = useState<SocketStatus>("connecting");
  const socketRef = useRef<WebSocket | null>(null);
  const delayRef = useRef(1000);
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  useEffect(() => {
    let closed = false;
    let timer: ReturnType<typeof setTimeout>;

    const wsUrl =
      (location.protocol === "https:" ? "wss://" : "ws://") +
      location.host +
      "/api/ws";

    function connect() {
      setStatus("connecting");
      const ws = new WebSocket(wsUrl);
      socketRef.current = ws;

      ws.addEventListener("open", () => {
        delayRef.current = 1000;
        setStatus("open");
      });
      ws.addEventListener("message", (e) => onMessageRef.current?.(String(e.data)));
      ws.addEventListener("close", () => {
        setStatus("closed");
        if (closed) return;
        timer = setTimeout(connect, delayRef.current);
        delayRef.current = Math.min(delayRef.current * 2, 30_000); // cap 30s
      });
    }

    connect();
    return () => {
      closed = true;
      clearTimeout(timer);
      socketRef.current?.close();
    };
  }, []);

  const send = useCallback((data: string) => {
    const ws = socketRef.current;
    if (ws?.readyState === WebSocket.OPEN) ws.send(data);
  }, []);

  return { status, send };
}
```

### Reference UI: `app/realtime-demo/page.tsx`

A minimal echo/broadcast demo the user keeps as reference and deletes once internalized.

```tsx
"use client";

import { useState } from "react";
import { useSocket } from "@/lib/realtime/use-socket";

export default function RealtimeDemoPage() {
  const [log, setLog] = useState<string[]>([]);
  const [text, setText] = useState("");
  const { status, send } = useSocket((data) => setLog((l) => [...l, data]));

  return (
    <main className="mx-auto max-w-xl px-6 py-16 space-y-4">
      <p className="text-sm text-foreground/60">socket: {status}</p>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (text) { send(text); setText(""); }
        }}
        className="flex gap-2"
      >
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          className="flex-1 border rounded-lg px-3 h-10"
          placeholder="Type and press enter…"
        />
        <button className="h-10 px-4 rounded-lg bg-foreground text-background">Send</button>
      </form>
      <ul className="space-y-1 font-mono text-sm">
        {log.map((m, i) => <li key={i}>{m}</li>)}
      </ul>
    </main>
  );
}
```

## Shared state (cross-instance broadcast, rooms, presence)

A WebSocket is pinned to one instance, and a reconnect may hit a different instance or deployment. In-memory `Set`s only see one instance. For app-wide broadcast / rooms / presence:

- Add **Redis** (Vercel Marketplace) and use **pub-sub**: on `message`, `PUBLISH` to a channel; a `SUBSCRIBE`r on each instance fans the message out to its local `peers`.
- Keep presence/room membership in Redis (with TTL), not in memory.
- Env: `REDIS_URL` (or the provider's vars). Document in `.env.local.example`.

Document this clearly: without an external store, "broadcast" only reaches users who happened to land on the same instance.

## Environment variables

- WebSockets themselves: **none**.
- Cross-instance state: `REDIS_URL` (only if you add the Redis pub-sub layer).

## Update meta.json

```json
{ "stack": { "realtime": "vercel-ws" } }
```

## Known caveats

- **Experimental API**: `experimental_upgradeWebSocket` may change — pin `@vercel/functions`.
- **Fluid compute required** — enable it on the project, else upgrades are rejected.
- **Max-duration disconnects**: the connection closes when the function hits its max duration. Client reconnect with backoff (in `use-socket.ts`) is mandatory; on reconnect, re-subscribe to rooms and reload state.
- **Non-sticky instances**: never trust in-memory state for anything user-visible across connections — use the external store.
- **Rate-limit the upgrade path**: the upgrade is an HTTP `GET` through routing/firewall/rate-limits; protect `/api/ws` like any endpoint that mints billable sessions.
- **Not for agent streaming**: eve already streams via `useEveAgent` — don't reinvent it here.
- **Pricing**: WS uses Function time while open + Fast Data/Origin Transfer for messages — a chatty long-lived connection costs more than request/response.
