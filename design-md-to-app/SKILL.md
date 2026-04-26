---
name: design-md-to-app
description: 'Generate or customize a frontend application from a DESIGN.md (Google design.md spec). Reads the YAML tokens + markdown rationale and produces a working React app whose theme, typography, spacing, radii, and components are pre-styled to match. Supports shadcn/ui (Tailwind-based) and MUI. Integrates with the dev-flow contract: when a `.workflow/` exists, reads `meta.json#stack`, writes the app at the project root (alongside `.workflow/`), and bumps phase to `scaffolded`. Use whenever the user has a DESIGN.md and wants to scaffold an app, set up a theme, customize shadcn/MUI from these tokens, or "use this DESIGN.md to start an app". Trigger on "DESIGN.md → app", "scaffold from design.md", "applica il DESIGN.md a shadcn / MUI", "crea l''app dal DESIGN.md", "init shadcn con questo DESIGN.md". Always ask shadcn vs MUI (with a suggestion) before generating, unless `meta.json#stack.ui` already specifies one.'
---

## Dev-flow contract

This skill participates in the **dev-flow** workflow. When invoked on a project that has a `.workflow/` folder at its root:

- **Input** is `<root>/.workflow/DESIGN.md` (mandatory) and `<root>/.workflow/meta.json#stack` (preferred — if `framework` and `ui` are set, use them; if not, ask the user once and persist).
- **Output** is the codebase scaffold at `<project-root>/`, **alongside** the existing `.workflow/` directory (NOT nested inside it). The framework's standard layout — `package.json`, `app/`, `components/`, `lib/`, etc. — sits at the top so `cd <project-root> && pnpm dev` works the way every developer expects.
- **State** is updated by setting `meta.json#phase = "scaffolded"`, refreshing `updated_at`, and appending an entry to `meta.json#history` describing the run (skill name, inputs, outputs, phase delta).
- **Standalone mode** (no `.workflow/` present) is still supported — fall back to the original "ask the user where to scaffold" behavior. The contract is opt-in.

The canonical contract spec is in `references/contracts.md`. Read it if any of the rules above are unclear.

# DESIGN.md → App

Take a `DESIGN.md` (Google design.md spec — see `references/spec.md`) and produce a working React app where shadcn/ui or MUI components are already themed and ready to compose into the actual product. The user picks the library; this skill turns design tokens into theme code, customizes component variants according to the `components` block, and leaves the user with a runnable scaffold plus a `/showcase` page they can visually verify.

## When this skill applies

Trigger on any of:
- A `DESIGN.md` (or `design.md`) file path or content provided by the user.
- Explicit requests: "fai partire l'app dal DESIGN.md", "scaffold from design.md", "customize shadcn/MUI from this DESIGN.md", "apply these tokens to shadcn/MUI".
- A user describing wanting to start a project where the design system is already specified in `DESIGN.md` form.

If the user has a `DESIGN.md` but only mentions shadcn/MUI without referencing the file, still trigger — they likely want their tokens applied.

## What you produce

A scaffolded (or augmented) **React + TypeScript** project where:

1. The chosen UI library (shadcn/ui or MUI) is installed and configured.
2. **Design tokens** from the YAML frontmatter are wired into the theme:
   - `colors` → CSS variables (shadcn) or `palette` (MUI). **Always two modes**: dark + light, with the source DESIGN.md driving the canonical mode and the other auto-derived (see §Dark + light below).
   - `typography` → typography scale (Tailwind theme extension or `theme.typography`).
   - `rounded` → radius scale (`borderRadius` extension or `theme.shape`).
   - `spacing` → spacing scale (Tailwind extension or `theme.spacing` overrides).
3. **Components** from the `components` block are reflected in:
   - shadcn: variant overrides on the corresponding component (e.g. `button-primary` → `Button` `default` variant in `components/ui/button.tsx`). All shadcn primitives are installed (`shadcn add --all`) so the app comes out of the box ready to compose.
   - MUI: `theme.components.MuiXxx.styleOverrides` and/or `defaultProps`.
4. A `/showcase` page renders every styled primitive so the user can verify the result.
5. Fonts referenced in `typography.fontFamily` are loaded — via `next/font/google` when on Next, via direct `<link>` for Vite/Remix when the font is on Google Fonts, otherwise self-hosted from a local `public/fonts/` (see §Font loading).
6. A `_design-md-mapping.json` is written at the project root showing exactly how each DESIGN.md token resolved to library values — useful for debugging and for the user to verify the mapping at a glance.
7. The markdown body's qualitative rules (gradients, glow, glassmorphism, "do's and don'ts") are encoded as utility classes / theme effects where they translate to CSS, and otherwise summarized in a `STYLE_NOTES.md` so the user — and future agents — can apply them consistently.

**Never invent the spec.** When in doubt about a token shape, valid units, references like `{colors.primary}`, or canonical section ordering, read `references/spec.md` first.

## Workflow

### Step 1 — Locate and parse the DESIGN.md

- **Preferred (dev-flow mode):** if a `.workflow/meta.json` exists at the project root, the DESIGN.md is at `.workflow/DESIGN.md`. Don't search further.
- **Fallback:** if the user gave a file path, use it. Otherwise look for `DESIGN.md` in the project root (case-insensitive). If multiple are found, ask which one.
- Run `python scripts/parse_design_md.py <path>` to get a normalized JSON dump of `{ frontmatter, body_sections, resolved_components }` where token references like `{colors.primary}` are resolved to literal values.
- If parsing fails (malformed YAML, duplicate sections), surface the error and stop. The user must fix the source.

**Two valid input shapes — handle both:**

1. **Frontmatter + body** (the canonical Google design.md spec). The parser returns a populated `frontmatter` dict; `resolved_components` is non-empty. This is the easy path — token values are already structured for you.

2. **Body-only / prose-only** (no `---` fences, the spec written entirely as markdown). The parser returns `frontmatter: {}` and everything goes into `body_sections`. This is now common in the wild — many DESIGN.md files written for AI agents are pure prose with section headings like `## 2. Color Palette`, `## 3. Typography Rules`, etc.

   When `frontmatter` is empty, **don't stop and ask for YAML**. Extract tokens directly from the body sections. Map sections to token categories by their heading (case-insensitive partial match):
   - "Color" / "Palette" / "Colors" → colors
   - "Typography" / "Type" / "Fonts" → typography levels + font families
   - "Component" / "Components" / "Cards" / "Buttons" → component variants
   - "Layout" / "Spacing" / "Grid" → spacing scale, container widths
   - "Radius" / "Shapes" / "Border" → radius scale
   - "Depth" / "Elevation" / "Shadow" → shadow utilities
   - "Do's and Don'ts" / "Notes" / "Known Gaps" → STYLE_NOTES.md content + mode/font opt-outs

   Read each section as the source of truth for its category — extract hex values from prose, copy typography tables, lift component prose specs verbatim. Document this extraction path explicitly in `_design-md-mapping.json` under a top-level `extraction_method` field so a reviewer can see what came from prose inference vs. from a structured field.

### Step 2 — Pick the library

Ask the user once: **shadcn/ui or MUI?** Offer a recommendation based on `references/library-choice.md`. Common heuristics:

- Highly custom visual identity (glassmorphism, brutalist, editorial, distinctive shapes) → **shadcn** wins, because every component is owned source.
- Material-leaning, dashboard, enterprise CRUD, lots of data tables / dialogs out of the box → **MUI** wins.
- Tailwind already in use, or the user wants utility-first → shadcn.
- Heavy Material Icons / Material Design heritage → MUI.

State the suggestion with a one-line rationale ("Suggerisco shadcn perché il tuo DESIGN.md descrive vetro/glassmorphism custom, che si esprime meglio con CSS owned"), then accept whatever the user picks.

### Step 3 — Pick the project target, framework, and scope

Ask the user **two** things in this step:

**3a. Project target**

- **Dev-flow mode** (`.workflow/meta.json` exists): scaffold the codebase **at `<project-root>/` alongside `.workflow/`** (e.g., `pnpm create next-app .` from the project root). Do NOT create a sub-directory like `app/` or `code/` to nest the codebase. The framework comes from `meta.json#stack.framework` if set, otherwise ask. The user does **not** pick the path — the contract pins it.
- **New project (standalone)** → ask which framework: **Next.js (App Router)** [default], **Vite + React**, or **Remix**. Then scaffold in a folder of the user's choice with TS + the chosen UI library wired in (see the relevant mapping reference for exact init commands).
- **Existing project?** → ask for the project root, then detect the framework by inspecting `package.json` and the file layout:
  - Next.js → `next` in deps + `app/` or `pages/`.
  - Vite + React → `vite` + `@vitejs/plugin-react` in deps.
  - Remix → `@remix-run/*` in deps.
  - Anything else → tell the user what you found and ask how to proceed (most often: "write the theme files anyway and I'll wire them up").

