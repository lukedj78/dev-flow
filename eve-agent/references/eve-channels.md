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

Verified against `eve@0.47.6` (`npm pack`, `docs/channels/` + the emitted `.d.ts`) — the Telegram
signatures, the send paths and the registry-item question below all still hold. These are
fast-moving surfaces, so re-check on upgrade rather than assuming this line ages well.

> **Re-read in full at `eve@0.47.6`** (2026-09-01, `docs/channels/*.mdx` + the emitted `.d.ts` and channel implementations). Every behavioural claim below held: Telegram's group dispatch rules and `message_thread_id` in the continuation token, Discord's three-second ACK deadline, the up-to-an-hour propagation of global commands, the 2000-character split and the unsupported inbound attachments, Teams' `defaultTeamsAuth` and Bot Connector JWT check, and the Chat SDK's `{ bot, channel, send }` return. The `eve add channel/<kind>` list is unchanged. Two Discord details were **missing** and are now written up below; nothing was wrong. Package names in the WhatsApp example re-checked on npm: `@chat-adapter/whatsapp@4.39.0` exports `createWhatsAppAdapter`, and `chat` / `@chat-adapter/state-memory` are on the same 4.39.0 line.

---

## Telegram — authored by hand, no registry item

⚠️ Per §Channel: `telegram` ships a subpath (`eve/channels/telegram`) and a docs page, but there
is **no `eve add channel/telegram`** — write the file yourself, as below. Still true at 0.47.6:
of the shipped channel docs pages, only `discord`, `github`, `linear-agent`, `linq`, `photon-imessage`,
`slack` and `web` name an `eve add`. Check `eve registry list` before assuming otherwise; the kind
list has been wrong before.

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
is capped at 64 bytes, so eve keeps compact ids in channel state. **Since 0.45.0 Telegram also
carries authorization challenges** — the "sign in to continue" flow, not just answer-a-question —
which Chat SDK direct messages gained in 0.44.4. The set of surfaces where a connection can ask a
user to authorize mid-turn is widening release by release, so **check the version before assuming a
channel can only ask questions**: on a surface without challenge support the same flow fails rather
than degrading to a question.

**Attachments** — opt in with an upload policy:

```ts
uploadPolicy: { allowedMediaTypes: ["image/*", "application/pdf"], maxBytes: 10 * 1024 * 1024 }
```

Since **0.77.0** eve applies `uploadPolicy` to **every staged file** — including links it downloads
itself — on the final bytes and their *verified* media type (checked against the bytes, not the
declared type); a file over the cap or of a disallowed type reaches the model as a note instead of
failing the turn. When a channel's `fetchFile` returns `null` (or there is none) **eve now fetches a
public `https:` link itself** (25 MB cap, 30 s timeout, at most 10 links per message) rather than
handing the URL to the model provider. Only PNG/JPEG/GIF/WebP up to 3 MiB and 8000 px per side, and
PDFs up to 20 MiB, go to the model as bytes; everything else arrives as a labelled sandbox path. A
custom `fetchFile` can throw `attachmentError(message)` from `eve/channels` to tell the model why a
file did not arrive while the original error stays in the logs. **Egress note:** eve's own
downloader is a new outbound fetch from the app runtime, driven by links users post.

**Gating inbound with `onMessage`.** On the installed types (re-verified against **0.47.6** — the
shape has not moved since 0.27.6, and it now also carries an optional `title` that overrides the
workflow run title without changing what the model receives):

```ts
onMessage?: (ctx: TelegramContext, message: TelegramMessage) => TelegramInboundResultOrPromise;

type TelegramInboundResult = { readonly auth: SessionAuthContext | null;
                               readonly context?: readonly string[] } | null;
```

