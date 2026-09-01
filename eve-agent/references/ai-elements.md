# AI Elements — the opt-in chat kit, bound to `useEveAgent()`

> **This is an OPTION, not the default.** The repo's best practice for an eve chat UI stays the
> **official shadcn chat components + `shadcn/typeset`** (`design-md-to-app/references/chat-and-typeset.md`)
> — they inherit the project's DESIGN.md tokens and stay consistent with the rest of the app. Reach for
> AI Elements **only when the user explicitly asks for that kit**. This file is the how-to for that case.

[AI Elements](https://elements.ai-sdk.dev/) is Vercel's prebuilt component kit for AI surfaces, built
**on top of shadcn/ui** (same theming conventions, components copied into your repo — not a runtime
dependency). Doc-grounded against <https://elements.ai-sdk.dev/overview> and
<https://elements.ai-sdk.dev/docs/setup> (⚠️ the setup page moved: the bare `/setup` this file used to
cite now **404s**). Components are **copied into your repo** by the registry, so there is no package to
pin or diff — `[VERIFY]` component names against the version you actually `add`, because this surface
moves fast (e.g. the standalone `Response` component is now documented as `MessageResponse`, exported
from `message`). The *types* they consume, by contrast, come from the `ai` package and can be checked:
this file is verified against **`ai@7.0.87`** and **`eve@0.47.6`** (2026-09-01, `npm pack` on both).

⚠️ **These two versions now drift independently** — eve stopped declaring `ai` as a dependency, so
neither one pins the other. Re-pack **both** before trusting a part-by-part row; a pass on one of them
proves nothing about the mapping.

## Install

Prerequisites, re-read from the setup page at 2026-09-01 and unchanged: **Node 18+, React 19, Next.js 14+ (App Router), Tailwind CSS 4,
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
| `status` | `agent.status` | ⚠️ **they no longer match**: eve added a fifth value, `"resuming"` (0.45.0), to the AI SDK's `"ready" \| "submitted" \| "streaming" \| "error"`. It is *not* an active turn — a hydrated session catching up. Map it to `"ready"` (or your own quiet state) before handing `status` to `PromptInputSubmit`; passing it straight through is now a type error waiting to happen. **Confirmed again at `ai@7.0.87`: `ChatStatus = "submitted" | "streaming" | "ready" | "error"` — still four values, and `"resuming"` is still not one of them, so the mismatch is stable rather than transitional.** |
| `sendMessage({ text })` | `agent.send(text)` | eve takes text **or** a full turn payload |
| `stop()` | `agent.cancel()` | eve renamed `stop()` → `cancel()` on frontend agent bindings in **0.38.0**; not 1:1 in name, same role |
| `error` | `agent.error` | 1:1 |
| `regenerate()` | *(none)* | re-`send` the previous user text yourself |
| `setMessages([])` | `agent.reset()` | also clears events + the local session cursor |
| — | `agent.session` / `agent.events` | eve-only: the resumability cursor + raw log |

Message items: eve's `EveMessage` follows the **AI SDK `UIMessage` convention** (`role` + `parts`), so
`<Message from={message.role}>` and a `switch` over `message.parts` line up — **but the part unions are
not the same one**, and a `switch` copied from an AI SDK example will silently miss cases.

Verified against `eve@0.45.0` (`EveMessagePart`) and `ai@7.0.79` (`UIMessagePart`):

| | eve | AI SDK |
|---|---|---|
| Shared | `"text"` · `"reasoning"` · `"file"` · `"step-start"` | same |
| Tool calls | **`"dynamic-tool"`** only | `"dynamic-tool"` **and** `` `tool-${name}` `` |
| eve-only | **`"authorization"`** — a connection asking the user to sign in mid-turn | — |
| AI-SDK-only | — | `"source-url"` · `"source-document"` · `` `data-${name}` `` · **`"custom"`** · **`"reasoning-file"`** |

Two fixes this pass. The AI-SDK-only row said `"custom-content"`: that is the *type name*
(`CustomContentUIPart`), but the **discriminant is `"custom"`** — a `switch` written from the old row
would never match. And `ai@7.0.87` added **`"reasoning-file"`** (`ReasoningFileUIPart`, a `mediaType` +
`url` pair), which eve does not emit.

Two things follow. **Don't switch on `` `tool-${name}` ``** — eve never emits it, so per-tool rendering
keys off the `dynamic-tool` part's own name field. And **handle `"authorization"` explicitly**: it has
no AI SDK counterpart, so a default branch will drop it — and the case it drops is the one where the
user is being asked to authorize something and nothing appears on screen.

**Narrow on `state` before reading anything else.** Both eve-side parts are discriminated twice: once
by `type`, then by `state`, and which fields exist depends on the second.

| Part | `state` values | What it means for the render |
|---|---|---|
| `"dynamic-tool"` | `"input-streaming"` · `"input-available"` · `"approval-requested"` · `"approval-responded"` · `"output-available"` · `"output-error"` · `"output-denied"` | `input`, `output`, `errorText` and `approval` are each present only in some states. `"input-streaming"` carries **possibly incomplete JSON** (see `eve-web-integration.md` §Stream protocol v24) — don't parse it as arguments. `"output-denied"` means `approval.approved === false`, and `"output-error"` puts the message in `errorText`. |
| `"authorization"` | `"required"` · `"completed"` | `"required"` carries the challenge (`url`, `userCode`, `instructions`, `expiresAt`) — render the sign-in affordance from it. `"completed"` carries `outcome` and an optional `reason`, and the two shapes are mutually exclusive in the type: reading `outcome` on a `"required"` part does not typecheck. |

Reading a field without narrowing is the failure mode this table exists to prevent — it typechecks
against the union in some editors and is `undefined` at runtime in the state you actually got.

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

- **Gate on `status === "ready"`.** Don't rely on the server to reject an overlapping `send` — since
  **0.33.0** the eve channel defaults to `turnPolicy: "steer"`, so a `send` while a turn is live is
  accepted and **cancels + replaces** the active turn rather than erroring (409/`session_not_active`
  is for a `send`/`respond` on an *inactive* session — unknown or terminal ID — a different case).
  `PromptInputSubmit` renders a stop affordance from `status` but does **not** block the submit — do
  it in your handler, as above, and wire the stop button to `agent.cancel()` (renamed from `stop()`
  in eve 0.38.0).
- **HITL breaks the kit's assumptions, and there are now TWO unrelated HITL mechanisms — don't cross them.**
  eve's `input.requested` / `authorization.required` events have **no `useChat` analogue**. Render them
  from `agent.events` (AI Elements' `Confirmation` component is the natural surface) and answer via
  `respond(inputResponses, …)` keyed by `requestId` — not through `PromptInput`.

  Meanwhile **AI SDK has its own approval flow**, documented in
  [`@shadcn/helpers` §Human in the loop](https://ui.shadcn.com/docs/helpers/ai-sdk#human-in-the-loop):
  a tool declares `needsApproval: true`, the client answers with
  `addToolApprovalResponse({ id: part.approval.id, approved: true })` (the full signature also takes `reason` and `options`, confirmed at `ai@7.0.87`), and `useChat` resumes on
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