The mapping references describe the framework-specific glue (font loading, root layout/provider wiring, where to put `theme.ts` / `globals.css`). Don't assume Next.js paths — branch on the detected framework.

**3b. Scope: full scaffold vs. theme-only**

Ask: **"Vuoi lo scaffold completo (showcase + STYLE_NOTES + provider wiring) o solo le patch al tema?"** Two modes:

- **Full scaffold** (default for new projects): everything described in §What you produce — theme files + component overrides + `/showcase` route + `STYLE_NOTES.md` + `_design-md-mapping.json` + provider wiring.
- **Theme-only patch** (recommended for mature existing projects): write *only* the design-token files as a reviewable diff:
  - shadcn: `globals.css`, `tailwind.config.ts`, the `cva` blocks of components named in DESIGN.md.
  - MUI: `lib/theme.ts` only (or wherever the theme already lives).
  - **Plus** `_design-md-mapping.json` and `STYLE_NOTES.md` because they're cheap to add and useful for the reviewer.

  In theme-only mode, **don't** create `/showcase`, **don't** install new dependencies, **don't** touch the root layout/provider unless the user explicitly asks. The goal is a diff a senior reviewer can read in five minutes.

Default the choice based on context: existing project with extensive code → suggest theme-only; new project or empty repo → full scaffold. State the suggestion in one line, accept whatever the user picks.

If overwriting any existing theme/config (`globals.css`, `tailwind.config.*`, `theme.ts`), show a diff of what will change and confirm before writing.

### Step 4 — Apply the chosen mapping

Read the relevant mapping reference and follow it:

- shadcn → `references/shadcn-mapping.md` — **note**: in dev-flow mode, the recommended path is the **token-first install via `registry.json`** (see the dedicated section in that reference). Three steps: scaffold framework → emit `registry.json` from DESIGN.md tokens (use `scripts/build_registry.py`) → run `pnpm dlx shadcn@latest init ./registry.json --yes` followed by `pnpm dlx shadcn@latest add --all --yes`. **`add --all` stays** — every primitive lands in `components/ui/*` and gets customized in the next step per the DESIGN.md `components` block (`cva` edits).
- MUI → `references/mui-mapping.md`

Each reference describes:
- the exact files to write per framework (Next.js / Vite / Remix),
- how each token category maps,
- which components to install/override (shadcn: `add --all` so the user has the full kit pre-themed; MUI: theme overrides cover all primitives by default),
- how to encode the qualitative rules from the markdown body that **can** be expressed in code (e.g. radial background gradients, glass surfaces with backdrop-filter, ambient glow as a custom utility),
- what to put in `STYLE_NOTES.md` for the rest (e.g. "Use radial gradients for hero backgrounds — see DESIGN.md §Layout").

The asset templates in `assets/shadcn/` and `assets/mui/` are starting points — read them, fill the placeholders with resolved tokens, write to disk. Do not paste them verbatim if the DESIGN.md doesn't define a value; fall back to library defaults rather than invent.

After writing the theme files, also write `_design-md-mapping.json` at the project root. This is a debug artifact: a JSON dump of `{ token_path → resolved_value → library_target }` for every color/typography/component that was mapped, plus the list of fallbacks that were used because the DESIGN.md didn't define a value. Add `_design-md-mapping.json` to `.gitignore` if the user wants to keep it local-only — by default leave it tracked since it's useful for reviewers.

### Step 4.3 — Library primitive priority (mandatory, supersedes custom components)

**Rule**: when the chosen UI library (shadcn or MUI) ships a primitive for the pattern, **use it**. Don't roll custom.

This is the single most-violated rule in scaffolders. The skill installs `shadcn add --all` (or MUI's full theme), giving the project access to dozens of pre-built, accessible, mobile-aware, theme-integrated primitives — and then the skill writes a custom 100-line `<Sidebar>` from scratch using `<aside>` + flex + lucide icons. The custom version is worse on every axis: less accessible, no mobile drawer, no collapsed state, no tooltip support, no keyboard shortcuts, no persistent state.

#### The mandate

Before authoring **any** component beyond the simplest (Eyebrow, simple text wrappers), **scan `components/ui/*.tsx`** for a primitive that matches the pattern. Common shadcn primitives projects miss:

| Pattern in DESIGN.md / Figma | shadcn primitive | What you get for free |
|---|---|---|
| Vertical app sidebar (icon-only or expanded) | `Sidebar` + `SidebarProvider` + `SidebarMenu*` | Collapsible state (icon ↔ expanded), mobile drawer via Sheet, tooltips on hover when collapsed, `Cmd+B` toggle, persistent state in cookies, active-route detection via context |
| Top navigation menu with hover dropdowns | `NavigationMenu` | Keyboard navigation, ARIA menu, hover delays |
| Dialog / modal | `Dialog` + `AlertDialog` | Focus trap, Escape close, scroll lock, portal |
| Hamburger drawer (mobile nav) | `Sheet` | Slide-in animation, focus management, swipe close |
| Autocomplete / type-ahead | `Combobox` (Command + Popover) | Async search, keyboard nav, fuzzy match |
| Command palette / cmd+k | `Command` (CMDK) | Categorized search, keyboard, animations |
| Date range picker | `Calendar` + `Popover` | Locale-aware, keyboard nav, range selection |
| Tabs (route-driven or panel) | `Tabs` | ARIA roles, keyboard nav, animations |
| Sheet / slide-out panel | `Sheet` | Right/left/top/bottom variants |
| Toast / notification | `Toast` (Sonner) | Stacking, swipe-dismiss, ARIA live region |
| Form with validation | `Form` + `react-hook-form` adapter | Zod-validated, inline errors, accessible labels |
| Table with sort/filter | `Table` (+ optional `tanstack-table` recipe) | ARIA grid, sortable columns, virtualizable |
| Combobox toggle group | `ToggleGroup` | Single/multi select, keyboard |
| Resizable panel layout | `Resizable` (react-resizable-panels) | Saved sizes, accessible, keyboard resize |
| Right-click menu | `ContextMenu` | Submenu, keyboard, ARIA |
| Tooltip | `Tooltip` + `TooltipProvider` | Delay, position, accessible |
| Slider | `Slider` | Range / single, keyboard, ARIA |
| Progress bar | `Progress` | ARIA progressbar, animations |
| Skeleton loading | `Skeleton` | Pulse animation, theme-aware |
| Avatar + fallback initials | `Avatar` + `AvatarFallback` | Image error fallback, accessible alt |
| Pagination controls | `Pagination` | Keyboard, ellipsis, ARIA |

The same logic applies to MUI: prefer `Drawer`, `AppBar`, `Modal`, `Autocomplete`, `DatePicker`, `Tabs`, `Snackbar`, `Table`, etc. over `<div>` constructions.

#### When custom IS appropriate

- The pattern doesn't exist in the library (e.g., a brand-specific WordmarkFooter, a project-specific KpiCard with a particular icon-badge + progress-bar shape).
- The library's primitive is too rigid for what the DESIGN.md describes (rare — usually you compose primitives, not replace them).
- The component is so trivial it'd be 5 lines either way (Eyebrow, simple section wrappers).

In all other cases: **default to the primitive**. The custom version is technical debt the user has to maintain forever.

#### Anti-patterns

- ❌ Writing `<aside class="flex flex-col w-64 ...">` when `Sidebar` exists.
- ❌ Building a hamburger drawer with `useState` + `<div className="fixed inset-0">` when `Sheet` exists.
- ❌ Authoring a "command palette" lookalike with `<input>` + `useEffect` when `Command` exists.
- ❌ Custom date pickers, custom modals, custom tooltips, custom comboboxes — all have shadcn primitives.

#### How to apply at scaffold time

1. Read the DESIGN.md / screenshot to identify the pattern (sidebar, modal, picker, etc).
2. **Grep `components/ui/` for a matching primitive** (`grep -l Sidebar components/ui/*.tsx`).
3. Check the primitive's exports + usage docs at https://ui.shadcn.com (or the primitive's source).
4. Compose with the primitive. Style overrides via `className` + the design tokens already in `globals.css` make it brand-faithful without re-implementing the behavior.

