---
name: screenshot-to-page
description: 'Generate a real, working page (route + components) inside an already-scaffolded app from a single UI screenshot, applying the project''s DESIGN.md tokens and the existing UI library (shadcn or MUI). Reads a screenshot from `.workflow/screenshots/`, plus `.workflow/DESIGN.md` and `.workflow/meta.json` for tokens and stack, then writes the route into the codebase at the project root. Use when the user says "fai questa pagina dallo screenshot", "build the home page from this image", "/journal route from this PNG", "convert this mockup to code", or the orchestrator routes here from phase `scaffolded` with unmapped screenshots present. Not for: scaffolding the app from scratch (use `design-md-to-app`), extracting tokens from Figma (use `figma-to-design-md`), or wiring backend modules (use `module-add`).'
---

# screenshot-to-page — screenshot → working route

This skill takes one screenshot and one route-name from the user, and produces a working page in the existing scaffolded app. The route renders close to the visual reference, uses **only** components and tokens already defined by the project's design system, and is reachable in `npm run dev`.

## What this skill targets

**Pixel-perfect on what's reproducible**: layout, typography, color, spacing, radii, component states. The skill iterates render → screenshot → pixel-diff → fix until the visual delta is below threshold (default <2% off-tokens).

**Placeholder, with explicit flag, on what isn't**: photography, illustration, custom illustrations, brand-licensed imagery. These are static raster contents that no skill can synthesize from a screenshot alone.

**Componentized aggressively**: the skill detects repeated visual patterns in the screenshot (3 cards with the same structure, 4 nav links, a list of testimonials, ...) and extracts each pattern into a reusable component before writing JSX. The page file ends up short and readable; the heavy lifting is in `components/<PageName>/`.

## What this skill is NOT

- Not a Figma-to-code service. The input is a static raster, not a vector.
- Not a layout designer — if the screenshot is ambiguous (e.g., two interpretations of a section break), ask the user.

## When this skill applies

- A `<project-root>/` exists (`phase >= scaffolded`).
- `.workflow/screenshots/` contains at least one image.
- A `.workflow/DESIGN.md` exists with valid tokens.
- The user names a route to build (`/`, `/pricing`, `/dashboard`, etc.) or points at a specific screenshot.

## Contract

This skill follows the dev-flow contract — see `references/contracts.md`. Key facts:
- Reads `<root>/.workflow/screenshots/<filename>`, `<root>/.workflow/DESIGN.md`, `<root>/.workflow/meta.json#stack`.
- Writes the route into the codebase at the project root, at the canonical path for the framework:
  - Next App Router: `<project-root>/app/<route>/page.tsx`
  - Vite + React: registers a route in `<project-root>/src/router.tsx` (or whatever the scaffold uses) plus a component file `<project-root>/src/pages/<Route>.tsx`.
  - Astro: `<project-root>/src/pages/<route>.astro`.
- Sets `phase = "page_generated"` (only if current phase is earlier in the enum).

## Workflow

### Step 1 — Pick the screenshot and route

If the user named a screenshot, use it. Otherwise list `.workflow/screenshots/*.png` and ask which one.

Ask for the route name (e.g., `/`, `/journal`, `/pricing`). Validate: must start with `/`, must be a valid URL path, must not collide with an existing route in `<project-root>/`. If there's a collision, ask: replace, or pick a different route.

### Step 2 — Read the screenshot

Use vision to inspect the screenshot. Identify, in this order:

1. **Page-level layout**: full-bleed sections vs. centered max-width column? Single column or grid? Sticky header? Footer?
2. **Sections**, top to bottom. For each section:
   - Type (hero, feature grid, testimonial, pricing table, footer, ...)
   - Vertical extent (rough height as fraction of viewport)
   - Content (text + imagery + CTAs)
3. **Components per section**: buttons, cards, inputs, navigation, list items, etc.
4. **Typography hierarchy**: which h-level for hero, which for section titles, which for body.
5. **Color usage**: where does primary appear? Where surfaces? Backgrounds?

Don't try to count pixels. Estimate, sanity-check against the design tokens.

### Step 3 — Detect repeated patterns and plan components

Before writing any JSX, scan the screenshot for **repeated visual patterns**. The output of this step is a small plan, not code.

For each section identified in Step 2, ask: *"is there a sub-element that appears 2 or more times with the same structure?"* Common patterns:

- **Card grid** — 3+ cards with identical structure (image + title + body + meta) → extract `<FeatureCard>`, `<ArticleCard>`, etc.
- **Nav items** — 4+ links in a header → extract `<NavLink>` and map over an array.
- **Pricing tiers** — 2–4 columns with identical structure → extract `<PriceColumn>`.
- **Testimonials / logos / metrics** — list of similar items → extract `<TestimonialCard>` / `<LogoCloud>` / `<StatCard>`.
- **Form fields** — repeated label+input → extract `<FormRow>`.
- **Sidebar / nav menu items** with icon+label → extract `<MenuItem>`.

