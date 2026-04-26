# dev-flow

> An end-to-end product-development workflow built on **8 atomic Claude Code skills**.
> From a paragraph of idea to a runnable, themed Next.js app — with a single shared filesystem contract.

```
idea  →  PRD  →  tasks  →  DESIGN.md  →  scaffold  →  pages  →  modules
        │              │              │              │              │
        prd-from-idea  prd-to-tasks   figma- /       design-       module-
                                      image-to-      md-to-app     add
                                      design-md
                                                     │
                                                     screenshot-to-page
```

---

## Why dev-flow

Building a real product from scratch is a sequence of distinct, well-understood activities — capturing the idea, producing requirements, designing the visual system, scaffolding the codebase, building pages, wiring modules. **dev-flow doesn't reinvent any of these activities.** It pins them as 8 small, opinionated, atomic skills that share one filesystem contract, so you (or the AI) can move forward one step at a time without losing context.

The contract is `.workflow/` — a single hidden folder at your project root that holds planning + design metadata. Every skill reads `meta.json` first, writes its outputs in `.workflow/` or in the codebase, then bumps the phase. That's the entire orchestration model.

---

## Quick start (5 minutes)

### 1. Install the skills

Pick whichever fits your setup — they all end up at `~/.claude/skills/<name>/` :

#### Option A — bundled `install.sh` (recommended for this repo)

```bash
git clone git@github.com:lukedj78/dev-flow.git
cd dev-flow
./install.sh
```

The script copies the 8 skill folders into `$CLAUDE_SKILLS_DIR` (defaults to `~/.claude/skills`), backing up any pre-existing version with the same name to `<skill>.bak`. To uninstall + restore backups: `./uninstall.sh`.

#### Option B — Claude Code `/plugin add` (interactive)

If you have the repo cloned locally:

```
/plugin add /path/to/dev-flow/dev-flow
/plugin add /path/to/dev-flow/prd-from-idea
…
```

Run once per skill folder. Useful if you only want to install a subset.

#### Option C — `gh skill install` (GitHub CLI extension)

```bash
gh extension install <ext-author>/gh-skill          # one-time
gh skill install lukedj78/dev-flow                   # private repo, requires auth
# OR for a specific subset
gh skill install lukedj78/dev-flow dev-flow design-md-to-app
```

This works with the same `gh auth` you already use to clone private repos.

#### Option D — drag-and-drop the `.skill` files

The `dist/` folder contains all 8 packaged `.skill` archives. Drag them into your Claude Code window one at a time — useful when you don't have shell access on the target machine.

#### Verify

```bash
ls ~/.claude/skills/ | grep -E "dev-flow|prd-|figma-|image-|design-|screenshot-|module-"
# Should print 8 entries. Restart Claude Code if you don't see them in /skills.
```

The 8 skills are:

| Skill | What it does |
|---|---|
| **`dev-flow`** | The orchestrator — reads `.workflow/meta.json` and proposes what to do next |
| `prd-from-idea` | Idea paragraph → `PROJECT.md` + `PRD.md` |
| `prd-to-tasks` | `PRD.md` → `tasks.md` (importable into beads / Linear / GitHub Issues) |
| `figma-to-design-md` | Figma URL → `DESIGN.md` (Google design.md spec) + screenshots |
| `image-to-design-md` | 1+ raster images → `DESIGN.md` + screenshots |
| `design-md-to-app` | `DESIGN.md` → scaffolded Next.js + shadcn app with theme + showcase + folder convention |
| `screenshot-to-page` | One screenshot → one route, with pixel-perfect verification loop |
| `module-add` | Wire `auth` / `db` / `payments` / `email` / `storage` / `deploy` modules |

### 2. Create a project

```bash
mkdir -p ~/projects/my-app && cd ~/projects/my-app
```

### 3. Open Claude Code in that directory and say:

> *"Voglio costruire un CRM per studi notarili italiani. Anagrafica clienti, pratiche, scadenze, archivio documentale."*

The orchestrator (`dev-flow`) will:
1. Create `.workflow/meta.json`.
2. Invoke `prd-from-idea` → `PROJECT.md` + `PRD.md`.
3. Ask if you have a Figma / images / want to write the DESIGN.md by hand.
4. Invoke the right design-extraction skill → `.workflow/DESIGN.md`.
5. Ask for stack choice (Next + shadcn is the default).
6. Invoke `design-md-to-app` → fully scaffolded codebase + showcase.
7. Optionally invoke `screenshot-to-page` for routes from your screenshots.
8. Optionally invoke `module-add` for db / auth / etc.

By the end you have a runnable Next.js app at the project root, with a `.workflow/` folder that documents every decision.

---

## Documentation

