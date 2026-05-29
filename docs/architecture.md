# Architecture — the `.workflow/` contract

The entire orchestration model of dev-flow is one shared folder + one shared schema. This document specifies both, exhaustively.

## Folder layout

A dev-flow project is a **standard codebase root** with a `.workflow/` overlay:

```
<project-root>/                   # the codebase root (where package.json lives)
├── .workflow/                    # dev-flow metadata (the only thing dev-flow owns)
│   ├── meta.json                 # required — machine-readable state
│   ├── PROJECT.md                # high-level brief
│   ├── PRD.md                    # product requirements
│   ├── tasks.md                  # task breakdown (beads / Issues / Linear compatible)
│   ├── DESIGN.md                 # design system, Google design.md spec
│   ├── screenshots/              # raw or annotated UI references
│   │   └── *.{png,jpg}
│   └── decisions/                # ADR-style decisions, optional
│       └── 0001-stack.md
├── package.json                  # ← codebase at the root
├── app/, components/, lib/       # ← framework conventions
├── registry.json                 # ← shadcn token registry, when applicable
└── ...                           # ← anything else the framework expects
```

**Key invariants**:

1. **The codebase lives at the project root, not inside `.workflow/`**. `cd <project-root> && pnpm dev` must work the way every developer expects.
2. **`.workflow/` is the only directory dev-flow owns**. Skills that touch the codebase (e.g., `design-md-to-app`, `module-add`) write directly to root paths, and update `meta.json` at the end.
3. **Files are written incrementally**. A skill writes only the files in its scope. Skills do NOT delete files written by other skills.
4. **`meta.json` is the single source of truth** for the project's current state. Every skill that runs must read `meta.json` first and update it last.
5. **File names are case-sensitive and exact**: `PROJECT.md` (not `project.md`), `PRD.md`, `DESIGN.md`, `tasks.md`, `meta.json`.

## `meta.json` schema

```json
{
  "project_slug": "wisely",
  "project_name": "Wisely",
  "created_at": "2026-04-25T17:00:00Z",
  "updated_at": "2026-04-25T18:00:00Z",
  "phase": "module_added",
  "stack": {
    "framework": "next",
    "ui": "shadcn",
    "auth": "better-auth",
    "db": "neon-drizzle",
    "payments": null,
    "deploy": "vercel"
  },
  "history": [
    {
      "skill": "prd-from-idea",
      "ran_at": "2026-04-25T17:05:00Z",
      "outputs": ["PROJECT.md", "PRD.md"],
      "phase_before": "empty",
      "phase_after": "prd_drafted"
    },
    {
      "skill": "image-to-design-md",
      "ran_at": "2026-04-25T17:18:00Z",
      "inputs": { "image_count": 3 },
      "outputs": ["DESIGN.md", "screenshots/"],
      "phase_before": "prd_drafted",
      "phase_after": "design_extracted"
    }
  ]
}
```

### Field-by-field

| Field | Type | Notes |
|---|---|---|
| `project_slug` | string | Filesystem-safe slug derived from `project_name`. Used for git branches, `app/` directory naming in some templates. |
| `project_name` | string | Human-readable name. |
| `created_at` / `updated_at` | ISO-8601 UTC | Updated on every skill run. |
| `phase` | enum (see below) | Monotonic — phases never regress. |
| `stack` | object | Pinned tech choices. `null` for "not yet decided". |
| `history` | array | Append-only log of skill runs. |

### `phase` enum (canonical)

The `phase` field tracks the project's progress through the pipeline. **Monotonic** in the order below — a skill never sets phase to an earlier value.

| Phase | Set by | Ready for next skill |
|---|---|---|
| `empty` | `init_workflow.py` | `prd-from-idea` |
| `idea_captured` | `prd-from-idea` (PROJECT.md only) | `prd-from-idea` (to expand) or `design-md-to-app` (skip if simple) |
| `prd_drafted` | `prd-from-idea` (PRD.md written) | `prd-to-tasks`, `figma-to-design-md`, `image-to-design-md`, or `design-md-to-app` |
| `tasks_split` | `prd-to-tasks` | `figma-to-design-md` / `image-to-design-md` / `design-md-to-app` |
| `design_extracted` | `figma-to-design-md` / `image-to-design-md` / manual import | `design-md-to-app` |
| `scaffolded` | `design-md-to-app` | `screenshot-to-page`, `module-add` |
| `page_generated` | `screenshot-to-page` | `module-add`, more `screenshot-to-page` |
| `module_added` | `module-add` | iterate (no terminal state) |

If a skill encounters an unknown phase value, it must NOT crash — it logs a warning and treats it as `empty` for routing purposes. New phases can be added; old skills will simply skip them.

