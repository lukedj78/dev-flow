# Vercel AI Elements as the eve chat UI

**Decision**: documented as an **option**, not the default
**Date**: 2026-08-02

## What it is
[AI Elements](https://elements.ai-sdk.dev) — Vercel's prebuilt component kit for AI chat surfaces (conversation, prompt input, reasoning, tool calls, sources), installed through the shadcn CLI.

## Why it was tempting
It is purpose-built for exactly what `eve-agent` needs a UI for, it's official, and it ships pieces (reasoning blocks, tool-call rendering) we'd otherwise hand-roll. It showed up in the `trycompai/crm` reference monorepo.

## Why not the default
The house best practice for a chat surface is the **shadcn chat components + `shadcn/typeset`**: they inherit the project's DESIGN.md tokens, so the agent surface looks like the rest of the app instead of like a different product. A second component vocabulary in the same app is a consistency cost paid on every screen.

There's also a concrete integration gap: AI Elements is shaped around the AI SDK's `useChat`, while eve exposes `useEveAgent()` (`data.messages` / `status` / `send`). They are not drop-in compatible — the binding has to be written either way.

## Adopted in reduced form
`eve-agent/references/ai-elements.md` documents the verified install and the `useChat` → `useEveAgent()` binding table, so choosing it is a decision, not an improvisation. Reach for it when the user explicitly wants that kit.

## What would change our mind
- AI Elements shipping shadcn-token theming deep enough that it stops looking foreign in a DESIGN.md-styled app.
- eve exposing a `useChat`-compatible adapter, which would remove the binding cost.
