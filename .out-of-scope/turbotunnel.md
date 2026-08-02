# TurboTunnel

**Decision**: not adopting — no skill, no reference
**Date**: 2026-07-31

## What it is
[TurboTunnel](https://turbotunnel.dev) — tunnelling local services to a public URL.

## Why it was evaluated
It came up while working on webhook-driven surfaces: eve channels (Slack, Telegram, GitHub) deliver over the public internet and can't reach `localhost`, so a tunnel looks like the missing piece of the local dev loop.

## Why not
It doesn't touch anything the skills own. The suite's guidance for that exact problem is already concrete and doesn't need a tunnel: **deploy first, then smoke-test the deployed agent with `eve dev <url>`** (`eve-agent/references/eve-capabilities.md`). A tunnel would add a third-party dependency to a workflow that already has an answer.

Generic developer tooling that no skill scaffolds, configures or reasons about doesn't belong in the suite — that's a personal-environment choice, not project guidance.

## What would change our mind
A skill needing to *configure* tunnelling as part of a project's setup (e.g. a local webhook-testing story we scaffold), rather than a developer choosing a tunnel for themselves.
