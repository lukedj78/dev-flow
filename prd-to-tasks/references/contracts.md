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

### `phase` enum (canonical)

The `phase` field tracks the project's progress through the pipeline. Every skill must set this correctly.

| `phase` value | When set | Ready for next skill |
|---|---|---|
| `empty` | `.workflow/` was just created, only `meta.json` exists | `prd-from-idea` |
| `idea_captured` | `PROJECT.md` exists | `prd-from-idea` (to expand into PRD) or `design-md-to-app` (skip if simple) |
| `prd_drafted` | `PRD.md` exists | `prd-to-tasks`, `figma-to-design-md`, `image-to-design-md`, or `design-md-to-app` |
| `tasks_split` | `tasks.md` exists | `figma-to-design-md`, `image-to-design-md`, or `design-md-to-app` |
| `design_extracted` | `DESIGN.md` + (optional) `screenshots/` exist | `design-md-to-app` |
| `scaffolded` | `app/` exists with framework + UI library installed | `screenshot-to-page`, `module-add` |
| `page_generated` | At least one route in `app/` is implemented from a screenshot or PRD | `module-add`, more `screenshot-to-page` runs |
| `module-added` | Auth/DB/payments/etc. wired up | iterative — repeat as needed |

**Phase progression is monotonic in the list above** — a skill should never set `phase` to an earlier value than what it found. If a skill is re-run (e.g., user re-extracts design from a new Figma), it appends to `history` but keeps the phase ≥ the current one.

### `stack` field

Captures user choices that downstream skills need. Keys:

- `framework`: `"next"` | `"vite-react"` | `"remix"` | `"astro"` | `"sveltekit"` | string
- `ui`: `"shadcn"` | `"mui"` | `"chakra"` | `"radix-vanilla"` | string
- `auth`: `"better-auth"` | `"next-auth"` | `"clerk"` | `"supabase-auth"` | `null`
- `db`: `"neon-drizzle"` | `"supabase"` | `"planetscale-prisma"` | `null`
- `payments`: `"stripe"` | `"lemon-squeezy"` | `null`
- `deploy`: `"vercel"` | `"fly"` | `"cloudflare-pages"` | `null`

Use `null` (not `"none"`) when not yet decided.

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