For each detected pattern, decide:
1. **Component name** (PascalCase, descriptive of *what it shows*, not *what it looks like* — `ArticleCard` not `RoundedBox`).
2. **Props** the component takes (the variable bits — title, image, href, ...).
3. **File path** — typically `app/<route>/<ComponentName>.tsx` for one-shot use or `components/<ComponentName>.tsx` if the pattern is likely reusable across pages.

**Don't over-componentize singletons.** A unique hero section is fine inline in `page.tsx`. Extract only when there's reuse (the same shape ≥2 times) or when the section is over ~80 lines of JSX (readability).

State the plan to the user briefly: *"Estraggo `ArticleCard` (4 occorrenze nella griglia 'Latest articles') e `NavLink` (5 occorrenze nell'header). Hero, footer, e signup-form restano inline. Procedo?"* The user can override before any code is written.

### Step 4 — Map to the design system

For each component you identified in Step 2, decide:

- **Use an existing primitive** (e.g., shadcn's `Button`, `Card`, MUI's `Card`, `Stack`). Prefer this.
- **Compose primitives** if no exact match (e.g., a "stat card" = `Card` + headline typography + body).
- **Hand-roll a small custom component** only if necessary, and only if it'll be reusable. One-off custom JSX in the page file is fine for unique sections.

For each color/spacing/radius decision, **reference the token by name**. Don't hardcode hex codes — use `bg-primary`, `text-on-surface-variant`, `rounded-md` (shadcn) or theme values (MUI). If the screenshot shows a color that's not in DESIGN.md, **ask the user before adding** — it's either an oversight in DESIGN.md or a one-off photo color that shouldn't become a token.

### Step 5 — Write the route + extracted components

Generate the files at the canonical framework path (see Contract). Constraints:

- **TypeScript** for everything.
- **Extracted components first**, then the page that imports them. This keeps `page.tsx` readable.
- **Imagery placeholders**: the screenshot likely has photography you don't have. Use a `<div>` with `bg-muted` and the dimensions of the original, plus an HTML comment `{/* TODO: replace with hero image */}`. Don't link to external image services.
- **Copy**: use the actual text visible in the screenshot. If text is illegible, write a one-line placeholder and flag it in the report.
- **Responsive**: read the DESIGN.md `## Layout` section for breakpoint rules. If the system documents 3 breakpoints (Desktop/Tablet/Mobile), generate the page with appropriate Tailwind breakpoint classes (`md:`, `lg:`) or MUI breakpoint props.

#### Accessibility checklist (always apply)

A page that looks right but fails basic a11y checks is not done. Run through this list as you write — most items take seconds when done at write-time and hours when retrofitted:

- **Semantic landmarks**: one `<main>` per page. Use `<nav>`, `<header>`, `<footer>`, `<aside>` instead of `<div>` when the role applies. Avoid wrapping everything in nested `<div>`s.
- **Heading hierarchy**: exactly one `<h1>` per page, then `<h2>` → `<h3>` without skipping levels. Visual size and heading level are independent — style with classes, not by demoting `<h1>` to `<h3>`.
- **Alt text**: every `<img>` and `<Image>` needs `alt`. For decorative-only imagery, use `alt=""` (empty string, not absent) so screen readers skip it. Photography placeholders inherit `alt="TODO"` plus a comment.
- **Buttons vs. links**: `<button>` for actions inside the page, `<a>` (or `<Link>`) for navigation. Don't style a `<div onClick>` as a button — keyboard users can't reach it.
- **Focus visible**: never `outline: none` without a replacement. shadcn ships `focus-visible:ring-2 focus-visible:ring-ring` by default — preserve it. If the design hides outlines for aesthetic reasons, add a custom `:focus-visible` style that's visible against the background.
- **Form labels**: every input has an associated `<label>` (matched by `htmlFor`+`id`, or wrapping). Placeholder text is **not** a label substitute — it disappears on focus and many screen readers ignore it.
- **Color contrast**: body text against its background needs ≥ 4.5:1 (WCAG AA). Brand colors that fail this on the surface they sit on are a DESIGN.md bug, not a screenshot-to-page bug — flag it back to the user instead of silently swapping the color.
- **Interactive target size**: tappable elements are ≥ 24×24px (WCAG 2.5.8). Tight icon-only buttons need `p-2` minimum.
- **`aria-label` for icon-only buttons**: a `<Button size="icon">` with only an icon inside is invisible to screen readers without `aria-label="Toggle theme"` or equivalent.
- **`prefers-reduced-motion`**: handled globally by `globals.css` if the scaffold ran `design-md-to-app`. If you add a new long animation here, double-check it respects the global guard.

