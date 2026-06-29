# module-add → planned variants (not yet implemented)

The references below describe modules that are **planned** but not yet wired into `module-add`. Each gives the structural shape (packages, env vars, prerequisites, out-of-band steps) so a contributor — or a future Claude session — can implement it from the cues here.

If the user invokes `module-add` for one of these and the full reference doesn't exist yet, **stop and tell them** — don't improvise. Improvising leads to half-wired modules that look done but break in production. The right path is: implement the full reference (copying the structure of `module-auth.md` / `module-db.md` / `module-payments.md` / `module-email.md`), commit, then run.

---

## `module-storage` — UploadThing (default) / S3 (alternative)

**Default**: UploadThing for file uploads (images, documents). Reference UI: a `/upload` example page with the UploadThing button + a `lib/uploadthing.ts` file router with size/type limits.

**Alternative**: S3 with presigned URLs — heavier setup (AWS credentials, IAM policy, CORS config) but no third-party dependency. Treat as a separate variant when the user explicitly asks.

**Prerequisites**: `auth` is recommended (to gate uploads to signed-in users and to associate uploads with the uploader).

**Packages**: `uploadthing`, `@uploadthing/react`.

**Env vars**: `UPLOADTHING_SECRET`, `UPLOADTHING_APP_ID`.

**Out-of-band steps**: register an UploadThing account, configure a file router with size/type limits, copy the keys to `.env.local`.

**Schema additions**: `files` table with `{ id, key, url, ownerId, sizeBytes, mimeType, createdAt }` — UploadThing doesn't track files for you beyond the upload itself.

**Caveats to document when implementing**:
- File size limits are enforced both client-side (UX) and server-side (security) — never trust the client.
- For images, ALWAYS validate MIME type server-side. Client-claimed type lies.
- Cleanup of orphaned uploads (uploaded but never linked to a record) is your responsibility — schedule a daily prune job.

---

## `module-deploy` — Vercel

**Default**: Vercel via `vercel.json` config + GitHub Actions integration. Detects framework from `meta.json#stack.framework` and writes the appropriate config (rewrites, redirects, function regions).

**Prerequisites**: at least one route should exist (so the deploy isn't deploying an empty scaffold). `module-add ci` should ideally have run, since `vercel.json` and the CI workflow share env-var conventions.

**Packages**: none (Vercel CLI is installed globally — `npm install -g vercel`).

**Env vars**: lifted from the existing `.env.local.example` and instructed to be set via the Vercel dashboard or `vercel env add`.

**Out-of-band steps**: run `vercel link`, push to GitHub, configure preview/production environments in the Vercel dashboard, set up branch protection.

**Alternative deploy targets**: Fly.io (containers, full Postgres), Cloudflare Pages (edge), Render, Railway. Each is a separate variant — implement when a user asks, copying the Vercel structure.

**Caveats to document when implementing**:
- Vercel's hobby tier has a 100GB-month bandwidth cap. Mention it.
- Edge runtime (`export const runtime = "edge"`) is a perf win for API routes that don't need Node APIs — but breaks for any route that uses `node:fs`, native modules, or heavy DB drivers (`pg` works, `@neondatabase/serverless` is preferred for edge).
- `vercel.json` `regions` defaults to `iad1` (Washington DC). For European audiences, set `["fra1"]` or `["lhr1"]` to halve cold-start latency.

---

## `module-voice` — realtime voice over AI Gateway

**What**: a realtime voice surface (speech in / speech out) for a Next.js app, on the **Vercel AI Gateway** audio modalities. Mints an ephemeral token server-side, connects over WebSocket client-side, renders a mic/transcript UI.

**Packages**: `@ai-sdk/gateway` (AI SDK 7), `@ai-sdk/react` (hook `experimental_useRealtime`).

**Models** (launch set, OpenAI/xAI only): `openai/gpt-realtime-2` (realtime), `openai/whisper-1` (STT), `xai/grok-tts` (TTS).

**Shape**:
- Server route `app/api/realtime/token/route.ts` → `gateway.experimental_realtime.getToken({ model })`. Never expose the gateway key client-side.
- Client component: `experimental_useRealtime({ api: { token: '/api/realtime/token' } })`, `connect()`, `startAudioCapture(stream)`, connection states via the `state-discipline` skill.

**Env vars**: `AI_GATEWAY_API_KEY`.

**Architecture decision (the important one)** — when the project also has an eve agent (`stack.agent="eve"`), **the agent is the brain and voice is just an I/O channel**: STT → eve agent (durable, your tools) → TTS. Do **not** let `gpt-realtime-2` run its own tool-calling loop *and* eve's loop — two control loops compete and fragment the logic. Pick one brain. Use the realtime speech-to-speech model as the primary loop only for low-latency, low-logic conversational products.

**Caveats to document when implementing**:
- The API is `experimental_*` (AI SDK 7) — expect breaking changes; pin versions.
- Launch providers are OpenAI/xAI only; check current model availability before wiring.
- Token endpoint must be rate-limited and auth-gated (it mints billable sessions).

---

## `module-realtime` — Vercel Functions WebSockets

**What**: app-level realtime over **Vercel Functions WebSockets** — multi-user chat, presence, collaborative cursors. Requires **Fluid compute** (default for projects created after 2025-04-23) and the WebSockets permission on the project.

**Shape** (Next.js has no native WS API → use the workaround):
- Route `app/api/ws/route.ts` exporting `GET` that returns `experimental_upgradeWebSocket((ws) => { ws.on('message', …) })` from `@vercel/functions`.
- Client: a plain `WebSocket('wss://…/api/ws')` with reconnect/backoff (connections close at the function's max duration).

**Packages**: `@vercel/functions` (Next.js workaround); `ws` / `socket.io` for non-Next Node servers.

**State**: instances are **not** sticky and a reconnect may hit a different instance / deployment → store rooms, presence, counters, pub/sub in an **external store** (e.g. Redis), never in memory.

**Architecture decision (the important one)** — **do NOT use this for agent streaming.** An eve agent already streams its responses (NDJSON via `useEveAgent`); reaching for raw WebSockets there just reinvents it. Use `module-realtime` only for genuine **user-to-user / collaborative** realtime that the agent doesn't own. (If you ever need an eve channel over WS, `defineChannel` has `WS()` helpers and eve-on-Nitro supports it on Vercel — niche.)

**Caveats to document when implementing**:
- API is `experimental_upgradeWebSocket` — expect changes; pin `@vercel/functions`.
- Connection drops at function max-duration → client reconnect with backoff is mandatory.
- Upgrade requests pass through routing/firewall/rate-limits; rate-limit the upgrade path.

---

## When to implement these

Implement on demand: the first time a user says "module-add storage" or "module-add deploy". Don't preemptively implement all of them — references that go stale (e.g., Stripe API version drift, UploadThing SDK changes) hurt more than the missing variant. Implement the variant fully — including the install templates and reference UI — when the user asks for it.

Always update:
1. `module-add/SKILL.md` — flip the row from 🚧 to ✅, swap `references/module-stubs.md` for the new file path.
2. `dist/` — re-package the skill.
3. README — same flip.
