# Chat interfaces & rendered markdown — the shadcn standard

When a Next.js + shadcn project needs **any conversational surface** (an AI chat, a
support inbox, a comment thread, an agent console) or needs to **render markdown/rich
text** (AI output, documentation, a description field), do NOT hand-roll it with
`div`/`ul` + manual autoscroll + `whitespace-pre-wrap`. Compose the official shadcn
primitives. This is a **standard**, not a suggestion.

Verify names/versions against the changelog (<https://ui.shadcn.com/docs/changelog>) and
the installed registry — the surface is young and grows.

> **The reference implementation is official and MIT**: [`shadcn-ui/chatbot-template`](https://github.com/shadcn-ui/chatbot-template)
> — Next.js + AI SDK + shadcn/ui + `@shadcn/react` + shadcn/typeset on the Vercel AI Gateway.
> When you need to know *how these pieces fit*, read it rather than inferring. Its pinned stack
> (verified 2026-08): `next@16.2.6`, `ai@^7`, `@ai-sdk/react@^4`, `@shadcn/react@^0.3`,
> `@base-ui/react@^1.7`, `react@19.2.4`, `tw-animate-css@^1.4`.

## 1. Chat components (shadcn, June 2026)

Install into the shared UI location (`packages/ui` in a monorepo, else the app):

```bash
pnpm dlx shadcn@latest add message-scroller message bubble attachment marker
pnpm add @shadcn/react           # peer of message-scroller (the scroll engine)
```

The five registry families — **use them all** where the data has the shape for it; each is
a set of composable parts, not one tag:

| Family | Parts | Renders |
|---|---|---|
| `message-scroller` | `MessageScrollerProvider` · `MessageScroller` · `Viewport` · `Content` · `Item` · `Button` | anchored turns, streamed replies, thread restore, prepended history, jump-to-message, scroll controls, visibility |
| `message` | `Message` · `MessageAvatar` · `MessageHeader` · `MessageContent` · `MessageFooter` · `MessageGroup` | the row: avatar, alignment, header, content, footer, grouping |
| `bubble` | `Bubble` · `BubbleContent` · `BubbleGroup` · `BubbleReactions` | the surface: variants, alignment, reactions, links, buttons |
| `attachment` | `Attachment` · `AttachmentGroup` · `AttachmentMedia` · `AttachmentContent` · `AttachmentTitle` · `AttachmentDescription` · `AttachmentActions` · `AttachmentAction` · `AttachmentTrigger` | files & images: media, metadata, upload state, actions, full-card trigger |
| `marker` | `Marker` · `MarkerIcon` · `MarkerContent` (variants `default`/`separator`/`border`) | status updates, system notes, labeled separators |

Render `MessageAvatar` **always**, `Attachment` **whenever a message has file parts**
(AI-SDK `FileUIPart`: `{ type:"file", url, mediaType, filename? }`), `Marker` for the
working/system state. Don't drop parts of the anatomy just because the first version didn't
need them — that's the gap this reference exists to close.

They reference CSS utilities — `scroll-fade-b`, `shimmer`, `scrollbar-thin`,
`scrollbar-gutter-stable`, `scrollbar-none` — that are **NOT guaranteed to be in your
`globals.css`** (they ship in fresh 2026 inits, but an older or hand-tokenized
`globals.css` won't have them, and the component renders unstyled/broken with no error).
**Field-verified gotcha:** after `shadcn add`, grep `globals.css` for `scroll-fade` — if
missing, add these Tailwind v4 `@utility` blocks (they consume your theme tokens):

```css
@utility scrollbar-thin { scrollbar-width: thin;
  &::-webkit-scrollbar { width: 6px; height: 6px; }
  &::-webkit-scrollbar-thumb { background-color: var(--border); border-radius: 9999px; }
  &::-webkit-scrollbar-track { background: transparent; } }
@utility scrollbar-none { scrollbar-width: none; &::-webkit-scrollbar { display: none; } }
@utility scrollbar-gutter-stable { scrollbar-gutter: stable; }
@utility scroll-fade-b { mask-image: linear-gradient(to bottom, black calc(100% - 2rem), transparent 100%); }
@keyframes ui-shimmer { 100% { transform: translateX(100%); } }
@utility shimmer { position: relative; overflow: hidden;
  &::after { content: ""; position: absolute; inset: 0; transform: translateX(-100%);
    background: linear-gradient(90deg, transparent, color-mix(in oklab, var(--foreground) 8%, transparent), transparent);
    animation: ui-shimmer 1.5s infinite; } }
```

Composition — the **full anatomy** (avatar + attachments included). Wrap it in ONE reusable
presentational component (e.g. `components/shared/chat/agent-conversation.tsx`) taking
`messages` + `isBusy`; keep the chat containers thin (they own the data hook + prefill), and
every chat in the app renders through it — the anatomy lives in exactly one place:

```tsx
<MessageScrollerProvider>
  <MessageScroller className="min-h-0 flex-1">
    <MessageScrollerViewport>
      <MessageScrollerContent>
        {messages.map((m, i) => {
          const files = m.parts.filter((p) => p.type === "file")
          const isUser = m.role === "user"
          return (
            <MessageScrollerItem key={m.id} scrollAnchor={i === messages.length - 1}>
              <Message align={isUser ? "end" : "start"}>
                <MessageAvatar>{isUser ? <User/> : <Bot/>}</MessageAvatar>
                <MessageContent>
                  <MessageHeader>{isUser ? "You" : "Assistant"}</MessageHeader>
                  {text && (
                    <Bubble variant={isUser ? "secondary" : "ghost"} align={isUser ? "end" : "start"}>
                      <BubbleContent>
                        {isUser
                          ? <span className="whitespace-pre-wrap">{text}</span>
                          : <AgentMarkdown compact>{text}</AgentMarkdown>}
                      </BubbleContent>
                    </Bubble>
                  )}
                  {files.length > 0 && (
                    <AttachmentGroup>
                      {files.map((f) => (
                        <Attachment key={f.url}>
                          <AttachmentMedia variant={f.mediaType.startsWith("image/") ? "image" : "icon"}>
                            {f.mediaType.startsWith("image/") ? <img src={f.url} alt={f.filename ?? ""}/> : <FileText/>}
                          </AttachmentMedia>
                          <AttachmentContent><AttachmentTitle>{f.filename ?? f.mediaType}</AttachmentTitle></AttachmentContent>
                        </Attachment>
                      ))}
                    </AttachmentGroup>
                  )}
                </MessageContent>
              </Message>
            </MessageScrollerItem>
          )
        })}
        {isBusy && (
          <MessageScrollerItem>
            <Marker><MarkerContent className="shimmer">Working…</MarkerContent></Marker>
          </MessageScrollerItem>
        )}
      </MessageScrollerContent>
    </MessageScrollerViewport>
    <MessageScrollerButton />   {/* "scroll to bottom" — free, don't hand-roll */}
  </MessageScroller>
</MessageScrollerProvider>
```

What you get for free — and therefore must NOT re-implement: autoscroll that yields to
the user, the scroll-to-bottom button, edge scroll-fade, virtualization hooks. **Deleting
a hand-rolled `useRef`+`scrollTop=scrollHeight`+`overflow-y-auto` is the point.**

**Keep `MessageScrollerButton`** — it is *the* scroll-to-bottom affordance and it stays
active during streaming (it sets `data-active` from the scrollable state, `inert` +
`tabIndex={-1}` when at the bottom). Don't remove it in favor of a custom pill; the two
serve different jobs.

**The scroller hooks** (from `@shadcn/react/message-scroller`, re-exported by the ui
component) let you *track the reader's position*, complementing the button — call them from a
child *inside* the Provider, and give each `MessageScrollerItem` a `messageId` (visibility
only tracks rows that have one). This is the docs' **"Tracking the Reader's Position"**
pattern. **The canonical shape is a Transcript Outline — a side minimap, NOT a chip/hint.**
Field lesson: a "you're reading history · back to latest" chip is what you build when you
*haven't* read the demo — it was explicitly rejected as "ugly and pointless." The demo
(`message-scroller#tracking-the-readers-position`) is a vertical **outline of dashes, one per
turn**, that visually marks where you are as you scroll, and lets you jump:

- `useMessageScrollerVisibility()` → `{ currentAnchorId, visibleMessageIds }`.
  `currentAnchorId` answers **"where am I"** — the current anchored turn, and it *stays set
  after that anchor scrolls above the viewport*. `visibleMessageIds` answers **"what's on
  screen"**, in document order.
- `useMessageScroller()` → `{ scrollToEnd, scrollToMessage, scrollToStart }` — imperative
  scroll; the outline wires `scrollToMessage(id, { align: "start", behavior: "smooth" })`.
- `useMessageScrollerScrollable()` → `{ start, end }` — whether more content exists in each
  direction (what `MessageScrollerButton` consumes internally).

**The Transcript Outline (verbatim from the demo, field-verified in-browser):** one anchor
per **user turn**, rendered as a `HoverCard` whose trigger is a column of tiny dashes (one
per turn) — the current turn's dash lights up via `data-current={turn.id === currentAnchorId}`.
Hover opens the list of turns (trimmed text, ~42 chars); clicking one calls
`scrollToMessage`. As you scroll (or after a jump), `currentAnchorId` moves and the lit dash
+ `aria-current="location"` row track it. Only render it with ≥2 turns.

```tsx
function TranscriptOutline({ turns }: { turns: { id: string; label: string }[] }) {
  const { scrollToMessage } = useMessageScroller()
  const { currentAnchorId } = useMessageScrollerVisibility()
  if (turns.length < 2) return null
  return (
    <div className="absolute top-1/2 right-2 z-10 -translate-y-1/2">
      <HoverCard>
        <HoverCardTrigger render={
          <button type="button" aria-label="Open transcript outline"
            className="flex w-4 flex-col items-center gap-1 rounded-md py-1 outline-none focus-visible:ring-2 focus-visible:ring-primary/50">
            {turns.map((t) => (
              <span key={t.id} data-current={t.id === currentAnchorId}
                className="h-0.5 w-4 rounded-full bg-muted-foreground/40 transition-colors data-[current=true]:bg-primary" />
            ))}
          </button>
        } />
        <HoverCardContent align="center" side="left" sideOffset={8} className="flex w-64 flex-col gap-0.5 p-1">
          {turns.map((t) => (
            <button key={t.id} type="button"
              aria-current={t.id === currentAnchorId ? "location" : undefined}
              onClick={() => scrollToMessage(t.id, { align: "start", behavior: "smooth" })}
              className="flex min-h-7 items-center rounded-lg px-2 py-1.5 text-left text-sm outline-none hover:bg-accent aria-[current=location]:bg-primary/15">
              <span className="line-clamp-1 min-w-0">{t.label}</span>
            </button>
          ))}
        </HoverCardContent>
      </HoverCard>
    </div>
  )
}
```

**Critical, field-verified:** `currentAnchorId` only changes if you mark each *turn* as an
anchor — the docs anchor the **user message** (`scrollAnchor={message.role === "user"}`), NOT
just the last item. If you anchor only the last row, `currentAnchorId` is stuck on it and the
lit dash never moves. So: `scrollAnchor={isUser}`, and build `turns` from the user messages.
Position the outline *inside* `MessageScroller` (its positioning context) on the right edge —
the demo hangs it outside the card (`-right-12`), but in a width-constrained chat panel that
clips, so pin it `absolute right-2` within the scroller instead.

So: `MessageScrollerButton` for jump-to-bottom (always), **plus** the Transcript Outline as
the visibility-driven position tracker. Both, not either.

**Field-verified gotcha — the scroller needs a BOUNDED-HEIGHT ancestor.** `MessageScroller`
scrolls internally only if every ancestor up to the viewport is height-constrained; if any
is `min-h-*` / auto-growing, the chat grows the whole page instead and the scroller "does
nothing" (no error, jump-to-bottom button never appears). The chain must be: an app-shell
region pinned to the viewport (`h-svh overflow-hidden` on the shadcn `SidebarInset`, header
`shrink-0`, content `min-h-0 flex-1`) → the chat page `flex h-full min-h-0 flex-col` → the
`MessageScroller` `min-h-0 flex-1`. The default shadcn `SidebarInset` is `min-h-svh` (grows)
— override it to `h-svh` for any route that hosts an internally-scrolling surface.

**Avatar gotcha.** `MessageAvatar` ships `self-end` — on a tall assistant message the avatar
floats at the *bottom* of the row, detached from its header. Override with `self-start` so it
sits at the top next to `MessageHeader`. Size it small (`size-7`) and style on-brand from the
DESIGN.md (a rounded-md square often reads better than the default circle in a dense theme).

Bubble variants map to your theme tokens (`secondary`, `muted`, `tinted`, `ghost`,
`outline`, `destructive`); `ghost` = borderless flowing text (ideal for assistant turns
paired with typeset). `align="start|end"` on both `Message` and `Bubble`.

### `@shadcn/helpers` — prototype the conversation in code (shadcn, July 2026)

For AI chat specifically, **`@shadcn/helpers`** ships **AI SDK** and **TanStack AI** helpers that let you write a conversation in code and run it through the `useChat` lifecycle **without a backend** — ideal for building and iterating the chat UI before the agent is wired. Pair it with the chat components above (the components render; the helpers drive the message flow). **Verified against `@shadcn/helpers@0.2.0` (2026-08-26)**: the package exports exactly two subpaths,
`@shadcn/helpers/ai-sdk` and `@shadcn/helpers/tanstack-ai`, and both expose the same entry point —
**`createChat(options)`** (`CreateChatOptions` → `AiSdkChat` / `TanStackChat`).

⚠️ **Read its peer ranges before adding it.** They are unusually tight:
`ai >=7.0.0 <8` is normal, but `@tanstack/ai >=0.40.0 <0.41.0` and
`@tanstack/ai-client >=0.20.0 <0.21.0` pin **a single minor each** — a pre-1.0 dependency that will
refuse to install against the next minor of the thing it wraps. Fine for a prototype you throw away,
a standing install-time hazard in a repo that lives. When the app is backed by an **eve** agent, keep eve as the single source of truth (see the two-brains note in `module-add/references/module-voice.md`) — use these helpers only for local prototyping, never as a second runtime.

### Ask-the-user HITL — a tool with **no `execute`**

The `chatbot-template` answers a question our other references leave open: how does a model *ask the
human something* mid-stream and get a typed answer back? Not with a special API — with an ordinary tool
that simply **has no `execute` function**:

```ts
// tools/ask_user.ts — inputSchema + outputSchema, and NO execute
export const askUser = tool({
  description: "Ask the user clarifying questions when their request is ambiguous. …",
  inputSchema: z.object({ questions: z.array(z.object({
    question: z.string(),
    choices: z.array(z.string()).length(3),      // exactly three, short and distinct
  })).min(1) }),
  outputSchema: z.array(z.object({ question: z.string(), answer: z.string() })),
})
```

With no `execute`, the call **parks on the client**. The UI reads the tool part's state, renders the
question, and the human's answer *becomes the tool output*:

```tsx
const { messages, addToolOutput } = useChat<ChatUIMessage>({
  sendAutomaticallyWhen: lastAssistantMessageIsCompleteWithToolCalls,   // resume once answered
})

// part.state === "input-available" → render; "output-available" → it's answered
<QuestionCard part={pendingQuestion} onAnswer={(toolCallId, answer) =>
  addToolOutput({ tool: "ask_user", toolCallId, output: answer })
} />
```

**And the surface it renders is the `<Questionnaire />`** the `forms` skill documents — same component,
used as a chat affordance rather than a page. That is the join between the two skills: `forms` owns the
component and its accessibility, this owns the wiring that turns it into a model-driven question.

**There are now three unrelated HITL mechanisms. Pick by runtime, don't mix them:**

| | The model wants | Answered with | Resumes on |
|---|---|---|---|
| **Ask** (this) | *information* — a tool with `outputSchema`, no `execute` | `addToolOutput({ tool, toolCallId, output })` | `lastAssistantMessageIsCompleteWithToolCalls` |
| **Approval** ([`@shadcn/helpers`](https://ui.shadcn.com/docs/helpers/ai-sdk#human-in-the-loop)) | *permission* — `needsApproval: true` on a tool | `addToolApprovalResponse({ id, approved })` | `lastAssistantMessageIsCompleteWithApprovalResponses` |
| **eve** (`eve-agent/references/ai-elements.md`) | either — `input.requested` / `authorization.required` | `respond(inputResponses)` | eve's durable session |

The first two are AI SDK and compose freely; **the third is not** — in an eve-backed app the approval
lives in eve's event stream, so `addToolOutput` and `addToolApprovalResponse` have nothing to answer.

### Two things the template does that a demo wouldn't

**The chat route is public and spends money.** Its own comment is the warning worth copying: *"This
endpoint is public and spends your AI Gateway credits on every request. Before exposing it to real
traffic, add a rate limit (Vercel Firewall / WAF or `@upstash/ratelimit`), authentication, and an AI
Gateway spend limit."* A chat route without those three is a funded denial-of-wallet.

**It validates before it trusts.** `validateUIMessages()` checks the shape of every message and tool
part arriving from the client, and `isModelAllowed()` rejects any model outside an explicit allowlist
with a 400 — otherwise the client picks the model, and picks the expensive one.

**On Vercel the Gateway needs no configuration at all**: deployments authenticate via **OIDC** and usage
runs on the team's AI Gateway credits. Locally you either `vercel env pull` an OIDC token or set
`AI_GATEWAY_API_KEY`. Nothing to wire, which is worth knowing before someone builds a key-management
story that Vercel already handles.

## 2. typeset (shadcn, July 2026) — for RENDERED markdown/HTML

`shadcn/typeset` is a **single CSS file that lives in your project** (no package, no
config layer). It styles rendered markdown/HTML consistently via three variables
(`--typeset-leading`, `--typeset-size`, `--typeset-flow`) and element rules
(`.typeset h1/strong/code/pre/ul/a…`). Add it to `globals.css` (or `packages/ui`'s
`globals.css`), **tuned to the project's DESIGN.md tokens** (link color, code surface,
mono font — don't ship the generic defaults). Create context variants as needed
(`.typeset-chat` tighter for bubbles, `.typeset-docs` roomier for a docs page).

Wrap rendered content: `<div className="typeset">{renderedHtml}</div>`.

**Canonical structure (field-verified — copy this into `globals.css`, then retune colors
to DESIGN.md).** Two non-obvious details that matter: use `:where(...)` so the rules have
**zero specificity** (Tailwind utilities always win), and apply **only `margin-block-start`**
(never `margin-block-end`) so streaming markdown doesn't reflow as blocks append. Opt out
with `.not-typeset`.

```css
.typeset {
  --typeset-font-body: inherit; --typeset-font-heading: var(--font-heading, inherit);
  --typeset-font-mono: var(--font-mono, ui-monospace, monospace);
  --typeset-size: 1em; --typeset-leading: 1.75; --typeset-flow: 1.25em;
  font-size: var(--typeset-size); line-height: var(--typeset-leading); font-family: var(--typeset-font-body);
}
.typeset :where(h1,h2,h3,h4,h5,h6):not(.not-typeset) { font-family: var(--typeset-font-heading); font-weight: 600; line-height: 1.25; margin-block-start: var(--typeset-flow); }
.typeset :where(p,ul,ol,blockquote,table,pre,hr):not(.not-typeset) { margin-block-start: var(--typeset-flow); }
.typeset :where(ul,ol):not(.not-typeset) { padding-inline-start: 1.5em; }
.typeset :where(ul):not(.not-typeset) { list-style: disc; }
.typeset :where(ol):not(.not-typeset) { list-style: decimal; }
.typeset :where(a):not(.not-typeset) { text-decoration: underline; text-underline-offset: 2px; }
.typeset :where(code):not(.not-typeset) { font-family: var(--typeset-font-mono); font-size: .875em; background: var(--muted); padding: .125em .375em; border-radius: var(--radius-sm); }
.typeset :where(pre):not(.not-typeset) { font-family: var(--typeset-font-mono); background: var(--muted); padding: 1em; border-radius: var(--radius-lg); overflow-x: auto; }
.typeset :where(pre code):not(.not-typeset) { background: transparent; padding: 0; }
.typeset :where(table):not(.not-typeset) { width: 100%; border-collapse: collapse; font-size: .9em; }
.typeset :where(th,td):not(.not-typeset) { border: 1px solid var(--border); padding: .5em .75em; text-align: start; }
.typeset :where(> *:first-child):not(.not-typeset) { margin-block-start: 0; }
.typeset-chat { --typeset-flow: 1em; --typeset-leading: 1.6; }
.typeset-docs { --typeset-size: 15px; --typeset-flow: 1.5em; }
```

### Sending attachments (the composer side)

The `attachment` family renders **inbound** files; to let the user **send** them, wire the
composer: a file `<input hidden>` behind a `Paperclip` button, pending files previewed as
`Attachment` chips (with `AttachmentAction` to remove), and on submit build the send payload.
Keep this in ONE shared `ChatComposer` that both/all chats use.

For AI-SDK / eve, `send({ message })` accepts `UserContent = string | Array<TextPart |
ImagePart | FilePart>`. Read each file with `FileReader.readAsDataURL` and send the file part
as **the full data URL string** in `data`:

```ts
{ type: "file", data: file_dataURL, mediaType: file.type, filename: file.name }
```

**Field-verified, both directions matter:** send the *full data URL* (`data:<mime>;base64,…`),
NOT the stripped raw base64 — with eve/AI-Gateway the raw-base64 form is silently NOT
forwarded to the model as an image (the model replies "no image"), while the data URL works
(the model sees it). Cap size (~8MB) and treat inline data URLs as the *groundwork* form —
fine for images and small files; for large/persistent files, upload to blob storage and send
the remote URL instead. `FilePart.data` also accepts a bare `URL` for that case.

Import the `UserContent` type from `ai` (add `ai` as a direct dep if the app doesn't have it;
it's usually already transitive via the agent SDK).

## 3. The catch — typeset needs a RENDERER

typeset styles **rendered** markdown. Feeding it a raw markdown string with
`whitespace-pre-wrap` leaves `**bold**` and `- lists` **literal** — the markdown leaks.
So pair typeset with a markdown renderer. The ecosystem standard for AI output is
**streamdown** (Vercel — a streaming-safe drop-in for react-markdown that survives
incomplete markdown mid-stream):

```bash
pnpm add streamdown
```

Wrap it once in a shared component so it's the single standard, and let typeset own the
typography:

```tsx
// components/shared/chat/agent-markdown.tsx
"use client"
import { Streamdown } from "streamdown"
import "streamdown/styles.css"

export function AgentMarkdown({ children, compact = false }: { children: string; compact?: boolean }) {
  return (
    <div className={compact ? "typeset typeset-chat" : "typeset"}>
      <Streamdown parseIncompleteMarkdown>{children}</Streamdown>
    </div>
  )
}
```

Use `AgentMarkdown` for EVERY agent/markdown surface (chat bubbles, a description panel,
notes). Never render agent markdown as `whitespace-pre-wrap` plain text — it's the #1
"looks unfinished" tell. `parseIncompleteMarkdown` is what makes streaming look clean.

## Anti-patterns (do not produce)

- ❌ Hand-rolled chat with `div` bubbles + `useRef` autoscroll when the chat primitives exist.
- ❌ `whitespace-pre-wrap` on model markdown output (bold/lists/code render as literal syntax).
- ❌ A spinner for "assistant is thinking" — use `<Marker>` with the `shimmer` utility.
- ❌ Copying the primitives into `apps/web/components/ui/` in a monorepo — they belong in
  the shared `packages/ui` (`@workspace/ui`), imported by every app.
- ❌ Re-styling typeset per-page with ad-hoc Tailwind — add a `.typeset-<context>` variant instead.
- ❌ Using only `MessageScroller` + `Bubble` and skipping `MessageAvatar` / `Attachment` /
  `Marker` — that's a partial anatomy. Use the whole kit where the data supports it.

## Prototyping a chat before a backend exists — `createChat`

`@shadcn/helpers` (npm, subpaths `./ai-sdk` + `./tanstack-ai`) exports **`createChat`** — a
builder for **scripted, fake** conversations:
`createChat().user("…").sleep(800).assistant(({ writer }) => { writer.reasoning("…"); writer.tool("getX",{…}).sleep(1200).output({…}); writer.text("…") })`.
Use it to drive a **demo/showcase** chat — a landing-page "watch the agent work" section,
Storybook, a test — through the SAME primitives above, with no tokens and no backend. It is
NOT a source of generic utilities (`cn`, hooks — see `shadcn-mapping.md`); it is the
demo-data counterpart to the chat components. In a real app the messages come from the
backend hook (`useChat`, `useEveAgent`, …), not `createChat`.

**You can script an approval, too** ([§Human in the loop](https://ui.shadcn.com/docs/helpers/ai-sdk#human-in-the-loop)) —
worth knowing, because a paused-for-approval turn is the hardest chat state to build without a
backend: you need a turn that stops mid-flight, a card, and a resume.

```tsx
chat.assistant(({ writer }) => {
  writer.text("That will archive 3 drafts. I need your approval.")
  writer.tool("archiveDrafts", { input: { count: 3 }, needsApproval: true, output: { archived: 3 } })
})
```

Client side it is plain AI SDK: `useChat` exposes `addToolApprovalResponse({ id: part.approval.id,
approved: true })`, and the turn resumes when `sendAutomaticallyWhen` includes
`lastAssistantMessageIsCompleteWithApprovalResponses` (from `ai`). The continuation streams as a
**new step of the same paused assistant message**, so the UI keeps one message and grows it —
build the renderer for that shape, not for a second bubble.

⚠️ **This prototypes the approval, it does not port to eve.** On an eve-backed app the approval is an
`input.requested` / `authorization.required` event on eve's stream, answered with `respond(…)` — see
`eve-agent/references/ai-elements.md`. Same UI, different plumbing: keep the components, swap the
wiring when the agent lands. Don't leave `addToolApprovalResponse` in an eve app, where it has nothing
to answer and the tool silently never resumes.