### `stack` field

Pinned tech choices that downstream skills consume. Keys:

- `framework`: `"next"` | `"vite-react"` | `"remix"` | `"astro"` | string
- `ui`: `"shadcn"` | `"mui"` | `"chakra"` | string
- `auth`: `"better-auth"` | `"clerk"` | `"next-auth"` | `null`
- `db`: `"neon-drizzle"` | `"supabase"` | `"planetscale-prisma"` | `null`
- `payments`: `"stripe"` | `"lemon-squeezy"` | `null`
- `deploy`: `"vercel"` | `"fly"` | `"cloudflare-pages"` | `null`

Use `null` (not `"none"`) for "not decided yet".

### `history` entry shape

```json
{
  "skill": "module-add",
  "ran_at": "2026-04-25T18:00:00Z",
  "inputs": { "module": "auth", "tech": "better-auth" },
  "outputs": ["lib/auth.ts", "lib/auth-client.ts", "app/api/auth/[...all]/route.ts"],
  "phase_before": "scaffolded",
  "phase_after": "module_added"
}
```

`inputs` and `outputs` are free-form per-skill; the only required keys on every entry are `skill`, `ran_at`, `phase_before`, `phase_after`.

## File-format conventions

### `PROJECT.md`
Free-form prose, one h1 (the project name). Sections expected: **Overview**, **Audience**, **Problem & current alternatives**, **Value proposition**, **Success criteria**, **Out of scope** (optional). Written by `prd-from-idea`.

### `PRD.md`
Free-form prose. Sections: **Problem**, **Solution overview**, **User stories** (`As a … I want …`), **Non-goals**, **Technical constraints**, **Open questions**. Written by `prd-from-idea`.

### `tasks.md`
A checklist compatible with beads / GitHub Issues / Linear import. Each task is a `## ` heading with a body, plus a `- [ ]` line for status. Written by `prd-to-tasks`.

### `DESIGN.md`
Strictly conformant to the [Google design.md spec](https://github.com/google-labs-code/design.md). YAML frontmatter (colors / typography / rounded / spacing / components) + 8 sections in order: Overview, Colors, Typography, Layout, Elevation & Depth, Shapes, Components, Do's and Don'ts. Written by `figma-to-design-md` / `image-to-design-md`, or by hand.

### `screenshots/`
Raw screenshots of the UI for reference. Filenames are slugged page names (`home-hero.png`, `pricing-comparison.png`). Owned by the design-extraction skills and consumable by `screenshot-to-page`.

## Codebase ownership zones

Two non-overlapping write zones:

| Zone | Owner skills |
|---|---|
| `<project-root>/.workflow/` | `prd-from-idea`, `prd-to-tasks`, `figma-to-design-md`, `image-to-design-md`, `dev-flow`. Plus, every skill updates `.workflow/meta.json#history`. |
| `<project-root>/` (everything else: `package.json`, `app/`, `components/`, `lib/`, etc.) | `design-md-to-app`, `screenshot-to-page`, `module-add`. |

A skill that modifies BOTH zones (e.g., `design-md-to-app` writes the codebase AND updates `meta.json`) writes codebase files first, then `meta.json` last. This guarantees that if a run is interrupted, the state in `meta.json` is consistent with what's on disk.

## Bootstrapping order

The codebase doesn't exist until `design-md-to-app` runs. Until then, the project root contains only `.workflow/` (and possibly a `.git/` if the user initialized one). When `design-md-to-app` runs `pnpm create next-app .` it scaffolds **into the project root**, alongside `.workflow/`. `.workflow/` does not interfere with framework scaffolders because no file there clashes with their expected entry points (`package.json`, `app/`, `src/`, `vite.config.ts`).

If the framework scaffolder refuses to write into a non-empty directory (some versions do), the workaround is: scaffold to a temp dir, then `mv temp/* temp/.* <project-root>/` skipping `.workflow/`.

## Backwards compatibility

If a skill encounters a `meta.json` with an unknown `phase` value, it MUST NOT crash — it logs a warning and treats it as `empty` for routing purposes. New phases can be added; old skills will simply skip them.

If a skill encounters fields in `meta.json` it doesn't recognize, it MUST preserve them verbatim when rewriting the file.

## Anti-patterns

- ❌ Putting the codebase inside `.workflow/`. The codebase is at the project root.
- ❌ Skipping `meta.json` updates. Without history, the orchestrator can't reason about what's been done.
- ❌ Setting `phase` to an earlier value than its current state. Phases are monotonic.
- ❌ Writing across both zones (`.workflow/` + codebase) without finishing one before the other.
- ❌ Inventing meta-fields. Stick to the schema; if you need new state, propose an extension.
