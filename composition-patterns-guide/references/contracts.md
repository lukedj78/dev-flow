# `.workflow/` — Contract between dev-flow skills

This document defines the **canonical contract** that all skills in the dev-flow family must respect. It is the load-bearing piece of the architecture: skills know nothing about each other, but they all read and write `.workflow/` in the same way.

> Living version: this file. Skills that need to consult the contract should read **this exact file** (vendor a copy into their `references/` if standalone) — do not paraphrase from memory.

## Folder layout

A "dev-flow project" is a **standard codebase root** (the directory that contains `package.json`, your framework files, your git repo) with a `.workflow/` overlay holding planning + design metadata. The codebase lives at the top, not nested inside `.workflow/`.

```
<project-root>/                   # ← standard codebase root (Next/Vite/Remix/etc.)
├── .workflow/                    # ← planning + design metadata only
│   ├── meta.json                 # required, machine-readable state
│   ├── PROJECT.md                # high-level idea, audience, success criteria
│   ├── PRD.md                    # product requirements
│   ├── tasks.md                  # task breakdown, beads/issues compatible
│   ├── DESIGN.md                 # design system per Google design.md spec
│   ├── screenshots/              # raw or annotated UI references
│   │   └── *.{png,jpg}
│   └── decisions/                # ADR-style decisions, one per file (optional)
│       └── 0001-stack.md
├── package.json                  # ← codebase lives at the root
├── app/, components/, lib/       # ← framework conventions, untouched
├── registry.json                 # ← shadcn registry (when applicable), at root
├── drizzle.config.ts             # ← config files at root
└── ...                           # ← anything else the framework expects
```

**Rules**:
- `.workflow/` is the **only** dev-flow-owned directory. Everything outside it is the framework's territory — skills modify framework files only when their scope says so (e.g., `design-md-to-app` writes `package.json` and `app/`, but doesn't put anything in `.workflow/` except updating `meta.json`).
- The codebase is at the project root. **No `app/` inside `.workflow/`.** This means `cd <project-root> && pnpm dev` works the way every developer expects.
- Files are written incrementally. A skill writes only the files in its scope. It must **not** delete files written by other skills.
- `meta.json` is the single source of truth for the project's current state. Every skill that runs must read `meta.json` first and update it last.
- All file names are case-sensitive and exact: `PROJECT.md` (not `project.md`), `PRD.md`, `DESIGN.md` (uppercase per Google spec), `tasks.md`, `meta.json`.

### Bootstrapping order

The codebase doesn't exist until `design-md-to-app` runs. Until then, the project root contains only `.workflow/` (and possibly a `.git/` if the user initialized one). When `design-md-to-app` runs `pnpm create next-app .` (or equivalent) it scaffolds **into the project root**, alongside `.workflow/`. `.workflow/` does not interfere with framework scaffolders because no file there clashes with their expected entry-points (`package.json`, `app/`, `src/`, `vite.config.ts`, etc.).

## `meta.json` schema

```json
{
  "project_slug": "aetherfield",
  "project_name": "Aetherfield",
  "created_at": "2026-04-25T14:00:00Z",
  "updated_at": "2026-04-25T15:30:00Z",
  "phase": "design_extracted",
  "stack": {
    "framework": "next",
    "ui": "shadcn",
    "auth": "better-auth",
    "db": "neon-drizzle",
    "payments": null,
    "deploy": "vercel"
  },
  "artifacts": {
    ".workflow/DESIGN.md": {
      "sha256": "abc123…",
      "produced_by": "figma-to-design-md",
      "produced_at": "2026-04-25T14:30:00Z"
    },
    "registry.json": {
      "sha256": "def456…",
      "produced_by": "design-md-to-app",
      "produced_at": "2026-04-25T15:30:00Z",
      "derived_from": [
        { "path": ".workflow/DESIGN.md", "sha256": "abc123…" }
      ]
    }
  },
  "history": [
    {
      "skill": "prd-from-idea",
      "ran_at": "2026-04-25T14:00:00Z",
      "outputs": ["PROJECT.md", "PRD.md"],
      "phase_before": "empty",
      "phase_after": "prd_drafted"
    },
    {
      "skill": "figma-to-design-md",
      "ran_at": "2026-04-25T14:30:00Z",
      "inputs": {"figma_url": "https://..."},
      "outputs": ["DESIGN.md", "screenshots/"],
      "phase_before": "prd_drafted",
      "phase_after": "design_extracted"
    }
  ]
}
```

### `artifacts` field

Tracks every contract-shaped file with its content hash and provenance. The model is content-addressed: an artifact entry says "skill X wrote this file with this exact content at time T". When the on-disk hash later differs from the recorded one, the artifact is **stale** and the producing skill (or the user) needs to decide what to do.

