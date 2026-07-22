---
name: monorepo-bootstrap
description: 'Scaffold a turborepo monorepo, with shared packages (types, design tokens or shared UI, backend client). Uses pnpm workspaces + turborepo. Reads .workflow/meta.json with stack.framework="monorepo" and phase in {prd_drafted, design_extracted}. Supports three topologies, detected/asked in Step 1: web+mobile (Next.js web app AND an Expo + RN mobile app — the classic case), web+agent (Next.js web app + an eve agent in apps/agent, no mobile), or web-only (just the turborepo/shared-package tooling around one web app). Produces: root package.json + pnpm-workspace.yaml + turbo.json + packages/typescript-config + packages/eslint-config; apps/web/ scaffolded via design-md-to-app; apps/mobile/ scaffolded via rn-bootstrap ONLY for the web+mobile topology; packages/shared/ + packages/api/ skeletons, plus packages/design/ (web+mobile) or packages/ui/ (web-only / web+agent, shadcn monorepo layout). Always idempotent. Use when dev-flow routes here from prd_drafted+monorepo, or the user says "scaffolda il monorepo", "create a turborepo with web + mobile", "bootstrap il monorepo da PRD + DESIGN.md", "scaffolda un turborepo per web + agent eve". Not for: scaffolding only web with no monorepo tooling (use design-md-to-app), scaffolding only mobile (use rn-bootstrap), adding modules after scaffold (use module-add or rn-module-add).'
---

# monorepo-bootstrap — scaffold a turborepo monorepo

## Contract

See `references/contracts.md` (vendored from `dev-flow`). Key facts:
- Reads `<project-root>/.workflow/meta.json#stack.framework` — must be `"monorepo"`.
- Requires `meta.json#phase` in `{prd_drafted, design_extracted}`.
- Reads `PROJECT.md`, `PRD.md`, and `DESIGN.md` from project root (DESIGN.md required for tokens; falls back to defaults if absent).
- Writes the monorepo at project root: `apps/{web,mobile}/`, `packages/{shared,design,api}/`, root config files.
- Transitions phase: `prd_drafted` → `monorepo_initialized` (root scaffold done) → `scaffolded` (both apps + packages exist).
- Always idempotent: re-running detects existing files, skips, reports.

## When this skill applies

- Orchestrator routes here from `dev-flow` when `stack.framework="monorepo"` and `phase ∈ {prd_drafted, design_extracted}`.
- User says: "scaffolda il monorepo", "create a turborepo", "bootstrap il monorepo".

## Knowledge dependencies (read these first)