When in doubt: open `components/ui/<primitive>.tsx` and read its API. If the API supports your pattern, use it.

### Step 4.4 — Folder convention (mandatory)

Once `add --all` lands the shadcn primitives, the project has too many "where does this go?" decisions waiting to happen. **Pin the convention now**, before writing application code, so every subsequent skill (and human) knows where to put things.

The Next.js App Router 2026 convention this skill enforces:

| Path | What lives here |
|---|---|
| `components/ui/` | shadcn primitives. **Untouched** after `add --all` except for `cva` variant customization per DESIGN.md `components` block. |
| `components/<group>/` (root) | **Cross-route shared**: layout shells (`app-shell`, `site-top-nav`, `wordmark-footer`), brand components, business components reused on 2+ routes. Group by domain when the count grows: `components/site/`, `components/marketing/`, `components/forms/`. |
| `app/<route>/_components/` | **Page-scoped**: sections unique to ONE route, NOT reused. The `_` prefix is a Next.js privacy marker — Next does not turn `_components` into a route. |
| `lib/server/<domain>.ts` | Server actions for a domain (`practices.ts`, `clients.ts`, `deadlines.ts`). Always start with `"use server";`. |
| `lib/queries/<domain>.ts` | Server-side data **reads** (separate from actions for clarity). Async functions called from RSC. |
| `lib/db/` | Drizzle (or equivalent) schema + connection — owned by `module-add db`. |
| `lib/auth.ts` + `lib/auth-client.ts` | better-auth — owned by `module-add auth`. |
| `lib/utils.ts` | Pure utilities (`cn()`, formatters, date helpers). |
| `hooks/` | Custom React hooks shared cross-route (`useDebounce`, `useOptimistic` wrappers, etc.). |

**Key rules**:

- **Don't put cross-route shared components inside `app/_components/`**. The `_` is a routing concern, not a "shared" marker. If a component is used on 2+ routes, it goes in `components/<group>/`.
- **Don't put server actions inside `app/`**. They belong in `lib/server/<domain>.ts` so they can be imported from any route or component without circular imports.
- **One file per business domain in `lib/server/`** — `practices.ts` not `practice-actions.ts`. The `lib/server/` folder is the namespace; don't repeat it in the filename.
- **`components/` first, then a group**. A new project starts with `components/site/` (layout shells); add `components/forms/`, `components/marketing/`, etc. as you grow. Never have flat 30+ files under `components/`.

When `screenshot-to-page` builds a new route and notices it's reusing a component from another route, **promote** it: move from `app/<route>/_components/` to `components/<group>/`, update imports.

When this skill scaffolds the project, **create at least the folder skeleton**:

```
components/
├── site/         # contains: app-shell.tsx, site-top-nav.tsx, wordmark-footer.tsx,
│                 #           theme-provider.tsx, mode-toggle.tsx, nav-item.tsx,
│                 #           dashboard-card.tsx (if dashboard exists), placeholder-page.tsx
└── ui/           # populated by `shadcn add --all`
lib/
├── server/       # empty initially, populated by Step 4.6 stub + by feature work
├── queries/      # empty initially
└── utils.ts      # populated by `shadcn init`
hooks/            # empty initially
```

### Step 4.5 — Generate placeholder routes for declared navigation

If the DESIGN.md, the source Figma screenshots, or the PRD describes a primary navigation (sidebar / topbar / nav menu) with N items, **every navigable item must resolve to a real route** in the scaffold. A nav that points to `<Link href="/clienti">` and that link goes to `/_not-found` is a worse first impression than no nav at all — it makes the user think the app is broken.

This step is **mandatory in dev-flow mode** when a navigation is detected. It is independent of `screenshot-to-page`: that skill builds **one** rich page from a single screenshot. This step builds **stub** pages for the remaining nav items so nothing 404s.

#### Detection

Look for navigation declarations in this order:

1. The **first screenshot** in `.workflow/screenshots/` (typically the dashboard / home) usually shows the primary nav. Identify the items visually.
2. The DESIGN.md `## Components` section, if it documents nav items.
3. The PRD's user stories, which often imply navigation (e.g., "as a user I want to see /clienti, /pratiche, /scadenze").
4. If unclear, **ask the user once**: "Quali voci di navigazione iniziali devo creare come placeholder? (es. /clienti, /pratiche, /scadenze, /impostazioni)".

#### What to write

For each nav item that is **not** the primary screen (which `screenshot-to-page` will build properly), generate a stub at the canonical framework path:

- Next App Router: `<project-root>/app/<slug>/page.tsx`
- Vite/Remix/Astro: equivalent path per `references/<framework>-<ui>.md`

The stub:

- Renders inside the same `<AppShell>` (or layout component) used by the home page, so the sidebar + topbar are consistent.
- Sets `active="/<slug>"` so the sidebar item highlights correctly.
- Shows a **"empty-state" card**: an icon (relevant to the section), the route name as title, a 1-sentence description of what the page will eventually do, and a CTA button (no-op for now).
- Optionally: a **"Task pianificati"** list inside the empty state, pulled from `tasks.md` for that user story (e.g., for `/clienti`, list the 3 tasks tagged with the relevant user story). This makes the placeholder useful — the user sees what's coming.
- Does **not** include real data, real forms, or any business logic.

#### Reusable placeholder component

Generate a single `<PlaceholderPage>` component that all stubs use, so:
- The visual consistency is automatic.
- Removing a stub later (when the real page lands) is replacing one file, not refactoring.
- The component itself becomes a shadcn-themed example that proves the design system works on a non-trivial layout.

#### What this step is NOT

- **Not feature implementation.** Stubs are visual scaffolding. Real CRUD lives in tasks owned by the user (or by `screenshot-to-page` when a screenshot becomes available).
- **Not a substitute for `screenshot-to-page`.** When the user has a screenshot for `/clienti`, `screenshot-to-page` replaces the stub with the real page.
- **Not for "every imaginable route".** Only for items declared in nav. A page like `/admin/users/new` is too deep — it's a feature task, not a top-level nav stub.

After writing stubs: rerun `pnpm run build` to confirm everything still compiles.

### Step 4.5b — Read `.workflow/screenshots/` before authoring the home page (mandatory)

