---
name: image-to-design-md
description: 'Generate a DESIGN.md (Google design.md spec) from 1+ raster images — PNG / JPG screenshots, mockups, Pinterest pins, Dribbble shots, competitor app captures. Extracts palette via k-means, identifies typography + components via vision-LLM, infers layout / radius / spacing, synthesizes a spec-compliant DESIGN.md + copies images to `screenshots/`. Use whenever the user provides 1+ images and asks to generate / extract / build a DESIGN.md / design system / design tokens — even phrased loosely like "estrai design da queste immagini", "make a DESIGN.md from this mockup", "design system from these screenshots". Not for: Figma files (use `figma-to-design-md`), code scaffolding (use `design-md-to-app` after), or single-page generation (use `screenshot-to-page` after the project is scaffolded).'
---

# Image(s) → DESIGN.md

Take 1 or more raster images (PNG / JPG) and produce a `DESIGN.md` that conforms to the Google design.md spec. The same workflow used in `figma-to-design-md` Path C (manual fallback) is the **default** here, since raster is all we have.

## When this skill applies

Trigger on any of:
- The user pastes 1+ image paths and asks for a design system / DESIGN.md.
- The user describes images they have (Pinterest pins, Dribbble shots, competitor screenshots, hand-drawn mockups, scanned printouts).
- An explicit request: "estrai design da queste immagini", "make a DESIGN.md from this image", "build a design system from this Figma export PNG".
- The orchestrator (`dev-flow`) routes here from phase `prd_drafted` or `empty` when the user has no Figma URL but has images.

If the user has BOTH a Figma URL AND images, prefer `figma-to-design-md` (more precise — Variables panel beats vision LLM) and pass the images to `screenshot-to-page` later.

## What you produce

In **dev-flow mode**: `<root>/.workflow/DESIGN.md` + `<root>/.workflow/screenshots/<slug>.png` for each input image.
In **standalone mode**: `<project-root>/DESIGN.md` + `<project-root>/screenshots/`.

The DESIGN.md follows the same 8-section structure as `figma-to-design-md` produces — same spec — see `references/spec.md` for the canonical Google design.md spec.

## Dev-flow contract

This skill participates in the dev-flow workflow. See `references/contracts.md` for the canonical schema. Key facts:

- **Output** goes into `<root>/.workflow/`:
  - `DESIGN.md` (the main artifact)
  - `screenshots/` (input images copied + slugged)
- **State** is updated by setting `meta.json#phase = "design_extracted"` (only if the current phase is earlier in the enum), refreshing `updated_at`, and appending a `history` entry.
- **Standalone mode** (no `.workflow/` present) is supported — fall back to writing at the user-specified project root.

## Prerequisites

- **Vision-capable LLM**. This skill leans on the model's vision capability for typography identification, component recognition, and layout inference. Claude Opus/Sonnet/Haiku 4.5+ all qualify; ChatGPT-4o and Gemini also work in their respective harnesses.
- **Python 3.10+** with Pillow + numpy + scikit-learn (only for `quantize_palette.py`).

If neither vision nor Python is available, this skill cannot run — refuse and explain. Don't fabricate token values.

## Workflow

### Step 1 — Locate the images and the output directory

- The user provides one or more image paths (absolute or relative to cwd). Validate each: exists, is a readable file, has extension `.png` / `.jpg` / `.jpeg` / `.webp` / `.bmp`.
- **Dev-flow mode**: if `<cwd>/.workflow/meta.json` exists, output goes into `<cwd>/.workflow/`. Read `meta.json#project_name` and `PROJECT.md` (if present) for brand context.
- **Standalone mode**: identify the project root (current working directory unless user says otherwise). Output goes there as `DESIGN.md` + `screenshots/`.
- If a `DESIGN.md` already exists at the target, ask before overwriting.

### Step 2 — Capture brand context

The images alone don't tell you "what this brand is for". Ask the user for, at minimum:

