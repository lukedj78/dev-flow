---
name: rn-bootstrap
description: 'Scaffold a new Expo + React Native app from a PROJECT.md + PRD.md + DESIGN.md using the opinionated stack (Expo Router, TypeScript, NativeWind v4, Zustand, TanStack Query, Reanimated, expo-image, FlashList). Reads .workflow/meta.json with stack.framework="expo-rn" and phase in {prd_drafted, design_extracted}. Produces a running Expo app at the project root, sets phase to "scaffolded". Always idempotent: re-running detects existing files and skips. Use when dev-flow routes here from prd_drafted+expo-rn, or the user says "scaffolda app expo from PRD", "create RN app from this PRD/DESIGN", "bootstrap expo app". Not for: adding screens (rn-add-screen, Wave 2), modules (rn-module-add, Wave 3), Next.js scaffolding (design-md-to-app — different stack).'
---

# rn-bootstrap — scaffold Expo + RN from PRD/DESIGN

## Contract

See `references/contracts.md` (vendored from `dev-flow`). Key facts:
- Reads `<project-root>/.workflow/meta.json#stack.framework` — must be `"expo-rn"`.
- Reads `<project-root>/{PROJECT.md, PRD.md, DESIGN.md}`. DESIGN.md is required for tokens; if absent, uses defaults from `references/stack-defaults.md`.
- Writes the app to `<project-root>/` (the same directory).
- Sets `meta.json#phase = "scaffolded"` on success.
- Always idempotent: re-running detects existing `package.json` + `app/` and exits 0.

## When this skill applies

- Orchestrator routes here from `dev-flow` when `meta.json#stack.framework == "expo-rn"` and `meta.json#phase ∈ {prd_drafted, design_extracted}`.
- User says: "scaffolda app expo", "create RN app from PRD".

## Knowledge dependencies (read these first)

- `rn-fundamentals/SKILL.md` — confirms Expo SDK + New Architecture + TypeScript + npm.
- `rn-styling/references/nativewind-setup.md` — the 7-step NativeWind setup (this skill automates it).
- `rn-expo-router/references/concepts.md` — folder layout for `app/`.

## Workflow

### Step 1 — Verify preconditions

Read `<project-root>/.workflow/meta.json`. Abort with a clear message if:
- file missing → "Run `dev-flow init_workflow.py` first."
- `stack.framework != "expo-rn"` → "This skill is for stack.framework=expo-rn. For Next.js use design-md-to-app."
- `phase ∉ {prd_drafted, design_extracted}` → "Expected phase prd_drafted or design_extracted, got X."

If `package.json` + `app/` already exist at project root: print "Already bootstrapped, nothing to do", set phase to scaffolded if not already, exit 0.

### Step 2 — Run create-expo-app

Run `scripts/init-expo-app.sh <project-root> <app-name>`. The app name comes from `meta.json#project_name` (or `PROJECT.md` title).

### Step 3 — Install opinionated stack

Run `scripts/install-stack.sh <project-root>`. Installs NativeWind v4 (with Tailwind 3.4 pin), Zustand, TanStack Query, Reanimated, RNGH, expo-image, FlashList.

### Step 4 — Wire NativeWind from DESIGN.md tokens