If any item can't be fixed in the screenshot-to-page run (e.g., the DESIGN.md mandates a low-contrast color), document it explicitly in the hand-off message under "Accessibility notes" — never silently ship an a11y violation.

### Step 6 — Verification loop (two modes)

The work isn't done after the first write. Iterate until visual quality matches the threshold for the chosen mode. **Required when a browser tool (Playwright / Chrome MCP / etc.) is available** — without one, fall back to the sub-section "No browser available" below.

#### Pick the mode FIRST, before writing a single iteration

Two modes — they're not interchangeable, and over-applying pixel-tight is a real failure pattern:

**`structure-first` (default for app routes — dashboards, forms, internal product pages)**
- Target: **token correctness** + **semantic correctness** + visual delta ≤ 8%.
- Stop after 3 iterations, or when delta plateaus.
- The HTML is allowed to differ from the screenshot in pixel position by up to ~8 px on most edges, AS LONG AS:
  - The colors used are the right tokens (no `bg-[#abc123]`, only `bg-primary` / `bg-card` / etc.).
  - The typography uses the declared scale (`text-display-lg`, etc.), not free `text-[42px]`.
  - The component structure is correct (a `<Card>` IS a `<Card>`, not a `<div>` faking it).
  - The layout is responsive and respects the breakpoint rules from DESIGN.md.
- **Why this is the default**: pixel-tight produces rigid HTML that imitates pixels instead of respecting tokens. For a dashboard / settings page / list view, that rigidity hurts more than it helps — the next developer can't tell which spacing was a "design choice" and which was an LLM matching one pixel.

**`pixel-tight` (opt-in for marketing / landing pages / brand-critical surfaces)**
- Target: **visual delta ≤ 2%** (the original threshold).
- Stop after 8 iterations, or earlier if delta plateaus.
- All `structure-first` rules still apply (still must use tokens, not arbitrary pixel values) — but on top of that, position, scale, and typographic detail must match the screenshot to within 2%.
- **When this is right**: hero pages, pricing pages, signup flows, conversion-critical surfaces where the visual fidelity IS the value. A landing where the headline is 4px off feels broken; a dashboard where the table padding is 4px off is fine.

#### How to decide

The signal is **the kind of route**, not the user's preference. Ask the user only if the case is genuinely ambiguous.

- Route looks like `/`, `/pricing`, `/about`, `/blog/<post>`, `/sign-up`, `/showcase` → **pixel-tight**.
- Route looks like `/dashboard`, `/clienti/<id>`, `/settings`, `/admin`, anything CRUD → **structure-first**.
- Mix on the same page (rare): pick `pixel-tight` for the hero, write the rest in `structure-first` style and call it good.

State the chosen mode in your hand-off message: "Iterated in `structure-first` mode (3 passes, final delta 6.4%) — token-correct, semantically clean. Switch to `pixel-tight` if you want closer fidelity for production."

#### The loop

1. **Build & start dev server**:
   ```bash
   cd <project-root>
   npm run build       # catch syntax/type errors before launching
   npm run dev &       # background dev server
   ```
   If build fails, fix the most likely cause once. If it still fails, stop and tell the user — don't loop on a broken build.

2. **Render and capture** the route at the same viewport as the source screenshot (typical: `1440×900` for desktop frames; read the source PNG dimensions and match):
   ```bash
   # via Playwright MCP, or equivalent
   browser_resize(width: <ref-width>, height: <ref-height>)
   browser_navigate(url: "http://localhost:3000<route>")
   browser_wait_for(time: 2)            # let fonts + animations settle
   browser_take_screenshot(filename: ".workflow/screenshots/_render-iter-N.png")
   ```

3. **Diff the renders**. Use the helper script:
   ```bash
   python3 scripts/visual_diff.py \
       <reference> .workflow/screenshots/_render-iter-N.png
   ```
   Output: a delta percentage (0–100), and an annotated diff PNG showing where the renders differ. Threshold depends on the mode you picked:
   - `structure-first` (default for app routes): **≤ 8%** delta is shippable. Concentrate on token correctness over pixel match.
   - `pixel-tight` (landing/marketing): **≤ 2%** delta. <5% is acceptable when the gap is on imagery placeholders.