- `rn-fundamentals/SKILL.md` — Expo SDK + New Architecture + TS for the mobile side (web+mobile topology only).
- `rn-bootstrap/SKILL.md` — how the mobile side is scaffolded; this skill invokes it ONLY for the web+mobile topology.
- `rn-styling/references/nativewind-setup.md` — for the mobile Tailwind config (web+mobile topology only).
- `design-md-to-app/SKILL.md` — how the web side is scaffolded; this skill invokes it in every topology.
- `design-md-to-app/references/<lib>-mapping.md` — based on `stack.monorepo.web.ui`.
- `design-md-to-app/references/shadcn-mapping.md` → "Monorepo (shared `packages/ui`)" — the shadcn monorepo layout used for the web-only / web+agent topologies.
- `eve-agent/SKILL.md` — scaffolds `apps/agent/` for the web+agent topology; this skill does NOT build the agent itself, only the surrounding workspace.
- `references/decision-tree.md` → "The `packages/ui` rule" — which topology gets `packages/design` vs `packages/ui`.
- `references/structure.md` — full monorepo layout (this file lives in this skill's references).
- `references/patterns.md` — turborepo conventions, pnpm protocols.

## Workflow

### Step 1 — Verify preconditions and detect the topology

Read `.workflow/meta.json`. Abort with clear message if:
- `stack.framework != "monorepo"` → "Wrong stack. For mobile-only use rn-bootstrap; for web-only with no monorepo tooling use design-md-to-app directly."
- `phase ∉ {prd_drafted, design_extracted, monorepo_initialized}` → "Expected phase prd_drafted/design_extracted/monorepo_initialized, got X."
- `stack.monorepo.web.framework` missing → ask user (default: `"next"`).
- `stack.monorepo.web.ui` missing → ask user (default: `"shadcn"`).

**Detect or ask the topology** — every later step branches on this, most importantly Step 5:

1. If `stack.monorepo.mobile` is already populated in `meta.json` → topology = `"web-mobile"`.
2. Else if `stack.agent == "eve"`, or the user has said they want an agent engine and no mobile app → topology = `"web-agent"`.
3. Else if the user has explicitly said there is no mobile app and no agent (monorepo wanted only for shared-package tooling, future multi-web-app plans, etc.) → topology = `"web-only"`.
4. Else **ask the user directly**: "Is this monorepo web + mobile, web + an eve agent, or web-only?" Do not default to web+mobile — v1 of this skill assumed it silently, which is exactly the bug this step fixes.

Write the answer to `meta.json#stack.monorepo.topology` (`"web-mobile"` | `"web-agent"` | `"web-only"`) so Step 5 (and any later re-run) doesn't have to re-derive it.

For topology `"web-mobile"` only, also resolve:
- `stack.monorepo.mobile.framework` missing → set to `"expo-rn"` (only valid value for v1).
- `stack.monorepo.mobile.ui` → set to `"nativewind"` (only valid value).

For `"web-agent"` / `"web-only"`, do NOT create a `stack.monorepo.mobile` key at all — its mere presence is what Step 5 uses as the mobile signal in idempotent re-runs.

If `apps/` + `packages/` + `pnpm-workspace.yaml` already exist at project root: print "Already initialized at phase X, skipping root scaffold" and proceed to Step 4.

### Step 2 — Scaffold the root

Run `scripts/init-monorepo.sh <project-root> <project-slug>`:
- Writes `pnpm-workspace.yaml` listing `apps/*` and `packages/*`.
- Writes `turbo.json` with the pipeline definition (build/dev/lint/test/typecheck).
- Writes root `package.json` with name `@<project-slug>/root`, scripts that proxy to turbo.
- Writes `packages/typescript-config/` with `base.json` (path aliases, strict mode), `nextjs.json`, `react-native.json` preset extensions. Also writes `packages/eslint-config/`. **No `tsconfig.base.json` in repo root** — Turborepo official pattern.
- Creates empty dirs: `apps/web/`, `apps/mobile/`, `packages/shared/`, `packages/design/`, `packages/api/`.

Update `meta.json`:
- `stack_config.monorepo_tool = "turborepo"`
- `stack_config.workspace_pm = "pnpm"`
- `stack_config.shared_packages = []` (filled by Step 6)
- `phase = "monorepo_initialized"`

### Step 3 — Scaffold the shared design/UI package from DESIGN.md

Branch by topology (see Step 1 → `stack.monorepo.topology`, and `references/decision-tree.md` → "The `packages/ui` rule"):

**Topology `"web-mobile"`** → `packages/design/` (tokens + two Tailwind flavors, no components — components can't cross the React-DOM/React-Native boundary):
- `src/tokens.ts` — parses `.workflow/DESIGN.md` `json tokens` block, emits typed JS object.
- `src/tailwind-preset.ts` — exports a Tailwind preset (web v3.4 / v4 compatible) consuming the tokens.
- `src/nativewind-preset.ts` — exports a NativeWind preset (Tailwind 3.4 syntax, mobile-compatible).
- `package.json` with name `@<project-slug>/design`, exports `./tokens`, `./tailwind`, `./nativewind`.
- `tsconfig.json` extending `@<slug>/typescript-config/<preset>.json` (e.g., `nextjs.json` for apps/web, `react-native.json` for apps/mobile).

This package is published as `workspace:*` to both apps.

**Topology `"web-agent"` or `"web-only"`** → `packages/ui/` instead, following shadcn's official monorepo layout (`@workspace/ui`), NOT `packages/design/`. Defer the actual scaffold to `design-md-to-app`'s `shadcn init --monorepo` flow in Step 4 (`design-md-to-app/references/shadcn-mapping.md` → "Monorepo (shared `packages/ui`)"); this step just reserves the empty `packages/ui/` slot so Step 6/7 don't collide with it. `packages/design/` does not exist in this topology — the tokens live in `packages/ui/src/styles/globals.css`.

### Step 4 — Scaffold `apps/web/` via `design-md-to-app`

Invoke `design-md-to-app` with:
- cwd = `<project-root>/apps/web/`
- DESIGN.md path = `<project-root>/.workflow/DESIGN.md`
- stack.ui = `meta.json#stack.monorepo.web.ui` (e.g. "shadcn")
- Special instruction, topology `"web-mobile"`: in the generated `tailwind.config.js`, the `presets` array MUST include `require("@<project-slug>/design/tailwind")` — this is how the design tokens reach the web app.
- Special instruction, topology `"web-agent"` / `"web-only"`: tell `design-md-to-app` to use its shadcn monorepo mode (`shadcn init --monorepo`) targeting the `packages/ui/` slot reserved in Step 3, instead of the single-app `components/ui/` layout.
- Skip the `/showcase` route's auto-creation if user already wants minimalist setup; otherwise let `design-md-to-app` create it as normal.

Update `meta.json#stack.monorepo.web` with any user choices recorded by design-md-to-app.

### Step 5 — Scaffold `apps/mobile/` via `rn-bootstrap` (topology `"web-mobile"` only)

**Check `meta.json#stack.monorepo.topology` first.** If it is `"web-agent"` or `"web-only"` (or `stack.monorepo.mobile` is simply absent), **skip this step entirely** — do not create `apps/mobile/`, do not invoke `rn-bootstrap`, and do not generate a NativeWind preset (there is no `packages/design/` in these topologies — see Step 3). Proceed straight to Step 6.

For topology `"web-agent"` specifically: `apps/agent/` is scaffolded by invoking `eve-agent` in Scaffold mode instead, once the workspace root exists — that skill owns everything under `apps/agent/`; this skill's job stops at making sure `pnpm-workspace.yaml` / `turbo.json` already cover `apps/*` so `eve-agent` slots in without extra wiring.

Otherwise (topology `"web-mobile"`), invoke `rn-bootstrap` with:
- cwd = `<project-root>/apps/mobile/`
- DESIGN.md path = `<project-root>/.workflow/DESIGN.md`
- Special instruction: the generated `tailwind.config.js` MUST include `presets: [require("@<project-slug>/design/nativewind")]` so the design tokens reach the mobile app.

Update `meta.json#stack.monorepo.mobile` with any choices.

### Step 6 — Scaffold `packages/shared/` skeleton

Create minimal scaffold:
- `src/index.ts` — barrel export.
- `src/types/.gitkeep`, `src/validators/.gitkeep`, `src/utils/.gitkeep`.
- `package.json` with name `@<project-slug>/shared`, main `./src/index.ts`.
- `tsconfig.json` extending base.

Update `meta.json#stack_config.shared_packages`: `["@<project-slug>/shared", "@<project-slug>/design", "@<project-slug>/api"]` for topology `"web-mobile"`, or `["@<project-slug>/shared", "@<project-slug>/ui", "@<project-slug>/api"]` for `"web-agent"` / `"web-only"` (see Step 3).

### Step 7 — Scaffold `packages/api/` skeleton

Create minimal scaffold (a wrapper that will be filled by `module-add` later):
- `src/index.ts` — barrel.
- `src/client.ts` — placeholder for the backend client (Supabase / tRPC, decided when `auth` module is added).
- `package.json` with name `@<project-slug>/api`.
- `tsconfig.json` extending base.

Don't install the actual backend client here — that's `module-add` / `rn-module-add`'s job. Just the skeleton.

### Step 8 — Install dependencies + verify

Run from project root:
```bash
pnpm install --recursive
```

Then verify:
- `pnpm tsc --noEmit` from `apps/web/`, from `apps/mobile/` (topology `"web-mobile"` only), and each `packages/*/` succeeds.
- `pnpm turbo dev --dry-run` lists every workspace that exists for the chosen topology (5 for `"web-mobile"`: web, mobile, and the 3 packages; 4 for `"web-agent"`/`"web-only"`: web, and the 3 packages — `apps/agent/` joins later once `eve-agent` scaffolds it).

If any verify fails, do NOT bump phase. Report and stop.

### Step 9 — Update meta.json + commit

```json
{
  "stack": { "framework": "monorepo", "monorepo": { "topology": "web-mobile", "web": {...}, "mobile": {...} }, ... },
  "stack_config": {
    "monorepo_tool": "turborepo",
    "workspace_pm": "pnpm",
    "shared_packages": ["@<project-slug>/shared", "@<project-slug>/design", "@<project-slug>/api"]
  },
  "phase": "scaffolded",
  "history": [..., {"skill": "monorepo-bootstrap", "ran_at": "<iso>", "outputs": [...]}]
}
```

For topology `"web-agent"` / `"web-only"`, `stack.monorepo` has no `mobile` key and `shared_packages` lists `@<project-slug>/ui` instead of `@<project-slug>/design` (see Step 3/Step 6).

If git repo: commit with `chore: scaffold monorepo (web + mobile + shared packages)` for `"web-mobile"`, or `chore: scaffold monorepo (web + shared packages, <topology> topology)` otherwise.

## Common anti-patterns (NEVER do)

- ❌ Try to use yarn or npm workspaces instead of pnpm — turborepo + Expo officially support pnpm best.
- ❌ Generate Tailwind config in `apps/web/` without the `@<project-slug>/design/tailwind` preset (topology `"web-mobile"`) — design tokens won't reach the web app.
- ❌ Generate `tailwind.config.js` in `apps/mobile/` without the nativewind preset — same problem mirrored.
- ❌ Install backend client (supabase-js, tRPC) at root — must live in `packages/api/`, consumed via workspace protocol.
- ❌ Add `tsconfig.base.json` in repo root — Turborepo recommends per-package configs that extend a shared package (`packages/typescript-config`). Don't centralize in root.
- ❌ Use `framework="monorepo"` on a project that already has scaffolded code (mid-project switch) — this skill is for fresh projects only.
- ❌ **Assume the topology is always `"web-mobile"` and blindly invoke `rn-bootstrap`** — Step 1 must detect/ask the topology first; Step 5 skips `rn-bootstrap` entirely for `"web-agent"` / `"web-only"`. This was v1's bug: it always scaffolded `apps/mobile/` even for mobile-less projects.
- ❌ Create both `packages/design/` AND `packages/ui/` in the same project — they are mutually exclusive per topology (Step 3).

## Updating meta.json (recommended pattern)

When this skill modifies state (artifact written, phase advanced, history appended), use the canonical script when available:

```bash
# Wherever dev-flow is installed (e.g. ~/.claude/skills/dev-flow/), invoke:
python3 .../dev-flow/scripts/update_meta.py <project-root> record-artifact \
    --path <relative-path> --produced-by 'monorepo-bootstrap' [--derived-from <p1> <p2> ...]
python3 .../dev-flow/scripts/update_meta.py <project-root> set-phase <new_phase>
python3 .../dev-flow/scripts/update_meta.py <project-root> append-history \
    --skill 'monorepo-bootstrap' --inputs '{...}' --outputs '{...}' --phase-after <new_phase>
```

The script enforces phase monotonicity, normalizes legacy kebab-case aliases (e.g. `module-added` → `module_added`), and writes the canonical sha256 + timestamp into `meta.json#artifacts`. **Fall back to direct JSON editing only if the script is not on PATH** (and warn the user).

## Sources

- Spec: `docs/superpowers/specs/2026-05-29-monorepo-set-design.md`
- Official: https://turbo.build/repo/docs
- Official: https://pnpm.io/workspaces
- Official: https://docs.expo.dev/guides/monorepos/
- Course: codewithbeto.dev/rnCourse — (no direct monorepo coverage; assembled from official sources).
