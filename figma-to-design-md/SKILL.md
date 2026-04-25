---
name: figma-to-design-md
description: 'Use when the user provides a Figma URL and wants to export/extract/generate design tokens, colors, typography, or system documentation into DESIGN.md format—a portable, AI-readable design standard. Includes requests like "crea il design.md", "estrai i token", "portare il design fuori da figma", "design system documentation". Not for converting Figma to code, reviewing production websites, or design brainstorming before Figma work.'
---

# Figma → DESIGN.md

Generate a `DESIGN.md` file that conforms to the **Google design.md spec** (open format for portable design systems across AI agents — see `references/spec.md`). The source of truth is a Figma file the user points to via URL.

## Dev-flow contract

This skill participates in the **dev-flow** workflow. When invoked on a project that has a `.workflow/` folder at its root:

- **Output** goes into `<root>/.workflow/`:
  - `DESIGN.md` (the main artifact)
  - `screenshots/` (any HD frame captures used during extraction — saved with slugged page names like `home-hero.png`, `type-system.png`)
- **State** is updated by setting `meta.json#phase = "design_extracted"` (only if the current phase is earlier in the enum), refreshing `updated_at`, and appending an entry to `meta.json#history` with skill name, inputs (figma URL, path used: MCP/REST/manual), and outputs.
- **Standalone mode** (no `.workflow/` present) is still supported — fall back to the original behavior of writing `DESIGN.md` at the user-specified project root.

The canonical contract spec is in `references/contracts.md`. Read it if any rule above is unclear.

## When this skill applies

Trigger on any of:
- A Figma URL pasted by the user (`figma.com/file/...`, `figma.com/design/...`, `figma.com/proto/...`, `figma.com/board/...`).
- An explicit request: "crea/genera il DESIGN.md", "estrai il design system", "build a DESIGN.md from this Figma", etc.
- Both combined.

If only a URL is pasted with no instructions, **ask once** whether the user wants a DESIGN.md generated. Don't assume.

## What you produce

In **dev-flow mode**: `<root>/.workflow/DESIGN.md` + `<root>/.workflow/screenshots/*.png` (for any HD captures used).
In **standalone mode**: `<project-root>/DESIGN.md`.

The DESIGN.md content (same in both modes):

1. **YAML frontmatter** — machine-readable design tokens (colors, typography, rounded, spacing, components).
2. **Markdown body** — eight sections in this exact order, each as `##`:
   1. Overview (a.k.a. "Brand & Style")
   2. Colors
   3. Typography
   4. Layout (a.k.a. "Layout & Spacing")
   5. Elevation & Depth
   6. Shapes
   7. Components
   8. Do's and Don'ts

Sections may be omitted only if there's truly no information to fill them, but should appear in this order when present.

**Never invent the spec.** Read `references/spec.md` first if you need to confirm any detail (token shape, valid units, naming conventions, "consumer behavior for unknown content"). The spec is the law.

## Workflow

### Step 1 — Confirm intent and locate the output directory

- Confirm the Figma URL.
- **Dev-flow mode:** if `<cwd>/.workflow/meta.json` exists, the output goes into `<cwd>/.workflow/` (no need to ask). Read `meta.json#project_name` and use it as the brand name fallback.
- **Standalone mode:** identify the project root (current working directory unless the user specifies otherwise). The output goes there as `DESIGN.md`.
- If a `DESIGN.md` already exists at the target, ask before overwriting (in dev-flow mode this means `.workflow/DESIGN.md`; in standalone, `<root>/DESIGN.md`).
- Ask the user (only if not obvious from context) for any high-level brand context that won't be in Figma: target audience, brand voice, desired emotional tone. This feeds the **Overview** section. If the user has nothing to add, infer from the Figma name and the optional `PROJECT.md` if present.

### Step 2 — Pick the Figma access path

You have **three** ways to read Figma. Try them in this order and stop at the first that works:

| # | Path | When available | Reference |
|---|------|----------------|-----------|
| A | **Figma Dev Mode MCP** | A tool whose name contains `figma` (e.g. `mcp__figma__*`, `mcp__figma_dev_mode__*`) is exposed in this session | `references/figma-mcp.md` |
| B | **Figma REST API** | A `FIGMA_ACCESS_TOKEN` env var is set, or the user can provide a personal access token | `references/figma-api.md` |
| C | **Manual export** | Neither of the above is available | `references/figma-manual.md` |

**How to detect path A**: scan available tools for any name containing the substring `figma`. If at least one is present, use path A. If you find a Figma MCP tool but it requires the user to be running Figma Desktop with Dev Mode active, tell them and fall back to B if it doesn't work.