Each entry:
- `sha256` — hex digest of the file's bytes at write time.
- `produced_by` — the skill name that last wrote (or rewrote) this file.
- `produced_at` — ISO-8601 timestamp.
- `derived_from` (optional) — list of `{path, sha256}` pairs. Each entry is an upstream input the skill used to derive this artifact, snapshotted at the version it was at when this artifact was produced. Used by `check_drift.py` to detect upstream-stale artifacts (output file is unchanged on disk but a `derived_from` input has drifted — common case: user edited `DESIGN.md` after `design-md-to-app` ran, so `registry.json` is now derived from a stale snapshot).

Skills update this via `dev-flow/scripts/update_meta.py record-artifact …`. The `check_drift.py` script reports which artifacts are fresh / self-drift / upstream-stale / missing — diagnostic only, never mutating.

The `artifacts` field is the foundation for resumability and drift detection: re-running a skill is safe if all its inputs are fresh; necessary if any are stale.

### `phase` enum (canonical)

The `phase` field tracks the project's progress through the pipeline. Every skill must set this correctly.

**All phase values are `snake_case` strings**. The canonical list below is the complete enum; skills MUST NOT use values outside it. Unknown values are treated as `empty` (forward-compatibility).

| `phase` value | Stacks | When set | Ready for next skill |
|---|---|---|---|
| `empty` | all | `.workflow/` was just created, only `meta.json` exists | `prd-from-idea` |
| `idea_captured` | all | `PROJECT.md` exists | `prd-from-idea` (to expand into PRD) or scaffold (skip if simple) |
| `prd_drafted` | all | `PRD.md` exists | `prd-to-tasks`, `figma-to-design-md`, `image-to-design-md`, or scaffold |
| `tasks_split` | all | `tasks.md` exists | `figma-to-design-md`, `image-to-design-md`, or scaffold |
| `design_extracted` | all | `DESIGN.md` + (optional) `screenshots/` exist | scaffold (`design-md-to-app` for web, `rn-bootstrap` for mobile) |
| `scaffolded` | all | `app/` exists with framework + UI library installed | next-stack-skill (`screenshot-to-page` web / `rn-add-screen` mobile) or `module-add` / `rn-module-add` |
| `page_generated` | all | At least one route is implemented from a screenshot or PRD | `module-add` / `rn-module-add`, more screen-gen runs |
| `module_added` | all | Auth/DB/payments/etc. wired up | iterative — repeat as needed; mobile leads to `feature_complete` |
| `feature_complete` | **expo-rn only** | All planned features built and tested; ready to ship | `rn-eas-deploy` |
| `deployed` | **expo-rn only** | App live on App Store + Play Store with EAS Update channels configured | maintenance loop (`rn-add-screen` for features, `rn-eas-build-submit-update` for OTA hotfixes) |

**Notes**:
- All values are `snake_case` (e.g., `module_added` NOT `module-added`). Skills that use the kebab-case variant are non-conforming and should be migrated.
- The `feature_complete` and `deployed` phases are **mobile-only** (`stack.framework="expo-rn"`); web stack ends at `module_added` and continues iteratively.
- **Phase progression is monotonic** — a skill should never set `phase` to an earlier value than what it found. If a skill is re-run (e.g., user re-extracts design from a new Figma), it appends to `history` but keeps the phase ≥ the current one.
- The `deployed` phase is terminal in the sense that future runs stay there; subsequent EAS Update or new-feature work appends to `history` without phase regression.

### `stack` field

Captures user choices that downstream skills need. Keys:

- `framework`: `"next"` | `"vite-react"` | `"remix"` | `"astro"` | `"sveltekit"` | `"expo-rn"` | `"monorepo"` (planned) | string
- `ui`: `"shadcn"` | `"base-ui"` | `"mui"` | `"chakra"` | `"radix-vanilla"` | `"nativewind"` (mobile) | string
- `auth`: `"better-auth"` | `"next-auth"` | `"clerk"` | `"supabase"` | `"supabase-auth"` | `"firebase"` | `"custom-rest"` | `"trpc"` | `null`
- `db`: `"neon-drizzle"` | `"supabase"` | `"firebase"` | `"planetscale-prisma"` | `"custom-rest"` | `"trpc"` | `null`
- `payments`: `"stripe"` | `"lemon-squeezy"` | `"revenuecat"` (mobile IAP) | `null`
- `deploy`: `"vercel"` | `"fly"` | `"cloudflare-pages"` | `"eas"` (mobile) | `null`
- `storage` (mobile, optional): `"supabase"` | `"firebase"` | `"custom-rest"` | `null`
- `realtime` (mobile, optional): `"supabase"` | `"firebase"` | `"custom-rest"` | `null`
- `push` (mobile, optional): `"expo-notifications"` | `null`
- `route_groups` (web/monorepo, optional): array of `"(marketing)"` | `"(auth)"` | `"(app)"` | `"(tabs)"` (mobile). E.g. `["(marketing)", "(auth)", "(app)"]` for SaaS, `["(auth)", "(app)"]` for internal tool, `["(marketing)"]` for marketing site. Written by `prd-from-idea` based on deduction from the PRD; can be overridden by user later.

