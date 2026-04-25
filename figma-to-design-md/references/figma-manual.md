# Path C — Manual export (fallback)

When neither the Figma MCP nor the REST API is usable (no MCP installed, no token, file in a workspace you can't access), you can still produce a respectable DESIGN.md by asking the user to export materials from Figma manually.

This path is slower and the result is less precise, but it always works.

## Path C-bis — Playwright-assisted extraction

**Before falling back to asking the user**, check whether you have Playwright (or any headless browser) available in this session. Look for tool names containing `playwright`, `browser`, or `chrome`. If yes, and the Figma URL is a public file (community files, shared "anyone with link" files), you can navigate the file yourself and extract a surprising amount visually.

The Figma editor in a browser is a WebGL canvas, so `getComputedStyle` won't work — you can't read CSS values through the DOM. But you can:

1. **Read the layer outline** via accessibility snapshot. Layers like `Home`, `/journal`, `Styles`, `Typography`, `Type System`, `Foundations`, `Design System` appear as named nodes you can click.
2. **Click a named layer** to select it. The URL's `node-id` parameter updates.
3. **Take screenshots** at the current zoom level.
4. **Run JavaScript** on the canvas via `browser_evaluate` for things like scrolling.

### Useful shortcuts in the Figma web editor (public/no-login)

| Action | Shortcut |
|---|---|
| Zoom 100% | `Cmd+0` (Mac) / `Ctrl+0` (Win) |
| Zoom to fit | `Shift+1` |
| Zoom to selection | `Shift+2` (often disabled without login — has a quirk on Sites) |
| Pan | hold space + drag |

⚠️ **Caveat from real-world testing**: on Figma Sites (community/public files) without a logged-in account, several keyboard shortcuts including `Shift+2` ("zoom to selection") silently fail. Cookie banners and "Sign up" prompts can also intercept clicks. If shortcuts don't work, you have to scroll/zoom the canvas via JS programmatically or rely on what's already visible.

### Strategy: find the Type System frame

This is the highest-value step on Path C-bis. Most production design files contain a frame named explicitly for type — designers use it as their own internal reference. Common names (in order of frequency):

- `Typography`
- `Type System`
- `Type Scale`
- `Styles`
- `Foundations`
- `Design System`
- `Brand` / `Brand Guidelines`
- `Type Specimen`

In the layer outline, search for any of these (case-insensitive). Click it; the URL's `node-id` will update. Take a high-resolution screenshot. From the screenshot:

- **Font family**: visible from the rendering. If the brand uses a custom font (Pangram Sans, Söhne, Roobert, etc.) the unique letterforms are usually identifiable. If unsure, name the closest mainstream lookalike (Inter, IBM Plex, etc.) and flag the uncertainty in the prose.
- **Sizes**: each row in a type specimen typically labels itself ("Display Large 72px / 80px"). Read the labels.
- **Weights**: same — type specimens annotate weights.
- **Line height / letter-spacing**: usually labeled or derivable from the visible spacing.

If the Type System frame is not visible at the current zoom, get into it with these moves (in order):

1. Click the layer in the outline (selects it).
2. Try `Shift+2` (zoom to selection). If nothing happens, continue.
3. Use `browser_evaluate` to scroll the canvas to the layer's bounding box (Figma stores positions in `data-*` attributes on internal nodes — inspect with the snapshot first).
4. Brute-force: pan the canvas with mouse drag while holding space, taking periodic screenshots.

### Strategy: extract colors via k-means

When you have any screenshot of the design with visible color blocks (a thumbnail, a banner, a hero), run k-means quantization on the cropped pixels (excluding Figma chrome — strip ~290px from the left, ~60px top, ~160px bottom of a 1440×900 viewport). Use k=10–15 and exclude near-white clusters that correspond to the editor's grey background. You'll get the dominant brand colors with reasonable accuracy.

A reference Python script lives at `scripts/quantize_palette.py` (added in v2 of this skill) — it takes a PNG path and prints hex codes ranked by frequency.

### When Playwright fails or isn't enough

Fall back to asking the user (the rest of this file). Do not invent values to fill gaps.

## Ask the user for these artifacts

In one message, request:

1. **A "tokens" export**, in any of these formats (in order of preference):
   - A `tokens.json` exported from a plugin like *Tokens Studio* or *Design Tokens*.
   - The "Variables → Export to JSON" feature in Figma (recent versions).
   - A screenshot of the Variables panel listing colors and numbers, plus a screenshot of the text styles panel.

2. **PNG screenshots of 2–4 representative frames**:
   - One "hero" frame (landing or main screen).
   - One frame showing typography hierarchy (article / settings / form).
   - One frame showing components (buttons, inputs, cards) with their variants.
   - Optionally: a dark-mode counterpart, if applicable.

3. **A 1–3 sentence brand brief** if the user hasn't already given one — for the **Overview** prose section.

Tell them where to drop the files (e.g., into the project root or a `figma-export/` subfolder).

## What to do with what they send

### If they sent a `tokens.json`

The format depends on the plugin, but most look like W3C-style nested groups:

```json
{
  "color": {
    "primary": { "value": "#1A1C1E", "type": "color" },
    "secondary": { "value": "#6C7278", "type": "color" }
  },
  "size": {
    "spacing": {
      "sm": { "value": "8px", "type": "dimension" }
    }
  }
}
```

Flatten the nested keys with hyphens (`color/primary` → `primary` in the design.md `colors` group). Convert as follows:

| W3C-ish type | design.md group |
|--------------|-----------------|
| `color` | `colors` |
| `typography` | `typography` (object with fontFamily, fontSize, etc.) |
| `dimension` (under `radius`/`rounded`) | `rounded` |
| `dimension` (under `space`/`spacing`/`gap`) | `spacing` |
| `fontFamilies`, `fontWeights`, `fontSizes` | merge into `typography` entries |

Don't blindly copy structure — design.md has a flat schema, not nested groups.

### If they sent screenshots only

Use vision to extract:

- **Colors**: use a color picker (or careful eyeballing) on the screenshot. Aim to identify ~6–10 distinct colors at most. Group as `primary`, `secondary`, `tertiary`, `neutral`, `surface`, etc.
- **Typography**: identify font family by visual style; estimate sizes by reference (a button label is ~14px, a body paragraph ~16px, a hero heading ~48–80px). Be honest about approximation in the prose.
- **Layout**: from the frame structure, infer grid (single column? 2-col? 12-col?), padding rhythm.
- **Shapes**: corner radii by inspection — typically 0px (sharp), 4–8px (subtle), 12–16px (rounded), 9999px (pill). Pick the recurring values.
- **Elevation**: any visible shadows? Tonal layering? Borders only? Describe in prose.

### Brand brief

Use the user's brief plus what's visible in the screenshots to write the **Overview** section. Don't fabricate emotion — if the user said "B2B SaaS for accountants", the tone is "professional, trust-building, dense", not "playful, organic, joyful".

## Important

- Tell the user upfront that this path's accuracy depends entirely on what they share. The DESIGN.md is editable — they can refine values after.
- Save any uploaded images to `figma-export/` (create the dir if needed) so the user can find them later. Don't leave them in `/tmp` or scattered.
- **Never** invent values you don't have evidence for. It's better to omit a token group than to ship made-up numbers.
- After generating, briefly note in your reply which sections are "high-confidence" (extracted directly) vs. "estimated" (from screenshots).