- 📐 **[Architecture](./docs/architecture.md)** — the `.workflow/` contract, the `meta.json` schema, the phase enum, file conventions.
- 🛠 **[Conventions](./docs/conventions.md)** — folder layout (`components/site/` vs `app/<route>/_components/`), server actions in `lib/server/<domain>`, theme system with keyboard shortcut, showcase template.
- 📚 **[Case studies](./docs/case-studies.md)** — three projects built with the suite (Aetherfield editorial, Notarius CRM, Wisely fintech). Each shows which skills were used and what was generated.

---

## The 8 skills, in detail

### `dev-flow` — the orchestrator

**When to use it:** when you want to *not* think about which skill comes next. Paste an idea / a Figma URL / images, and `dev-flow` figures out the right specialist to invoke based on `phase` in `meta.json`.

```
phase=empty            → prd-from-idea
phase=idea_captured    → prd-from-idea (expand)
phase=prd_drafted      → prd-to-tasks  OR  figma-to-design-md  OR  image-to-design-md  OR  design-md-to-app
phase=tasks_split      → figma-to-design-md  OR  image-to-design-md  OR  design-md-to-app
phase=design_extracted → design-md-to-app
phase=scaffolded       → screenshot-to-page  OR  module-add
phase=page_generated   → module-add  OR  more screenshot-to-page
phase=module-added     → iterate
```

`dev-flow` does not do specialist work itself — it **only routes** and updates state. If you find it doing PRD drafting or scaffolding directly, that's a bug.

**Bundled scripts:**
- `scripts/init_workflow.py <project-root> [--name "Project Name"]` — creates `.workflow/` with a fresh `meta.json`.
- `scripts/show_state.py <project-root>` — prints current phase, files present, proposed next step.

### `prd-from-idea` — paragraph → PRD

**Input**: a paragraph or two describing what you want to build.
**Output**:
- `.workflow/PROJECT.md` — strategic brief (audience, problem, value prop, success criteria).
- `.workflow/PRD.md` — product requirements (user stories, acceptance criteria, non-goals, open questions).

**How it works**: the skill asks you 5–8 high-leverage questions, parses your answer, fills the templates. It refuses to invent: if you can't answer "who is this for", it writes `<TBD — needs user input>` rather than guess.

### `prd-to-tasks` — PRD → executable checklist

**Input**: `.workflow/PRD.md` (and `.workflow/PROJECT.md` for context).
**Output**: `.workflow/tasks.md` with 1 task per `- [ ]` checkbox. Compatible with **beads**, **GitHub Issues import**, **Linear CSV**, **ralph-tui**.

**Sizing**: each task ≈ 2–8 hours of focused work. If a task is bigger, the skill splits it. If smaller, it merges with a sibling. Output ≤ ~15 tasks for an MVP.

### `figma-to-design-md` — Figma → DESIGN.md

**Input**: a Figma URL (`figma.com/file/`, `/design/`, `/proto/`, `/board/`, `/site/`).
**Output**: `.workflow/DESIGN.md` (Google design.md spec) + `.workflow/screenshots/` (HD captures).

**3 access paths, picked automatically**:
- **A — Figma Dev Mode MCP**, if a `mcp__figma*` tool is exposed.
- **B — Figma REST API**, if a `FIGMA_ACCESS_TOKEN` env var is set.
- **C — Manual / Playwright-assisted**, if a browser tool is available; falls back to asking the user for screenshots.

The skill validates the output against the Google spec before writing (frontmatter delimited correctly, `colors.primary` defined, no duplicate sections, dimensions in `px/em/rem` only, all `{path.to.token}` references resolve).

### `image-to-design-md` — 1+ raster images → DESIGN.md

**Input**: 1 or more PNG / JPG / WebP images (screenshots of competitor apps, Pinterest pins, Dribbble shots, Figma exports).
**Output**: `.workflow/DESIGN.md` + `.workflow/screenshots/<slug>.png` for each image.

**How it works**:
- **Palette**: k-means quantization on the cropped pixels (`scripts/quantize_palette.py`); when there are multiple images, `scripts/aggregate_palettes.py` merges near-duplicates and rewards colors that recur across screens.
- **Typography**: vision-LLM identifies font lookalike + estimates sizes / weights / line-heights from pixel measurements. Proprietary fonts (Söhne, Wise Sans, Cera Pro) are recognized AND mapped to a Google Fonts open-source fallback that the DESIGN.md emits as `fontFamily`.
- **Components**: vision-LLM detects buttons / cards / inputs / nav / badges; emits the `components` block with the variants seen.
- **Layout / shapes / elevation**: inferred from corners + spacing + shadow patterns visible in the images.