Use `null` (not `"none"`) when not yet decided. For `route_groups`, an empty array `[]` means "no route groups, flat routing".

## Folder structure conventions

Skills that scaffold a codebase (`design-md-to-app`, `rn-bootstrap`, `monorepo-bootstrap`) MUST generate the canonical folder structure documented in `docs/superpowers/specs/2026-06-06-folder-structure-refactor.md`. Key rules:

- **Co-location via `_components/`**: page-private components live in `app/<route>/_components/`. The underscore prefix is Next.js convention for non-routable folders.
- **Shared components by domain**: cross-route-group shared business components live in `components/shared/<dominio>/<Component>.tsx`. The domain folder name is the business domain (post/, user/, billing/), never generic ("shared"/"common"/"global").
- **UI primitives separate**: shadcn/Base UI/MUI primitives live in `components/ui/`. Never mixed with business components.
- **Theme system explicit**: ThemeProvider + ModeToggle live in `components/theme/`, NOT loose in `components/`.
- **No `src/` directory**: code lives at project root, alongside config files. Aligned with Vercel commerce, Cal.com, and shadcn templates.
- **Route groups opt-in via `route_groups`**: scaffold only the route groups listed in `stack.route_groups`. Never create empty `(marketing)/` for a project that doesn't need it.
- **Rule of Three for promotion**: components stay at the lowest level until used 3+ times. The `promote-component` skill handles the move + import updates.
- **Cross-platform sharing (monorepo)**: only types, Zod schemas, and pure logic in `packages/shared/`. NEVER JSX. Web and mobile UI are separate (each app has its own `components/`).

## File-format conventions

### `PROJECT.md`
Free-form prose, one h1 (the project name). Sections expected: **Overview**, **Audience**, **Problem & current alternatives**, **Value proposition**, **Success criteria**, **Out of scope** (optional). Written by `prd-from-idea`.

### `PRD.md`
Free-form prose. Conventional sections: **Problem**, **Solution overview**, **User stories** (`As a … I want …`), **Non-goals**, **Technical constraints**, **Open questions**. Written by `prd-from-idea`.

### `tasks.md`
A checklist compatible with beads / GitHub Issues / Linear import. Each task is a `## ` heading with body, plus a `- [ ]` line for status. Written by `prd-to-tasks`.

### `DESIGN.md`
Strictly conformant to the Google design.md spec — see `figma-to-design-md/references/spec.md`. Written by `figma-to-design-md`, `image-to-design-md`, or by hand (downstream skills consume it).

### `screenshots/`
Raw screenshots of the UI for reference. Filenames should be slugged page names (`home-hero.png`, `pricing-comparison.png`). Written by `figma-to-design-md` and `image-to-design-md`, consumable by `screenshot-to-page`.

### Codebase (project root)
The actual codebase lives at `<project-root>/` (NOT inside `.workflow/`). It's owned by `design-md-to-app` (which scaffolds it) and modified by `screenshot-to-page` and `module-add`. Skills must **not** edit codebase files unless that's their explicit job — the orchestrator routes to the right specialist.

Specifically:
- `<project-root>/package.json`, `<project-root>/app/`, `<project-root>/components/`, `<project-root>/lib/`, etc. — owned by the codebase skills (`design-md-to-app`, `screenshot-to-page`, `module-add`).
- `<project-root>/.workflow/` — owned by the planning skills and by `meta.json` updates from any skill.

These two zones never overlap in writes. If a skill edits both (e.g., `design-md-to-app` writes the codebase AND updates `meta.json`), the contract is: codebase files at root, then `.workflow/meta.json` at end.

## Project slug

`project_slug` is derived from `project_name` by lowercasing, replacing non-alphanumeric with hyphens, and trimming. It must be filesystem-safe (used for things like the `app/` directory name in some templates and for git branch names).

## Project root location

Skills do **not** decide where the project lives. The user (via `dev-flow`) chooses an absolute path; skills receive it as input. The user's current shell `cwd` is *not* assumed to be the project root — verify by checking for `.workflow/meta.json`.

## Backwards compatibility

If a skill encounters a `meta.json` with an unknown `phase` value, it must not crash — it logs a warning and treats it as `empty` for routing purposes. New phases can be added to this contract; old skills will simply skip them.

If a skill encounters fields in `meta.json` it doesn't recognize, preserve them verbatim when rewriting the file.