**How to detect path B**: run `printenv FIGMA_ACCESS_TOKEN` (Bash). If empty, ask the user "Hai un Figma personal access token? (https://www.figma.com/developers/api#access-tokens)". If yes, accept it for the session — do **not** persist it to disk.

**Fallback to C** only if A and B both fail. Path C requires the user to manually export PNG screenshots and (ideally) a tokens JSON from Figma; it's slower and less complete, but always works.

Tell the user which path you're using and why ("Uso Figma MCP perché vedo lo strumento `mcp__figma__get_file`" / "Uso REST API con token dall'env" / "Procedo manualmente perché non ho né MCP né token").

### Step 3 — Extract tokens and assets from Figma

Follow the path-specific reference file. The goal is to gather, in this rough order of priority:

1. **Color styles / variables** → `colors` token group.
2. **Text styles** → `typography` token group.
3. **Effect styles** (shadows, blurs) → input for **Elevation & Depth** prose.
4. **Number / dimension variables** for radii and spacing → `rounded` and `spacing` token groups.
5. **Components** (especially `Button*`, `Chip*`, `Input*`, `Card*`, `Tooltip*`) → `components` token group.
6. **Frame screenshots** of representative pages → context for **Overview**, **Layout**, **Shapes** prose.

For **Overview** specifically: synthesize from frame names, page structure, components present, and brand context. Describe personality, target audience, emotional tone — not just what's drawn.

### Step 4 — Map Figma data to design.md tokens

Apply these mapping rules:

- **Colors**: hex SRGB, lowercase, double-quoted. Strip alpha unless the design genuinely needs it (then note in prose). Use semantic names from the spec's recommended list when possible: `primary`, `secondary`, `tertiary`, `neutral`, `surface`, `on-surface`, `error`. If Figma uses a Material-like scheme (Material 3 variables), preserve it — those names are widely accepted ("Consumer Behavior for Unknown Content" allows it).
- **Typography**: each text style becomes a token. Recommended names: `display-lg`, `headline-lg/md/sm`, `body-lg/md/sm`, `label-lg/md/sm`. Always emit `fontFamily`, `fontSize`, `fontWeight`, `lineHeight`. Add `letterSpacing` only when non-zero. Quote `fontWeight` as a string (`"600"`) — both bare numbers and quoted strings are valid per spec, but quoted is safer for YAML parsers.
- **Rounded**: map Figma corner-radius values to a scale: `none/sm/md/lg/xl/full` (`full: 9999px`). Deduplicate similar values.
- **Spacing**: pick the recurring base unit (often 4px or 8px) and emit `xs/sm/md/lg/xl` plus any `gutter`/`margin` if the design uses a grid.
- **Components**: only emit a component group when you can fill at least 2 properties. Use token references: `backgroundColor: "{colors.primary}"`. Variants go as separate keys with hyphenated suffix: `button-primary-hover`.
- **Token references**: must wrap the path in curly braces, must point to a primitive (except inside `components`, which may reference composite typography tokens).
- **Dimensions**: only `px`, `em`, `rem` are valid units. **Single values only** — never CSS shorthand. `padding: "12px 24px"` is invalid; the spec accepts one dimension. If a Figma component has asymmetric padding (e.g. `12px` vertical, `24px` horizontal), pick the dominant axis and describe the asymmetry in the **Components** prose, OR split into two component variants if the difference is meaningful. The same rule applies to `size`, `height`, `width`, `rounded` — one dimension per key.

When uncertain, prefer **fewer, well-defined tokens** over many half-defined ones. The DESIGN.md is read by other agents; ambiguity hurts.

### Step 5 — Write the markdown body

For each `##` section, write **2–6 sentences of prose** that explain *why* the tokens are what they are — the rationale, not a re-listing of values. The prose may use descriptive color names (e.g. "Midnight Forest Green") that correspond to systematic token names (e.g. `primary`); this is encouraged by the spec.

Concrete prompts per section:
- **Overview**: brand personality, target audience, emotional tone. 3–5 sentences.
- **Colors**: semantic role of each palette (primary, secondary, etc.) and where it's used. Include hex inline next to the descriptive name (see example).
- **Typography**: which font families, why those, what each weight is for.
- **Layout**: grid model (fluid / fixed-max / breakpoints), spacing rhythm.
- **Elevation & Depth**: shadows? tonal layers? borders? Specify how hierarchy is conveyed.
- **Shapes**: corner-radius philosophy (sharp / soft / mixed). What feeling it evokes.
- **Components**: brief description of the most important component variants and states. Detailed values live in the YAML.
- **Do's and Don'ts**: 3–6 actionable bullets. Mix positive guardrails ("Do …") and antipatterns ("Don't …"). Include at least one accessibility item (contrast, target size).

