> Sources: docs/superpowers/specs/2026-05-29-monorepo-set-design.md (canonical spec)

# Stack: monorepo

Identifier in `meta.json#stack.framework`: **`"monorepo"`**

## What it means

A single repo containing BOTH a Next.js web app AND an Expo + RN mobile app, plus shared `packages/` (types, design tokens, backend client). Built on **pnpm workspaces + turborepo**. One `.workflow/` at root, one PRD, one DESIGN.md — shared by both apps.

## Stack object shape

When `stack.framework="monorepo"`, the full `stack` object looks like:

```json
{
  "framework": "monorepo",
  "monorepo": {
    "web": { "framework": "next", "ui": "shadcn" },
    "mobile": { "framework": "expo-rn", "ui": "nativewind" }
  },
  "auth": "supabase",
  "db": "supabase",
  "storage": "supabase",
  "payments": "revenuecat+stripe",
  "deploy": "eas+vercel"
}
```

- The `monorepo` sub-object captures the choices per-app.
- Top-level `auth`/`db`/`storage` are SHARED — both apps consume the same backend via `packages/api/`.
- `payments` is split: web side uses Stripe, mobile uses RevenueCat (Apple 3.1.1 mandates IAP for digital goods).
- `deploy` is split: web via Vercel, mobile via EAS.

## Phase routing

| `phase` | Skill |
|---|---|
| `prd_drafted` or `design_extracted` | `monorepo-bootstrap` (scaffolds root + apps + packages) |
| `monorepo_initialized` (new phase, mid-bootstrap) | `monorepo-bootstrap` continues by invoking `design-md-to-app` in `apps/web/` and `rn-bootstrap` in `apps/mobile/` |
| `scaffolded` | `screenshot-to-page` (operates in `apps/web/`), `rn-add-screen` (operates in `apps/mobile/`), `eve-agent` (operates in `apps/agent/` — optional agent engine, see below), `monorepo-add-shared-package`, `monorepo-sync-types` |
| `page_generated` | `module-add` (web side) or `rn-module-add` (mobile side) — both check `stack.framework="monorepo"` and operate in the right sub-folder |
| `module_added` | iterative: more screens, more modules, more shared packages |
| `feature_complete` | (mobile side) `rn-eas-deploy`; (web side) Vercel deploy via `vercel-deploy` |
| `deployed` | both stores + Vercel live; maintenance via EAS Update for mobile + Vercel redeploys for web |

## New phase introduced

**`monorepo_initialized`** — between `prd_drafted` and `scaffolded`. Means the turborepo skeleton exists (root `package.json`, `pnpm-workspace.yaml`, `turbo.json`, `tsconfig.base.json`, empty `apps/` and `packages/`) but neither sub-app has been scaffolded yet. The bootstrap process then continues by running `design-md-to-app` and `rn-bootstrap` inside the sub-folders.

## Routing rules across skills

All operative skills must read `meta.json#stack.framework` and branch:

- **`monorepo`** → operate inside the relevant sub-app (`apps/web/` or `apps/mobile/`) or in `packages/<name>/`.
- **`next` / `expo-rn` / etc.** → operate at the repo root (current behavior).

### Skills that need patches (monorepo-aware):
- `design-md-to-app`: when `monorepo`, scaffold inside `apps/web/` instead of root. Generate Tailwind config that imports the shared `@myapp/design` preset.
- `rn-bootstrap`: when `monorepo`, scaffold inside `apps/mobile/`. Same Tailwind preset import.
- `screenshot-to-page`: when `monorepo`, operate in `apps/web/`.
- `rn-add-screen`: when `monorepo`, operate in `apps/mobile/`.
- `module-add`: when `monorepo`:
  - backend modules (auth, db, storage, realtime) → installed in `packages/api/`, exposed to both apps.
  - web-specific modules (motion, email server actions, queries) → installed in `apps/web/`.
- `rn-module-add`: when `monorepo`:
  - backend modules consume from `packages/api/` (no reinstall).
  - mobile-specific modules (push, RevenueCat) → installed in `apps/mobile/`.
- `write-tests` / `rn-write-tests`: when `monorepo`, operate in the right sub-app respecting workspace tsconfig paths.

## NEVER use these skills on this stack