1. **Project name** (used as `name:` in the frontmatter and as the slug for screenshot filenames).
2. **Audience / use-case** (1–2 sentences). Used to write the **Overview** section.
3. **Voice / tone** if obvious — playful, editorial, austere, etc.

If `PROJECT.md` exists in `.workflow/`, reuse it: it already answers most of these.

### Step 3 — Extract the palette via k-means

For each input image:

1. Run `python3 scripts/quantize_palette.py <image-path> --k 12 --no-crop` to get the top 12 dominant colors.
2. The script returns `(hex, percentage)` pairs. Don't take all 12 blindly — filter:
   - Drop pure-grays unless they're explicitly a UI surface color.
   - Drop colors that appear only in photographic content (skin tones, sky, foliage). These are content, not brand.
   - Cluster near-duplicates (Δhex < 8 per channel).

When you have **multiple images**, run `scripts/aggregate_palettes.py <img1> <img2> …` to merge their palettes into a single deduped list ranked by total weighted frequency. This handles the case "5 screenshots of the same app" where the brand palette repeats across images — the cross-image-recurring colors are the real tokens; one-off colors are noise.

Map the surviving colors to spec-recommended names: `primary`, `secondary`, `tertiary`, `neutral`, `surface`, `on-surface`, `error` (per the spec's "Recommended Token Names"). When in doubt about which color is `primary`, ask the user — typically it's the most saturated brand-distinct color, NOT the one that takes the most pixels (white usually wins on pixel count).

### Step 4 — Identify typography

This is the highest-confidence-loss step. Vision LLMs can identify a font family within a small set of candidates but **cannot read fontFamily metadata that doesn't exist in raster pixels**.

For each image:

1. Identify text regions and their visual hierarchy (display headline, body, caption, button label, …).
2. For each tier, estimate:
   - **Family**: name 1–3 likely candidates. If the font is clearly proprietary (Söhne, Roobert, Wise Sans, Helvetica Now, Cera Pro, GT Walsheim, Brown, Söhne Breit), name it AND a Google Fonts open-source fallback (Inter, Manrope, DM Sans, IBM Plex Sans). The DESIGN.md should emit the **fallback** as `fontFamily` and document the proprietary original in the prose.
   - **Size**: estimate from pixel height of cap-letters relative to known image dimensions. Use designer-friendly numbers (12, 14, 16, 18, 20, 24, 32, 40, 48, 64, 72, 96, 126).
   - **Weight**: identify from stroke thickness — typical buckets are 400 (regular), 500 (medium), 600 (semibold), 700 (bold), 900 (black).
   - **Line-height**: estimate from spacing between lines.
   - **Letter-spacing**: estimate, expressed in `em` (positive ≈ tracked, negative ≈ tight).

State the confidence level explicitly in the prose: `display-lg: Inter 96/0.9/900 (visually identified — original may be Söhne Breit, swap if available)`.

### Step 5 — Identify components

For each image, scan for recurring UI patterns:

- **Buttons**: shape (pill / rounded / sharp), fill color, text color, padding hint, hover-state if visible.
- **Cards**: radius (sharp ≈ 4px, soft ≈ 12–16px, generous ≈ 24–40px, mega ≈ 9999px-pill — eyeball it), surface color, border presence.
- **Inputs**: radius, fill, border treatment, error state if any.
- **Navigation**: top-bar / sidebar / mixed. Active-item style.
- **Badges / chips**: shape, color mapping (status-driven? semantic?).

Map each to the `components` block in the frontmatter. **Don't invent variants you don't see** — if only the default state is visible, emit only the default. Variants get added later by `screenshot-to-page` when more images arrive.

### Step 6 — Identify layout, shapes, elevation

- **Layout**: grid model (single-column / 2-col / 12-col / asymmetric mosaic). Container max-width if visible. Spacing rhythm if you can read it (4 / 8 / 16 px clusters).
- **Shapes**: corner-radius scale (collect distinct radii observed). Map to `rounded` tokens (`sm/md/lg/full`).
- **Elevation**: drop-shadows? ring borders? tonal layers? For each card-like surface, decide.
- **Brand voice prose**: synthesize the **Overview** section from the user's audience input + observed visuals. 4-6 sentences.

### Step 7 — Synthesize and write the DESIGN.md

Assemble the frontmatter (colors / typography / rounded / spacing / components) + 8 prose sections (Overview / Colors / Typography / Layout / Elevation & Depth / Shapes / Components / Do's and Don'ts) per the spec.

Validate before writing:

- Frontmatter delimited with `---` lines.
- All color values are `"#rrggbb"`.
- All dimensions use `px`, `em`, or `rem`.
- All `{path.to.token}` references resolve.
- 8 sections in spec order, no duplicates.
- `colors.primary` is defined (mandatory).

Write to `<root>/.workflow/DESIGN.md` (dev-flow) or `<project-root>/DESIGN.md` (standalone).

### Step 8 — Copy images to screenshots/

Each input image is copied into `<root>/.workflow/screenshots/<slug>.png` so:
- Future `screenshot-to-page` invocations can use them as references.
- The DESIGN.md prose can cite them: "Pattern observed in `screenshots/dashboard.png`".

Slug each filename: lowercase, replace non-alphanumeric with hyphens, ensure uniqueness.

### Step 9 — Update state and report

**Dev-flow mode:** before reporting, update `<root>/.workflow/meta.json`:
- if current `phase` is earlier than `design_extracted`, set `phase = "design_extracted"`.
- bump `updated_at` to ISO-8601 UTC now.
- append a `history` entry:
  ```json
  {
    "skill": "image-to-design-md",
    "ran_at": "<now>",
    "inputs": {"image_count": <n>, "images": ["<paths>"]},
    "outputs": ["DESIGN.md", "screenshots/"],
    "phase_before": "<prev>",
    "phase_after": "design_extracted"
  }
  ```

**Then tell the user, briefly:**
- Number of images analyzed.
- How many color / typography / component tokens you extracted.
- Confidence per section (palette: high; typography: medium-low; components: medium).
- Sections you flagged as low-confidence and would benefit from human input.
- Where the file was saved.
- In dev-flow mode: the new phase and the next-step proposal (`design-md-to-app` to scaffold the codebase).

## Important constraints

- **Don't invent values you don't have evidence for.** If only one image is supplied and it doesn't show typography, emit a stub `typography:` block with a prominent note in the prose, OR ask the user for one extra image showing text. Don't fabricate.
- **Be explicit about font names.** Vision can't read embedded font metadata; everything is a guess. Always name a Google Fonts fallback and mention the likely original in prose.
- **Don't try to identify dark/light modes from a single image.** If the image is dark-themed, generate the dark variant; auto-derive light only if the user requests.
- **Don't store images outside `screenshots/`.** Skills downstream expect them there.
- **Don't process images larger than ~10 MB without warning the user** — k-means on a 4K image is slow.
- **Per la lingua delle prose**: la skill scrive le sezioni in inglese di default. Se il `PROJECT.md` o l'input utente è in italiano, la skill rispetta la lingua dell'utente per la prosa (frontmatter resta in formato spec — nomi token in inglese).

## Quality bar — what a good output looks like

- **Palette section**: 8–15 named tokens with prose justification ("primary `#7839CD` reserved for the load-bearing CTA"). No "color1 / color2" placeholder names.
- **Typography section**: 6+ levels with samples that read as real product copy (extracted from PRD.md if available, or asked from the user). NEVER use `Lorem ipsum` or "Body 16/400/regular" as samples.
- **Confidence flags**: every section that contains a guess is marked. Future agents reading the DESIGN.md should know what to trust.
- **Screenshot citations**: the prose references `screenshots/<file>` for any inferred-from-image claim.

A good DESIGN.md from this skill is one that the user can read, agree with, edit a few prose lines, and ship — not one they have to rewrite.