The skill is explicit about confidence: every guess is flagged in the prose. A 1-image input where text isn't visible produces a stub `typography:` block + a prominent note ("typography pending — supply a second image with visible text").

### `design-md-to-app` — DESIGN.md → working app

**Input**: `.workflow/DESIGN.md` + `.workflow/meta.json#stack`.
**Output**: a fully scaffolded codebase at the project root (NOT inside `.workflow/`), with:

- Framework installed (Next.js + Tailwind v4 by default; Vite + React, Remix, Astro variants supported via `references/<framework>-<ui>.md`).
- shadcn/ui via the **token-first registry approach**: emits `<root>/registry.json` from DESIGN.md, runs `pnpm dlx shadcn@latest init ./registry.json --yes`, then `pnpm dlx shadcn@latest add --all --yes`. Every primitive lands in `components/ui/` pre-themed.
- **Theme system**: `next-themes` + `<ThemeProvider>` + a `<ModeToggle>` button with a global `D` keyboard shortcut (excluded when typing in inputs).
- **Folder skeleton**: `components/<group>/` for cross-route shared, `app/<route>/_components/` for page-scoped, `lib/server/<domain>.ts` for server actions, `lib/queries/<domain>.ts` for reads, `hooks/`.
- **Site-shell components**: `SiteTopNav`, `WordmarkFooter`, `MarketingShell` for public pages; `AppShell` for authenticated routes; `Eyebrow` helper.
- **`/showcase` route**: a 9-section design-system documentation page (Color tokens, Typography ladder, Buttons, Cards, Inputs, Badges, Radius, Spacing, Do's/Don'ts) — non-skippable in dev-flow mode.
- **Placeholder routes** for every nav item declared in DESIGN.md / screenshots / PRD, so no link goes to `/_not-found`.
- **Server actions stub**: at least one `lib/server/<domain>.ts` with Zod schemas + `ActionResult<T>` discriminated union + `flattenZod` helper, as a referenceable pattern.

The structure is mandatory in dev-flow mode — see [docs/conventions.md](./docs/conventions.md).

### `screenshot-to-page` — screenshot → working route

**Input**: one image from `.workflow/screenshots/` + `DESIGN.md` + `meta.json#stack`.
**Output**: a real route in the codebase (`app/<route>/page.tsx`) with extracted reusable components.

**Workflow**:
1. **Pattern detection**: scan the screenshot for repeated visual patterns (3 cards same shape → extract one `<Card>` + map; 5 nav items → extract `<NavItem>`).
2. **Map to design system**: every color / radius / spacing must reference a DESIGN.md token. If you need a value that doesn't exist, the skill asks before adding.
3. **Pixel-perfect loop** (when a browser tool is available): build → take screenshot at the same viewport → diff vs. reference (`scripts/visual_diff.py`) → fix the worst region → repeat until delta < 2% (or 8 iterations).
4. Imagery is left as `bg-muted` placeholders with `{/* TODO: replace */}` comments — the skill doesn't fabricate photography.

### `module-add` — wire backend / infra modules

**Input**: a module name (`auth` / `db` / `payments` / `email` / `storage` / `deploy`).
**Output**: dependencies installed, config files written, a reference implementation at the canonical path, `meta.json#stack` updated.

**Currently shipped variants** (see `references/`):
- `module-auth.md` — better-auth with Drizzle adapter, email/password + magic-link.
- `module-db.md` — Drizzle ORM + Neon Postgres.
- `module-stubs.md` — scaffolding cues for Stripe payments / Resend email / UploadThing storage / Vercel deploy.

The skill is **idempotent**: re-running `module-add db` on a project that already has it detects the install and skips, instead of double-installing.

---

## How the skills compose

A typical "from scratch to running app" session uses the skills in this order:

```
1. dev-flow             → init `.workflow/` + ask the user what they want to build
2. prd-from-idea        → PROJECT.md + PRD.md
3. prd-to-tasks         → tasks.md (optional)
4. figma-to-design-md   → DESIGN.md + screenshots/
   OR
   image-to-design-md   → DESIGN.md + screenshots/
   OR
   manual               → user pastes their own DESIGN.md
5. design-md-to-app     → scaffolded codebase + theme + showcase + placeholder routes
6. screenshot-to-page   → for each screenshot, generate a real route (loop)
7. module-add db        → Drizzle + Neon
8. module-add auth      → better-auth
9. module-add (others)  → payments / email / storage / deploy as needed
```

Or in one sentence:

> **An idea → a working, themed, branded Next.js app with theme toggle, server actions, db, auth, and 12 routes — all driven by 8 small skills sharing one `.workflow/` folder.**

---

## Anatomy of `.workflow/`