Run `npx tsx scripts/wire-nativewind.ts <project-root>`. Generates `tailwind.config.js`, `global.css`, `babel.config.js`, `metro.config.js`. Reads tokens from a fenced ` ```json tokens ` block in DESIGN.md (accepts LF + CRLF line endings).

### Step 5 — Generate folder structure + boilerplate

Create (only if absent — idempotent):
- `app/_layout.tsx` — Stack root, imports `../global.css`, renders `<Stack />`.
- `app/index.tsx` — hello-world screen using NativeWind classes (wraps in `SafeAreaView` from `react-native-safe-area-context`).
- `components/`, `lib/`, `store/`, `types/`, `assets/` — empty dirs with `.gitkeep`.
- `.env.example` — empty stub with `EXPO_PUBLIC_API_URL=`.
- `tsconfig.json` — extend `expo/tsconfig.base`, add `paths` for `@/*`.

Also patch `app.json`:
- `expo.scheme` — set to a kebab-case of `meta.json#project_name`.
- `expo.experiments.typedRoutes` — `true`.
- `expo.newArchEnabled` — `true`.
- `expo.plugins` — add `"expo-router"`.

### Step 6 — Verify (scripts/verify.ts)

Run `npx tsx scripts/verify.ts <project-root>`. If exit code != 0, do NOT bump phase. Report failures from `references/post-bootstrap-checklist.md`.

### Step 7 — Update meta.json + commit

Update `meta.json`:
- `stack`: merge `{ framework: "expo-rn", ui: "nativewind", auth: null, db: null, payments: null, deploy: null }` (existing keys preserved if already set).
- `stack_config`: merge `{ expo_sdk: "<X>", state_lib: "zustand", data_lib: "tanstack-query" }`.
- `phase`: set to `"scaffolded"`.
- `history`: append `{ skill: "rn-bootstrap", ran_at: <iso>, outputs: ["package.json", "app/", "tailwind.config.js", ...], phase_before: <prev>, phase_after: "scaffolded" }`.

If `<project-root>` is a git repo, create a commit: `chore: scaffold Expo + RN app via rn-bootstrap`.

## Updating meta.json (recommended pattern)

When this skill modifies state (artifact written, phase advanced, history appended), use the canonical script when available:

```bash
# Wherever dev-flow is installed (e.g. ~/.claude/skills/dev-flow/), invoke:
python3 .../dev-flow/scripts/update_meta.py <project-root> record-artifact \
    --path <relative-path> --produced-by '<this-skill-name>' [--derived-from <p1> <p2> ...]
python3 .../dev-flow/scripts/update_meta.py <project-root> set-phase <new_phase>
python3 .../dev-flow/scripts/update_meta.py <project-root> append-history \
    --skill '<this-skill-name>' --inputs '{...}' --outputs '{...}' --phase-after <new_phase>
```

The script enforces phase monotonicity, normalizes legacy kebab-case aliases (e.g. `module-added` → `module_added`), and writes the canonical sha256 + timestamp into `meta.json#artifacts`. **Fall back to direct JSON editing only if the script is not on PATH** (and warn the user).

## Folder structure rules (canonical — Expo Router hybrid)

**Non-negotiable Expo Router constraint**: `app/` is **file-based routing only**. Unlike Next.js App Router, Expo Router has no private-folder convention — there is no `_`-prefix skip rule, so every file placed under `app/` (aside from reserved names like `_layout.tsx`, `+not-found.tsx`) becomes a real route. A previous revision of this skeleton put `_components/` folders inside `app/`, copied from the Next.js convention — that was wrong for Expo (it creates ghost routes) and is corrected below. **[VERIFY]** against the installed `expo-router` version: there's an open upstream request for an underscore-skip convention; until it ships, assume `app/` has zero tolerance for non-route files.

This skill scaffolds the canonical RN structure, hybrid model (spec: `docs/superpowers/specs/2026-06-06-folder-structure-refactor.md`, adapted for Expo Router):

```
app/                        # ROUTES ONLY — no components, no hooks, no utils
├── (auth)/                 # opt-in based on stack.route_groups
│   ├── _layout.tsx
│   └── sign-in.tsx
├── (app)/
│   ├── _layout.tsx         # redirect to (auth) if !session
│   ├── (tabs)/             # opt-in based on stack.route_groups
│   │   ├── _layout.tsx
│   │   ├── feed/
│   │   └── profile/
│   └── settings.tsx
└── _layout.tsx             # root: GestureHandlerRootView + ThemeProvider

components/                 # ALL non-route UI lives here, outside app/
├── ui/                     # NativeWind primitives
├── theme/                  # ThemeProvider, useThemeColor
├── shared/                 # L2 per dominio (created empty)
└── <feature>/              # L0/L1 screen-private components (e.g. components/feed/, components/profile/)
                             # created on demand by rn-add-screen, not scaffolded empty here

lib/                        # api, supabase, secure-store, utils
store/                      # Zustand cross-feature (auth-store, app-preferences)
hooks/                      # RN-specific (useColorScheme, useKeyboard)
assets/                     # images/, fonts/
```

No `src/` prefix: `app/`, `components/`, `lib/` etc. stay at the project root — matches the default `create-expo-app` templates (which don't use `src/`) and keeps `rn-add-screen` / `promote-component` consistent with this scaffold.

Read `meta.json#stack.route_groups` to decide which route groups to scaffold. Empty array → flat routing (rare for mobile).

Components follow Rule of Three for promotion (L0 → L1 → L2), targeting `components/<feature>/` (L0/L1) and `components/shared/<dominio>/` (L2) — **never** `app/<route>/_components/`. See `rn-add-screen` for screen-level details and `promote-component` for the promotion mechanics.

## Sources

- Course: codewithbeto.dev/rnCourse — free lessons 5-6 (Creating Your First App, Project Structure).
- Official: https://docs.expo.dev/get-started/create-a-project/
- Official: https://www.nativewind.dev/v4/getting-started/expo-router
