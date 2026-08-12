# AI Elements — the opt-in chat kit, bound to `useEveAgent()`

> **This is an OPTION, not the default.** The repo's best practice for an eve chat UI stays the
> **official shadcn chat components + `shadcn/typeset`** (`design-md-to-app/references/chat-and-typeset.md`)
> — they inherit the project's DESIGN.md tokens and stay consistent with the rest of the app. Reach for
> AI Elements **only when the user explicitly asks for that kit**. This file is the how-to for that case.

[AI Elements](https://elements.ai-sdk.dev/) is Vercel's prebuilt component kit for AI surfaces, built
**on top of shadcn/ui** (same theming conventions, components copied into your repo — not a runtime
dependency). Doc-grounded against <https://elements.ai-sdk.dev/overview> and `/setup`; `[VERIFY]`
component names against the version you install — this surface moves fast (e.g. the standalone
`Response` component is now documented as `MessageResponse`, exported from `message`).

## Install

Prerequisites per the setup page: **Node 18+, React 19, Next.js 14+ (App Router), Tailwind CSS 4,
shadcn/ui initialized** (the CLI will initialize shadcn for you if it's missing).

```bash
# dedicated CLI
npx ai-elements@latest add message
# or via the shadcn CLI + the @ai-elements registry namespace
npx shadcn@latest add @ai-elements/message
```

`pnpm dlx` / `yarn dlx` / `bun x` variants are documented too. Components land in
**`@/components/ai-elements/`**. In a monorepo, install them into the shared `packages/ui`
(`@workspace/ui`) and import from `apps/web`, same as every other shadcn primitive.

The setup page also recommends Vercel **AI Gateway** (`AI_GATEWAY_API_KEY`) for model access — that
is a recommendation **for AI-SDK-backed apps and is irrelevant here**: your model calls happen inside
the eve agent, not in the Next.js route. Skip it.

## What it ships (verified categories, `overview`)

- **Chatbot** — Attachments, Chain of Thought, Checkpoint, Confirmation, Context, Conversation,
  Inline Citation, Message, Model Selector, Plan, Prompt Input, Queue, Reasoning, Shimmer, Sources,
  Suggestion, Task, Tool
- **Code** — Agent, Artifact, Code Block, Commit, Environment Variables, File Tree, JSX Preview,
  Package Info, Sandbox, Schema Display, Snippet, Stack Trace, Terminal, Test Results, Web Preview
- **Voice** — Audio Player, Mic Selector, Persona, Speech Input, Transcription, Voice Selector
- **Workflow** — Canvas, Connection, Controls, Edge, Node, Panel, Toolbar
- **Utilities** — Image, Open In Chat

A minimal eve chat needs four: `Conversation`, `Message`, `PromptInput`, and (if the agent streams
them) `Reasoning` / `Tool` / `Sources`.

## The binding problem

AI Elements' examples are written against the AI SDK's `useChat()`. **eve does not expose that hook** —
`useEveAgent()` from `eve/react` has its own shape (see `eve-web-integration.md`). There is no adapter
package; you write the ~15-line mapping yourself.

| AI SDK `useChat()` | eve `useEveAgent()` | Note |
|---|---|---|
| `messages` | `agent.data.messages` | eve's default reducer projects `{ messages }`; a custom `reducer` changes this |
| `status` | `agent.status` | both are `"ready" \| "submitted" \| "streaming" \| "error"` — passes straight into `PromptInputSubmit`. `[VERIFY]` against the installed AI Elements `ChatStatus` type |
| `sendMessage({ text })` | `agent.send(text)` | eve takes text **or** a full turn payload |
| `stop()` | `agent.stop()` | 1:1 |
| `error` | `agent.error` | 1:1 |
| `regenerate()` | *(none)* | re-`send` the previous user text yourself |
| `setMessages([])` | `agent.reset()` | also clears events + the local session cursor |
| — | `agent.session` / `agent.events` | eve-only: the resumability cursor + raw log |

Message items: eve's `EveMessage` follows the **AI SDK `UIMessage` convention** (`role` + `parts`), so
`<Message from={message.role}>` and a `switch` over `message.parts` line up. `[VERIFY]` the exact part
`type` strings against the installed eve version before assuming `"text"` / `"reasoning"` / `"tool-*"`.

## The adapter

```tsx
"use client";
import { useEveAgent } from "eve/react";
import { Conversation, ConversationContent, ConversationScrollButton } from "@/components/ai-elements/conversation";
import { Message, MessageContent, MessageResponse } from "@/components/ai-elements/message";
import { PromptInput, PromptInputBody, PromptInputTextarea, PromptInputSubmit,
         type PromptInputMessage } from "@/components/ai-elements/prompt-input";

export function EveChat() {
  const agent = useEveAgent();
  const messages = agent.data?.messages ?? [];

  function handleSubmit(message: PromptInputMessage) {
    if (agent.status !== "ready") return;          // one turn at a time — eve has no inbound queue
    const text = message.text?.trim();
    if (text) agent.send(text);
  }

  return (
    <>
      <Conversation>
        <ConversationContent>
          {messages.map((m) => (
            <Message key={m.id} from={m.role}>
              <MessageContent>
                {m.parts.map((part, i) =>
                  part.type === "text" ? <MessageResponse key={i}>{part.text}</MessageResponse> : null
                )}
              </MessageContent>
            </Message>
          ))}
        </ConversationContent>
        <ConversationScrollButton />
      </Conversation>

      <PromptInput onSubmit={handleSubmit}>
        <PromptInputBody><PromptInputTextarea /></PromptInputBody>
        <PromptInputSubmit status={agent.status} />
      </PromptInput>
    </>
  );
}
```

`PromptInput`'s `onSubmit` is `(message: PromptInputMessage, event: FormEvent) => void` and carries
**text + file attachments**; eve's `send` takes text or a turn payload, so if you enable attachments you
must map `message.files` into the turn payload yourself — there is no automatic path.

## Non-obvious gotchas

- **Gate on `status === "ready"`.** eve rejects a second `send` while a turn is live (since 0.31.0
  that surfaces as HTTP **409** / `code: "session_not_active"`, not a stale-token error). `PromptInputSubmit` renders a stop affordance from `status` but does **not**
  block the submit — do it in your handler, as above, and wire the stop button to `agent.stop()`.
- **HITL breaks the kit's assumptions, and there are now TWO unrelated HITL mechanisms — don't cross them.**
  eve's `input.requested` / `authorization.required` events have **no `useChat` analogue**. Render them
  from `agent.events` (AI Elements' `Confirmation` component is the natural surface) and answer via
  `respond(inputResponses, …)` keyed by `requestId` — not through `PromptInput`.

  Meanwhile **AI SDK has its own approval flow**, documented in
  [`@shadcn/helpers` §Human in the loop](https://ui.shadcn.com/docs/helpers/ai-sdk#human-in-the-loop):
  a tool declares `needsApproval: true`, the client answers with
  `addToolApprovalResponse({ id: part.approval.id, approved: true })`, and `useChat` resumes on
  `sendAutomaticallyWhen: lastAssistantMessageIsCompleteWithApprovalResponses` — "the continuation
  streams as a new step of the paused assistant message".

  **That path is for chats whose transport is the AI SDK, not eve sessions.** In an eve-backed app the
  approval lives in eve's event stream and its durable session, so `addToolApprovalResponse` has nothing
  to answer and the tool never resumes. Reach for the shadcn helper when you are prototyping a chat
  **without** a backend (which is what it is for — `createChat()` scripts a conversation in code and runs
  it through the `useChat` lifecycle); reach for `agent.events` + `respond()` the moment eve is the
  runtime. Mixing them produces a UI that renders an approval card nobody is listening to.
- **The widget protocol may not survive.** `MessageResponse` is built on Streamdown and forwards
  `components` / `remarkPlugins` / `rehypePlugins`, but its documented prop list does **not** include
  streamdown's `plugins` — which is what the widget protocol uses for custom fence renderers
  (`plugins.renderers`, see `eve-web-integration.md`). `[VERIFY]` against the installed version; if it's
  absent, render assistant text with your own `<Markdown plugins={{ renderers }}>` **inside**
  `<MessageContent>` and skip `MessageResponse`.
- **Streamdown styles are a separate step.** `MessageResponse` requires the Streamdown styles in
  `globals.css`; that overlaps with `shadcn/typeset` — don't stack both on the same subtree.
- **Resumability is still yours.** Persisting `agent.events` + `agent.session` and rehydrating via
  `initialEvents` / `initialSession` is unchanged by the choice of UI kit.
- **You still own auth.** `useEveAgent({ headers })` + a real authenticator in `agent/channels/eve.ts`
  — AI Elements changes nothing here, and `placeholderAuth()` still fails closed in production.

## When to say no

If the user has a DESIGN.md and cares about visual consistency, the shadcn chat components win: AI
Elements brings its own opinions (and a large surface of components you won't use) and drifts from the
project's tokens. Use it when the ask is explicitly "the Vercel AI chat kit", when you need one of its
non-chat surfaces (Workflow canvas, Code/Sandbox blocks) that has no equivalent in the repo, or for a
throwaway demo where speed beats fit.
