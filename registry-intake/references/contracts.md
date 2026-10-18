# `.workflow/` — Contract between dev-flow skills

This document defines the **canonical contract** that all skills in the dev-flow family must respect. It is the load-bearing piece of the architecture: skills know nothing about each other, but they all read and write `.workflow/` in the same way.

> Living version: this file. Skills that need to consult the contract should read **this exact file** (vendor a copy into their `references/` if standalone) — do not paraphrase from memory.

## Knowledge principle — doc-grounded, never invent (rule zero)

The skills are a **second brain**: authoritative, doc-grounded knowledge of the domains we build in, so we act as **experts and never improvise an API**. This governs how every skill is written and used:

1. **Never invent.** Do not guess an API, flag, config shape, file path, or command. If the skill states it, it must be **grounded in the official documentation** (or the installed source, e.g. `node_modules/<pkg>`), not memory.
2. **Prefer the version-matched source the tool itself gives you.** Upstreams increasingly ship their docs *to* the agent: `next dev` writes and maintains a version-matched `AGENTS.md` block pointing at the docs bundled in `node_modules`, and eve ships its docs at `node_modules/eve/docs/`. Read those first — they match the installed version, which a web page may not. (Vercel retired its own doc-shipping skills once this landed; the lesson for us is that **a skill must encode workflow and conventions, never a frozen copy of someone's documentation** — that part rots.) ⚠️ **Don't clobber that block**: `next dev` upserts it into the project's `AGENTS.md` *and* `CLAUDE.md` between `<!-- BEGIN:nextjs-agent-rules -->` markers and preserves everything outside them — so any dev-flow bootstrap file **merges**, never overwrites, and never edits inside the markers. (`create-next-app` generates both files; `agentRules: false` opts out.)
3. **If we don't have the knowledge, get it.** When a skill says "use library X", it must also document **how** — the real setup + usage from X's official docs — so we don't scaffold something wrong and redo it later. A bare "use X" without the how-to is an incomplete skill. When the knowledge isn't in the skill yet, consult the official online docs *before* writing code, then capture what you learned back into the skill.
4. **Mark the moving surface `[VERIFY]`.** Any identifier from a fast-moving or beta upstream (eve, next-intl, shadcn CLI, Expo SDK, Motion, Stripe apiVersion, …) carries a `[VERIFY]` note to check against the installed version — because docs move (e.g. **Next 16** deprecated `middleware.ts` in favour of `proxy.ts` — and note it was *Next*, not next-intl: the `next-intl/middleware` subpath never renamed, which is exactly the kind of misattribution a `[VERIFY]` is meant to catch). **And when the `[VERIFY]` is about a *default* or about *what leaves the machine*, verify it against the shipped artefact, not the page**: `npm pack <pkg>@<version>` needs no install and carries the compiled `dist`, the `.d.ts`, `engines`, `peerDependencies`, the `exports` map and usually the `CHANGELOG`. A page states the intent; the `dist` states the behaviour, and the `dist` is what reaches the customer. Measured on 2026-10-04: a documented "exports by default" turned out to be metadata-only, because the content ceiling lived in a type comment two pages from the sentence — see `dev-flow/references/before-you-build.md` §Shipped source outranks the prose.
5. **Update periodically.** Upstreams change; the knowledge base must keep pace. Run the ecosystem watch (`docs/vercel-changelog-watch.md` and the per-skill audit recipes) on a cadence, apply what changed, and log it. Stale docs-grounding is a bug.

Reference material (`references/*.md`) exists to satisfy #3 — every "use X" default in this contract points at a doc-grounded how-to, not just a name. **`docs/knowledge-index.md` is the map of them all**: which domains we're expert in, where each how-to lives, and which upstream to re-verify when it moves. Read it before wiring a library; walk it when running a periodic refresh; **add a row whenever you introduce a new "use X" default**.

## Golden rules (all projects, all stacks)

Three non-negotiable rules every dev-flow skill follows, regardless of the user's or team's spoken language. They are not checked the same way, and each says how: **rule 3 is enforced by tools** (the design lint, the write-time guard, `set-phase`); **rules 1 and 2 are checked in review** — `spec-review`'s Standards axis — and no tool catches a breach of either. (This line used to say every skill *enforces* all three.)

1. **Code is written in English.** Every code identifier — functions, variables, constants, types, enums, file/folder names, DB columns, API field names, commit messages — **and all code comments** are in English, always. This holds even when the user converses in another language (e.g. Italian): the conversation language and the code language are independent. English code stays portable, greppable, and consistent across contributors and tools. The one thing that is *not* English-by-default is **user-facing copy** — that goes through i18n (rule 2), never hardcoded.
   - **Checked by:** review only (`spec-review`, Standards axis). No lint rule enforces it: an identifier or a comment in another language passes every tool dev-flow installs.

2. **Every frontend ships i18n from day one.** No user-facing string is ever hardcoded; all visible copy (labels, buttons, errors, empty states, emails) routes through i18n keys. The minimum locale set is **English + Italian** (`stack.locales = ["en", "it"]`, default locale `en`); a project may declare more, decided per project. The library:
   - **Web (Next.js App Router)** → **[next-intl](https://next-intl.dev/)** (`stack.i18n = "next-intl"`), the canonical default. **The doc-grounded how-to is `design-md-to-app/references/i18n-next-intl.md`** (routing vs no-routing modes, `routing.ts`/`navigation.ts`/`proxy.ts`/`request.ts`, `[locale]` layout with `setRequestLocale` + `generateStaticParams`, `messages/{en,it}.json`, server vs client usage) — read it, don't reinvent the setup. Wired at scaffold time by `design-md-to-app`; the `forms` skill routes all form copy through it.
   - **Mobile (Expo/RN)** → the RN i18n stack (e.g. `i18next` + `expo-localization`) — next-intl is web-only.
   Record both `stack.i18n` and `stack.locales` in `meta.json`. Adding i18n later touches every screen, so it is set up **at scaffold**, not deferred.
   - **Checked by:** the scaffold, which wires the i18n library and records `stack.i18n` / `stack.locales`, then review (`spec-review`, Standards axis). No lint rule catches a hardcoded string — the design-lint preset does not include one (`react/jsx-no-literals` or an equivalent) — so a literal in JSX passes the lint.

3. **UI is composed only from the chosen library's primitives.** For shadcn: components installed with the shadcn CLI into `components/ui/`, customised only through DESIGN.md tokens and `cva` variants. Domain components are compositions of those primitives. Never hand-roll a primitive the library already ships (sidebar, dialog, sheet, tooltip, popover, combobox, date picker, table, tabs, toast, skeleton, empty state, field/input…), never add a second component library, never fork a primitive's behaviour. If no primitive fits, compose existing ones; a truly new primitive requires an explicit, recorded exception (ADR or `meta.json` note) with the reason. Same rule for MUI, Base UI standalone, Coss/UI and, on mobile, the RN/NativeWind component stack declared in `meta.json#stack`.
   - **Before writing a component, look for the primitive.** Search `components/ui/` (in a shadcn monorepo `packages/ui/src/components/`; MUI and standalone Base UI: the library's component list; mobile: React Native / Expo core components plus what `meta.json#stack` declares, and `components/shared/`) for one that covers the pattern. If it is there, use it; if two together cover it, compose them.
   - **Primitives are installed at `scaffolded`, all of them** — `shadcn add --all` (Coss/UI: its full `@coss/*` set, via `coss-ui`), so "the primitive isn't installed" is never a reason to write one. A primitive missing later is added with the library's CLI, never re-created by hand. ⚠️ **`--all` means "all that the index lists", which is not all that ships** — verified 2026-10-17, the index carries 61 `registry:ui` items while `trace`, `code-block` and `use-highlighted-code` install by name and are absent from it. So the rule stands with one extra step: **before writing a component by hand, ask the registry by name** (`pnpm dlx shadcn@latest view <name>`) rather than trusting that `--all` would have brought it. `design-md-to-app` tops the scaffold up with the known gap; a missing primitive is still never a reason to hand-roll one.
   - **`components/ui/` files change only in their `cva` variants and token classes** — not their markup, handlers, state or accessibility wiring. That is where a primitive is tuned to the design; a behaviour change there is a fork.
   - **The primitive renders the design.** Every piece of UI is a primitive from `components/ui/`. When the board (wireframe, screenshot, Figma) or a screen the user already approved differs from the primitive — a radius, a border instead of a ring, a hover tint, a selected background, a font weight, a padding — **the primitive is tuned**: its `cva` variants and the DESIGN.md tokens it reads change until it renders the design, **verified pixel by pixel**. A visual drift is never accepted, an element is never written by hand, and the look is never rebuilt with classes at the call site. A new variant goes into DESIGN.md first, then into the primitive's `cva`. **The board changes only when the user decides to change the design.**
   - **Why the primitive is tuned and not the board (smart-travel, 2026-10-12):** the first version of this rule said «the primitive wins, the board is corrected». Converting the 238 hand-made elements below to primitives used as they ship changed the screens — radii, selected backgrounds, weights, padding — and the user rejected them. The approved design is the target; the primitive is how it gets rendered.
   - **Converting existing screens proves parity.** Before a screen is converted to primitives (a retrofit, a hand-made element replaced), screenshot it at every width and state the board has; after, screenshot it again and **diff the two pixel by pixel** (Playwright screenshots + `pixelmatch`, or ImageMagick `compare -metric AE`). A non-zero diff is fixed by tuning the primitive — never accepted, never patched with call-site classes. A diff that the user wants is a design change, and the board changes with it.
   - **A hand-made element is a violation even with no import at all.** A `<button>`, `<label>`, `<input>`, `<a>`, `<hr>`, `<img>`, `<details>`, `<table>` written in app code, a hand-written ARIA role (`tab`, `radio`, `menu`, `switch`…), or a `<div>`/`<span>` whose classes redraw a Card, Badge, Alert or Separator, breaks this rule exactly as importing a second library does. Allowed raw, and only these: an element passed as a primitive's `render` (or the child of `asChild`); an `<a>` styled by `buttonVariants` (download, `tel:`, `mailto:`); a hidden or file input; an `sr-only` data table; a file that renders no DOM (`next/og`, react-email, react-pdf); an exception recorded in the preset's `designExceptions` with its reason (e.g. map marks drawn inside MapLibre).
   - **A missing variant is added, not worked around.** When no existing variant renders the design, add one: first in DESIGN.md (`components` block), then in the primitive's `cva`, and say in the report which variant was added. When no primitive covers the pattern at all, or rendering the design would need a change to the primitive's markup or behaviour (a fork), the agent **stops and asks the user**. A missing variant never authorises an element by hand, a restyle with classes at the call site, or an `eslint-disable`. Pattern → primitive table: `design-md-to-app/references/primitives-first.md`, read before writing any component.
   - **Every web project with a Tailwind UI (shadcn, base-ui, coss) has the write-time guard**: Claude Code hooks in `.claude/settings.json` running `scripts/guard/primitives-guard.mjs`, which refuse a Write/Edit that adds hand-made UI (PreToolUse), report it right after a shell command that wrote it (Pre/PostToolUse on Bash, checking only the files the command touched), and stop an agent or subagent that added it through the shell (Stop / SubagentStop). Installed at scaffold by `design-md-to-app` (`setup_design_lint.py`, which calls `setup_primitives_guard.py`), recorded as `stack.primitives_guard`. A project already started gets it with the same one command (the retrofit).
   - **Why (smart-travel, 2026-10-12):** three days of building behind a green lint produced 238 hand-made elements where a primitive existed — 84 div-cards, 62 `<button>`, 34 `<label>`, 22 alert boxes, 14 `<a>`, 11 span-badges. The rule existed only as text; a raw element imports nothing, so the import bans could not see it; `shadcn/no-restyle` made writing the element by hand the easiest way around a board that did not match a variant (tuning the variant was the way); 57 of 71 buttons came in one night of parallel agents copying the neighbouring file; `meta.json#phase` was still `design_extracted`, so no check was ever proposed; and every verification was visual. **A green lint and a screenshot that matches the board are not proof of conformity** — a hand-made button identical to the board passes both. Conformity needs both halves: `design/no-handmade-ui` at zero, and the pixel diff at zero.
   - **The exception record.** An ADR in `docs/adr/` or an entry in `meta.json#stack_config.primitive_exceptions`: `{ "component": "<Name>", "path": "<file>", "reason": "<why no primitive or composition fits>", "recorded_at": "<ISO-8601>" }`, mirrored in the preset's `designExceptions` when it turns the rule off for a file. An exception without a reason is not an exception.
   - **Enforced by:** the design-system lint — `design/no-handmade-ui` at `error` (raw elements, hand-written roles, classes that redraw a primitive, each with the primitive to use) and `design/no-card-in-card`, plus `no-restricted-imports` on undeclared component libraries and on the primitives' headless bases (`radix-ui`, `@base-ui/react`, `cmdk`, `vaul`…) outside `components/ui/`, all written by `design-md-to-app/scripts/setup_design_lint.py`; the **write-time guard** above; `update_meta.py set-phase`, which refuses `scaffolded` **and every later phase** without the rule and the guard; `spec-review`'s Standards axis on every diff (four checks, the fourth a lint/grep for raw elements); and `shadscan`'s gate.
   - **Open gap — mobile (`expo-rn`, NativeWind):** no equivalent rule or guard exists yet. A hand-made `Pressable` + `View` styled as a button, or a `View` with NativeWind classes drawn as a card, is the same violation and nothing catches it. It has to be built (the same guard over the RN component set); until then, `spec-review` checks it by reading.

Rules 1–2 are recorded in the `stack` block (`i18n`, `locales`) and treated as defaults, not questions — skip asking; only confirm extra locales beyond en/it. Rule 3 is recorded through `stack.ui` (and `ui_base`, `shadcn_preset`): the library a project declares is the only one it composes.

### Recommended default libraries (ecosystem-first)

When a project needs one of these capabilities, reach for the default below instead of hand-rolling or picking ad-hoc — the same ecosystem-first rule used everywhere in dev-flow. Not every project needs them; these are the defaults **when** it does.

| Capability | Web default | Mobile default |
|---|---|---|
| **Maps** | **[mapcn](https://mapcn.dev/)** — MapLibre GL, shadcn-registry. How-to: `design-md-to-app/references/maps-mapcn.md` (⚠️ CARTO default tiles need an Enterprise license for commercial use). `stack.maps = "mapcn"`. | **[mapcn-rn](https://mapcn-rn.dev/)** — MapLibre/Mapbox RN + NativeWind. How-to: `rn-components-apis/references/maps-mapcn-rn.md` (⚠️ native modules → dev build, not Expo Go). `stack.maps = "mapcn-rn"`. |
| **File / blob storage** | **Vercel Blob** (`@vercel/blob`) when deploying to Vercel — same platform, one less sub-processor. UploadThing / S3 only on request. How-to: `module-add/references/module-storage.md`. `stack.storage = "vercel-blob"`. | provider-side (`supabase` / `firebase` / custom) via `rn-module-add` |
| **Illustration / spot art** | **[Koboyo](https://koboyo.com/icons)** — 71k hand-drawn SVGs, free commercially, found via its MCP server. ⚠️ **Use sparingly and only when DESIGN.md admits it**; the licence forbids products where the art *is* the feature. How-to: `design-md-to-app/references/illustrations.md`. | same source, vendored as SVG |
| **Animated icons** | `animated-icons` (skill) | `rn-animations-gestures` |
| **Motion** | `transitions` + `module-add motion` | `rn-animations-gestures` |
| **Node graphs** | **[React Flow](https://reactflow.dev)** (`@xyflow/react`, MIT) — only for a graph the user acts on; nodes from shadcn primitives or React Flow UI (via `registry-intake`). How-to: `design-md-to-app/references/react-flow.md`. `stack.graphs = "react-flow"` | — (no RN equivalent) |
| **WebGPU shaders** | `vgpu-shaders` (`stack.shaders`) — `transitions`' Tier 4, MIT, first-party skill for the API | — (no WebGPU rung on RN) |
| **Documents → Markdown** | [`anydoc`](https://github.com/firecrawl/anydoc) (Firecrawl, MIT) — `.docx`/`.pptx`/`.xlsx`/`.pdf`/ODF/RTF/EPUB/CSV, **converted locally**; first-party skill `npx skills add firecrawl/anydoc`. ⚠️ `--ocr hosted` sends the **whole** document to a third party — an R3 transfer decision, not a flag | same CLI |
| **Forms** | `forms` (`stack.forms`) | RN form stack |
| **Design-system lint** | **[`@shadcn/lint`](https://github.com/shadcn-ui/lint)** (`stack.design_lint`) — errors that name the token or variant to use; `error` from day one on a scaffold. How-to: `design-md-to-app/references/design-system-lint.md`. | — (no RN equivalent) |
| **EU data residency** | `dev-flow/references/eu-data-sovereignty.md` — per service: default, EU region to set, European alternative, with sources and dates. `stack.data_residency`; register in `docs/compliance/subprocessors.md` | same reference (Supabase / Firebase regions, push relay, purchases) |
| **Third-party registries** | `registry-intake` (`stack.registry_intake`) — allowlist, review, hashed snapshot, PreToolUse hook; wired at scaffold, checked by `set-phase`. Covers every shadcn-format registry (pdfcn, emailcn, mcpcn, agentcn, evex…) and `eve add @ns/…` | — (RN has no shadcn registry) |
| **Measurement (opt-in)** | three levels, each on request: **traffic** = Vercel Web Analytics + Speed Insights; **product** = own-database events + activation/D7/D30 SQL; **advanced** = PostHog EU, or OpenPanel for `eu-sovereign`. Vercel Analytics and Plausible cannot do D7/D30 retention. How-to: `module-add/references/module-analytics.md`. `stack.analytics` | no traffic level; product per backend, advanced with `posthog-react-native` via `rn-module-add analytics` |
| **Content / headless CMS** | **Sanity** via `next-sanity` — `module-add cms`; how-to `module-add/references/module-cms.md`. The hosted Studio is the editors' admin panel. `stack.cms = "sanity"` | **Sanity** over the HTTP Query API (plain `fetch`, no SDK in the bundle) — `rn-module-add cms`; how-to `rn-module-add/references/module-cms-sanity.md`. Same `cms/` Studio package as web in a monorepo |

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
│   ├── founder/                  # only on the founder path (founder-intelligence), absent otherwise
│   │   ├── founder-playbook.md   # the strategic document the founder approves
│   │   ├── sources.md            # evidence register: URL, date read, what it supports, decisions that depend on it
│   │   ├── interviews/NN-<who>.md  # notes of real interviews, written or pasted by the founder
│   │   └── handoff.md            # existing projects only: proposed PRD/scope/metric changes for dev-flow
│   └── decisions/                # ADR-style decisions, one per file (optional)
│       └── 0001-stack.md
├── docs/wireframes/              # ← screen-inventory.md + png/<ID>-{desktop,phone}.png (wireframe-canvas)
├── package.json                  # ← codebase lives at the root
├── app/, components/, lib/       # ← framework conventions, untouched
├── registry.json                 # ← shadcn registry (when applicable), at root
├── drizzle.config.ts             # ← config files at root
├── cms/                          # ← Sanity Studio package when stack.cms = "sanity" (own package.json; excluded from the app's bundler)
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
  "contract_version": 1,
  "meta_digest": { "sha256": "9f2c…", "checked_phase": "design_extracted" },
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

### `wireframes` field (optional, owned by `wireframe-canvas`)

Every project with a UI draws all its screens before any code is scaffolded (the user's standing rule, 2026-10-10): a screen inventory mapped to the PRD's `US-N` stories, then one desktop (1440) and one phone (390) artboard per screen on a claude.ai Design canvas, reviewed area by area and approved by the user. Written only through `wireframe-canvas/scripts/wireframes.py`:

```json
"wireframes": {
  "canvas_url": "https://claude.ai/…", "inventory": "docs/wireframes/screen-inventory.md",
  "screens": 24, "artboards": 48,
  "approved_at": "<ISO-8601 UTC>", "approved_by_user": true, "approval_quote": "<the user's words>",
  "screenshots_posted_at": "<ISO-8601 UTC>" | null
}
```

The opt-out is `{ "skipped": true, "reason": "<sentence>" }`; a skip without a reason does not count. **`update_meta.py set-phase` (and `append-history --phase-after`) refuses to cross into `monorepo_initialized` or `scaffolded` while the block is missing, unapproved, short of two artboards per screen, or pointing at an inventory that is not on disk** (`dev-flow/scripts/wireframes_gate.py`). Projects already past that point are not blocked; `show_state.py` flags them, and flags an approved canvas whose screenshots are not yet on the issues. Agent-only projects (`framework: "agent"`) are not affected. After approval the PNGs live in `docs/wireframes/png/<ID>-desktop.png` / `<ID>-phone.png` and are commented on every tracker issue whose story maps to the screen.

### `inventory` field (owned by `dev-flow/scripts/inventory.py`)

"Does this already exist?" answered before any PRD: in the house, in tools already paid for, in the Claude ecosystem, outside (`dev-flow/references/before-you-build.md`). Written only through `inventory.py record`:

```json
"inventory": {
  "verdict": "have-it | adapts | halfway | build | skipped",
  "summary": "<one paragraph>", "searched": ["<channel or query>", "..."], "not_covered": ["<channel not reached>"],
  "reason": "<required when skipped>", "ran_at": "<ISO-8601 UTC>"
}
```

A verdict other than `skipped` needs a non-empty `searched`; `skipped` needs a `reason`. **`update_meta.py set-phase` (and `append-history --phase-after`) refuses to cross into `prd_drafted` without it** (`dev-flow/scripts/inventory_gate.py`). On the founder path, `founder-intelligence` records this verdict at its feasibility stage, so the gate is the same on both paths.

### `founder` field (optional, owned by `founder-intelligence`)

For a commercial idea whose market is not settled, the founder path replaces the inventory step: research, customer discovery, competitors, business model and MVP scope, collected in a Playbook the founder approves before any PRD (the user's decision, 2026-10-17; `docs/superpowers/specs/2026-10-17-founder-intelligence-design.md`). Written only through `founder-intelligence/scripts/founder.py`:

```json
"founder": {
  "mode": "new | existing",
  "research": "in_progress | complete",
  "decision": "pending | approved | approved_experiment | revise | stop | bypassed",
  "playbook": ".workflow/founder/founder-playbook.md",
  "version": 3, "playbook_sha256": "<sha256 of the Playbook as approved>",
  "open_hypotheses": ["H2", "H5"],
  "approved_at": "<ISO-8601 UTC>", "approved_by_user": true, "approval_quote": "<the founder's words>",
  "experiment": { "scope": "…", "objective": "…", "constraints": "…", "acceptance": "…" },
  "reason": "<why revise, stop or bypassed>"
}
```

Research and decision are two axes, because a Playbook can be approved with hypotheses still open. The labels people read are derived from them (`show_state.py`, `founder.py status`):

| Label | When |
|---|---|
| `RESEARCH_COMPLETE` | `research = complete` |
| `NEEDS_VALIDATION` | `open_hypotheses` not empty (shown alongside the others) |
| `READY_FOR_FOUNDER_APPROVAL` | `research = complete` and `decision = pending` |
| `APPROVED_FOR_DEVFLOW` | `decision = approved` or `approved_experiment` |
| `REVISE_OR_STOP` | `decision = revise` or `stop` |

**Applies only when present.** A project without the field is on the direct path and nothing here concerns it. With `mode: "new"`, **`update_meta.py set-phase` (and `append-history --phase-after`) refuses to cross into `prd_drafted` unless the decision is `approved` or `approved_experiment` with the founder's quote and a Playbook whose sha256 still matches, or `bypassed` with a reason** (`dev-flow/scripts/founder_gate.py`). A Playbook edited after approval needs a new `founder.py approve`. With `mode: "existing"` (invoked on a project already past the PRD) the gate does not apply; the result is `handoff.md`, applied with `prd-from-idea` / `prd-to-tasks` once the founder agrees. Approval is not product-market fit: open hypotheses stay listed.

### `phase` enum (canonical)

The `phase` field tracks the project's progress through the pipeline. Every skill must set this correctly.

**All phase values are `snake_case` strings**. The canonical list below is the complete enum; skills MUST NOT use values outside it. Unknown values are treated as `empty` (forward-compatibility).

| `phase` value | Stacks | When set | Ready for next skill |
|---|---|---|---|
| `empty` | all | `.workflow/` was just created, only `meta.json` exists | `prd-from-idea` |
| `idea_captured` | all | `PROJECT.md` exists | `prd-from-idea` (to expand into PRD) or scaffold (skip if simple) |
| `prd_drafted` | all | `PRD.md` exists | `prd-to-tasks`, `figma-to-design-md`, `image-to-design-md`, or scaffold |
| `tasks_split` | all | `tasks.md` exists | `figma-to-design-md`, `image-to-design-md`, or scaffold |
| `design_extracted` | all | `DESIGN.md` + (optional) `screenshots/` exist | `wireframe-canvas` (every screen on a Design canvas, approved by the user — the gate into the scaffold), then scaffold (`design-md-to-app` for web, `rn-bootstrap` for mobile, `monorepo-bootstrap` for monorepo) |
| `monorepo_initialized` | **monorepo only** | turborepo root exists (`pnpm-workspace.yaml` + `turbo.json`), before the apps are scaffolded | `monorepo-bootstrap` continues — scaffolds `apps/web` (`design-md-to-app`), `apps/mobile` (`rn-bootstrap`), and/or `apps/agent` (`eve-agent`) |
| `scaffolded` | all | `app/` exists with framework + UI library installed — **every primitive of it** (`shadcn add --all`), so golden rule 3 always has something to compose | next-stack-skill (`screenshot-to-page` web / `rn-add-screen` mobile) or `module-add` / `rn-module-add` |
| `page_generated` | all | At least one route is implemented from a screenshot or PRD | `module-add` / `rn-module-add`, more screen-gen runs |
| `module_added` | all | Auth/DB/payments/etc. wired up | iterative — repeat as needed; leads to `feature_complete` when the build is done (all stacks) |
| `feature_complete` | all | All planned features built and tested; ready to ship | pre-deploy gates — `compliance-audit` (any stack), plus `vercel-doctor`, `shadscan` and `launch-audit` for web — then deploy: web → `vercel-deploy`, mobile → `rn-eas-deploy`, agent → `eve deploy` |
| `deployed` | all | Live in production (web on Vercel / mobile on App Store + Play Store / agent via `eve deploy`) | maintenance loop (web: `screenshot-to-page` / `module-add`; mobile: `rn-add-screen` / `rn-eas-build-submit-update`; re-run `compliance-audit` after material changes) |

**Notes**:
- All values are `snake_case` (e.g., `module_added` NOT `module-added`). Skills that use the kebab-case variant are non-conforming and should be migrated.
- The `feature_complete` and `deployed` phases are **cross-stack** (web, mobile, agent, monorepo). A web or agent project stays iterating at `module_added` and advances to `feature_complete` when the user declares the build done — at which point dev-flow proposes the `compliance-audit` pre-deploy gate and then the stack's deploy skill. `monorepo_initialized` is **monorepo-only** (a mid-`monorepo-bootstrap` checkpoint before the apps are scaffolded).
- **Phase progression is monotonic** — a skill should never set `phase` to an earlier value than what it found. If a skill is re-run (e.g., user re-extracts design from a new Figma), it appends to `history` but keeps the phase ≥ the current one.
- **The phase must not fall behind the code.** Routes in `app/` or components in `components/` while `phase` is still before `scaffolded` / `page_generated` means every check keyed on the phase (spec-review, shadscan, the set-phase gates) is silently off — smart-travel built for three days at `design_extracted`. `show_state.py` reports it as **PHASE BEHIND THE CODE** and routes to realignment (retrofit golden rule 3, `set-phase page_generated`, then spec-review + shadscan on what was built). Independently of the phase, `spec-review` runs whenever a piece of work lands.
- The `deployed` phase is terminal in the sense that future runs stay there; subsequent EAS Update or new-feature work appends to `history` without phase regression.

### `stack` field

Captures user choices that downstream skills need. Keys:

- `framework`: `"next"` | `"vite-react"` | `"remix"` | `"astro"` | `"sveltekit"` | `"expo-rn"` | `"monorepo"` (planned) | `"agent"` | string

  `"agent"` is the **agent-only topology** (shape ③ in `dev-flow/references/stack-decisions.md` §Topology policy): an eve agent at the repo root with **no web app**, whose surfaces are elsewhere — Slack, email, GitHub, Linear. Always paired with `agent: "eve"`; `ui`, `forms`, `nextjs_version`, `locales` stay `null` (there is no frontend, so golden rule ② does not apply — agent *output* is localised by instructions, not by an i18n bundle).

  **The 17 skills that guard on `framework` need no change: refusing is the correct answer.** `forms`, `data-fetching`, `design-md-to-app`, `shadscan` and the rest exist to build and audit a web UI, and an agent-only project has none. The only skills that apply are `eve-agent` (which owns the whole repo root here, not `apps/agent/`), `eve-registry-porting`, `compliance-audit`, `prd-from-idea` / `prd-to-tasks` / `linear-scrum`, and `vercel-deploy` only insofar as `eve deploy` is the ship step.
- `ui`: `"shadcn"` | `"base-ui"` | `"coss"` | `"mui"` | `"chakra"` | `"radix-vanilla"` | `"nativewind"` (mobile) | string. **Note**: `"base-ui"` here means *standalone* Base UI (headless library, no shadcn CLI). With shadcn CLI v4 you can also run shadcn **on top of** Base UI — that is `ui="shadcn"` + `ui_base="base"` (below), and is usually the better way to get "shadcn philosophy on Base UI" because you keep the shadcn component set + blocks. `"coss"` = **Coss/UI** (the Cal.com design system on Base UI, installed via the shadcn `@coss/*` registry; implies `ui_base="base"`, requires Tailwind v4) — owned by the `coss-ui` skill.
- `ui_base` (web, only when `ui="shadcn"`): `"radix"` | `"base"` | `"aria"`. The primitive library shadcn builds on (`shadcn create --base`). **Default `"base"`** (Base UI — shadcn's default for new projects since 2026-07). `"radix"` is the long-standing base (still fully supported); `"aria"` = React Aria (`--base aria`, Adobe's a11y-first primitives, first-class since 2026-07). Every shadcn block/component ships in all variants; `shadcn add` pulls the matching one.
- `shadcn_preset` (web, optional, only when `ui="shadcn"`): a **shadcn preset code** (short string, e.g. `"b5owWMfJ8l"`) built on <https://ui.shadcn.com/create>. Encodes style, base color, theme, chart palette, icon library, fonts (body/heading), and radius — the whole shadcn visual system in one token, designed to hand off to coding agents. When set, the **preset is the source of truth for the shadcn visual layer** (passed as `--preset`), and the DESIGN.md token-first install (`registry.json`) is **skipped** for the visual layer — preset XOR DESIGN.md-tokens, never both. `null`/unset → DESIGN.md-first (default). Decode/inspect with `shadcn preset decode <code>`; `ui_base` is still set separately (the preset may not encode the primitive base).
- `base_color` (web, only when `ui="shadcn"`): `"neutral"` | `"gray"` | `"zinc"` | `"stone"` | `"slate"`. The shadcn base color. Default `"neutral"`. In dev-flow mode the **DESIGN.md tokens override** the actual palette — this is only the scaffold starting point.
- `ui_theme` (web, only when `ui="shadcn"`): `"vega"` | `"nova"` | `"maia"` | `"lyra"` | `"mira"` | `null`. The shadcn create starting theme. Default `null` (plain). DESIGN.md tokens override.
- `icon_library` (web): `"lucide"` | `"radix-icons"` | `"tabler"` | `"hugeicons"` | `"phosphor"` | string. Default `"lucide"`. **`"phosphor"` was promoted 2026-10-09 for the same reason as `"hugeicons"`: the enum could not express a value the toolchain itself chooses** — shadcn's `lyra` style ships `@phosphor-icons/react` (MIT, 2.1.10, 1,512 icons, **six weights per icon** — thin, light, regular, bold, fill, duotone — 31.5 MB installed, tree-shakeable), so a `lyra` scaffold set a library the contract had to record as a bare string. **The style decides this key**: read it from `shadcn info --json` after `init` rather than assuming the default (`design-md-to-app/references/shadcn-styles.md`). ⚠️ `animated-icons` has registries for heroicons and hugeicons only, so an animated-icon request on a `phosphor` project needs a different answer.
- `illustrations` (frontend, optional): `"koboyo"` | string | `null`. **Default `null` — the honest value for most products.** Spot art / illustration for *moments* (empty states, onboarding, 404), distinct from `icon_library` (UI icons). Set it only when DESIGN.md's visual language actually admits illustration; how-to + the restraint rules + the licence boundary are in `design-md-to-app/references/illustrations.md`.
- `data_residency` (all stacks): `"eu"` | `"eu-sovereign"` | `"none"` | `null`. **Decided at the stack decision, before any module wires a provider**, by `dev-flow/scripts/data_residency.py decide` from four answers — EU data subjects, sensitive categories, sector residency obligations, CLOUD Act exposure to avoid — kept in `stack_config.data_residency_answers` (with `override_reason` when the choice departs from the suggestion). `"eu"` = every service in an EU region where one exists; `"eu-sovereign"` = EU region **and** a vendor not under US control where a European alternative exists; `"none"` = no EU constraint. **`update_meta.py set-phase` refuses `scaffolded` while it is `null`** — and that is all it refuses: a provider with no EU region is **flagged** in the sub-processor register with its transfer basis and never blocks a module or a phase. How-to, the service table and the regulations: `dev-flow/references/eu-data-sovereignty.md`.
- `design_lint` (web): `"shadcn-lint"` | `"none"` | `null`. Written by `design-md-to-app/scripts/setup_design_lint.py` once `@shadcn/lint` is installed, wired and capped. `"none"` is an **explicit opt-out** and requires `stack_config.design_lint_reason` (a sentence; an opt-out without one does not count). **`null` means undecided, and `update_meta.py set-phase` refuses to move a Next web app on a Tailwind UI (shadcn, base-ui, coss) into `scaffolded` while it is undecided or not wired — and, since 2026-10-12, any later phase too while the preset lacks `design/no-handmade-ui` or the write-time guard (`primitives_guard`).** `show_state.py` flags projects already past it and proposes the one-command retrofit. MUI, mobile and agent-only projects are not affected. Retrofitting an existing app starts at `warn` with a measured `--max-warnings`, never straight to `error`.
- `primitives_guard` (web): `"installed"` | `"none"` | `null`. The write-time guard of golden rule 3 (`.claude/settings.json` hooks + `scripts/guard/`), written by `design-md-to-app/scripts/setup_primitives_guard.py` (called by `setup_design_lint.py`). `"none"` is an explicit opt-out and requires `stack_config.primitives_guard_reason`; a reasoned `design_lint: "none"` takes the guard with it (no rule to run). **`update_meta.py set-phase` refuses `scaffolded` and every later phase on a Next web app with a Tailwind UI while it is missing or the preset lacks `design/no-handmade-ui` at `error`**; `show_state.py` flags it and proposes the retrofit (`setup_design_lint.py <root>`, one command: rule + guard + AGENTS.md section). Mobile is not covered yet (golden rule 3, open gap).
- `lint` (optional): `"eslint"` | `"biome"` | `"eslint+biome"` | `null`. Which **code** linter the project runs — a different question from `design_lint`, which is the shadcn design-system lint and is wired by a script of ours. **The repository is the truth and this key is a cache of it**: the operative facts are the `lint` script in `package.json`, the config file on disk and the dependency, and every skill that lints reads those. `show_state.py` reports a declaration the repository contradicts. **Written 2026-10-10 after a survey of 36 projects found it declared in two of them and wrong in both** — one said `biome` with no biome anywhere (it runs ESLint and Prettier), the other said `eslint` while carrying both. A key nothing writes, nothing reads and nothing checks does not stay true; this one is now checked, which is the only reason to keep it. **`design_lint = "shadcn-lint"` needs ESLint**: `@shadcn/lint` is an ESLint plugin, so a biome-only project cannot run the design lint and must record `design_lint: "none"` with its reason. ⚠️ In a monorepo the toolchain lives in `apps/*`, not at the root — a check that reads only the root package.json reports six healthy projects as broken, which is how this paragraph was nearly written wrong.
- `registry_intake` (web on a Tailwind UI, and eve agents): `"enforced"` | `"none"` | `null`. Written by `registry-intake/scripts/registry_intake.py setup`, which creates `registry-lock.json` (allowlisted registries with their reason, approved items with snapshot hash, reviewer and accepted findings), `vendor/registry/` and the PreToolUse hook in `.claude/settings.json`. **`update_meta.py set-phase` refuses `scaffolded` while `registry_intake.py check` fails**, unless `"none"` is recorded with `stack_config.registry_intake_reason`. From then on a component from any registry other than shadcn's own is installed only through `review → approve → install`; `@coss` is the one registry trusted live, and only when `ui = "coss"`.
- `test`: a **string, never an array** — the test layers joined by `+`, in this canonical order: `vitest` · `jest-expo` · `rntl` · `playwright` · `maestro` · `e2e`. Unit layers first, end-to-end layers last, no repeats. `"vitest+playwright"` is the web default, `"jest-expo+rntl"` the mobile one, `"jest-expo+rntl+maestro"` mobile with end-to-end flows, `"vitest"` unit only; `null` is undecided. **The grammar is validated rather than a fixed list of whole strings**, because a list cannot express a legitimate combination — the first project to add a layer would be told its honest value is wrong. `e2e` is the agentic runner (tester-army, Apache-2.0): **read, not adopted**, and `write-tests/references/e2e-agentic.md` is the one copy of how it is used, what it costs per run and which gates it passes first — `rn-write-tests` reads the mobile half from the same file. Written by `module-add test` (web) and `rn-bootstrap` (mobile) at scaffold; read by `write-tests` and `rn-write-tests` to pick the framework and to follow the mocking patterns already in the repo. `null` means undecided, and nothing refuses it: a project may ship without tests, and recording that honestly beats a value nobody wired. **This enum was written 2026-10-10, after the key had been free text since the first contract.** Eleven projects had drifted into four spellings, and one of them held an **array** — `write-tests` reads `stack.test` as the name of a framework, so `["vitest", "playwright"]` is a framework called `['vitest', 'playwright']`, which matches nothing and fails silently by writing tests in whatever style the sibling files happen to use. A new layer joins this enum deliberately; it is not invented at a call site.
- `css_variables` (web): `true` | `false`. shadcn `--css-variables`. Default `true` (required for token-driven theming from DESIGN.md).
- `rtl` (web, optional): `true` | `false`. shadcn `--rtl` (right-to-left support). Default `false`.
- `auth`: `"better-auth"` | `"next-auth"` | `"clerk"` | `"supabase"` | `"supabase-auth"` | `"firebase"` | `"custom-rest"` | `"trpc"` | `null`
- `db`: `"neon-drizzle"` | `"supabase"` | `"firebase"` | `"planetscale-prisma"` | `"custom-rest"` | `"trpc"` | `null`
- `payments`: `"stripe"` | `"lemon-squeezy"` | `"revenuecat"` (mobile IAP) | `null`
- `deploy`: `"vercel"` | `"fly"` | `"cloudflare-pages"` | `"eas"` (mobile) | `null`
- `storage` (optional — file/blob storage): **web** → `"vercel-blob"` (**default** when `deploy = "vercel"` — same platform, no extra vendor/sub-processor; how-to `module-add/references/module-storage.md`) | `"uploadthing"` | `"s3"`; **mobile** → `"supabase"` | `"firebase"` | `"custom-rest"`; `null` when the product stores no files.
- `realtime` (mobile, optional): `"supabase"` | `"firebase"` | `"custom-rest"` | `null`
- `analytics` (optional — only when the user asks to measure usage; never asked twice): a list of the active levels, any of `"traffic"` (Vercel Web Analytics + Speed Insights; web only) | `"product"` (an `analytics_events` table in the project's own database, server-side `track()`, activation and D7/D30 retention as SQL — no new sub-processor) | `"advanced"` (funnels, replay, dashboards from a provider, on request). Absent or `[]` = not requested: no skill and no check treats that as a gap. Can be switched on at any phase, a level at a time. How-to: `module-add/references/module-analytics.md` (web), `rn-module-add/references/module-analytics.md` (Expo).
- `analytics_provider` (only with `"advanced"` in `analytics`): `"posthog"` (PostHog Cloud EU, host written explicitly) | `"openpanel"` (the `eu-sovereign` default, self-hosted). Registered with `data_residency.py add`.
- `cms` (optional — content a non-developer edits and the product only *reads*: catalogue, pages, articles, FAQs): `"sanity"` (**default when the product needs one** — the hosted Sanity Studio is the admin panel, so no admin CRUD and no admin roles are built into `db`; how-to `module-add/references/module-cms.md` for web, `rn-module-add/references/module-cms-sanity.md` for mobile) | `"payload"` | `"contentful"` | `null`. User-owned data (accounts, orders, bookings) never goes here — it stays in `db` behind RLS.
- `push` (mobile, optional): `"expo-notifications"` | `null`
- `route_groups` (web/monorepo, optional): array of `"(marketing)"` | `"(auth)"` | `"(app)"` | `"(tabs)"` (mobile). E.g. `["(marketing)", "(auth)", "(app)"]` for SaaS, `["(auth)", "(app)"]` for internal tool, `["(marketing)"]` for marketing site. Written by `prd-from-idea` based on deduction from the PRD; can be overridden by user later.
- `i18n` (frontend, **golden rule 2**): `"next-intl"` (web canonical default) | `"i18next"` | `"react-i18next"` | `null`. Every frontend has i18n — do not leave `null` for a frontend. Web new projects default to `"next-intl"`; mobile uses the RN i18n stack.
- `locales` (frontend, **golden rule 2**): array of BCP-47 codes, first entry = default locale. **Minimum `["en", "it"]`**; a project may add more (e.g. `["en", "it", "fr"]`). Set at scaffold, not asked.
- `maps` (frontend, optional — only when the product shows maps): `"mapcn"` (web, MapLibre GL — how-to `design-md-to-app/references/maps-mapcn.md`) | `"mapcn-rn"` (mobile, MapLibre/Mapbox RN — how-to `rn-components-apis/references/maps-mapcn-rn.md`) | `null`. Ecosystem-first default when a project needs a map. `null` when the product has no maps.
- `graphs` (web, optional — only when a screen is an interactive node graph): `"react-flow"` | `null`. How-to `design-md-to-app/references/react-flow.md`. A read-only diagram that fits the screen is not a reason to set it. If the project hides React Flow's attribution, `stack_config.react_flow_subscription` records the subscription that allows it.
- `shaders` (web, optional — only when a WebGPU shader actually ships): `"vgpu"` | `null`. [`vgpu`](https://vgpu.sh) (Vercel Labs, MIT) as the **Tier 4** rung of `transitions` — how-to `vgpu-shaders`. ⚠️ Set it only when a shader renders in production: it commits the project to a GPU device, a compile step and a render loop. Record alongside it how the **reduced-motion** path is served and what a **no-WebGPU** visitor sees; neither has a default, and the library documents neither.
- `monorepo` (only when `framework = "monorepo"`): the per-side sub-object. `monorepo.web.*` and `monorepo.mobile.*` are defined in `dev-flow/references/stack-monorepo.md` (the canonical monorepo reference); the contract adds one key here because it is not per-side:
  - `monorepo.services` (optional): array of non-JS apps living in `apps/`, each `{ "name", "runtime", "framework", "path", "package_manager" }` — e.g. `{ "name": "ml", "runtime": "python", "framework": "fastapi", "path": "apps/ml", "package_manager": "uv" }`. Written by `monorepo-add-python-service`, which owns those apps the way `eve-agent` owns `apps/agent/`. An entry here tells every other skill that a directory under `apps/` is **not** a JS app: the web skills (`design-md-to-app`, `screenshot-to-page`, `forms`, `shadscan`, …) must never be proposed for it, and **golden rule 2 does not apply** to it — a service that returns JSON has no UI to localise.
- `canvas` (web, optional — only when the product ships a pan/zoom workspace): `"iframe-live"` | `"iframe-snapshot"` | `"single-live"` | `"rendered"` | `null`. Which canvas architecture was chosen, and therefore which constraints the rest of the editor is built under — owned by `iframe-canvas`. The value matters more than most: it decides how many browsing contexts the tab pays for, and changing it later invalidates the camera, the overlays and the protocol at once.
- `launch_audit` (web, optional — written by the `launch-audit` gate, not a stack choice): `{ ran_at, findings[], dismissed{} }`. The fourth pre-deploy gate — **can a stranger find this, trust it, and buy from it?** `dismissed` carries a *reason* per rejected finding so the next run does not re-litigate it. Reports, never blocks, never scores; how-to `launch-audit/SKILL.md`.
- `mcp` (web, optional — only when the product is published as an MCP server): `"better-auth"` | `null`. The app exposes `/mcp` over `@modelcontextprotocol/sdk`, guarded by its own OAuth server (`@better-auth/mcp`) — owned by `module-add mcp`; how-to `module-add/references/module-mcp.md`. Requires `auth` with its MCP section. **Not the same as an eve agent published as MCP** (`mcpChannel()` on `eve/channels/mcp`), which publishes the *agent*; this publishes the *product*.
- `pdf` (web, optional — only when the product generates documents): `"forme"` | `"takumi"` | `null`. The PDF renderer under the [pdfcn](https://www.pdfcn.dev) component registry — owned by `module-add pdf`. Both engines are **pre-1.0 on the PDF path** (2026-09-10); the components are copied into the repo shadcn-style, so a breaking change arrives as a diff you own rather than an upgrade you take.
- `forms` (web/monorepo, optional): `"tanstack-form"` | `"react-hook-form"` | `null`. The form-handling library. Defaults to `"tanstack-form"` for new Next.js 16 App Router projects (aligned with `nextjs-forms` skill from `lusentis/next-skills`). `"react-hook-form"` is supported for legacy projects or teams with strong preference. Written by `prd-from-idea` Q8 or set at scaffold time by `design-md-to-app`.
- `agent` (optional): `"eve"` | `null`. An **optional product component** — the agent engine, owned exclusively by the `eve-agent` skill, in `agent/` beside the app, `apps/agent/` in a monorepo, or `agent/` at the root (the topologies below). Opted into at stack-decision time or later on demand (not a pipeline phase). `null`/unset → no agent (or `eve-agent` will scaffold one when opted in); `"eve"` → an eve agent exists and `eve-agent` runs in capability mode. Setting it to `"eve"` does **not** dictate a repo shape. Three topologies are valid and the **project** picks — see `dev-flow/references/stack-decisions.md` §Topology policy for the decision, which proposes them in this order: **① single web app** with the agent inside it (the default — the product *is* the interface), **② monorepo** `apps/web` + `apps/agent` (the agent has its own deploy cadence, channels, or a second consumer), **③ agent only** (every surface is elsewhere and nothing needs rendering). Shape ③ is real, not theoretical: Vercel Labs' [`kody-eve-template`](https://github.com/vercel-labs/kody-eve-template) is a single-package repo whose `agent/` sits at the root and whose surfaces are GitHub, Linear and **email**. Pick by the product, not by habit, and **say which shape you are proposing** — ① and ② are different projects, not two spellings of one. Shape ③ is recorded as **`framework: "agent"`** (see the `framework` enum above): `eve-agent` owns the repo root instead of `apps/agent/`, and the web skills that refuse it are behaving correctly — there is no frontend for them to touch. What must not happen: scaffolding a Next.js app to satisfy a schema. A web app that exists only to host a chat box is worse than the email thread the users already have. `eve-agent` writes this key and appends to `history` but does **not** bump `phase` — the agent has its own capability cadence, separate from the web app's linear build.

  ⚠️ **One exception, and it follows from the reasoning above.** In the agent-only topology (`framework: "agent"`) there *is* no web app whose linear build the agent runs alongside, so nothing would ever advance the phase and the project would sit at `prd_drafted` forever. There, `eve-agent` **is** the bootstrap skill — the counterpart of `design-md-to-app` for web and `rn-bootstrap` for mobile — and bumps `phase` to `scaffolded` once the agent exists, exactly as they do. It still does not bump on subsequent capability additions (a tool, a channel, a skill); those append to `history` only. The meaningful phase path for this topology is `empty → idea_captured → prd_drafted → scaffolded → feature_complete → deployed`: `design_extracted`, `page_generated` and `module_added` are web concepts and are simply never reached.
- `nextjs_version` (web only, optional): `"16"` | string. The Next.js major version. **Canonical default for new projects = `"16"`** (App Router, RSC, async `searchParams`, `use(promise)`, `revalidatePath`, `revalidateTag`). Pages Router (`pages/` dir) is explicitly NOT supported by the dev-flow skill set — use only App Router. If an existing project is Pages Router or pre-16, the web skills refuse to apply. **Next 16.3 is stable** (released 2026-08-03; `latest` on npm) and every Next 16 project should upgrade — most of it is zero-config (dev memory, build cache, native Node streams, TS 7 type checking). **Instant Navigations** is the opt-in part (`cacheComponents` + `partialPrefetching`): it doesn't change this pin, and is adopted deliberately per `data-fetching/SKILL.md` §Instant Navigations.

  ⚠️ **Next.js now has support lines and a scheduled security cadence — the patch digit is not cosmetic.** Since 2026-07-13 Vercel publishes **pre-announced security releases roughly monthly** on the Next.js blog, each naming the highest anticipated severity so teams can plan the upgrade. Two lines are maintained, and **which line is Active LTS moves**: as of 2026-10-03 it is still **16.3.x**, with **15.5.x = Maintenance LTS** — and both lines received the 2026-09-30 patches (16.3.8 and 15.5.27), which is the evidence that both are live, not the label. The 16.2 line stopped at `16.2.12` (2026-07-25) and did **not** receive the August patch — a project sitting on 16.2.x is now unpatched, so "16.2 is Active LTS" was true in July and is wrong today. Re-read the line labels on every pass; don't cache them.

  **Security floor: `16.3.8` (Active LTS) or `15.5.27` (Maintenance LTS) — moved 2026-10-03, read from the GitHub Security Advisory database for `vercel/next.js` and the npm registry. The previous record, `16.3.3`/`15.5.24` of 2026-08-25, is five releases and nine CVEs out of date; the September set is below.** The 2026-07-20 release fixed **9 CVEs — 4 high, 5 medium** — and several land squarely on what these skills prescribe:
  - **CVE-2026-64641** (high, DoS) and **CVE-2026-64646** (medium, unbounded payload) hit *any* App Router app with **at least one Server Action** — i.e. every project we scaffold.
  - **CVE-2026-64642** (high, middleware/proxy bypass) needs Turbopack **and a single entry in `config.i18n.locales`**. Golden rule ② (ship `en` + `it` minimum) means a conforming project has ≥2 locales and is not exposed — one of the rare cases where a style rule is also a security control. A single-locale project must patch.
  - **CVE-2026-64645** / **CVE-2026-64649** (high, SSRF/open redirect) apply when `rewrites()`/`redirects()` or a Server Action build an outbound destination from request-controlled input.
  - **CVE-2026-64643** (medium) discloses Server Action and **`use cache`** endpoint IDs — relevant wherever `data-fetching` recommends `use cache`.
  - **CVE-2026-64647/64648** (medium) are `fetch` **cache confusion**: a response body can be served for a *different* request to the same URL, for calls shaped `fetch(new Request(init), aDifferentInit)`.

  **2026-08-25 — two CRITICAL unauthenticated RCEs, and the release was moved forward for the second.** Both are worth reading because each is neutralised by a rule this contract already imposes, which is the second time that has happened:

- **AVIF image optimization → unauthenticated RCE** ([GHSA-2xp9-vwfh-vxw4](https://github.com/vercel/next.js/security/advisories/GHSA-2xp9-vwfh-vxw4), via `libheif` under `sharp`). Triggered when Next.js optimises an **attacker-controlled AVIF image**. The patch **disables AVIF optimization outright** until upstream fixes it — so a project that configured `formats: ['image/avif']` loses that format silently on upgrade, and one that never enabled it was never exposed. We have never recommended AVIF anywhere; leave it that way until the upstream fix lands.
- **Windows-hosted RCE** ([CVE-2026-75604](https://www.cve.org/CVERecord?id=CVE-2026-75604)) — requires **both Pages Router and App Router** in the same app, without Cache Components, on a **Windows filesystem**. Linux and macOS are unaffected, and **there is no workaround** for affected Windows hosts. A dev-flow project cannot be in this position: the web skills refuse Pages Router outright, so "App Router only" is a security control as well as a style rule — exactly like golden rule ② and CVE-2026-64642.

  **2026-09 — a critical RCE, then eight more CVEs eight days later. This is the pass where the floor had drifted furthest.** Read from the advisory database on 2026-10-03; note several of the September advisories carry a literal `16.3.?` placeholder in their patched-version field, so the floor is taken from the newest patch on the line (`16.3.8`, 2026-09-30) rather than from the advisory text.

- **`next/og` ImageResponse → RCE** ([GHSA-vcvr-r3jv-pc5j](https://github.com/vercel/next.js/security/advisories/GHSA-vcvr-r3jv-pc5j), CVE-2026-94545, **critical**, published 2026-09-22): affects `>= 16.2.0 < 16.3.6`, fixed in **16.3.6**. No dev-flow skill prescribes `next/og`, so a conforming project is unlikely to reach it — but it is a *critical* in a package a designer adds for an OG image without telling anyone, so check `app/**/opengraph-image.tsx` rather than assuming.
- **SSRF in Image Optimization** ([GHSA-cjq9-62q9-8jv4](https://github.com/vercel/next.js/security/advisories/GHSA-cjq9-62q9-8jv4), CVE-2026-94483, **high**): an allow-listed remote URL whose DNS an attacker controls reaches private IPs during optimization. **Conditional on `images.remotePatterns` being configured at all** — with none, the app is not affected — and the stated workaround is to audit those hosts for DNS you do not trust. Any project pulling images from a CMS or an S3-alike is in scope.
- **Cache leak across root param values in nested `'use cache'`** ([GHSA-h694-7cp9-m8p3](https://github.com/vercel/next.js/security/advisories/GHSA-h694-7cp9-m8p3), CVE-2026-103004, medium, **no known workaround**): with `cacheComponents: true`, a `'use cache'` function calling another that reads a **root param** can be keyed without that param, so one entry is written once and reused for *every* value of it. **This is our exact shape, not a hypothetical**: golden rule ② puts `[locale]` in the root segment and `design-md-to-app`'s i18n branch reads it with `next/root-params`, so on an affected version a cached page can be served in the wrong language — and shared cache headers let a CDN spread it. The leaked values are not attacker-chosen; which one wins is whichever invocation wrote first. Only reachable with Cache Components on, which `data-fetching` adopts deliberately for Instant Navigation.
- **Draft Mode content leaking out of a pending `'use cache'` fill** ([GHSA-3w37-wq28-93x7](https://github.com/vercel/next.js/security/advisories/GHSA-3w37-wq28-93x7), CVE-2026-94544, medium): same `cacheComponents` precondition, and it lands on `module-add cms` — a CMS preview is exactly what Draft Mode is for, and the unpublished draft can end up in a regular response or a persisted page.
- **Cache poisoning of SSG/ISR via a root-level catch-all** ([GHSA-mcj8-r9mp-w47p](https://github.com/vercel/next.js/security/advisories/GHSA-mcj8-r9mp-w47p), CVE-2026-94484, medium): a **single unauthenticated crafted request** poisons the shared response cache, giving cross-user content substitution and a persistent DoS. Conditional on a **root-level catch-all page** alongside static or ISR routes — a `[locale]` dynamic segment is not one, but an `app/[[...slug]]` CMS catch-all is, which is a shape `module-add cms` can produce.
- **Metadata image routes ignore `dynamicParams`** ([GHSA-f87g-xv8r-7p7x](https://github.com/vercel/next.js/security/advisories/GHSA-f87g-xv8r-7p7x), CVE-2026-94485, medium): `opengraph-image` / `twitter-image` serve segments deliberately excluded from `generateStaticParams()`. **Conditional on a webpack build** — our scaffolds are Turbopack, so this one is normally out of scope, which is worth knowing before anyone adds a webpack config "just for one plugin".
- **Pages Router SSG/ISR cache poisoning, self-hosted** ([GHSA-4jqv-mc3x-m676](https://github.com/vercel/next.js/security/advisories/GHSA-4jqv-mc3x-m676), CVE-2026-94543, medium): a page's cache entry is replaced with another route's content for every visitor until revalidation. **Pages Router only, self-hosted only** — Vercel-deployed apps are explicitly unaffected, and the web skills refuse Pages Router. That is the **third** time an App-Router-only rule has doubled as a security control (after CVE-2026-64642 and CVE-2026-75604); it is no longer a coincidence worth remarking on so much as a reason the rule exists.
- **Dev-server MCP endpoint information disclosure** ([GHSA-39w2-rjm5-chcv](https://github.com/vercel/next.js/security/advisories/GHSA-39w2-rjm5-chcv), CVE-2026-94486, low): the development server only. Low severity and not a production exposure — but it is a dev-server endpoint an agent may be talking to, so patch rather than reason about it.

**A platform mitigation is not a patch.** For the earlier CVE-2026-23869 Vercel deployed global WAF rules for all hosted projects and still stated the protection "should not be considered a complete substitute for upgrading to a fixed release". Being on Vercel does not exempt a project from the version floor; self-hosted projects have no such net at all. `vercel-deploy` checks this floor before shipping.

Use `null` (not `"none"`) when not yet decided. For `route_groups`, an empty array `[]` means "no route groups, flat routing".

## Folder structure conventions

Skills that scaffold a codebase (`design-md-to-app`, `rn-bootstrap`, `monorepo-bootstrap`) MUST generate the canonical folder structure documented in `docs/superpowers/specs/2026-06-06-folder-structure-refactor.md`. Key rules:

- **Co-location via `_components/`**: page-private components live in `app/<route>/_components/`. The underscore prefix is Next.js convention for non-routable folders. **Web only** — this applies to Next.js (`stack.framework ∈ {next, monorepo}` web side). **Expo Router (`stack.framework = "expo-rn"`) has NO private-folder convention** — every file under `app/` becomes a route, so on mobile screen-private components live in `components/<feature>/` **outside** `app/`, not in `app/<route>/_components/` (see `rn-add-screen` / `promote-component`).
- **Shared components by domain**: cross-route-group shared business components live in `components/shared/<dominio>/<Component>.tsx`. The domain folder name is the business domain (post/, user/, billing/), never generic ("shared"/"common"/"global").
- **UI primitives separate**: shadcn/Base UI/MUI primitives live in `components/ui/`. Never mixed with business components, and never authored there by hand (golden rule 3).
- **Theme system explicit**: ThemeProvider + ModeToggle live in `components/theme/`, NOT loose in `components/`.
- **No `src/` directory**: code lives at project root, alongside config files. Aligned with Vercel commerce, Cal.com, and shadcn templates.
- **Route groups opt-in via `route_groups`**: scaffold only the route groups listed in `stack.route_groups`. Never create empty `(marketing)/` for a project that doesn't need it.
- **Rule of Three for promotion**: components stay at the lowest level until used 3+ times. The `promote-component` skill handles the move + import updates.
- **Cross-platform sharing (monorepo)**: only types, Zod schemas, and pure logic in `packages/shared/`. NEVER JSX. Web and mobile UI are separate (each app has its own `components/`).

## File-format conventions

### `compliance` field (owned by `compliance-audit`, fed from the stack decision and every module)

- `data_categories`: array from `"identity-documents"` | `"tax"` | `"health"` | `"biometric"` | `"minors"` | `"financial"` | `"location"` | `"criminal"` | `"special-category-other"` | `"contact"` | `"usage"`. Written by `data_residency.py decide`.
- `sub_processors`: array of `{ name, service, data, region, region_class ("eu" | "adequacy" | "non-eu" | "global" | "unknown"), transfer ("none" | "adequacy" | "dpf" | "scc" | "bcr" | "derogation" | "unknown"), dpa, us_controlled, eu_alternative, flags[], added_by, updated_at }`. Written by `data_residency.py add` — called by `module-add`, `rn-module-add`, `eve-agent` and `compliance-audit` — and rendered to **`docs/compliance/subprocessors.md`** between markers (text outside them is kept). One register, customer-facing; there is no second copy in `.workflow/`.
- `last_audit_at`, `findings`, `remediated`, `flagged`, `high_risk`, `residency_verified_at`: written by `compliance-audit` (its SKILL.md §`meta.json#compliance` block).

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

**`contract_version`** (integer) is the contract version the file conforms to, stamped by every write
through `meta_io.py` (`CONTRACT_VERSION`, today `1`). A file without it predates the field and is
version-1 compatible; it gains the field on its next write. It changes only with a **breaking** contract
change, and then together with the migration that brings older files up to it — additive changes (a new
optional field, a phase appended to the enum) leave it alone. A script never rewrites a file whose
version is higher than the one it knows: it refuses with exit 2 and leaves the file untouched, since it
would save back fields whose meaning it does not have. Reading such a file is allowed, with a warning
(`show_state.py`).

**`meta_digest`** (`{ "sha256", "checked_phase" }`) is stamped by every write through `meta_io.py`, so a
direct edit — allowed as a fallback — can be told from a scripted write. `sha256` hashes the document's
values without the digest (key order and layout ignored, so reformatting is not an edit); when it no
longer matches, `show_state.py` says the file was changed outside the scripts. `checked_phase` is the
last phase the phase gates checked: only `update_meta.py`, after they pass, moves it forward, and every
other writer carries it over. When `phase` is ahead of it, the phase was set by hand: `show_state.py`
names it, and `set-phase` / `append-history --phase-after` check the gates **from `checked_phase`**, so
a phase typed into the file cannot skip them. A file without the field predates it and is trusted as it
is until its next write.
