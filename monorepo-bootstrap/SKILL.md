---
name: monorepo-bootstrap
description: 'Scaffold a turborepo monorepo containing both a Next.js web app AND an Expo + RN mobile app, with shared packages (types, design tokens, backend client). Uses pnpm workspaces + turborepo. Reads .workflow/meta.json with stack.framework="monorepo" and phase in {prd_drafted, design_extracted}. Produces: root package.json + pnpm-workspace.yaml + turbo.json + packages/typescript-config + packages/eslint-config; apps/web/ scaffolded via design-md-to-app; apps/mobile/ scaffolded via rn-bootstrap; packages/shared/ + packages/design/ + packages/api/ skeletons. Always idempotent. Use when dev-flow routes here from prd_drafted+monorepo, or the user says "scaffolda il monorepo", "create a turborepo with web + mobile", "bootstrap il monorepo da PRD + DESIGN.md". Not for: scaffolding only web (use design-md-to-app), scaffolding only mobile (use rn-bootstrap), adding modules after scaffold (use module-add or rn-module-add).'
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

- `rn-fundamentals/SKILL.md` — Expo SDK + New Architecture + TS for the mobile side.
- `rn-bootstrap/SKILL.md` — how the mobile side is scaffolded; this skill invokes it.
- `rn-styling/references/nativewind-setup.md` — for the mobile Tailwind config.
- `design-md-to-app/SKILL.md` — how the web side is scaffolded; this skill invokes it.
- `design-md-to-app/references/<lib>-mapping.md` — based on `stack.monorepo.web.ui`.
- `references/structure.md` — full monorepo layout (this file lives in this skill's references).
- `references/patterns.md` — turborepo conventions, pnpm protocols.

## Workflow

### Step 1 — Verify preconditions

Read `.workflow/meta.json`. Abort with clear message if:
- `stack.framework != "monorepo"` → "Wrong stack. For mobile-only use rn-bootstrap; for web-only use design-md-to-app."
- `phase ∉ {prd_drafted, design_extracted, monorepo_initialized}` → "Expected phase prd_drafted/design_extracted/monorepo_initialized, got X."
- `stack.monorepo.web.framework` missing → ask user (default: `"next"`).
- `stack.monorepo.web.ui` missing → ask user (default: `"shadcn"`).
- `stack.monorepo.mobile.framework` missing → set to `"expo-rn"` (only valid value for v1).
- `stack.monorepo.mobile.ui` → set to `"nativewind"` (only valid value).

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

### Step 3 — Scaffold `packages/design/` from DESIGN.md

Generate `packages/design/`:
- `src/tokens.ts` — parses `.workflow/DESIGN.md` `json tokens` block, emits typed JS object.
- `src/tailwind-preset.ts` — exports a Tailwind preset (web v3.4 / v4 compatible) consuming the tokens.
- `src/nativewind-preset.ts` — exports a NativeWind preset (Tailwind 3.4 syntax, mobile-compatible).
- `package.json` with name `@<project-slug>/design`, exports `./tokens`, `./tailwind`, `./nativewind`.
- `tsconfig.json` extending `@<slug>/typescript-config/<preset>.json` (e.g., `nextjs.json` for apps/web, `react-native.json` for apps/mobile).

This package is published as `workspace:*` to both apps.

### Step 4 — Scaffold `apps/web/` via `design-md-to-app`

Invoke `design-md-to-app` with:
- cwd = `<project-root>/apps/web/`
- DESIGN.md path = `<project-root>/.workflow/DESIGN.md`
- stack.ui = `meta.json#stack.monorepo.web.ui` (e.g. "shadcn")
- Special instruction: in the generated `tailwind.config.js`, the `presets` array MUST include `require("@<project-slug>/design/tailwind")` — this is how the design tokens reach the web app.
- Skip the `/showcase` route's auto-creation if user already wants minimalist setup; otherwise let `design-md-to-app` create it as normal.

Update `meta.json#stack.monorepo.web` with any user choices recorded by design-md-to-app.

### Step 5 — Scaffold `apps/mobile/` via `rn-bootstrap`

Invoke `rn-bootstrap` with:
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

Update `meta.json#stack_config.shared_packages` with the array `["@<project-slug>/shared", "@<project-slug>/design", "@<project-slug>/api"]`.

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
- `pnpm tsc --noEmit` from `apps/web/`, `apps/mobile/`, and each `packages/*/` succeeds.
- `pnpm turbo dev --dry-run` lists all 5 workspaces.

If any verify fails, do NOT bump phase. Report and stop.

### Step 9 — Update meta.json + commit

```json
{
  "stack": { "framework": "monorepo", "monorepo": { "web": {...}, "mobile": {...} }, ... },
  "stack_config": {
    "monorepo_tool": "turborepo",
    "workspace_pm": "pnpm",
    "shared_packages": ["@<project-slug>/shared", "@<project-slug>/design", "@<project-slug>/api"]
  },
  "phase": "scaffolded",
  "history": [..., {"skill": "monorepo-bootstrap", "ran_at": "<iso>", "outputs": [...]}]
}
```

If git repo: commit with `chore: scaffold monorepo (web + mobile + shared packages)`.

## Common anti-patterns (NEVER do)

- ❌ Try to use yarn or npm workspaces instead of pnpm — turborepo + Expo officially support pnpm best.
- ❌ Generate Tailwind config in `apps/web/` without the `@<project-slug>/design/tailwind` preset — design tokens won't reach the web app.
- ❌ Generate `tailwind.config.js` in `apps/mobile/` without the nativewind preset — same problem mirrored.
- ❌ Install backend client (supabase-js, tRPC) at root — must live in `packages/api/`, consumed via workspace protocol.
- ❌ Add `tsconfig.base.json` in repo root — Turborepo recommends per-package configs that extend a shared package (`packages/typescript-config`). Don't centralize in root.
- ❌ Use `framework="monorepo"` on a project that already has scaffolded code (mid-project switch) — this skill is for fresh projects only.

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