The single most common scaffolder failure mode: **generating a generic home page when the source Figma file has a canonical product layout in screenshots/**. The user expects the scaffold to **mirror what's in the Figma**, not invent a homepage from design tokens alone.

This step pins the discipline.

#### The protocol

1. **List `.workflow/screenshots/`.** If empty, skip — generate the default home from design tokens (the Constellation marketplace pattern).

2. **For each screenshot, classify it by file name + visual content** (you can `Read` each PNG — the Read tool returns image content):
   - `cover` / `welcome` / `intro` → marketing/onboarding frames, not the canonical product layout
   - `style-guide` / `design-system` → reference for the `/showcase` page, not the home
   - `inspiration` / `dashboard` / `home` / `app` / `product` → **CANONICAL product layout** — this is what the home page must mirror
   - `components` / `cards` / `<component-name>` → component-level references, can be borrowed for cards inside other pages

3. **If a canonical layout exists, READ it visually** with the Read tool. Then identify:
   - **Layout pattern**: sidebar + main? topbar only? full-width hero? split-pane?
   - **Information density**: how many cards/widgets per row? what kind?
   - **Specific components**: the exact KPI labels, the exact chart types, the exact statuses, the exact navigation items
   - **Interactive surfaces**: search input position, profile avatar, primary CTA, mode toggle

4. **Build the home page faithful to that screenshot.** Use the exact metric names ("Total Orders Today" not "Revenue"), the exact chart types (radar + area + pie + bar + heatmap, not generic bars), the exact sidebar pattern (vertical 64-72px wide if that's what the screenshot shows). The design tokens are how you style it; the Figma frame is how you compose it.

5. **State the source explicitly** in the hand-off message: "Home page mirrors the `inspiration-dark-dashboard.png` frame from Figma — sidebar + 4 KPI cards (Orders/Conversion/Clients/Revenue Ratio) + 5 chart types (radar, area, pie, bar, heatmap)."

#### Why this is mandatory

When the user provides a Figma URL, they expect the scaffold to look like the Figma. A generic dashboard "themed with the design tokens" misses the point — the design system isn't a paint job, it's a layout vocabulary too. The icons in KPI cards, the progress bars, the way the radar chart relates to the area chart — these aren't decoration. They're the design.

#### When to fall back to a generic home

- `.workflow/screenshots/` is empty AND no PROJECT.md describes a specific product (rare).
- The screenshots are all marketing / cover / intro frames with no canonical product layout.
- The user explicitly says "ignore the Figma frames, build a generic dashboard for now".

In these cases, default to the generic pattern but **state it in the hand-off**: "No canonical product layout found in screenshots/ — generated a generic home with the design tokens. Run `screenshot-to-page` later when you have a target frame."

#### Anti-patterns

- ❌ Generating a generic 4-card KPI grid when the Figma shows specific KPI cards with icon badges + progress bars.
- ❌ Using a horizontal pill nav when the Figma shows a vertical icon sidebar.
- ❌ Inventing chart types (the user got "bars" when the Figma had radar + area + pie + bar + heatmap).
- ❌ Skipping the `Read` step on the canonical PNG and writing the layout from imagination.

### Step 4.6 — Theme system + dark/light toggle (mandatory)

`registry.json` already produces both `cssVars.light` and `cssVars.dark` blocks. Without a runtime toggle, the dark variant is dead code. **Wire the toggle as part of the scaffold** — every project gets dark mode for free, plus a keyboard shortcut.

#### Install + components

```bash
pnpm add next-themes
```

Generate two components in `components/<group>/`:

**`components/<group>/theme-provider.tsx`** — a thin client wrapper around `next-themes`:

```tsx
"use client";
import * as React from "react";
import { ThemeProvider as NextThemesProvider } from "next-themes";

export function ThemeProvider({
  children,
  ...props
}: React.ComponentProps<typeof NextThemesProvider>) {
  return <NextThemesProvider {...props}>{children}</NextThemesProvider>;
}
```

**`components/<group>/mode-toggle.tsx`** — a client button with global keyboard shortcut on `D`:

The component must:
- Render a `<Button variant="ghost" size="icon">` showing `<Sun>` when the resolved theme is `dark` and `<Moon>` when light.
- Use `useTheme()` from `next-themes`.
- Use a `mounted` state guard to avoid SSR/CSR mismatch (return an inert placeholder until mounted).
- Register a `keydown` listener on `window` that toggles theme when `D` is pressed AND:
  - No modifier keys (Cmd / Ctrl / Alt) are held.
  - The user is NOT typing — exclude `INPUT`, `TEXTAREA`, `SELECT`, `contentEditable`. **This rule is critical** — without it, every time the user types a `D` in a form, the theme flips.
- Show a tooltip / `aria-label` mentioning the shortcut: `aria-label={\`Toggle theme (current: ${resolvedTheme}). Shortcut: D\`}`.

A reference implementation lives at `references/mode-toggle.template.tsx` — copy-and-rename instead of writing from scratch.

#### Wiring

In `app/layout.tsx`:

```tsx
import { ThemeProvider } from "@/components/site/theme-provider";

<html lang="..." suppressHydrationWarning>
  <body>
    <ThemeProvider attribute="class" defaultTheme="light" enableSystem disableTransitionOnChange>
      {children}
    </ThemeProvider>
  </body>
</html>
```

`suppressHydrationWarning` on `<html>` is required by `next-themes` to avoid React warnings on the first paint when the theme class is applied.

Mount `<ModeToggle />` in **both** the public site shell (`SiteTopNav` next to the primary CTA) and the internal app shell (`AppShell` topbar next to notifications/help). Users hit it from either context.

#### Default mode

Use `defaultTheme="light"` unless the source DESIGN.md explicitly declares dark as canonical (some editorial brands do — Aetherfield is light-only, Notarius is light-only, devops-graphite is dark-by-default). `enableSystem` lets the user's OS preference win on first visit.

### Step 4.7 — Server actions scaffold (mandatory)

Scaffold **at least one** server-action file at `lib/server/<domain>.ts` so the next developer (or skill) has a referenceable pattern to copy. Pick the domain from the PRD's most-prominent user story (for Notarius: `practices.ts`; for an e-commerce: `orders.ts`; for a CRM: `contacts.ts`).

#### Install dependencies

```bash
pnpm add zod
```

#### File template

The scaffold must include:

1. `"use server";` directive at the top.
2. A typed `ActionResult<T>` discriminated union returned by every action — never throw across the server boundary.
3. Zod schemas for input validation (one per action), grouped at the top of the file.
4. A `flattenZod()` helper that converts `z.ZodError` into `{ message, fieldErrors }` for form-friendly responses.
5. 2–3 actions covering the verb spread the user is most likely to need:
   - **Create**: validate input → insert → `revalidatePath(<list-route>)` → return `{ ok: true, data: { id } }`.
   - **Update**: validate input → update by id → `revalidatePath` for both list and detail → return.
   - **Archive / soft-delete**: prefer over hard delete; same shape.
6. A `getCurrentTenantId()` helper stub that throws "not yet wired — implement after `module-add auth` runs" — leaves a clear TODO without lying about authorization.
7. A comment block at the top documenting the convention (return shape, throw policy, revalidatePath usage, tenant scoping).

A reference implementation lives at `references/server-action.template.ts` — copy-and-rename. The template is wired to the Drizzle schema produced by `module-add db`.

#### Why this is mandatory

Server actions are the load-bearing connection between forms and the database. Without a reference file, every developer invents their own return shape, error handling, and validation pattern. A single scaffolded file pins the convention for the whole project.

### Step 4.8 — Robustness scaffold (mandatory)

Five tiny files that make the difference between "demo-grade scaffold" and "senior fullstack scaffold". Every project gets them — they take ~3 minutes to write and prevent entire categories of production incidents.

Write each file from its template under `references/`:

| File | Template | Why it matters |
|---|---|---|
| `app/error.tsx` | `references/error.template.tsx` | Root error boundary. Without it, a single uncaught render error blanks the whole app to a Next default page that leaks `error.message` to the user. The template scrubs the message, shows a clean fallback with `reset()`, and surfaces `digest` for log lookup. |
| `app/loading.tsx` | `references/loading.template.tsx` | Streaming-RSC suspense fallback. Without it, navigating to a route that does any async work hangs on a blank page until the server finishes. The template uses shadcn `<Skeleton>` to render a content-shaped placeholder. |
| `lib/env.ts` | `references/env.template.ts` | Zod-validated environment at boot. Without it, a missing `DATABASE_URL` only blows up the first time a request hits the DB layer — often in production, never in dev. The template fails fast with a clear message at module-eval time. **Import `env` from this file** instead of reading `process.env` ad hoc. |
| `lib/queries/<domain>.ts` | `references/queries.template.ts` | Counterpart to `lib/server/<domain>.ts`. **Reads** live here (called from RSC), **mutations** live in `lib/server/`. Keeps the boundary clean — read-from-anywhere, mutate-only-from-actions. |
| `next.config.ts` | `references/next-config.template.ts` | Security headers (CSP, X-Frame-Options DENY, X-Content-Type-Options nosniff, Referrer-Policy strict-origin-when-cross-origin, Permissions-Policy minimal, HSTS). Default Next config has none of these. The template ships sane defaults; the user tightens CSP later if they introduce inline scripts. |

These are **not optional** in dev-flow mode. A scaffold without `app/error.tsx` is a scaffold that crashes loudly the first time a server action throws. A scaffold without `lib/env.ts` is a scaffold where missing secrets are discovered in production.

#### Wiring notes

- `lib/env.ts` should be imported by `lib/db/index.ts`, `lib/auth.ts`, and any other module that reads env. The `module-add db` and `module-add auth` references already produce code that reads `process.env.DATABASE_URL` — when this skill runs **before** those, they pick up `env.DATABASE_URL` automatically; when they run after, do a quick pass on the existing files to swap `process.env.X` → `env.X`.
- `next.config.ts` may already exist (Next scaffolds it). **Merge** the security headers block into the existing config — don't overwrite settings the user/scaffold has already chosen.
- The `lib/queries/` folder is created empty alongside `lib/server/` in Step 4.4. The queries template is dropped in for the same domain as the server action template (e.g., `lib/queries/practices.ts` next to `lib/server/practices.ts`).

### Step 4.9 — Mobile-first responsive (mandatory)

The DESIGN.md §Responsive Behavior (or equivalent prose section) is **not optional reading**. Every project ships with non-trivial mobile usage; a desktop-only scaffold is a half-shipped scaffold. Yet the failure mode is consistent: skills generate beautiful desktop layouts, then drop responsive concerns to "I'll add `lg:` modifiers later" — and "later" never happens.

This step pins **mobile-first** as the writing discipline, not as an afterthought.

#### The mobile-first writing discipline

For every component you author:

1. **Write the mobile layout first.** The base classes — no `sm:`, `md:`, `lg:`, `xl:` prefix — describe the mobile experience. THEN add desktop modifiers as overrides:
   ```tsx
   // Right: base = mobile, lg: = desktop override
   <div className="grid grid-cols-1 gap-6 lg:grid-cols-3 lg:gap-12">

   // Wrong: base = desktop, mobile is afterthought via override
   <div className="grid grid-cols-3 gap-12 sm:grid-cols-1 sm:gap-6">
   ```

2. **Read the DESIGN.md §Responsive Behavior table** and match its breakpoints. Most DESIGN.md files declare 3-4 breakpoints:
   - Mobile ≤ 767px
   - Tablet 768–1023px
   - Desktop ≥ 1024px
   - Wide ≥ 1440px (optional)

   Map them to Tailwind:
   - default (no prefix) → mobile (≤640)
   - `md:` → 768+ (tablet)
   - `lg:` → 1024+ (desktop)
   - `xl:` → 1280+ (wide)

   Don't invent custom breakpoints — Tailwind's defaults align with the typical DESIGN.md scale.

3. **Apply the DESIGN.md's collapsing strategy.** A typical DESIGN.md will say things like:
   - "Service grid: asymmetric constellation → 2-up → 1-up stack on mobile"
   - "Hero headline drops from 64px to ~40px on mobile"
   - "Footer 4 columns → 1 column accordion on mobile"
   - "Spacing compresses from 128px to 48px"
   - "Nav full pill → compact pill with hamburger"

   Each of these is a concrete Tailwind class set:
   - `hero h1`: `text-[40px] lg:text-[64px]` (or use `clamp()` in inline style)
   - `service grid`: `grid-cols-1 sm:grid-cols-2 lg:grid-cols-4`
   - `section padding`: `py-12 lg:py-32`
   - `footer columns`: collapse to `<details>` accordion below `md:` OR stack vertically with `grid-cols-1 md:grid-cols-4`
   - `nav`: hide primary links below `md:`, show hamburger button instead

4. **Touch target minimums (WCAG 2.5.8)**: every interactive element ≥ 44×44px. Tailwind's `h-11` (44px) is the minimum for buttons and tap-friendly icons. Avoid `h-9` or `h-10` for primary tap targets on mobile.

5. **Hamburger nav** for any nav with 4+ primary links. The DESIGN.md typically describes "Mobile Nav: full-screen overlay with primary links stacked vertically" — implement that, don't just hide the links. Use shadcn's `Sheet` primitive for the slide-in panel.

6. **Mobile-only visual elements**: orbital arcs / decorative SVGs / asymmetric layouts often work only at desktop widths. The DESIGN.md will say so explicitly ("Orbital arcs are removed on mobile — they only work with asymmetric placement"). Hide them at small viewports with `hidden lg:block`.

#### The 375px verification (best-effort but mandatory to attempt)

Before declaring the scaffold done, **verify at 375px viewport** (iPhone SE / 12 mini width, the conservative lower bound):

1. **If a browser tool is available** (Playwright MCP, Chrome MCP, Claude_Preview, etc.):
   ```
   browser_resize(width: 375, height: 812)
   browser_navigate(url: "http://localhost:3000")
   browser_take_screenshot()
   ```
   Then visit `/`, `/showcase`, and 1–2 placeholder routes. Spot-check:
   - No horizontal scroll
   - All primary nav reachable (hamburger visible)
   - Hero headline doesn't overflow (clamps under 40px)
   - Cards stack vertically
   - Footer columns either accordion-collapse or stack 1-up
   - All buttons ≥ 44px height
   - Showcase 9-section structure intact, just narrower

2. **If no browser tool is available**: state explicitly in the hand-off:
   > ⚠ **Mobile verification pending**: I couldn't open a browser at 375px to verify the layout. Run `pnpm dev` and check `http://localhost:3000` in DevTools mobile emulation (375×812) before considering the scaffold done.

   And surface the same warning in the final summary.

3. **Do not** declare done from a desktop-only screenshot. "Mobile works" is not the same as "mobile compiles".

#### The mobile-first checklist (apply before moving to Step 5)

- [ ] DESIGN.md §Responsive Behavior section read and consumed
- [ ] All grids start `grid-cols-1` and add larger breakpoints as overrides
- [ ] All hero/section padding starts small and grows: `py-12 lg:py-24`
- [ ] All hero headlines use `clamp()` or `text-[Xpx] lg:text-[Ypx]`
- [ ] Touch targets ≥ 44×44px (`h-11` minimum on tappable elements)
- [ ] Nav with 4+ links uses hamburger pattern below `md:` (Sheet primitive)
- [ ] Decorative SVGs (orbital arcs, etc.) hidden below `lg:` if the design intent is asymmetric placement
- [ ] Footer collapses appropriately (accordion or vertical stack)
- [ ] Verified at 375px viewport (or stated as pending)

Skipping any of these = scaffold is desktop-only and the user has to fix it before shipping.

### Step 5 — `/showcase` page (mandatory in dev-flow mode)

It is not optional, not "nice to have", not skippable for time. The reason: without `/showcase` the user has no way to visually verify that the DESIGN.md tokens landed correctly in the running app. Every primitive that shadcn `add --all` installed is dark code unless `/showcase` proves it's themed. Skipping `/showcase` and declaring the scaffold "done" is a contract violation.

**The only valid skip** is **theme-only mode**, where the user explicitly opted out of any new pages — in that case the verification is a code review of the diff, not a visual check.

In full-scaffold mode (the default): generate `/showcase` (or `/design-system`).

#### Required structure (in this exact order)

The `/showcase` page is **not a free-form gallery**. It is a fixed sequence of 9 sections. Skipping a section, reordering them, or replacing them with shadcn primitives stripped of context is a contract violation.

**The structural template is non-negotiable.** Every showcase across every project must use the same skeleton — only the brand-specific contents inside change. See `references/showcase-template.md` for the full HTML pattern (vendored from airbnb-clone, aetherfield, devops-graphite, notarius-crm — four projects that converge on the same shape).

#### Site-shell (Step 5a, mandatory)

The `/showcase` page is wrapped in a **site-shell**, NOT in the app's internal AppShell:

```tsx
export default function Showcase() {
  return (
    <>
      <SiteTopNav />
      <main className="bg-surface text-on-surface">
        { 9 sections here }
      </main>
      <WordmarkFooter />
    </>
  );
}
```

The site-shell has two components, both **mandatory** and both written by this skill alongside `/showcase`:

**`<SiteTopNav>`** at `components/site/site-top-nav.tsx`:
- Container `mx-auto max-w-[1280px] px-6 lg:px-12 h-14 flex items-center gap-8`.
- Brand on the left: small logo box (`size-7 rounded-md bg-primary text-surface`) with the project initial + project name in `text-[14px] font-semibold`.
- Nav links in the middle: 4–6 links to the project's main routes (`/`, `/showcase`, plus 2–4 product routes), `text-[14px] text-on-surface-variant hover:text-on-surface`.
- Right side: a secondary text link (e.g., `Accedi` / `Sign in`) + the project's primary CTA as a small `<Button>` ("Nuova pratica" / "Reserve" / "Deploy").
- Background `bg-surface` with `border-b border-outline`.

**`<SiteFooter>`** at `components/site/site-footer.tsx` (or `wordmark-footer.tsx` if the wordmark variant is chosen — see below):

The footer **must be DESIGN.md-faithful**. Hardcoding the same wordmark template for every project is a contract violation — Mastercard-style design systems describe a 4-column link grid with a conversational H2; minimal portfolio designs may want a one-line footer; editorial brands use the giant wordmark. **Read the DESIGN.md before writing the footer.**

#### Decision flow (mandatory in this order)

1. **Look in DESIGN.md for an explicit footer specification.** The likely sections are §4 Components → Footer, §Layout, §Footer (top-level), or a `components.footer` block in YAML frontmatter. If found, generate the footer described there — colors, padding, structure, copy patterns. **The DESIGN.md is the spec.**

2. **If the DESIGN.md describes a footer with named columns + conversational H2** (Mastercard pattern, common in institutional brands): generate a `SiteFooter` matching the spec — typically:
   - Background: the spec's stated footer color (often a dark warm-black, sometimes a lifted brand surface)
   - Layout: large left-aligned conversational H2 ("We're always here when you need us"-style), then a 4-column link grid below with uppercase muted column headers
   - Bottom row: copyright, legal links, optional country/language selector pill, social icons
   - **Skip the giant lowercase wordmark** unless the spec specifically asks for it

3. **If the DESIGN.md is silent on the footer, OR explicitly describes a wordmark/marquee footer**, default to the WordmarkFooter pattern below. Editorial / portfolio / brand-focused projects (Aetherfield, Notarius, Wisely-style) live here — a giant lowercase project name **is** the footer's identity.

4. **Always include the mono micro-row at the bottom** regardless of which pattern: two-column flex with `font-mono text-[11px] tracking-wide uppercase text-on-surface-variant` — left "© YEAR Project · regional/legal note", right "Generated by design-md-to-app from .workflow/DESIGN.md". This is the audit signature.

#### WordmarkFooter pattern (the fallback)

When DESIGN.md is silent or asks for a wordmark, write `wordmark-footer.tsx`:

- Background: a soft branded surface — for projects with a brand banner color (Aetherfield lime, Notarius lavender), use it; otherwise `bg-background-primary` or equivalent tinted surface.
- Container `mx-auto max-w-[1280px] px-6 lg:px-12 pt-16 pb-10 space-y-10`.
- **Meta row** (top): brand description on the left (eyebrow + 1-2 sentences) + 2-3 columns of nav links on the right (uppercase eyebrow + 3 links each).
- **Wordmark** (middle, the load-bearing visual): the project name in lowercase, sized `clamp(96px, 18vw, 240px)`, color = primary, line-height tight (~0.85), letter-spacing tight (-0.04em). It must span enough of the container width to BE the footer's identity, not garnish it.
- **Mono micro-row** (bottom, mandatory): the audit signature described above.

Visual reference: see Aetherfield's giant "aetherfield" lime wordmark and Notarius's purple "notarius" wordmark on lavender — both sized to fill the container, both unmistakably the project's signature.

#### Why this order

Hardcoding wordmark for every project produces an identity mismatch on Mastercard-style designs (warm cream, 4-column institutional footer with "We're always here when you need us"). The wordmark is great for editorial brands; it's wrong for institutional / payments-network / corporate-brand designs. Always start from the DESIGN.md.

When in doubt: which specific brands does the DESIGN.md prose evoke? Aetherfield-style (warm/editorial/portfolio) → wordmark fits. Mastercard/IBM/Stripe/Apple-style (institutional/utility) → 4-column link grid fits. The skill's job is to read that signal and produce the right one.

#### Either way: site-shell is mandatory

Whatever footer pattern is chosen, the site-shell rule stands: every page wrapped in `<SiteTopNav>` + `<SiteFooter>` (or `<WordmarkFooter>`). A naked `<main>` is a contract violation regardless.

The site-shell is what makes the showcase **a complete document about the design system**. Without it the page reads as a free-floating gallery; with it the page reads as a real branded surface that proves the system works in shipping context.

#### The skeleton — every section follows this exact wrapper

```tsx
<section className="border-b border-outline">
  <div className="mx-auto max-w-[1280px] px-6 lg:px-12 py-20 space-y-10">
    <div className="space-y-3">
      <Eyebrow>{ section name uppercase }</Eyebrow>
      <h2 style={{ fontSize: "48px", lineHeight: "56px", letterSpacing: "-0.02em", fontWeight: 600 }}>
        { brand-voice tagline, ends with period }
      </h2>
      <p className="text-on-surface-variant" style={{ fontSize: "16px" }}>
        { 1–2 sentence description with token references in <code> chips }
      </p>
    </div>
    { section content }
  </div>
</section>
```

**Three rules that distinguish a real showcase from a generic one**:
1. **Every section is full-width with `border-b`**. The whole page is a vertical stack of bordered bands. Not a single container with everything inside.
2. **Every section has an Eyebrow** (small uppercase mono label) above the h2.
3. **Every h2 is 48px in the display font**, with a brand-voice tagline ending in a period. Generic titles like "Colors" or "Typography" go in the Eyebrow above; the h2 is "The palette." or "The voice." or "Quietly opinionated CRM for X."

#### The 9 sections (in order)

**1. Header — standalone, NOT wrapped in AppShell.**
Same wrapper, but `py-20` and the h1 is bigger (`72px / 80px / -0.02em / 600`). The Eyebrow says `<PROJECT NAME> design system` (e.g., `Notarius design system`, `Aetherfield design system`). The h1 is a brand-voice tagline ending with a period: `"Quietly opinionated CRM for notary studios."` / `"Aetherfield design tokens."` / `"Production: Healthy"`. Below: 1-paragraph description with `<code>` chips on `.workflow/DESIGN.md` and `design-md-to-app`. Last: a back-link to `/`.

**2. Colors — "color-as-card" with 3 lines of info.**
- Grid `grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4`.
- Each card: `h-32 rounded-md p-4 flex flex-col justify-between`. The swatch IS the background.
- **3 lines of content** (this is what distinguishes a real showcase from a chip+label gallery):
  - Top: hex in `font-mono text-[12px] opacity-80`
  - Bottom-top: token name `text-[14px] font-semibold`
  - Bottom-bottom: 1-line note explaining the role (`text-[12px] opacity-80`) — e.g., `"Brand purple — primary CTAs, active sidebar item"`
- All three lines use the on-color text variant — the swatch must be readable inside itself.

**3. Typography — ladder with spec-in-mono + DOMAIN-CONTEXTUAL samples.**
- Three-column grid `[140px_240px_1fr]` with `divide-y divide-outline`.
- Column 1: token name (regular weight, 14px).
- Column 2: spec in `text-[12px] tracking-wide uppercase font-mono text-on-surface-variant` — e.g., `"Inter · 32 / 40 · 600 · -0.01em"`.
- Column 3: sample rendered AT the actual size and weight via inline style.
- **Sample is real product copy.** Examples by domain:
  - Notary CRM: `"Compravendita immobile via Roma 12"`, `"P.IVA 01234567890 · 3 pratiche aperte"`
  - Airbnb: `"Hosted by Marco"`, `"$280 / night · 4.81 · 124 reviews"`
  - DevOps console: `"Production: Healthy"`, `"Last deployment 14 minutes ago — 240 tests passed"`
- This is the single most important rule. Generic samples ("Body 16 / 400 / body text") = useless showcase.

**4. Buttons — flex-wrap with DOMAIN-SPECIFIC copy, NOT card-per-variant.**
- A single `<div className="flex flex-wrap gap-4 items-center">`.
- Each `<Button>` has copy that comes from the actual product, not "Default" / "Secondary" / "Click me":
  - Notary: `"Nuova pratica"`, `"Filtra pratiche"`, `"Esporta CSV"`, `"Annulla pratica"`, `"Termini di servizio"`
  - Airbnb: `"Reserve"`, `"Become a host"`, `"View all wishlists"`, `"Cancel reservation"`
  - DevOps: `"Deploy to production"`, `"Cancel"`, `"Logs"`, `"View commit"`, `"Roll back"`
- Cover variants: default (primary CTA), outline, secondary, ghost, link, destructive, disabled. One per kind, in this exact order.
- **Do NOT make one card per variant.** That was a wrong interpretation. The reference projects all use a single flex-wrap.

**5. Cards & containers — product-level blocks that prove the system scales.**
- Grid `sm:grid-cols-2 lg:grid-cols-3 gap-6`.
- 3 cards, each demonstrating a different SURFACE LEVEL:
  - One **default surface card** showing a real product block with stats (e.g., a practice card with status badge + dl/dt list of metrics; a service health card; a listing card).
  - One **tinted accent card** (for Notarius `bg-background-primary`, for Aetherfield `bg-aether-surface-soft`) — used for callouts, pull-quotes, primary-emphasis information.
  - One **bright/contrast card** (for Notarius `bg-surface-bright`, for designs with multiple surfaces) — used for nested content or high-importance summaries.
- Each card has real-looking content with mono code chips for technical fields (versions, IDs, timestamps).

**6. Inputs & forms — labeled with uppercase mono, with one error state.**
- Grid `sm:grid-cols-2 gap-6 max-w-2xl`.
- Each label uses `text-[12px] font-medium tracking-wide uppercase text-on-surface-variant`.
- Inputs use the radius scale (`rounded-sm` on most systems = 4px).
- **Include exactly one input in error state** (red border + helper text in error color) so the spec's error-handling story is visible.
- Sample copy from the domain (e.g., `"Bianchi srl"`, `"VRDMRA80…"`, `"api-gateway"`, `"us-east-1"`).

**7. Badges — status pills that map 1:1 to product states.**
- Single `<div className="flex flex-wrap gap-3 items-center">`.
- Map each semantic color in the palette to a real product status badge:
  - For Notarius: `bg-success-weak text-success` for `Firmata`; `bg-alert-weak text-alert` for `In scadenza`; `bg-error-weak text-error` for `Errore validazione`; tinted-primary for `In corso`; outline for `Bozza`; on-surface for `Archiviata`.
  - For Airbnb: `Guest Favorite`, `New`, `Superhost`.
  - For DevOps: `healthy`, `building`, `degraded`.
- The badge copy is the literal status that ships in the app. Default/Secondary/Outline as 1–2 final fallbacks at the end.

**8. Radius scale + Spacing scale (two sub-sections).**
- **Radius**: `flex flex-wrap gap-6` of `size-24` squares with each radius applied + label.
- **Spacing**: `<ul className="space-y-3">` with rows `[name] [px] [horizontal bar]`. The bar is `h-3 bg-on-surface rounded-sm` and width = the actual spacing token. Visualizes the rhythm.

**9. Do's and Don'ts — VERBATIM from the DESIGN.md.**
- Two cards `grid sm:grid-cols-2 gap-6`, both `bg-surface-bright`.
- Left card: heading `DO` in `text-on-surface`, list of 3–4 do-rules from `## Do's and Don'ts` in DESIGN.md.
- Right card: heading `DON'T` in `text-on-surface`, list of 3–4 don't-rules.
- Use `<strong className="text-on-surface">` to highlight key terms (color names, tokens) inside the prose.

#### Footer

```tsx
<footer className="border-t border-outline">
  <div className="mx-auto max-w-[1280px] px-6 lg:px-12 py-10 text-center font-mono text-[12px] tracking-wide uppercase text-on-surface-variant">
    Generated from .workflow/DESIGN.md · See registry.json + .workflow/screenshots
  </div>
</footer>
```

#### Anti-patterns — do not produce

- ❌ Wrapping `/showcase` in the same `AppShell` used by the rest of the app. The showcase is a **document about the system**, not a route inside the app.
- ❌ Producing `/showcase` WITHOUT a site-shell (no `SiteTopNav`, no `SiteFooter` of any kind). The page must be branded top-and-bottom. A naked `<main>` is a contract violation.
- ❌ Using a 1-line minimal text footer when DESIGN.md describes either a wordmark OR a structured 4-column footer. Match what's specified.
- ❌ Writing the giant lowercase wordmark on a project where DESIGN.md describes an institutional 4-column link grid (Mastercard-style). The wordmark is for editorial brands; for institutional brands it reads as off-brand.
- ❌ Skipping the mono micro-row at the bottom of the footer ("© YEAR · Generated by design-md-to-app"). It's the audit signature regardless of which footer pattern is used.
- ❌ Sections without `border-b` full-width wrapper. The whole page is a vertical stack of bordered bands.
- ❌ Sections without an Eyebrow above the h2.
- ❌ h2 at 28px or smaller. The h2 is **48px display**, always.
- ❌ Color swatches as `[icon-sized chip] [name + hex outside]`. Use color-as-card with 3 lines of info.
- ❌ Color cards with only 2 lines (hex + name). The note is mandatory.
- ❌ Typography samples that read "Body Medium — 16 / 400 / body text" or any other meta-description. Use real product copy.
- ❌ Buttons as one-card-per-variant. Use a single flex-wrap with domain-specific copy.
- ❌ Generic h1 like "Visual identity, applied" or "Showcase UI". Use a brand-voice tagline ending in a period.
- ❌ Skipping Spacing scale or Do's/Don'ts because "they take time". They take 5 minutes each and are required.
- ❌ Skipping the showcase entirely. **Mandatory in dev-flow mode.**

Then start the dev server (`pnpm dev` / `npm run dev`) and report the URL.

**Visual verification — best-effort obbligatorio.** The work is not done until you've either looked at it or explicitly told the user you couldn't:

1. Scan the available tools for a browser-control surface. The common names are `mcp__plugin_playwright_playwright__*`, `browse`, `gstack`, `mcp__Claude_Preview__*`, `mcp__Claude_in_Chrome__*`, `connect-chrome`. **Any** of these counts.
2. **If at least one is available**: navigate to `/showcase` (and the equivalent dark/light counterpart), take a screenshot, and compare against the DESIGN.md. Spot-check 3 colors, 2 typography levels, and 1 component hover state. If anything is off, fix it and re-shoot. Don't declare done from a single broken screenshot.
3. **If none is available**: do not silently claim done. State explicitly in your hand-off message:

   > ⚠ **Verifica manuale richiesta**: nessun browser tool è disponibile in questa sessione, quindi non posso confermare visivamente che `/showcase` rispecchi il DESIGN.md. Apri http://localhost:3000/showcase e verifica i colori e la tipografia prima di considerare il task chiuso.

   …and surface the same warning in the final summary so the user can't miss it.

**Do not** mark the task complete based on "code compiles" or "TypeScript passes" — the design must visibly match (or be explicitly flagged as unverified).

### Step 6 — Hand off + state update

**Dev-flow mode:** before reporting, update `<root>/.workflow/meta.json`:
- set `phase = "scaffolded"`
- bump `updated_at` to ISO-8601 UTC now
- append a `history` entry:
  ```json
  {
    "skill": "design-md-to-app",
    "ran_at": "<now>",
    "inputs": {"design_md": ".workflow/DESIGN.md", "stack": {"framework": "...", "ui": "..."}},
    "outputs": ["package.json", "app/", "components/ui/", "lib/utils.ts", "registry.json"],
    "phase_before": "<prev>",
    "phase_after": "scaffolded"
  }
  ```
- if `stack.framework` / `stack.ui` were null and the user picked them now, persist them in `stack`.

Do this **after** confirming the build succeeded — don't bump phase on a broken scaffold.

**Then summarize for the user:**
- what was scaffolded / changed,
- which files hold the tokens (so they can tweak),
- which components were customized,
- what's in `STYLE_NOTES.md` and why those rules couldn't be fully encoded,
- in dev-flow mode: the new phase and the next-step proposal (`screenshot-to-page` if `.workflow/screenshots/` has unmapped images; `module-add` to wire auth/db/etc.).

If the user is going to keep building, point them at the showcase as their living reference.

## Dark + light

A DESIGN.md typically describes a single visual mode (often dark, sometimes light, rarely both). By default the skill generates **both** modes so the resulting app supports `prefers-color-scheme` / a theme toggle out of the box — **unless the spec explicitly opts out** (see below).

### Single-mode opt-out

**Before generating both modes, scan the DESIGN.md for an explicit single-mode declaration.** If any section (typically §Known Gaps, §Notes, §Themes, or a body paragraph) says any of:

- "no dark mode" / "no light mode"
- "single light-mode theme only" / "single dark-mode theme only"
- "dark mode is out of scope" / "light mode is out of scope"
- "this document describes the [light|dark]-mode theme only"
- equivalent phrasings

…**respect it**. Generate only the declared mode:

- shadcn → write tokens under `:root` only. **Delete the `.dark` block** the `init` command wrote, and remove the `prefers-color-scheme` media query if any. Don't write a `<ThemeProvider>` toggle.
- MUI → use `createTheme` with a single `palette.mode`, not `extendTheme` with both schemes. Skip `<CssVarsProvider>` in favor of plain `<ThemeProvider>`.
- Document the choice in `_design-md-mapping.json` under `modes_skipped` with the exact quote from the DESIGN.md as `reason`. Repeat in `STYLE_NOTES.md` so future agents don't try to "fix" the missing mode.

Forcing a mode the spec rejects is worse than missing one the spec wants — derived dark modes from a spec written for light-only usually look broken (e.g. Airbnb's photography-first aesthetic doesn't translate to dark surfaces).

### Process (when both modes are needed)

1. Detect the source mode by inspecting `colors.background` / `colors.surface`. If the L (lightness) channel is below ~25%, treat the source as **dark**; above ~75% as **light**; otherwise ask the user.
2. Wire the source mode into the canonical block (`:root` for shadcn, the primary theme for MUI).
3. Auto-derive the opposite mode. The rule depends on the token family:
   - **Surfaces and backgrounds** (`surface*`, `background`, `card`, `popover`, `muted`): invert L (e.g. 9% → 96%, 12% → 92%, 14% → 88%) while keeping H and S unchanged.
   - **Foreground / text colors** (`on-surface`, `on-background`, `foreground`, `muted-foreground`): invert L correspondingly so the contrast against the inverted surface is preserved.
   - **Brand colors** (`primary`, `secondary`, `tertiary`, `accent`, `error`, `destructive`, `ring`): **keep H, S, and L unchanged across both modes.** A well-designed M3 brand value is already chosen to read on both light and dark surfaces; flipping its L destroys the visual identity (a vivid amber becomes navy). The contrast comes from the `*-foreground` partners, which *do* flip.
   - **Brand foregrounds** (`primary-foreground`, `on-primary`, `secondary-foreground`, etc.): typically these have `light brand → dark on-color` and `dark brand → light on-color` baked into M3. If the spec defines only one mode, derive the opposite by flipping the on-color's L and leaving brand H/S/L alone.
   - **Borders, outlines, dividers** (`border`, `input`, `outline`, `outline-variant`): shift L towards the opposite mode's neutral (dark border at 22% L → light border at 88% L, same H/S).
   - **Decorative tints** (`surface-tint`, `*-fixed`, `*-fixed-dim`): treat as brand-ish — keep H/S/L unless the prose argues otherwise.
4. Wire the derived mode into the secondary block (`.dark` / `.light` selector for shadcn, second `createTheme` call merged with the dark counterpart for MUI).
5. Surface this in `_design-md-mapping.json` and `STYLE_NOTES.md`: explicitly state which mode is canonical and that the other was auto-derived from it. The user may want to hand-tune the derived mode later.

**The canonical mode is the source of truth.** If the user later edits `DESIGN.md`, the derived mode is regenerated.

## Font loading

`typography.fontFamily` values fall into three buckets — handle each:

1. **Google Fonts** (Inter, Space Grotesk, Public Sans, Manrope, etc.):
   - **Next.js**: use `next/font/google` in `app/layout.tsx`, expose as CSS variable.
   - **Vite/Remix**: import via Google Fonts `<link>` in `index.html` / `root.tsx` `<Links>`. Don't fight `next/font` here — it's Next-only.

2. **System fallbacks** (`system-ui`, `ui-sans-serif`, generic stacks): pass through as-is. No loading needed.

3. **Custom / proprietary / non-Google fonts** (Airbnb Cereal VF, Circular Std, Söhne, F37 Glare, brand-licensed fonts): the silent-substitute path (Söhne → Inter, Cereal → Manrope) is **forbidden**. The brand identity is downstream of typography — quietly swapping a paid foundry font for an open one corrupts the perception of the design system in ways the user can't easily undo later. Use the three-way branch below.

#### The 3-way font branch (mandatory for non-Google families)

When the parser surfaces a custom/proprietary font name that's not a Google Font and not a system stack:

**Branch A — License owned (files present)**
1. Look for files at `<project-root>/public/fonts/<family>/` (any of `.woff2`, `.woff`, `.ttf`, `.otf`).
2. If files exist: wire via `next/font/local` (Next) or `@font-face` (Vite/Remix). Done — no fallback needed.
3. Record the resolution in `_design-md-mapping.json` under `fonts` as `{ name, source: "self-hosted", path: "public/fonts/<family>" }`.

**Branch B — Pick alternative (with explicit user choice)**
If no files are present, **stop and ask** with this exact pattern (Italian or English, match the user's language):

> Il DESIGN.md richiede `Söhne` (Klim Type Foundry, font commerciale). Non ho i file di licenza. Ho due alternative open-source visivamente vicine — vuoi vederle?
>
> **Opzione 1 — Manrope** (Google Fonts): geometric sans, x-height un filo più alta di Söhne, terminali leggermente più morbidi. Più "tech" che "editorial".
>
> **Opzione 2 — Inter** (Google Fonts): neo-grotesque, terminali più squadrati, ottimizzato per UI ad alta densità. Più "neutrale".
>
> Se li vuoi confrontare, posso renderizzare entrambe le opzioni nel `/showcase` e farti scegliere visualmente. Oppure vuoi cercare la licenza ora? L'opzione fallback è sempre `system-ui`.

**Critical**: list **two** alternatives with concrete pros/cons grounded in the typographic difference (x-height, terminals, weight axis, optical sizing, mood). Don't list five — paralyzes the user. Don't list one — feels like a forced choice.

For each known proprietary family the skill has seen before, keep the recommendation pair stable:

| Original | Alt 1 (closer) | Alt 2 (different mood) |
|---|---|---|
| Söhne | Manrope | Inter |
| Circular Std | Public Sans | Manrope |
| Cereal VF (Airbnb) | Manrope | Plus Jakarta Sans |
| F37 Glare | Fraunces | Playfair Display |
| Söhne Mono | JetBrains Mono | IBM Plex Mono |
| Roobert | Geist | Inter |

If the family isn't in the table: ask the user to name two alternatives they trust, OR look up VFonts/Fontesk for "alternatives to <family>" and propose the top two from there.

**Branch C — Defer**
If the user says "I'll think about it" or doesn't respond, scaffold with `system-ui` fallback chain and:
1. Add a banner in the generated `STYLE_NOTES.md`:
   > ⚠ **Font decision pending**: DESIGN.md specifies `<family>`. The scaffold is currently rendering with `system-ui` fallback. Choose a final font (license / alternative / different) before shipping — the design will look different from the source until then.
2. Record `{ name, source: "deferred", fallback: "system-ui" }` in `_design-md-mapping.json`.
3. Surface it in the hand-off message: "Font decision deferred — see STYLE_NOTES.md before shipping."

#### Why this rigour

The font is the most visible piece of the design system. Silently swapping it ships a project that *looks like* it has the right brand but doesn't. The user only notices when they show it to a client, and at that point fixing it requires re-installing the alt font everywhere, possibly different weight axes, possibly different metrics — hours of rework that 30 seconds of asking would have prevented.

This is also where AI tools earn the most distrust: a tool that "did its best" and silently degraded the quality is harder to live with than a tool that paused and asked.

**Load only the font weights the DESIGN.md declares.** Read the typography table or prose: if the spec says "weights observed: 500, 600, 700. No 400-regular", load exactly those weights. Don't pre-load 400 "for safety" — the design system explicitly forbade it, and keeping the option around lets code accidentally render in the wrong weight. Smaller payloads are a free side effect.

In every case, declare a fallback chain in CSS so the layout doesn't break before fonts load:

```css
font-family: var(--font-display), Inter, ui-sans-serif, system-ui, -apple-system, sans-serif;
```

## Notes on faithful translation

- **Token references** (`{colors.primary}`) must be resolved to literal values at write time. The theme files should hold concrete values — re-resolving at runtime is out of scope.
- **Variants** in the `components` block (e.g. `button-primary`, `button-primary-hover`) are sibling keys in the spec, not nested. Group them per component when generating override code.
- **Missing tokens** are normal. The spec allows omitting sections. Don't fabricate; fall back to library defaults and note it in `_design-md-mapping.json` under `fallbacks`.
- **Unknown sections / fields** in the body must be preserved (per spec consumer rules) — copy them into `STYLE_NOTES.md` so nothing is lost.
- The markdown body is **prose, not config**. It's the source for `STYLE_NOTES.md` and for inferring qualitative rules. Never try to parse it like YAML.

## Things to avoid

- Don't pick the library for the user without asking.
- Don't generate a 50-component showcase if the DESIGN.md only defines four — only render what's defined plus the absolute basics needed to verify the theme.
- Don't run `npx create-next-app` non-interactively without confirming the directory and package manager with the user.
- Don't silently overwrite an existing `theme.ts` / `globals.css`.
- Don't skip the visual verification step. Token files passing TypeScript means nothing if buttons render the wrong color. If no browser tool is available, **say so explicitly** in the hand-off — never imply you've verified when you haven't.
- Don't run `/showcase` generation, `next dev`, dependency installs, or `create-next-app` in **theme-only** mode. The point of that mode is a small, reviewable diff.
