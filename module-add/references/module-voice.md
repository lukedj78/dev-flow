# module-add → `voice` (realtime voice over Vercel AI Gateway)

Wire a **realtime voice surface** (speech in / speech out) into a Next.js App Router app using the **Vercel AI Gateway** audio modalities: a server route mints a short-lived token, a client component captures the mic and streams over a WebSocket the SDK manages.

Goal: a working push-to-talk / live voice UI backed by the AI Gateway, with the token minted server-side (the gateway key never reaches the browser).

> ⚠️ **Lower-confidence source.** This reference is built from the AI Gateway announcement, not a verbatim API spec. The surface is `experimental_*` (AI SDK 7) and providers are OpenAI/xAI only at launch. **Before applying, verify every identifier** (`experimental_useRealtime`, `gateway.experimental_realtime.getToken`, model ids) against the installed `@ai-sdk/gateway` / `@ai-sdk/react` and <https://vercel.com/blog/realtime-voice-agents-on-ai-gateway>.

## The architecture decision (read first)

If the project also has an eve agent (`stack.agent="eve"`), **the agent is the brain and voice is just an I/O channel**: speech-to-text → eve agent (durable, your tools) → text-to-speech. Do **not** also let the realtime speech-to-speech model (`gpt-realtime-2`) run its own tool-calling loop — two control loops compete and fragment the logic. Use the realtime model as the primary brain only for low-latency, low-logic conversational products with no eve agent behind them.

## Idempotency check

1. `package.json` contains `"@ai-sdk/gateway"` and `"@ai-sdk/react"`.
2. `app/api/realtime/token/route.ts` exists.
3. `components/voice/voice-agent.tsx` exists.

If all three: report installed, offer to change the model/voice or regenerate the demo. Don't double-install.

## Prerequisites

- `meta.json#stack.framework` is `"next"` (or `"monorepo"` → operate in `apps/web/`). App Router only.
- A **Vercel AI Gateway** key (`AI_GATEWAY_API_KEY`) — the same gateway eve bills through.
- HTTPS in production (mic capture + secure WebSocket require a secure context).

## Install

```bash
cd <project-root>            # or <project-root>/apps/web for monorepo
npm install @ai-sdk/gateway @ai-sdk/react
```

## Files to write

### `app/api/realtime/token/route.ts` — mint the ephemeral token (server-only)

```ts
import { gateway } from "@ai-sdk/gateway"; // [VERIFY] import + method names

export async function POST() {
  // The gateway key (AI_GATEWAY_API_KEY) stays server-side; the browser only
  // ever receives a short-lived token + the connection URL.
  const { token, url } = await gateway.experimental_realtime.getToken({
    model: "openai/gpt-realtime-2", // [VERIFY] current model id
  });
  return Response.json({ token, url });
}
```

Rate-limit and auth-gate this route — it mints billable realtime sessions.

### `components/voice/voice-agent.tsx` — client component

```tsx
"use client";

import { experimental_useRealtime } from "@ai-sdk/react"; // [VERIFY]

export function VoiceAgent() {
  const agent = experimental_useRealtime({
    api: { token: "/api/realtime/token" }, // SDK calls this to fetch a token
  });

  async function start() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    await agent.connect();
    await agent.startAudioCapture(stream);
  }

  return (
    <div className="space-y-3">
      <button
        onClick={start}
        className="h-11 px-5 rounded-full bg-foreground text-background"
      >
        🎙️ Start talking
      </button>
      {/* render agent state / transcript from `agent` here — verify the
          hook's return shape (status, transcript, events) against the SDK */}
    </div>
  );
}
```

Connection state (idle / listening / speaking) belongs in the UI via the `state-discipline` skill.

### Reference UI: `app/voice-demo/page.tsx`

```tsx
import { VoiceAgent } from "@/components/voice/voice-agent";

export default function VoiceDemoPage() {
  return (
    <main className="mx-auto max-w-md px-6 py-20 text-center space-y-6">
      <h1 className="text-3xl font-bold">Voice demo</h1>
      <VoiceAgent />
    </main>
  );
}
```

## Wiring voice over an eve agent (the recommended topology)

When eve is the brain, don't point the realtime model at its own tools. Instead:
1. STT (`openai/whisper-1`) turns speech into text. For low-latency partial transcripts, the AI Gateway also supports **streaming transcription** via the AI SDK's `streamTranscribe` (new 2026-07-22) — stream mic audio and receive incremental transcript updates instead of one final blob; prefer it for live captions / barge-in. `[VERIFY]` the method name + import against the installed `ai` / `@ai-sdk/*`.
2. Send that text to the eve agent (its HTTP session API, via the same web integration `useEveAgent` uses).
3. Stream the agent's text reply to TTS (`xai/grok-tts`) and play it.

This keeps eve's durable session + tools as the single source of truth; voice is purely the microphone/speaker channel.

## Environment variables

- `AI_GATEWAY_API_KEY` — server-side only.

## Update meta.json

```json
{ "stack": { "voice": "ai-gateway-realtime" } }
```

## Known caveats

- **Experimental + provider-limited**: `experimental_*` API, OpenAI/xAI only at launch (`openai/gpt-realtime-2`, `openai/whisper-1`, `xai/grok-tts`). Re-check availability and pin SDK versions.
- **Never expose the gateway key client-side** — only the minted token.
- **Two-brains trap**: with an eve agent present, voice is I/O, not a second agent loop (see top).
- **Billing**: realtime audio bills through the Vercel AI Gateway, separate from any Claude Code tooling — and audio sessions are not cheap; gate the token endpoint.
- **Secure context**: mic + secure WS need HTTPS; won't work on plain `http://` except `localhost`.
- **Service tiers don't apply here**: the AI Gateway `serviceTier` (`priority`/`flex`/`default`, via `providerOptions.gateway`) is a *text-generation* control (OpenAI/Gemini `generateText`/`streamText`). It is **not** a knob on the realtime speech surface — don't try to pass it through `getToken`. Tune realtime latency at the model/voice level instead. Ref: <https://vercel.com/changelog/service-tiers-now-available-on-ai-gateway>.
