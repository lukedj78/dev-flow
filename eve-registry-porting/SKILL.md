---
name: eve-registry-porting
description: >-
  Port a tool, connection or skill from a public eve/Flue agent registry — atomeve.dev,
  evex.sh, agentcn, eveagents.dev, the "shadcn for agents" registries — into a multi-tenant
  eve app WITHOUT adopting the registry's standalone-agent runtime model. Its core is the
  conformance checklist that makes third-party eve code tenant-safe. Use when the user wants
  to "install / use / borrow an agent from atomeve (or evex / agentcn / eveagents)", "add a
  Stripe/PostHog/Sentry/GitHub tool or connection from a registry", "reuse a skill from a
  shadcn-for-agents registry", or asks whether a registry agent is usable and how to adapt it.
  Not for: scaffolding a fresh tool/connection/skill slot (use `eve-agent`), building the
  Next.js app or its pages (use design-md-to-app / screenshot-to-page / module-add), or wiring
  the monorepo (monorepo-bootstrap).
---

# eve-registry-porting — borrow the bricks, not the agent

The eve ecosystem has spawned **"shadcn for agents"** registries — you copy
source, not a dependency. They are a great **catalog + code mine**. But their
unit of distribution is a **standalone agent** (one eve project that runs itself
on a cron or from Slack), which is the **opposite** of a multi-tenant app where
**one interpreter wears profiles from a DB** and delegates in a hierarchy.

So the rule is: **port the components (tool / connection / skill), never the
agent-as-a-runtime**, and rewrite each one to be tenant-safe.

## Where porting sits — the sourcing priority

Porting is **third choice**, not first. Before vendoring third-party source, prefer a maintained option higher up the list:

1. **eve's official integrations** — discover + install from the CLI: **`eve registry search <cap>`** → **`eve add <kind>/<name>`** (catalog at <https://eve.dev/integrations> — 50+ MCP/OpenAPI connections, 11+ channels, official extensions). If the service is there, install and stop — don't port. (`eve-agent` → §Install from the registry FIRST / Connection / Channel.)
2. **Install a third-party registry as a source** — the community registries below are **shadcn-registry format**, so you can register one as an eve source (**`eve registry add @name=https://…/r/{name}.json`**, stored in `package.json#registries`) and pull with **`eve add @name/<slug>`**. That's an *install* (files written, dep tracked) — prefer it over porting whenever you **don't** need to own/modify the source. **The mechanism is verified** against `eve@0.45.0`'s own docs: *"eve stores the mapping in
`package.json#registries`. The `{name}` placeholder becomes the integration name, so `@acme/analytics`
resolves to `https://registry.acme.com/r/analytics.json`."* Narrow a query to one source with
`eve registry list --registry @acme` / `eve registry search <q> --registry @acme`.

**`[VERIFY]` each registry actually serves the shadcn JSON shape** — one `curl` and look at `$schema`;
it must be `https://ui.shadcn.com/schema/registry-item.json`. The four this skill set names were all
checked on **2026-08-26** and all four pass:

| Registry | Item URL pattern | `$schema` |
|---|---|---|
| mapcn (web maps) | `https://mapcn.dev/r/{name}.json` | ✓ shadcn registry-item |
| mapcn-rn (mobile maps) | `https://mapcn-rn.dev/maps/{name}.json` | ✓ shadcn registry-item |
| Coss/UI | `https://coss.com/ui/r/{name}.json` | ✓ shadcn registry-item |
| heroicons-animated | `https://www.heroicons-animated.com/r/{name}.json` | ✓ shadcn registry-item |
| hugeicons-animated | `https://hugeicons-animated.com/r/{name}.json` | ✓ shadcn registry-item — note it also serves a `registry:lib` file (`lib/use-icon-animation.ts`), so an item is not always one file |

⚠️ **Serving the shape is necessary, not sufficient.** `mapcn-rn` serves shadcn-format items *and*
ships its own `mapcn-rn` CLI with a `mapcn.json` of its own — install it the project's way, not through
`eve add`, or you get files without the config that tracks them. Check whether a registry has a first-party
installer before treating it as a plain source.
3. **An extension package** — a versioned npm bundle you install and `pnpm up` (`agent/extensions/<name>.ts`). (`eve-agent` → Extension.)
4. **Port / vendor from a public registry** — *this skill*. Use it when the source **isn't** installable as above (not registry-served) **or** you need to own/modify it. You take on tenant-hardening **and** maintenance by hand.
5. **Hand-write** from scratch — when nothing exists to borrow (`eve-agent` boilerplate).

Go down a rung only when the one above has nothing. Porting trades "no dependency, full control" for "you tenant-harden and maintain it forever" — worth it for the code mine or a source you must modify, not as a default now that `eve registry add` + `eve add` can install directly from shadcn-format registries.

## The registries

| Registry | URL | Install | Registry endpoint (checked 2026-08-26) |
|---|---|---|---|
| Atom Eve | https://www.atomeve.dev | `npx atom-eve create my-agent --agent <slug>` · `npx atom-eve add <slug>` | **no `/r/registry.json`** — own CLI only |
| **evex** | https://www.evex.sh | `npx shadcn add @evex/<slug>` | **`/r/registry.json`, 13 items, `$schema: ui.shadcn.com/schema/registry.json`** — items at `/r/{name}.json`, `type: registry:item` |
| agentcn | https://agentcn.vercel.app | `npx shadcn add <url>` | `/r/registry.json`, 76 items — but **no `$schema` declared**, and item names are namespaced (`eve/claw` → `/r/eve/claw.json`, *not* `/r/claw.json`) |
| eveagents | https://www.eveagents.dev | `npx @bergside/eveagents install <slug>` | not reachable at check time (HTTP 429) — own CLI anyway |

**Only evex declares the shadcn registry schema**, which makes it the one that slots cleanly into
`eve registry add @evex=https://www.evex.sh/r/{name}.json`. agentcn serves registry-shaped JSON without
declaring the schema *and* nests item names, so the `{name}` placeholder does not expand the way the
table above would suggest — install it by URL. The other two ship their own installers, which is a
decision they made, not an oversight to route around.

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