4. **Identify the worst region** in the diff and fix it. Common categories of delta, in order of frequency:

   - **Spacing wrong** (padding / margin / gap off by a step) → adjust the Tailwind `p-N` / `gap-N` to the next token.
   - **Color drift** (you used `bg-muted` but the screenshot shows `bg-surface-soft`) → fix the token name.
   - **Typography weight or size** off → change `text-display-lg` → `text-display-xl` or `font-medium` → `font-semibold`.
   - **Component mis-pick** (used a `Card` but the original is just a div with a border) → swap.
   - **Layout structure** (you stacked vertically, the original is side-by-side) → restructure the JSX section.

   Make **one targeted fix per iteration**. Don't try to fix everything at once — you lose the ability to attribute progress.

5. **Repeat** Steps 2–4 until delta drops below the threshold for your mode (≤ 8% for `structure-first`, ≤ 2% for `pixel-tight`) OR you've hit the iteration cap (3 for `structure-first`, 8 for `pixel-tight`). If stuck, stop and ask the user — usually the screenshot is ambiguous on the disputed region. Don't over-iterate in `structure-first` — past 3 passes you're chasing pixels in a context where pixels weren't the goal.

6. **Kill the dev server** when done.

#### No browser available

If no browser tool is in this session: build only, don't loop. Say explicitly:

> ⚠ Verifica visiva richiesta: nessun browser tool in questa sessione. Apri `http://localhost:3000<route>` e confronta con `.workflow/screenshots/<filename>`. Il pixel-perfect loop non è stato eseguito; il risultato è quindi un primo draft, non un match verificato.

Don't claim convergence you didn't measure.

#### What the loop tries hard NOT to fix

- **Photography content** — if the source has a hero photo of someone holding a coffee, the placeholder div will always diff. Mark this as "expected delta — imagery placeholder" in the report.
- **Custom fonts not loaded** — if DESIGN.md references a font that isn't on Google Fonts and the user hasn't supplied a local file, the rendered font is a fallback and will diff. Flag and stop chasing.
- **Animations / hover states / scroll behavior** — static screenshots can't show motion. Don't hallucinate state.

### Step 7 — Update state and report

Update `.workflow/meta.json`:
- if current phase is earlier than `page_generated`, set `phase = "page_generated"`
- bump `updated_at`
- append history:
  ```json
  {
    "skill": "screenshot-to-page",
    "ran_at": "<now>",
    "inputs": {"screenshot": "screenshots/<file>", "route": "<route>"},
    "outputs": ["app/<framework-specific-path>"],
    "phase_before": "<prev>",
    "phase_after": "page_generated"
  }
  ```

Tell the user:
- Path to the new route in `app/` (relative).
- Components used (existing primitives + any custom ones added).
- Tokens referenced (prove the design system was applied, not bypassed).
- Things you couldn't replicate from the screenshot (e.g., specific photography, custom illustrations, pixel-perfect spacing) — flagged for hand-tuning.
- Next-step proposal: another `screenshot-to-page` run for the next page, or `module-add` to wire features behind these routes.

## Important constraints

- **Use only tokens that exist in DESIGN.md.** If you need a color/radius/spacing not in the spec, ask the user — they decide whether to add to DESIGN.md or accept a fallback.
- **Don't add new dependencies.** Whatever's in `app/package.json` is your kit. If a library's missing (e.g., a chart library for a dashboard screenshot), flag it in the report and let `module-add` handle it.
- **Don't break the build.** A page that doesn't compile is worse than no page.
- **Don't over-componentize.** A simple landing page in one `page.tsx` is fine. Don't split into 12 files just to "follow best practices" if there's no reuse.
- **Prefer plain JSX over abstractions.** Server actions, complex hooks, custom contexts are out of scope here — they belong to the feature implementation step, not to the visual scaffolding.
- **One screenshot, one route, one run.** If the user wants 4 routes, the orchestrator (or the user) invokes this skill 4 times. Don't try to do them in one shot.


## Folder structure rules (canonical)

When generating a route + components, follow the canonical structure (spec: `docs/superpowers/specs/2026-06-06-folder-structure-refactor.md`):

- **Default for new components**: `app/<route>/_components/<Name>.tsx` (L0 page-private).
- **Detect route group from path**: if the route is under `app/(app)/dashboard/`, components go in `app/(app)/dashboard/_components/`.
- **Never `components/site/`**: that folder no longer exists. Cross-route shared components live in `components/shared/<dominio>/`.
- **Promotion on detect**: when this skill notices a repeated pattern from another route, suggest calling `promote-component` to lift it to L1 (group `_components/`) or L2 (`components/shared/<dominio>/`).
- **Co-location for compound components**: a compound (e.g. `<Card>` + `<Card.Header>`) lives in a single file until ~250 lines, then becomes a folder with `index.ts` barrel.