- (none) — every existing skill is monorepo-aware after the patches in Ondata C.

## Family membership

New operative skills:
- `monorepo-bootstrap` — scaffolds the full repo (root + apps + packages)
- `monorepo-add-shared-package` — extracts logic into `packages/shared/`
- `monorepo-sync-types` — generates backend types into `packages/shared/types/` (Supabase types, tRPC inference)

All other skills (24 existing) are consumed via monorepo-aware patches.

## Required sub-keys in `meta.json` for monorepo projects

After `monorepo-bootstrap`:
- `stack.framework = "monorepo"`
- `stack.monorepo.web.framework` = `"next"` (or `"astro"`, `"vite-react"`, ...)
- `stack.monorepo.web.ui` = `"shadcn" | "base-ui" | "mui"`
- `stack.monorepo.mobile.framework` = `"expo-rn"`
- `stack.monorepo.mobile.ui` = `"nativewind"` (only valid value)
- `stack_config.monorepo_tool` = `"turborepo"` (only valid value in v1)
- `stack_config.workspace_pm` = `"pnpm"` (only valid value in v1)
- `stack_config.shared_packages` = array of created shared packages, e.g. `["@myapp/shared", "@myapp/design", "@myapp/api"]`

## Phase progression example for a fresh monorepo project

```
1. user runs claude in empty dir, says "voglio app web e mobile per X"
   → dev-flow → prd-from-idea Q6="both/monorepo" → stack.framework="monorepo"
   → phase: empty → prd_drafted

2. user provides DESIGN.md or Figma
   → figma-to-design-md or image-to-design-md
   → phase: prd_drafted → design_extracted

3. dev-flow routes to monorepo-bootstrap
   → scaffolds root: pnpm-workspace.yaml, turbo.json, tsconfig.base.json
   → phase: design_extracted → monorepo_initialized
   → invokes design-md-to-app inside apps/web/
   → invokes rn-bootstrap inside apps/mobile/
   → scaffolds packages/{shared,design,api}/
   → phase: monorepo_initialized → scaffolded

4. user iterates: rn-add-screen, screenshot-to-page, monorepo-add-shared-package, etc.
   → phase: scaffolded → page_generated → module_added

5. user wires backend
   → module-add (writes in packages/api/) + rn-module-add (consumes from packages/api/)
   → phase: module_added

6. user says "siamo feature complete, deploy"
   → mobile side: rn-eas-deploy
   → web side: vercel-deploy (Vercel)
   → phase: feature_complete → deployed
```

## Agent engine (eve) — optional third app

A monorepo can include an optional **`apps/agent/`** — an **eve** agent (Vercel's filesystem-first agent framework) that acts as the AI engine behind the web app. It is an **optional product component** (a scope decision, opted into at analysis time or later on demand), owned exclusively by the **`eve-agent`** skill, and it sits **outside** the `phase` line:

- `eve-agent` reads/writes `meta.json#stack.agent` (`null`/unset → scaffold mode; `"eve"` → capability mode) and appends to `history`, but does **not** bump `phase` — the agent has its own open-ended capability cadence (often Linear-driven), distinct from the web app's linear build.
- `apps/web` consumes the agent via eve's official Next.js integration (`withEve()` + `useEveAgent()`), and they share the wire contract through `packages/types` (re-exported eve session/event types) — not by importing the agent as a library.
- The agent deploys to Vercel via `eve deploy`; its model calls bill through the Vercel AI Gateway.
- No other skill writes inside `apps/agent/`; `eve-agent` does not write `apps/web/` or `apps/mobile/`.

When the user asks for an "agent engine / AI core / agent backend" or names "eve", route to `eve-agent` regardless of `phase`. See the `eve-agent` skill's `references/eve-conventions.md` for the full contract.

## Decision rules

- **One stack per project** — you can't mix monorepo with non-monorepo. Choose at PRD time.
- **Switch is hard** — going from `framework="next"` to `framework="monorepo"` mid-project requires manual restructure. Use `monorepo-bootstrap` only on fresh projects (phase ≤ design_extracted).
- **No partial monorepos** — if you want only web + a shared package (no mobile), this skill set is overkill. Use `framework="next"` + manually add a `packages/shared/` if you really need one.
