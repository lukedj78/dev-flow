# Chat interfaces & rendered markdown — the shadcn standard

When a Next.js + shadcn project needs **any conversational surface** (an AI chat, a
support inbox, a comment thread, an agent console) or needs to **render markdown/rich
text** (AI output, documentation, a description field), do NOT hand-roll it with
`div`/`ul` + manual autoscroll + `whitespace-pre-wrap`. Compose the official shadcn
primitives. This is a **standard**, not a suggestion.

Verify names/versions against the changelog (<https://ui.shadcn.com/docs/changelog>) and
the installed registry — the surface is young and grows.

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
pattern — don't reinvent it as a "new messages" pill (that's not what the primitive models):

- `useMessageScrollerVisibility()` → `{ currentAnchorId, visibleMessageIds }`.
  `currentAnchorId` answers **"where am I"** — the current anchored turn, and it *stays set
  after that anchor scrolls above the viewport*. `visibleMessageIds` answers **"what's on
  screen"**, in document order. Canonical use (per the docs): a **table-of-contents / jump
  menu that highlights the current anchored turn**, or a lightweight "you're reading an
  earlier message" hint shown only when `currentAnchorId !== <the LAST turn's anchor id>`.
  **Critical, field-verified:** `currentAnchorId` only changes if you mark each *turn* as an
  anchor — the docs anchor the **user message** (`scrollAnchor={message.role === "user"}`),
  NOT just the last item. If you anchor only the last row, `currentAnchorId` is stuck on it
  and the hint never fires. So: `scrollAnchor={isUser}`, and compare `currentAnchorId` to the
  *last user message's id* (the last turn), not to the last message overall.
- `useMessageScroller()` → `{ scrollToEnd, scrollToMessage, scrollToStart }` — imperative
  scroll; e.g. wire `scrollToEnd({ behavior: "smooth" })` to that hint's click.
- `useMessageScrollerScrollable()` → `{ start, end }` — whether more content exists in each
  direction (what `MessageScrollerButton` consumes internally).

So: `MessageScrollerButton` for jump-to-bottom (always), **plus** a visibility-driven
position indicator when you want the reader to know they've scrolled into history.

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
