# `.workflow/` — Contract between dev-flow skills

This document defines the **canonical contract** that all skills in the dev-flow family must respect. It is the load-bearing piece of the architecture: skills know nothing about each other, but they all read and write `.workflow/` in the same way.

> Living version: this file. Skills that need to consult the contract should read **this exact file** (vendor a copy into their `references/` if standalone) — do not paraphrase from memory.

## Knowledge principle — doc-grounded, never invent (rule zero)

The skills are a **second brain**: authoritative, doc-grounded knowledge of the domains we build in, so we act as **experts and never improvise an API**. This governs how every skill is written and used:

1. **Never invent.** Do not guess an API, flag, config shape, file path, or command. If the skill states it, it must be **grounded in the official documentation** (or the installed source, e.g. `node_modules/<pkg>`), not memory.
2. **Prefer the version-matched source the tool itself gives you.** Upstreams increasingly ship their docs *to* the agent: `next dev` writes and maintains a version-matched `AGENTS.md` block pointing at the docs bundled in `node_modules`, and eve ships its docs at `node_modules/eve/docs/`. Read those first — they match the installed version, which a web page may not. (Vercel retired its own doc-shipping skills once this landed; the lesson for us is that **a skill must encode workflow and conventions, never a frozen copy of someone's documentation** — that part rots.) ⚠️ **Don't clobber that block**: `next dev` upserts it into the project's `AGENTS.md` *and* `CLAUDE.md` between `<!-- BEGIN:nextjs-agent-rules -->` markers and preserves everything outside them — so any dev-flow bootstrap file **merges**, never overwrites, and never edits inside the markers. (`create-next-app` generates both files; `agentRules: false` opts out.)
3. **If we don't have the knowledge, get it.** When a skill says "use library X", it must also document **how** — the real setup + usage from X's official docs — so we don't scaffold something wrong and redo it later. A bare "use X" without the how-to is an incomplete skill. When the knowledge isn't in the skill yet, consult the official online docs *before* writing code, then capture what you learned back into the skill.
4. **Mark the moving surface `[VERIFY]`.** Any identifier from a fast-moving or beta upstream (eve, next-intl, shadcn CLI, Expo SDK, Motion, Stripe apiVersion, …) carries a `[VERIFY]` note to check against the installed version — because docs move (e.g. next-intl renamed `middleware.ts` → `proxy.ts`).
5. **Update periodically.** Upstreams change; the knowledge base must keep pace. Run the ecosystem watch (`docs/vercel-changelog-watch.md` and the per-skill audit recipes) on a cadence, apply what changed, and log it. Stale docs-grounding is a bug.

Reference material (`references/*.md`) exists to satisfy #3 — every "use X" default in this contract points at a doc-grounded how-to, not just a name. **`docs/knowledge-index.md` is the map of them all**: which domains we're expert in, where each how-to lives, and which upstream to re-verify when it moves. Read it before wiring a library; walk it when running a periodic refresh; **add a row whenever you introduce a new "use X" default**.

## Golden rules (all projects, all stacks)

Two non-negotiable rules every dev-flow skill enforces, regardless of the user's or team's spoken language:

1. **Code is written in English.** Every code identifier — functions, variables, constants, types, enums, file/folder names, DB columns, API field names, commit messages — **and all code comments** are in English, always. This holds even when the user converses in another language (e.g. Italian): the conversation language and the code language are independent. English code stays portable, greppable, and consistent across contributors and tools. The one thing that is *not* English-by-default is **user-facing copy** — that goes through i18n (rule 2), never hardcoded.

2. **Every frontend ships i18n from day one.** No user-facing string is ever hardcoded; all visible copy (labels, buttons, errors, empty states, emails) routes through i18n keys. The minimum locale set is **English + Italian** (`stack.locales = ["en", "it"]`, default locale `en`); a project may declare more, decided per project. The library:
   - **Web (Next.js App Router)** → **[next-intl](https://next-intl.dev/)** (`stack.i18n = "next-intl"`), the canonical default. **The doc-grounded how-to is `design-md-to-app/references/i18n-next-intl.md`** (routing vs no-routing modes, `routing.ts`/`navigation.ts`/`proxy.ts`/`request.ts`, `[locale]` layout with `setRequestLocale` + `generateStaticParams`, `messages/{en,it}.json`, server vs client usage) — read it, don't reinvent the setup. Wired at scaffold time by `design-md-to-app`; the `forms` skill routes all form copy through it.
   - **Mobile (Expo/RN)** → the RN i18n stack (e.g. `i18next` + `expo-localization`) — next-intl is web-only.
   Record both `stack.i18n` and `stack.locales` in `meta.json`. Adding i18n later touches every screen, so it is set up **at scaffold**, not deferred.

These are recorded in the `stack` block (`i18n`, `locales`) and treated as defaults, not questions — skip asking; only confirm extra locales beyond en/it.

### Recommended default libraries (ecosystem-first)

When a project needs one of these capabilities, reach for the default below instead of hand-rolling or picking ad-hoc — the same ecosystem-first rule used everywhere in dev-flow. Not every project needs them; these are the defaults **when** it does.

| Capability | Web default | Mobile default |
|---|---|---|
| **Maps** | **[mapcn](https://mapcn.dev/)** — MapLibre GL, shadcn-registry. How-to: `design-md-to-app/references/maps-mapcn.md` (⚠️ CARTO default tiles need an Enterprise license for commercial use). `stack.maps = "mapcn"`. | **[mapcn-rn](https://mapcn-rn.dev/)** — MapLibre/Mapbox RN + NativeWind. How-to: `rn-components-apis/references/maps-mapcn-rn.md` (⚠️ native modules → dev build, not Expo Go). `stack.maps = "mapcn-rn"`. |
| **File / blob storage** | **Vercel Blob** (`@vercel/blob`) when deploying to Vercel — same platform, one less sub-processor. UploadThing / S3 only on request. How-to: `module-add/references/module-storage.md`. `stack.storage = "vercel-blob"`. | provider-side (`supabase` / `firebase` / custom) via `rn-module-add` |
| **Illustration / spot art** | **[Koboyo](https://koboyo.com/icons)** — 71k hand-drawn SVGs, free commercially, found via its MCP server. ⚠️ **Use sparingly and only when DESIGN.md admits it**; the licence forbids products where the art *is* the feature. How-to: `design-md-to-app/references/illustrations.md`. | same source, vendored as SVG |
| **Animated icons** | `heroicons-animated` (skill) | `rn-animations-gestures` |
| **Motion** | `transitions` + `module-add motion` | `rn-animations-gestures` |
| **Forms** | `forms` (`stack.forms`) | RN form stack |

Per the **Knowledge principle**, each of these defaults must ship (or point at) a **doc-grounded how-to** — not just a name — before it's used to scaffold; `[VERIFY]` install command + license + API against the official site each time (docs move). These are starting defaults; a project may override with a documented reason.

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
    "deploy": "vercel",
    "agent": null
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

### `linear` and `scrum` fields (optional, owned by `linear-scrum`)

Present once a project is taken into Linear. Written only by the `linear-scrum` skill; other skills must not touch them.

```json
"linear": {
  "team_id": "…", "team_name": "…", "project_id": "…", "url": "…",
  "issue_map": { "<task_key>": "LUC-123" },
  "last_synced_at": "<ISO-8601 UTC>"
},
"scrum": {
  "cadence_weeks": 2, "estimate_scale": "fibonacci", "velocity_target": null,
  "states": { "backlog": "Backlog", "todo": "Todo", "in_progress": "In Progress",
              "in_review": "In Review", "done": "Done", "blocked_label": "blocked" },
  "labels": { "web": "frontend", "agent": "agent-eve", "scaffold": "setup" }
}
```

`issue_map` keys are `task_key()` digests of `tasks.md` lines (see `linear-scrum/scripts/task_key.py`) so re-syncing never duplicates issues. Linear is the source of truth for status/ordering/estimates after Setup; `tasks.md` stays the append-only intake for new work.

### `phase` enum (canonical)

The `phase` field tracks the project's progress through the pipeline. Every skill must set this correctly.

**All phase values are `snake_case` strings**. The canonical list below is the complete enum; skills MUST NOT use values outside it. Unknown values are treated as `empty` (forward-compatibility).

| `phase` value | Stacks | When set | Ready for next skill |
|---|---|---|---|
| `empty` | all | `.workflow/` was just created, only `meta.json` exists | `prd-from-idea` |
| `idea_captured` | all | `PROJECT.md` exists | `prd-from-idea` (to expand into PRD) or scaffold (skip if simple) |
| `prd_drafted` | all | `PRD.md` exists | `prd-to-tasks`, `figma-to-design-md`, `image-to-design-md`, or scaffold |
| `tasks_split` | all | `tasks.md` exists | `figma-to-design-md`, `image-to-design-md`, or scaffold |
| `design_extracted` | all | `DESIGN.md` + (optional) `screenshots/` exist | scaffold (`design-md-to-app` for web, `rn-bootstrap` for mobile, `monorepo-bootstrap` for monorepo) |
| `monorepo_initialized` | **monorepo only** | turborepo root exists (`pnpm-workspace.yaml` + `turbo.json`), before the apps are scaffolded | `monorepo-bootstrap` continues — scaffolds `apps/web` (`design-md-to-app`), `apps/mobile` (`rn-bootstrap`), and/or `apps/agent` (`eve-agent`) |
| `scaffolded` | all | `app/` exists with framework + UI library installed | next-stack-skill (`screenshot-to-page` web / `rn-add-screen` mobile) or `module-add` / `rn-module-add` |
| `page_generated` | all | At least one route is implemented from a screenshot or PRD | `module-add` / `rn-module-add`, more screen-gen runs |
| `module_added` | all | Auth/DB/payments/etc. wired up | iterative — repeat as needed; leads to `feature_complete` when the build is done (all stacks) |
| `feature_complete` | all | All planned features built and tested; ready to ship | pre-deploy gate `compliance-audit`, then deploy: web → `vercel-deploy`, mobile → `rn-eas-deploy`, agent → `eve deploy` |
| `deployed` | all | Live in production (web on Vercel / mobile on App Store + Play Store / agent via `eve deploy`) | maintenance loop (web: `screenshot-to-page` / `module-add`; mobile: `rn-add-screen` / `rn-eas-build-submit-update`; re-run `compliance-audit` after material changes) |

**Notes**:
- All values are `snake_case` (e.g., `module_added` NOT `module-added`). Skills that use the kebab-case variant are non-conforming and should be migrated.
- The `feature_complete` and `deployed` phases are **cross-stack** (web, mobile, agent, monorepo). A web or agent project stays iterating at `module_added` and advances to `feature_complete` when the user declares the build done — at which point dev-flow proposes the `compliance-audit` pre-deploy gate and then the stack's deploy skill. `monorepo_initialized` is **monorepo-only** (a mid-`monorepo-bootstrap` checkpoint before the apps are scaffolded).
- **Phase progression is monotonic** — a skill should never set `phase` to an earlier value than what it found. If a skill is re-run (e.g., user re-extracts design from a new Figma), it appends to `history` but keeps the phase ≥ the current one.
- The `deployed` phase is terminal in the sense that future runs stay there; subsequent EAS Update or new-feature work appends to `history` without phase regression.

### `stack` field

Captures user choices that downstream skills need. Keys:

- `framework`: `"next"` | `"vite-react"` | `"remix"` | `"astro"` | `"sveltekit"` | `"expo-rn"` | `"monorepo"` (planned) | string
- `ui`: `"shadcn"` | `"base-ui"` | `"coss"` | `"mui"` | `"chakra"` | `"radix-vanilla"` | `"nativewind"` (mobile) | string. **Note**: `"base-ui"` here means *standalone* Base UI (headless library, no shadcn CLI). With shadcn CLI v4 you can also run shadcn **on top of** Base UI — that is `ui="shadcn"` + `ui_base="base"` (below), and is usually the better way to get "shadcn philosophy on Base UI" because you keep the shadcn component set + blocks. `"coss"` = **Coss/UI** (the Cal.com design system on Base UI, installed via the shadcn `@coss/*` registry; implies `ui_base="base"`, requires Tailwind v4) — owned by the `coss-ui` skill.
- `ui_base` (web, only when `ui="shadcn"`): `"radix"` | `"base"` | `"aria"`. The primitive library shadcn builds on (`shadcn create --base`). **Default `"base"`** (Base UI — shadcn's default for new projects since 2026-07). `"radix"` is the long-standing base (still fully supported); `"aria"` = React Aria (`--base aria`, Adobe's a11y-first primitives, first-class since 2026-07). Every shadcn block/component ships in all variants; `shadcn add` pulls the matching one.
- `shadcn_preset` (web, optional, only when `ui="shadcn"`): a **shadcn preset code** (short string, e.g. `"b5owWMfJ8l"`) built on <https://ui.shadcn.com/create>. Encodes style, base color, theme, chart palette, icon library, fonts (body/heading), and radius — the whole shadcn visual system in one token, designed to hand off to coding agents. When set, the **preset is the source of truth for the shadcn visual layer** (passed as `--preset`), and the DESIGN.md token-first install (`registry.json`) is **skipped** for the visual layer — preset XOR DESIGN.md-tokens, never both. `null`/unset → DESIGN.md-first (default). Decode/inspect with `shadcn preset decode <code>`; `ui_base` is still set separately (the preset may not encode the primitive base).
- `base_color` (web, only when `ui="shadcn"`): `"neutral"` | `"gray"` | `"zinc"` | `"stone"` | `"slate"`. The shadcn base color. Default `"neutral"`. In dev-flow mode the **DESIGN.md tokens override** the actual palette — this is only the scaffold starting point.
- `ui_theme` (web, only when `ui="shadcn"`): `"vega"` | `"nova"` | `"maia"` | `"lyra"` | `"mira"` | `null`. The shadcn create starting theme. Default `null` (plain). DESIGN.md tokens override.
- `icon_library` (web): `"lucide"` | `"radix-icons"` | `"tabler"` | string. Default `"lucide"`.
- `illustrations` (frontend, optional): `"koboyo"` | string | `null`. **Default `null` — the honest value for most products.** Spot art / illustration for *moments* (empty states, onboarding, 404), distinct from `icon_library` (UI icons). Set it only when DESIGN.md's visual language actually admits illustration; how-to + the restraint rules + the licence boundary are in `design-md-to-app/references/illustrations.md`.
- `css_variables` (web): `true` | `false`. shadcn `--css-variables`. Default `true` (required for token-driven theming from DESIGN.md).
- `rtl` (web, optional): `true` | `false`. shadcn `--rtl` (right-to-left support). Default `false`.
- `auth`: `"better-auth"` | `"next-auth"` | `"clerk"` | `"supabase"` | `"supabase-auth"` | `"firebase"` | `"custom-rest"` | `"trpc"` | `null`
- `db`: `"neon-drizzle"` | `"supabase"` | `"firebase"` | `"planetscale-prisma"` | `"custom-rest"` | `"trpc"` | `null`
- `payments`: `"stripe"` | `"lemon-squeezy"` | `"revenuecat"` (mobile IAP) | `null`
- `deploy`: `"vercel"` | `"fly"` | `"cloudflare-pages"` | `"eas"` (mobile) | `null`
- `storage` (optional — file/blob storage): **web** → `"vercel-blob"` (**default** when `deploy = "vercel"` — same platform, no extra vendor/sub-processor; how-to `module-add/references/module-storage.md`) | `"uploadthing"` | `"s3"`; **mobile** → `"supabase"` | `"firebase"` | `"custom-rest"`; `null` when the product stores no files.
- `realtime` (mobile, optional): `"supabase"` | `"firebase"` | `"custom-rest"` | `null`
- `push` (mobile, optional): `"expo-notifications"` | `null`
- `route_groups` (web/monorepo, optional): array of `"(marketing)"` | `"(auth)"` | `"(app)"` | `"(tabs)"` (mobile). E.g. `["(marketing)", "(auth)", "(app)"]` for SaaS, `["(auth)", "(app)"]` for internal tool, `["(marketing)"]` for marketing site. Written by `prd-from-idea` based on deduction from the PRD; can be overridden by user later.
- `i18n` (frontend, **golden rule 2**): `"next-intl"` (web canonical default) | `"i18next"` | `"react-i18next"` | `null`. Every frontend has i18n — do not leave `null` for a frontend. Web new projects default to `"next-intl"`; mobile uses the RN i18n stack.
- `locales` (frontend, **golden rule 2**): array of BCP-47 codes, first entry = default locale. **Minimum `["en", "it"]`**; a project may add more (e.g. `["en", "it", "fr"]`). Set at scaffold, not asked.
- `maps` (frontend, optional — only when the product shows maps): `"mapcn"` (web, MapLibre GL — how-to `design-md-to-app/references/maps-mapcn.md`) | `"mapcn-rn"` (mobile, MapLibre/Mapbox RN — how-to `rn-components-apis/references/maps-mapcn-rn.md`) | `null`. Ecosystem-first default when a project needs a map. `null` when the product has no maps.
- `forms` (web/monorepo, optional): `"tanstack-form"` | `"react-hook-form"` | `null`. The form-handling library. Defaults to `"tanstack-form"` for new Next.js 16 App Router projects (aligned with `nextjs-forms` skill from `lusentis/next-skills`). `"react-hook-form"` is supported for legacy projects or teams with strong preference. Written by `prd-from-idea` Q8 or set at scaffold time by `design-md-to-app`.
- `agent` (optional): `"eve"` | `null`. An **optional product component** — the agent engine wired into `apps/agent/`, owned exclusively by the `eve-agent` skill. Opted into at stack-decision time or later on demand (not a pipeline phase). `null`/unset → no agent (or `eve-agent` will scaffold one when opted in); `"eve"` → an eve agent exists and `eve-agent` runs in capability mode. Setting it to `"eve"` implies a monorepo (`apps/web` + `apps/agent`). `eve-agent` writes this key and appends to `history` but does **not** bump `phase` — the agent has its own capability cadence, separate from the web app's linear build.
- `nextjs_version` (web only, optional): `"16"` | string. The Next.js major version. **Canonical default for new projects = `"16"`** (App Router, RSC, async `searchParams`, `use(promise)`, `revalidatePath`, `revalidateTag`). Pages Router (`pages/` dir) is explicitly NOT supported by the dev-flow skill set — use only App Router. If an existing project is Pages Router or pre-16, the web skills refuse to apply. **Next 16.3 is stable** (released 2026-08-03; `latest` on npm) and every Next 16 project should upgrade — most of it is zero-config (dev memory, build cache, native Node streams, TS 7 type checking). **Instant Navigations** is the opt-in part (`cacheComponents` + `partialPrefetching`): it doesn't change this pin, and is adopted deliberately per `data-fetching/SKILL.md` §Instant Navigations.

Use `null` (not `"none"`) when not yet decided. For `route_groups`, an empty array `[]` means "no route groups, flat routing".

## Folder structure conventions

Skills that scaffold a codebase (`design-md-to-app`, `rn-bootstrap`, `monorepo-bootstrap`) MUST generate the canonical folder structure documented in `docs/superpowers/specs/2026-06-06-folder-structure-refactor.md`. Key rules:

- **Co-location via `_components/`**: page-private components live in `app/<route>/_components/`. The underscore prefix is Next.js convention for non-routable folders. **Web only** — this applies to Next.js (`stack.framework ∈ {next, monorepo}` web side). **Expo Router (`stack.framework = "expo-rn"`) has NO private-folder convention** — every file under `app/` becomes a route, so on mobile screen-private components live in `components/<feature>/` **outside** `app/`, not in `app/<route>/_components/` (see `rn-add-screen` / `promote-component`).
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