Look at `references/example.md` (Atmospheric Glass) for tone, density, and length.

### Step 5b — Typography is non-negotiable

Typography is **load-bearing** for any DESIGN.md consumer. An AI agent that knows the colors but not the font family or the size scale cannot reproduce the brand — it will silently default to system-ui at arbitrary sizes and the output will look generic. So:

**Do not write the DESIGN.md without Typography evidence.** If after Step 3 you have no font names and no measured sizes, stop and obtain them. In order of preference:

1. **Re-attempt extraction** with a more capable path. If you used Path C and Playwright is available, search the file for a frame literally named "Typography", "Type", "Type System", "Type Scale", "Styles", "Foundations", or "Design System" — these are universal designer conventions for the type-specimen page. Click that layer in the outline (it changes `node-id` in the URL), then zoom in (`Cmd+0` for 100%, scroll/zoom on the canvas via JS if keyboard shortcuts don't work without login). Take a high-resolution screenshot of the specimen and read font names + sizes directly from the rendered text.

2. **Ask the user explicitly**, with concrete options. Don't ask vaguely "any info on fonts?". Ask: "I need typography to ship a usable DESIGN.md. Pick one: (a) drop a screenshot of any frame that contains visible body text and a heading; (b) tell me the font family name (you can read it in Figma's right panel when you click any text layer) plus the size of the hero headline and body — I'll infer the rest from typical scales; (c) paste an export from a Tokens Studio plugin."

3. **As a last resort**, write the DESIGN.md with a Typography section that *omits the YAML token group* and replaces it with a clearly-marked **stub block** in prose:

   ```markdown
   ## Typography

   > **Typography pending.** Not extracted in this run because [specific reason — e.g.
   > "the file's type-specimen frame was inaccessible without a Figma login and the
   > user did not supply a screenshot."]. Before this DESIGN.md is usable, a designer or
   > developer must add: (1) primary font family, (2) size scale (display/headline/body/
   > label tiers), (3) line-height per tier. The frontmatter below intentionally has no
   > `typography:` key so consumers don't silently load the wrong values.
   ```

   The stub is acceptable only after options 1 and 2 have actually been attempted and failed. A bare omission with no explanation is not.

Apply the same rigor — but less strictly — to `colors.primary`: at least one primary color must be present. Without it the spec rejects the file outright.

### Step 6 — Validate before writing

Before writing the file, mentally check:

- ✅ Frontmatter starts with `---` on its own line and ends with `---` on its own line.
- ✅ All color values are `"#rrggbb"` (or `"#rrggbbaa"` only if alpha is intentional).
- ✅ `primary` color palette is defined (mandatory per spec).
- ✅ Every dimension uses `px`, `em`, or `rem`.
- ✅ All `{path.to.token}` references resolve to existing tokens.
- ✅ Section headings are `##`, in spec order, with no duplicates.
- ✅ No `## Colors` (or any other section) appears twice — that's a hard error per spec.

Then write the file with the `Write` tool to `<project-root>/DESIGN.md`.

### Step 7 — Update state and report

**Dev-flow mode:** before reporting, update `<root>/.workflow/meta.json`:
- if current `phase` is earlier than `design_extracted` in the enum, set `phase = "design_extracted"` (don't regress)
- bump `updated_at` to ISO-8601 UTC now
- append a `history` entry:
  ```json
  {
    "skill": "figma-to-design-md",
    "ran_at": "<now>",
    "inputs": {"figma_url": "...", "path_used": "mcp|rest|manual|playwright"},
    "outputs": ["DESIGN.md", "screenshots/"],
    "phase_before": "<prev>",
    "phase_after": "design_extracted"
  }
  ```

Skip this in standalone mode.

**Then tell the user, briefly:**
- Which Figma access path you used (MCP / REST API / manual / Playwright-assisted).
- How many color / typography / component tokens you extracted.
- Any sections you couldn't fill confidently and would benefit from human input.
- Where the file was saved.
- In dev-flow mode: the new phase and the next-step proposal (`design-md-to-app` to scaffold the codebase, or stay here to refine).

If the user wants companion artifacts (Tailwind config, `tokens.json`), offer them — but they're outside the spec and only on request.

## Important constraints

- **Do not invent values that aren't in Figma.** If something can't be extracted (e.g. brand voice not visible in the file), ask the user or leave the prose intentionally light and flag the gap.
- **Do not duplicate section headings.** Per spec, this rejects the file.
- **Do not write the file in a directory other than the project root** unless the user explicitly says so.
- **Do not store the user's Figma token to disk.** Use it only for the current session.
- **The spec evolves.** If you're unsure about a detail, the canonical reference is in `references/spec.md` — re-read it rather than guessing.