```
<project-root>/                   ← codebase root (Next/Vite/Remix)
├── .workflow/                    ← planning + design metadata
│   ├── meta.json                 ← single source of truth
│   ├── PROJECT.md                ← high-level brief
│   ├── PRD.md                    ← requirements
│   ├── tasks.md                  ← task breakdown
│   ├── DESIGN.md                 ← Google design.md spec
│   └── screenshots/              ← raw / annotated UI references
├── package.json                  ← codebase at root
├── app/, components/, lib/       ← framework conventions
├── registry.json                 ← shadcn token registry
└── …
```

`meta.json` schema (excerpt):

```json
{
  "project_slug": "wisely",
  "project_name": "Wisely",
  "phase": "module-added",
  "stack": {
    "framework": "next",
    "ui": "shadcn",
    "auth": "better-auth",
    "db": "neon-drizzle"
  },
  "history": [
    { "skill": "prd-from-idea", "phase_after": "prd_drafted", "ran_at": "..." },
    { "skill": "image-to-design-md", "phase_after": "design_extracted", "ran_at": "..." },
    { "skill": "design-md-to-app", "phase_after": "scaffolded", "ran_at": "..." },
    { "skill": "module-add", "phase_after": "module-added", "inputs": { "module": "db" } },
    { "skill": "module-add", "phase_after": "module-added", "inputs": { "module": "auth" } }
  ]
}
```

The full schema is in [docs/architecture.md](./docs/architecture.md).

---

## When you'd skip a skill

| You have | Skip |
|---|---|
| A DESIGN.md already written | `figma-to-design-md` + `image-to-design-md`. Just `cp` your file into `.workflow/`. |
| A Figma file | `image-to-design-md`. Use Figma path B (REST API with token) for highest precision. |
| Only inspiration images | `figma-to-design-md`. Use `image-to-design-md` instead. |
| A scaffold already running | `design-md-to-app`. Theme-only mode applies a DESIGN.md to existing code. |
| No screenshots | `screenshot-to-page`. Hand-write the routes. |
| No backend yet | `module-add`. Stays empty until the user wants persistence. |

---

## What's intentionally NOT in dev-flow

- A code-generation tool that writes business logic for you. The skills generate **structure + conventions + first-pass UI**. Business logic stays human.
- A CMS. Content layer is project-specific.
- Hosting. `module-add deploy` produces config; the actual deploy is your call.
- Analytics / observability. Too project-specific to template.

---

## What comes next — when dev-flow hands you the keys

When the skills are done, you have:

- A scaffolded app with routing, theme system, dark/light toggle, server-action conventions.
- A `/showcase` page proving the design system landed.
- (Optionally) auth, db, tests, CI wired up via `module-add`.
- A `lib/server/<domain>.ts` reference action that you can copy-evolve.

What dev-flow does **not** do — these are your work as the developer:

1. **Real business logic.** The server-action template returns mock data. You write the actual mutations (`db.insert(...)`, `db.update(...)`) for your domain.
2. **Real forms wired to the actions.** The scaffold ships one stub form per declared route. You bind real inputs, real Zod schemas, real `useFormState` (or React 19's `useActionState`) per page.
3. **Production env vars.** `.env.local.example` is a checklist — fill `.env.local` with real values from your Neon/Vercel/Stripe dashboards.
4. **Migrations to a real DB.** Switch from `pnpm db:push` to `pnpm db:generate` + commit + `pnpm db:migrate` once you have data that matters.
5. **Tightening the CSP.** `next.config.ts` ships a permissive default Content-Security-Policy. Tighten it as you remove inline scripts/styles.
6. **Real photography / iconography.** Image placeholders are `bg-muted` divs with `TODO` comments. Replace with `next/image` + your CDN.
7. **Test coverage.** `module-add test` ships smoke tests. Real coverage (unit + integration + E2E for critical flows) is yours.
8. **A11y audit.** The scaffold passes basic checks (semantic landmarks, focus rings, reduced-motion). Run axe-core or Lighthouse on every shipped page before launch.

If any of these feel too big to tackle alone, dev-flow's siblings ([screenshot-to-page](./screenshot-to-page) for new pages, `module-add` for new infra) keep working — call them again whenever you need a fresh page or a new module.

---

## Contributing

The skills are **plain folders** with a `SKILL.md` + `references/` + optional `scripts/`. To add a new skill or modify an existing one, follow the [skill-creator](https://github.com/anthropics/skills) conventions and contribute via PR.

To add a new module variant to `module-add` (e.g., Clerk auth, Supabase db), drop a new `references/module-<name>.md` following the same pattern as `module-auth.md` / `module-db.md`. The orchestrator picks it up automatically.

---

## License

MIT — see [LICENSE](./LICENSE).
