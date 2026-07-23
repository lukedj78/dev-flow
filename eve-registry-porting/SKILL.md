---
name: eve-registry-porting
description: >-
  Port a component (tool, connection, or skill) from a public eve/Flue agent
  registry — atomeve.dev, evex.sh, agentcn, eveagents.dev, the "shadcn for
  agents" registries — into a multi-tenant eve app WITHOUT adopting the
  registry's standalone-agent runtime model. Use when the user wants to
  "install / use / borrow an agent from atomeve (or evex / agentcn /
  eveagents)", "add a Stripe/PostHog/Sentry/GitHub tool or connection from a
  registry", "reuse a skill from a shadcn-for-agents registry", or asks whether
  a registry agent is usable and how to adapt it. The skill's core is the
  conformance checklist that makes third-party eve code safe in a multi-tenant
  app: tenant from the verified session (never model input), companyId in every
  query, per-tenant encrypted secrets (never global env keys), verified npm
  deps only, sensitive actions behind tool-grants/approval. For AgentOS
  specifically it defers to docs/eve-registries.md. Not for: scaffolding a fresh
  tool/connection/skill slot from scratch (use `eve-agent` for the boilerplate),
  building the Next.js app or its pages (use design-md-to-app /
  screenshot-to-page / module-add), or wiring the monorepo (monorepo-bootstrap).
  This skill governs "what to port from a registry and how to make it
  tenant-safe", not "how to write an eve primitive".
---

# eve-registry-porting — borrow the bricks, not the agent

The eve ecosystem has spawned **"shadcn for agents"** registries — you copy
source, not a dependency. They are a great **catalog + code mine**. But their
unit of distribution is a **standalone agent** (one eve project that runs itself
on a cron or from Slack), which is the **opposite** of a multi-tenant app where
**one interpreter wears profiles from a DB** and delegates in a hierarchy.

So the rule is: **port the components (tool / connection / skill), never the
agent-as-a-runtime**, and rewrite each one to be tenant-safe.

## The registries

| Registry | URL | Install (per registry — verify) |
|---|---|---|
| Atom Eve | https://www.atomeve.dev | `npx atom-eve create my-agent --agent <slug>` · `npx atom-eve add <slug>` |
| evex | https://www.evex.sh | `npx shadcn add @evex/<slug>` |
| agentcn | https://agentcn.vercel.app | `npx shadcn add <url>` |
| eveagents | https://www.eveagents.dev | `npx @bergside/eveagents install <slug>` |

All community projects, not official Vercel. Framework source of truth:
https://github.com/vercel/eve.

## When this skill applies

- The user names a registry (atomeve / evex / agentcn / eveagents) or "shadcn
  for agents" and wants to use something from it.
- The user wants a capability (Stripe metrics, PostHog, Sentry triage, GitHub
  PRs, website QA) and a registry has an eve implementation to borrow.
- The user asks "can we install this agent / is it useful / how do we adapt it".

If instead the user wants to **author a new** tool/connection/skill from scratch
(no registry involved), use **`eve-agent`**. If they want to run the registry's
`npx … create` to spin up a **brand-new standalone agent project** (not a
multi-tenant app), that's the registry's own flow — this skill is for pulling
pieces INTO an existing multi-tenant eve app.

## Decision: is it portable?

```
Component in the registry
├─ a full standalone agent / schedule / Slack channel  → DO NOT adopt as runtime.
│                                                         Extract its bricks ↓
├─ a tool (defineTool)                → PORT (rewrite tenant-safe)
├─ a connection (OpenAPI / MCP)       → PORT (auth from tenant)
├─ a skill (defineSkill markdown)     → PORT (near drop-in)
└─ instructions / persona             → adapt into profile config (DB seed)
```

## Conformance checklist (the whole point)

Every ported component MUST pass these before merge. In a multi-tenant eve app
this is non-negotiable — registry code assumes single-tenant/global env.

- [ ] **Tenant from the verified session, never from model input.** Derive the
      tenant id from the session principal (in AgentOS:
      `sessionIdentity(ctx.session.auth)` → `companyId`), never from a Zod input
      field.
- [ ] **Tenant id in EVERY query** — no DB read/write without the tenant filter.
- [ ] **Per-tenant, encrypted secrets.** No global `process.env.<KEY>` for
      credentials: fetch the key from the tenant's connection, decrypted at
      runtime (AgentOS: `getConnectionSecret(companyId, provider)`), encrypted at
      rest (AES-256-GCM). Not connected → fail honest (e.g. 401), never fall back
      to a shared key.
- [ ] **No unverified npm deps.** Prefer plain `fetch` over adding a package;
      verify anything a component pulls in before installing. Never `pnpm add`
      unverified packages, especially not inside a subagent.
- [ ] **Sensitive actions gated.** A tool that acts in the world (email, shell,
      spend, open-PR) goes into the gated set + per-role grants + human approval
      where appropriate. For the concrete syntax/pattern — `approval: always()` /
      `once()` from `eve/tools/approval`, custom input-dependent policies, and why
      gating a side effect on approval is also what makes it replay-safe under
      eve's durable-workflow re-run semantics — see
      `eve-agent/references/eve-conventions.md` → "Durability & idempotency (the
      rule scaffolds get wrong)". Apply that pattern directly; don't reopen
      `eve-agent` to rediscover it.
- [ ] **Framework hygiene.** Correct import paths (in a monorepo: `drizzle-orm`
      directly only in the agent, never in the web app); valid eve file names
      (tool files start with a letter).
- [ ] **License** of the individual component checked (registries are community,
      quality/licence vary per agent).
- [ ] **Verify via eve logs**, not just typecheck — read `eve dev` error logs
      after any agent change; eve has discovery/bundle rules `tsc` won't catch.

## Porting procedure

1. **Read the registry component's `SETUP`/source**: env, endpoints, deps.
2. **Classify** it (tool / connection / skill; if "whole agent", extract bricks).
3. **Rewrite into the target slot** applying the checklist — tenant from session,
   secrets per-tenant, queries filtered, no new unverified deps.
4. **Register a connection provider** if needed (connect/disconnect + encryption),
   and add it to the app's connections catalog.
5. **Gate sensitive tools** (tool-catalog + governance + approval).
6. **Add/extend tests** — tenant isolation + component logic.
7. **Verify**: eve error logs clean → typecheck → commit.

For the slot boilerplate itself (how a `defineTool`/`defineOpenAPIConnection`/
`defineSkill` is written and discovered), hand off to **`eve-agent`**.

## Project-specific reference

When working inside **AgentOS**, the concrete mapping (slots, provider
registration files, governance files, worked examples) lives in
`docs/eve-registries.md` in that repo — read it first; this skill is the
portable, project-agnostic version of the same discipline.
