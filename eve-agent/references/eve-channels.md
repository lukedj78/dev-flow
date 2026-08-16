# eve-channels — per-surface guides

Deep dives for the platform channels that `eve-capabilities.md` §Channel only names. Read
§Channel first for the shared rules — including **which of these are a registry item
(`eve add channel/<kind>`) and which are authored by hand**, default export, Vercel Connect.
**Slack**, the **Chat SDK / Resend** channel, **Linear** and **custom** `defineChannel` channels
stay in `eve-capabilities.md` — they are already written up there.

Every channel here mounts at **`/eve/v1/<kind>`** by default: inside eve's protocol prefix, so
`withEve()` proxies it and no extra Next.js rewrite is needed. Routes *outside* that prefix do
need one.

**None of these can be smoke-tested on localhost** — the platform delivers over the public
internet. Deploy, then attach the TUI to the deployment with `eve dev <url>`.

`[VERIFY]` everything below against the installed `node_modules/eve/docs/` and types: these are
fast-moving surfaces, and the sections below were written against the published docs at
<https://eve.dev/docs/channels/>.

---

## Telegram — authored by hand, no registry item

⚠️ Per §Channel: `telegram` ships a subpath (`eve/channels/telegram`) and a docs page, but there
is **no `eve add channel/telegram`** — write the file yourself, as below. `[VERIFY]` against
`eve registry list` before assuming otherwise; the kind list has been wrong before.

```ts
// agent/channels/telegram.ts
import { telegramChannel } from "eve/channels/telegram";

export default telegramChannel({
  botUsername: "my_bot",
});
```

```bash
TELEGRAM_BOT_TOKEN=123456:...
TELEGRAM_WEBHOOK_SECRET_TOKEN=...
```

…or pass `credentials: { botToken, webhookSecretToken }`. The channel validates the
`X-Telegram-Bot-Api-Secret-Token` header before processing anything.

Mounts `POST /eve/v1/telegram`. Register the webhook once, out of band:

```bash
curl -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://your-app.example.com/eve/v1/telegram",
       "secret_token":"'"$TELEGRAM_WEBHOOK_SECRET_TOKEN"'",
       "allowed_updates":["message","callback_query"]}'
```

**Dispatch rules — the source of the most common "the bot ignores us" report.** Private chats
pass text, captions, photos and documents through. In **groups** only commands (`/ask`,
`/ask@my_bot`), `@my_bot` mentions, or replies to the bot's own messages reach the agent. That
is by design, not a misconfiguration. Forum topics carry `message_thread_id` in the continuation
token.

**Delivery.** The default handler sends plain text via `sendMessage` with no `parse_mode`;
messages over 4096 chars are split. Don't write the splitter — `eve/channels/telegram` exports
`splitTelegramMessageText` and `TELEGRAM_MESSAGE_TEXT_MAX_LENGTH`.

**HITL.** Option requests render as inline buttons, freeform ones as `ForceReply`. Callback data
is capped at 64 bytes, so eve keeps compact ids in channel state.

**Attachments** — opt in with an upload policy:

```ts
uploadPolicy: { allowedMediaTypes: ["image/*", "application/pdf"], maxBytes: 10 * 1024 * 1024 }
```

**Gating inbound with `onMessage`.** `[VERIFY]` — on the installed types (checked against
**0.27.6**; re-check on upgrade):

```ts
onMessage?: (ctx: TelegramContext, message: TelegramMessage) => TelegramInboundResultOrPromise;

type TelegramInboundResult = { readonly auth: SessionAuthContext | null;
                               readonly context?: readonly string[] } | null;
```

