---
name: monorepo-bootstrap
description: 'Scaffold a turborepo monorepo on pnpm workspaces, with shared packages (types, design tokens or shared UI, backend client). Four topologies, asked in Step 1: web+mobile (Next.js app AND an Expo + RN app), web+agent (Next.js app + an eve agent in apps/agent), web-agent-inapp (one web app with the eve agent inside it, domain packages with enforced boundaries, Biome, one packages/config), or web-only (the turborepo tooling around one web app). Reads `.workflow/meta.json` with `stack.framework="monorepo"` and phase in {prd_drafted, design_extracted}. Always idempotent. Use when dev-flow routes here, or the user says "scaffolda il monorepo", "create a turborepo with web + mobile", "bootstrap il monorepo da PRD + DESIGN.md", "scaffolda un turborepo per web + agent eve". Not for: scaffolding only web with no monorepo tooling (use design-md-to-app), scaffolding only mobile (use rn-bootstrap), or adding modules after the scaffold (use module-add or rn-module-add).'
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
- `references/boundaries.md` — the `"web-agent-inapp"` topology: `boundaries.json`, the four checks `check_boundaries.py` runs, and why the agent inside the app imports only services and contracts.

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
3. Else if `stack.agent == "eve"` and the agent's only consumer is the web app, but the product needs **domain packages with enforced boundaries** (a services facade, a db package, capability packages) → topology = `"web-agent-inapp"`: the agent lives in `apps/web/agent/` (eve-agent's layout A), and the monorepo exists for the packages, not for a second app. Ask when unsure between this and `"web-agent"` — the question is whether the agent has a second consumer or its own deploy cadence (then `"web-agent"`).
4. Else if the user has explicitly said there is no mobile app and no agent (monorepo wanted only for shared-package tooling, future multi-web-app plans, etc.) → topology = `"web-only"`.
5. Else **ask the user directly**: "Is this monorepo web + mobile, web + an eve agent (its own app, or inside the web app), or web-only?" Do not default to web+mobile — v1 of this skill assumed it silently, which is exactly the bug this step fixes.

Write the answer to `meta.json#stack.monorepo.topology` (`"web-mobile"` | `"web-agent"` | `"web-agent-inapp"` | `"web-only"`) so Step 5 (and any later re-run) doesn't have to re-derive it.

For topology `"web-mobile"` only, also resolve:
- `stack.monorepo.mobile.framework` missing → set to `"expo-rn"` (only valid value for v1).
- `stack.monorepo.mobile.ui` → set to `"nativewind"` (only valid value).

For `"web-agent"` / `"web-only"`, do NOT create a `stack.monorepo.mobile` key at all — its mere presence is what Step 5 uses as the mobile signal in idempotent re-runs.

If `apps/` + `packages/` + `pnpm-workspace.yaml` already exist at project root: print "Already initialized at phase X, skipping root scaffold" and proceed to Step 4.

### Step 2 — Scaffold the root

Run `scripts/init-monorepo.sh <project-root> <project-slug> <topology>` (it creates only the folders that topology uses).

**Topology `"web-agent-inapp"` follows its own path here** — `references/boundaries.md` is the procedure, in short:

1. The script writes `pnpm-workspace.yaml` (`apps/*`, `packages/*`, `capabilities/*`), `turbo.json`, a root `package.json` whose `lint` is **`biome check . && python3 scripts/check_boundaries.py . && turbo lint`**, `engines.node >=24`, and the project's own copy of `scripts/check_boundaries.py`. No ESLint config package and no `typescript-config`: one **`packages/config`** holds tsconfig, Biome and env.
2. **Write `boundaries.json` at the root** — the single source for which workspace packages exist and who may depend on whom (folders that are not packages, like `tools/` or `infrastructure/`, are the project's own call). From the PRD or the project's spec when it has a boundary table; otherwise start from `references/boundaries-web-agent-inapp.json` (replace `@SLUG`) and confirm the table with the user. A package or folder outside it is a decision, not a default.
3. `python3 <skills>/monorepo-bootstrap/scripts/scaffold_packages.py <project-root>` (the skill's script, not a project file) creates each declared package with `exports` on `.` only, an empty `src/index.ts` and a `tsconfig.json` extending `../config/tsconfig/library.json`, plus `packages/config` (`tsconfig/{base,library,nextjs}.json`, `biome.base.json`, `src/env.ts`) and a root `biome.json` that extends it.
4. `corepack use pnpm@<current>` (it writes `packageManager`, which Turbo 2 reads), then tools at their current versions, exact: `pnpm add -D -w --save-exact turbo typescript @biomejs/biome vitest @types/node` and `pnpm --filter @<slug>/config add --save-exact zod`. Record them; this skill writes no version numbers.
5. `pnpm exec biome check --write .` once — the generated files are not in Biome's format — then `pnpm lint`, `pnpm typecheck`, `pnpm test` must exit 0, and `python3 scripts/check_boundaries.py --self-test` must pass.

Steps 3, 6 and 7 below do not apply to this topology: `packages/ui` is one of the declared packages, and there is no `packages/shared` or `packages/api` unless `boundaries.json` declares them. Continue at Step 4, then Step 5's agent paragraph.

For the other topologies, `scripts/init-monorepo.sh` does the following:
- Writes `pnpm-workspace.yaml` listing `apps/*` and `packages/*`.
  - ⚠️ **On pnpm 11, add a `minimumReleaseAgeExclude` list for any dependency you track at head.** `minimumReleaseAge` refuses to install a version published less than N minutes ago — the window in which a compromised release is normally caught — and **its default became `1440` (one day) in pnpm v11**, from `0` before. Nothing errors: `pnpm add <pkg>@latest` simply resolves to yesterday's version. Exempt fast-moving packages by name (`eve`, `ai`, `"@ai-sdk/*"`, `"@vercel/*"`), never by lowering the setting globally — the delay is worth keeping for the transitive dependencies nobody chose. Patterns need pnpm ≥ 10.17. Ref: <https://pnpm.io/settings/dependency-resolution#minimumreleaseage>.
- Writes `turbo.json` with the pipeline definition (build/dev/lint/test/typecheck).
- Writes root `package.json` with name `@<project-slug>/root`, scripts that proxy to turbo.
- Writes `packages/typescript-config/` with `base.json` (path aliases, strict mode), `nextjs.json`, `react-native.json` preset extensions. Also writes `packages/eslint-config/`. **No `tsconfig.base.json` in repo root** — Turborepo official pattern.
- Creates the empty dirs of the topology: `apps/web/`, `packages/shared/`, `packages/api/`, plus `apps/mobile/` and `packages/design/` for `"web-mobile"` or `packages/ui/` for `"web-agent"` / `"web-only"`. (v1 created all five for every topology.)

Update `meta.json`:
- `stack_config.monorepo_tool = "turborepo"`
- `stack_config.workspace_pm = "pnpm"`
- `stack_config.shared_packages = []` (filled by Step 6)
- `phase = "monorepo_initialized"`

### Step 3 — Scaffold the shared design/UI package from DESIGN.md

Branch by topology (see Step 1 → `stack.monorepo.topology`, and `references/decision-tree.md` → "The `packages/ui` rule"):

**Topology `"web-mobile"`** → `packages/design/` (tokens + Tailwind flavors, no components — components can't cross the React-DOM/React-Native boundary):
- `src/tokens.ts` — parses `.workflow/DESIGN.md` `json tokens` block, emits typed JS object.
- `theme.css` — an **`@theme` block** built from the tokens. This is how the **web** app (Tailwind v4, which `create-next-app@16 --tailwind` installs) consumes the tokens: `apps/web/app/globals.css` does `@import "@<slug>/design/theme.css";`. Tailwind v4 is CSS-first and has **no JS `presets` mechanism**.
- `src/tailwind-preset.ts` — a v3-style JS preset, exported **only** as a fallback for a web app still on Tailwind v3 (`scaffold-web.sh --patch` auto-detects: `tailwind.config.*` present → patch this preset; absent → v4 `@import` path above).
- `src/nativewind-preset.ts` — exports a NativeWind preset (Tailwind 3.4 syntax) for **mobile** (NativeWind still tracks the v3 config shape).
- `package.json` with name `@<project-slug>/design`, exports `./tokens`, `./theme.css`, `./tailwind` (v3 fallback), `./nativewind`.
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

For topology `"web-agent-inapp"`: invoke `eve-agent` in Scaffold mode **inside `apps/web`** — its layout A, the agent in `apps/web/agent/` beside `app/`, `withEve()` in `apps/web/next.config.ts`, no `apps/agent` and no `packages/types`. `boundaries.json#paths` already limits what `agent/` may import (contracts, services, capability packages), so moving it to its own app later stays a move. Set `stack_config.agent_capabilities = "packages"` when the product has capabilities (`eve-agent/references/capability-package.md`).

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

For `"web-agent-inapp"` the verification is Step 2's last item plus `pnpm typecheck` in `apps/web` once Step 4 has run. ⚠️ `set-phase scaffolded` also checks the design lint: when the UI library is not styled with Tailwind, record `stack.design_lint = "none"` with `stack_config.design_lint_reason`, or the move is refused. The design lint (`@shadcn/lint`, an ESLint plugin) stays on ESLint only for `apps/web` and `packages/ui`, and only where the UI library styles with Tailwind; its preset goes in `packages/config/eslint/` (there is no `packages/eslint-config`). ⚠️ `setup_design_lint.py` does not know that location yet: until it does, run it, read where it put the preset, and move it — or record the design-lint decision as an exception with its reason.

For the other topologies, wire the design lint — automatically, here, because this is the first point where the workspace
is installed and `packages/ui` (or `apps/web/components/ui`) is populated:

```bash
python3 design-md-to-app/scripts/setup_design_lint.py <project-root>
```

It handles all three topologies on its own: the shadcn monorepo (`web-only` / `web-agent`: preset in
`packages/eslint-config`, spread into `apps/web` and `packages/ui`, `--max-warnings` because the
template loads `eslint-plugin-only-warn`) and `web-mobile` (`apps/web` is a full create-next-app,
wired as a single app). A non-zero exit is a failed verify. `design-md-to-app` skipped its own
Step 4.10 when invoked from Step 4 for exactly this reason.

Right after it, set up registry intake at the repo root — the lock covers `apps/*/components.json` and
`packages/*/components.json`, and takes the caps just set as its baseline:

```bash
python3 registry-intake/scripts/registry_intake.py setup <project-root>
```

If any verify fails, do NOT bump phase. Report and stop.

### Step 9 — Update meta.json + commit

Move the phase with `python3 dev-flow/scripts/update_meta.py <project-root> set-phase scaffolded`,
never by writing `phase` into the JSON: the design-lint and registry-intake gates live in `set-phase`
and refuse the transition until both from Step 8 are in place. The rest of the block below is written as before.

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

For topology `"web-agent-inapp"`: `stack.monorepo.topology = "web-agent-inapp"`, `stack.agent = "eve"`, `stack.lint = "biome"` (or `"eslint+biome"` once the design lint is wired), `stack_config.config_package = "single"`, and `stack_config.shared_packages` lists the packages `boundaries.json` declares.

For topology `"web-agent"` / `"web-only"`, `stack.monorepo` has no `mobile` key and `shared_packages` lists `@<project-slug>/ui` instead of `@<project-slug>/design` (see Step 3/Step 6).

If git repo: commit with `chore: scaffold monorepo (web + mobile + shared packages)` for `"web-mobile"`, or `chore: scaffold monorepo (web + shared packages, <topology> topology)` otherwise.

## Common anti-patterns (NEVER do)

- ❌ Try to use yarn or npm workspaces instead of pnpm — turborepo + Expo officially support pnpm best.
- ❌ Generate Tailwind config in `apps/web/` without the `@<project-slug>/design/tailwind` preset (topology `"web-mobile"`) — design tokens won't reach the web app.
- ❌ Generate `tailwind.config.js` in `apps/mobile/` without the nativewind preset — same problem mirrored.
- ❌ Install backend client (supabase-js, tRPC) at root — must live in `packages/api/`, consumed via workspace protocol.
- ❌ Add `tsconfig.base.json` in repo root — Turborepo recommends per-package configs that extend a shared package (`packages/typescript-config`, or `packages/config` in `"web-agent-inapp"`). Don't centralize in root.
- ❌ Put the shared Biome config at `packages/config/biome.json` — Biome 2 finds it, calls it a *nested root configuration* and refuses to run. It is `biome.base.json`, extended by the root `biome.json`.
- ❌ Add a package, or let a package depend on another, without changing `boundaries.json` first — `pnpm lint` fails, and that is the point.
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
- Official: https://turborepo.dev/docs
- Official: https://pnpm.io/workspaces
- Official: https://docs.expo.dev/guides/monorepos/
- Course: codewithbeto.dev/rnCourse — (no direct monorepo coverage; assembled from official sources).