Returning **`null` suppresses the session entirely** — that is the gate for a `/start <token>`
deep link (bind an identity, don't start a turn) or an unknown sender (reply with an invite).
⚠️ **Don't generalise this to eve's own channel**: a canonical eve `onMessage` lost the ability to
veto by returning `null` in 0.31.0. Telegram's hook still drops the update; they are different
contracts wearing the same name.
`context` is `readonly string[]`, plain text lines prepended to the turn — not an attribute bag.
`TelegramContext` is deliberately minimal (no channel state, no session ops: the session does not
exist yet), so any lookup must hit your own store. `defaults` exports `defaultOnMessage`, so a
custom gate can **wrap** it instead of reimplementing the private/group/reply filter.

**Two send paths, and they are not interchangeable.** The docs page documents proactive sends as
`to(telegram, target).send(message, { auth })` (`target.chatId` required, `messageThreadId`
optional) — that starts or resumes an **agent session**. For delivery *without* running the model
(templated transactional mail, audit copies), `eve/channels/telegram` also exports
`sendTelegramMessage({ chatId, body })`. Confirmed at 0.47.6: `body` is a `TelegramMessageBody`
whose only required field is **`text: string`** — a bare string is rejected — and the result's `id` is `""` when Telegram returns none, so project it as
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

Handler: `onCommand: (ctx, interaction) => ({ auth, title?, context?, ephemeral? }) | null`.
Returning `null` drops the interaction with an ephemeral "Command ignored."; `title` names the session,
`context` prepends extra blocks before eve's own interaction context block, and `ephemeral: true` makes
the deferred acknowledgement visible only to the caller.

Gotchas in the order they bite:

* **Three-second ACK deadline.** The channel acknowledges immediately and runs the work in the
  background — nothing you add to the command path may block.
* **Global commands take up to an hour to appear.** A command "missing" right after the PUT is
  usually just propagating.
* Long replies are split at Discord's 2000-character limit.
* **Inbound file attachments are not supported** on this channel today.
* **Generated messages default to `allowed_mentions: { parse: [] }`** — nothing the agent writes can
  ping `@everyone`, a role, or a user unless you override it. Worth knowing before you wonder why a
  deliberate mention did nothing; worth leaving alone otherwise.
* **Delivery falls back on its own.** The first reply edits the deferred interaction response and
  later ones are followups; if the interaction token is rejected, the channel retries as a
  bot-authenticated channel message rather than dropping the reply.
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

⚠️ **Version floor: `chat` and the `@chat-adapter/*` packages at `^4.42.0`.** eve declares `chat`
as an **optional peer** at `^4.42.0` and never as a dependency — checked on both eve 0.80.0 and
0.91.0 — so the host app owns the only copy. **chat 4.41 broke Workflow DevKit workflows in host
apps** (vercel/chat#969), which is what the floor is for. The 4.39.0 line recorded in the 0.47.6
note above is below it — pin the adapters to the same minor as `chat`.

🔴 **The floor is a minimum, and `^4.42.0` no longer resolves to 4.42.0.** Read on npm 2026-11-07:
`chat` and the whole `@chat-adapter/*` line are at **4.44.0**, while eve pins **exactly 4.42.0** in
its own `devDependencies` (`chat`, `@chat-adapter/slack`, `@chat-adapter/twilio`,
`@chat-adapter/state-memory`) — that is the minor eve is tested against. So a fresh `pnpm add chat`
installs two minors above it. This is not a reason to pin backwards; it is a reason to **say which
minor is installed** when a Chat SDK channel misbehaves, because on this line a minor has already
broken a host app once.

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

---

## json-render — a native card instead of markdown, when the client is not ours

A Chat SDK channel answers in text. **json-render** is the layer that lets the model answer in
**components the platform draws natively**: Block Kit on Slack, Adaptive Cards on Teams. The agent
emits a JSON spec from a **typed catalog**, so it composes from a declared set and cannot invent an
element — golden rule 3, applied to the model's output at runtime instead of to our code.

⚠️ **Read from Vercel's changelog (2026-11-06) and npm metadata, not from the packages' `dist`.**
The names below are the changelog's. Read each one out of the shipped package before building on it,
as `release-intelligence/references/provider-contracts.md` had to after documenting an export that
did not exist.

| Package | Version | Licence | First published |
|---|---|---|---|
| `@json-render/core` | 0.22.0 | Apache-2.0 | 2026-01-14 |
| `@json-render/chat` | 0.22.0 | Apache-2.0 | **2026-11-04** |
| `@json-render/react` | 0.22.0 | Apache-2.0 | 2026-01-14 |

The shape, as the changelog gives it: `defineCatalog` (`@json-render/core`) declares the components;
`schema`, `standardComponentDefinitions`, `toCard`, `streamCard` and `CardSpecError`
(`@json-render/chat`) validate and post. `catalog.prompt()` goes into the model's system prompt, and
`await streamCard(thread, result.textStream)` streams the card into the thread the bot was mentioned
in — the same `bot.onNewMention` handler as the WhatsApp example above.

🔴 **Pass `limits`, or the degradation is silent.** Every platform caps a single message, and past
that cap an adapter degrades on its own: the changelog's own example is the Slack adapter turning a
second table into a code block. A silent downgrade reads as success, which is the one thing refused
everywhere else in this suite — `limits` makes the card **fail** instead, and a refusal is the answer
we want. Two more facts before promising live updates: edits are throttled to at most one every
**500 ms**, and the **final validated card exists only once the stream has ended**. `CardSpecError`
carries one readable issue per problem, so the natural recovery is to hand it back to the model.

**Not adopted (2026-11-07):** `@json-render/chat` is three days old. The row in
`dev-flow/references/resources.md` records why it is worth knowing anyway — it is the only answer we
have to *what an agent's reply looks like on a surface where our own components cannot run*, which is
most of the channels on this page. The web-chat half of that question is the `OpenUI` row beside it,
and the step that would decide between them is still unwritten.