Returning **`null` suppresses the session entirely** — that is the gate for a `/start <token>`
deep link (bind an identity, don't start a turn) or an unknown sender (reply with an invite).
`context` is `readonly string[]`, plain text lines prepended to the turn — not an attribute bag.
`TelegramContext` is deliberately minimal (no channel state, no session ops: the session does not
exist yet), so any lookup must hit your own store. `defaults` exports `defaultOnMessage`, so a
custom gate can **wrap** it instead of reimplementing the private/group/reply filter.

**Two send paths, and they are not interchangeable.** The docs page documents proactive sends as
`to(telegram, target).send(message, { auth })` (`target.chatId` required, `messageThreadId`
optional) — that starts or resumes an **agent session**. For delivery *without* running the model
(templated transactional mail, audit copies), `eve/channels/telegram` also exports
`sendTelegramMessage({ chatId, body })`. `[VERIFY]`: `body` requires `{ text }` — a bare string
is rejected — and the result's `id` is `""` when Telegram returns none, so project it as
`result.id || undefined` rather than storing an empty string. This export is **not on the docs
page**, so treat it as less stable than the documented path.

---

## Discord — `eve add channel/discord`

```ts
// agent/channels/discord.ts
import { connectDiscordCredentials } from "@vercel/connect/eve";
import { discordChannel } from "eve/channels/discord";

export default discordChannel({
  credentials: connectDiscordCredentials("discord/my-agent"),
});
```

Mounts `POST /eve/v1/discord`. Credentials go through **Vercel Connect**, which verifies the
request signature before forwarding — the signing secret stays out of your env. Documented env
vars: `DISCORD_APPLICATION_ID`, `DISCORD_BOT_TOKEN`, `DISCORD_PUBLIC_KEY` (the first two are what
the registration call below reads).

Register the slash command once:

```bash
curl -X PUT "https://discord.com/api/v10/applications/$DISCORD_APPLICATION_ID/commands" \
  -H "Authorization: Bot $DISCORD_BOT_TOKEN" -H "Content-Type: application/json" \
  -d '[{"name":"ask","description":"Ask the eve agent","type":1,
    "options":[{"name":"message","description":"What should the agent do?","type":3,"required":true}]}]'
```

Handler: `onCommand: (ctx, interaction) => ({ auth }) | null`.

Gotchas in the order they bite:

* **Three-second ACK deadline.** The channel acknowledges immediately and runs the work in the
  background — nothing you add to the command path may block.
* **Global commands take up to an hour to appear.** A command "missing" right after the PUT is
  usually just propagating.
* Long replies are split at Discord's 2000-character limit.
* **Inbound file attachments are not supported** on this channel today.
* The typing indicator only shows when a bot token is present.

---

## Microsoft Teams — authored by hand, no registry item

⚠️ Same as Telegram: `teams` ships a subpath (`eve/channels/teams`) and a docs page, but **no
`eve add channel/teams`** — write the file yourself.

```ts
// agent/channels/teams.ts
import { teamsChannel } from "eve/channels/teams";

export default teamsChannel();
```

```bash
MICROSOFT_APP_ID=...
MICROSOFT_APP_PASSWORD=...
MICROSOFT_TENANT_ID=...   # optional, single-tenant bots
```

Mounts `POST /eve/v1/teams`; move it with `teamsChannel({ route: "/api/teams/activity" })`.
Exports `teamsChannel` and `defaultTeamsAuth`. A bearer JWT is validated on every Bot Framework
Activity POST. eve strips the mention, adds a `<teams_context>` block, and scopes channel and
group threads by root activity id.

Handlers: `onMessage(ctx, message)` (personal chats and mentions), `onInputResponse` (HITL
Adaptive Card submissions), `onInvoke(ctx, activity)` (non-HITL invoke logic). Proactive sends go
through `receive(teams, { target })` with a conversation reference.

> **⚠️ Authorization bypass worth reading twice.** HITL submissions carry the Teams identity of
> **whoever clicked the card**, not whoever started the thread. If you customize the `onMessage`
> allowlist, **apply the same policy in `onInputResponse`** — otherwise an unauthorized user
> pressing a button walks straight past the gate you put on messages.

Inbound files are disabled by default; enable and whitelist hosts explicitly:

```ts
teamsChannel({ files: { enabled: true, allowedHosts: ["..."] } })
```

---

## WhatsApp — no channel and no registry item, hand-author on the Chat SDK

WhatsApp has no first-class eve channel and nothing under `eve add channel/…` installs it: it
rides the **Chat SDK** (see `eve-capabilities.md` §Channel → Chat SDK for the shared shape and
the Resend worked example) with a WhatsApp adapter, authored by hand like the Resend example.

```ts
// agent/channels/whatsapp.ts
import { createWhatsAppAdapter } from "@chat-adapter/whatsapp";
import { createMemoryState } from "@chat-adapter/state-memory";
import type { Message, Thread } from "chat";
import { chatSdkChannel } from "eve/channels/chat-sdk";

export const { bot, channel, send } = chatSdkChannel({
  userName: "My Agent",
  adapters: { whatsapp: createWhatsAppAdapter() },
  state: createMemoryState(),
});

bot.onNewMention(async (thread: Thread, message: Message) => {
  await thread.subscribe();
  await send(message.text, { thread });
});

bot.onSubscribedMessage(async (thread: Thread, message: Message) => {
  await send(message.text, { thread });
});

export default channel;
```

Mounts `/eve/v1/whatsapp`. Credentials come from `createWhatsAppAdapter(...)` or the adapter's
env vars; full adapter docs at <https://chat-sdk.dev/adapters/official/whatsapp>. Note this
example does **not** set `streaming: false` — unlike email, WhatsApp tolerates progressive edits.
`chat-sdk-kapso` is the managed alternative if you don't want to own the WhatsApp Business Cloud
setup.

---

## Chat SDK threading — when it does not fit your domain

Before adopting a Chat SDK adapter for a surface where **you already have a conversation model**,
check how the adapter derives its thread. The Resend adapter resolves threads from the standard
`Message-ID` / `In-Reply-To` / `References` headers
(<https://chat-sdk.dev/adapters/vendor-official/resend>), and `openDM(address)` opens a new one;
there is no documented way to force an arbitrary thread id.

If your conversations are keyed on a **domain entity** — an order, a booking, a ticket, typically
carried in a `reply+<token>@` sub-address whose token is also the capability and the anti-spoofing
identity — the adapter's threading is at a different granularity than yours, and it is **not a
drop-in replacement**. Same question applies to any adapter: find out what the thread id is
derived from before you build on it, not after.

The mirror-image trap: a Chat SDK proactive send (`channel.receive()`) **starts an agent
session**. Templated transactional messages that must not run the model need a raw delivery path
instead — see the two Telegram send paths above for the shape of that distinction.
