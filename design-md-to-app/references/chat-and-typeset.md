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

The registry items: `message-scroller`, `message`, `bubble`, `attachment`, `marker`,
plus two CSS utilities that ship with `shadcn/tailwind.css` in new projects —
`scroll-fade` (edge fades) and `shimmer` (text shimmer). Composition:

```tsx
<MessageScrollerProvider>
  <MessageScroller className="min-h-0 flex-1">
    <MessageScrollerViewport>
      <MessageScrollerContent>
        {messages.map((m, i) => (
          <MessageScrollerItem key={m.id} scrollAnchor={i === messages.length - 1}>
            <Message align={m.role === "user" ? "end" : "start"}>
              <MessageContent>
                <MessageHeader>{m.role === "user" ? "You" : "Assistant"}</MessageHeader>
                <Bubble variant={m.role === "user" ? "secondary" : "ghost"} align={...}>
                  <BubbleContent>
                    {m.role === "user"
                      ? <span className="whitespace-pre-wrap">{text}</span>
                      : <AgentMarkdown compact>{text}</AgentMarkdown>}
                  </BubbleContent>
                </Bubble>
              </MessageContent>
            </Message>
          </MessageScrollerItem>
        ))}
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
