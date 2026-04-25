# Path A — Figma Dev Mode MCP

Use this when an MCP server exposes Figma tools to the session. The most common ones come from the official **Figma Dev Mode MCP** (requires Figma Desktop running with Dev Mode active) or third-party servers like `figma-developer-mcp`.

## Detect

Look for any tool whose name contains `figma`. Common shapes:

- `mcp__figma__*` — generic Figma MCP servers
- `mcp__figma_dev_mode__*` — Figma's official Dev Mode MCP
- `mcp__figma_developer_mcp__*` — popular community server

If you see one, use it. If multiple, prefer the official Dev Mode server.

## What you typically get

Different servers expose different tools, but you'll usually find some subset of:

- A tool that **fetches a node by URL or ID** and returns its tree (frames, components, styles applied).
- A tool that **lists styles / variables** for a file.
- A tool that **exports an image** of a node (PNG/SVG).
- A tool that **returns code** (CSS / Tailwind / React) for a selection.

Read the tool descriptions in your environment — don't assume names.

## How to use them

1. **Resolve the URL to a file key.** A Figma URL has shape:
   ```
   https://www.figma.com/design/<FILE_KEY>/<file-name>?node-id=<NODE_ID>&...
   ```
   Extract `<FILE_KEY>` (and `<NODE_ID>` if present) from the URL.

2. **Get the file's variables and styles first.** These give you tokens directly:
   - Color variables → `colors` tokens
   - Number variables (radius, spacing) → `rounded` and `spacing` tokens
   - Text styles → `typography` tokens
   - Effect styles (shadows) → input for the **Elevation & Depth** prose

3. **Walk the components.** Look for top-level component sets named like `Button`, `Chip`, `Input`, `Card`. For each, read its variant properties (default, hover, active, disabled) and capture `fill`, `stroke`, `cornerRadius`, `padding` — map these to `components.<name>` tokens with references to the color tokens (`{colors.primary}`).

4. **Sample 2–4 hero frames** to inform the prose sections (Overview, Layout, Shapes). Use the image-export tool if you need to "see" them; otherwise the frame structure (children, auto-layout settings, padding) is often enough to write meaningful prose about the layout system.

## Mapping notes

- **Figma Variables vs. Styles**: modern files use Variables (typed, scoped, support modes for light/dark). Older files use Styles (untyped, name-based). Both are fine — Variables map more cleanly to design.md tokens because they already have names like `color/primary/60` that you can flatten to `primary-60`.
- **Modes (light/dark)**: design.md alpha doesn't formally specify multi-mode token sets. If the Figma file has light + dark variables, generate the DESIGN.md for one mode (the default) and note the other mode's existence in the **Overview** prose. Don't invent a multi-mode YAML structure that isn't in the spec.
- **Auto-layout padding** in Figma → the component's `padding` token. design.md accepts only a single dimension per key (no CSS shorthand). If Figma's auto-layout has different vertical and horizontal paddings, pick the dominant axis and note the asymmetry in the **Components** prose. Never emit `padding: "12px 24px"` — that fails the spec.
- **Effects** (`drop-shadow`, `inner-shadow`, `background-blur`) → describe in **Elevation & Depth** prose. The current spec doesn't have a dedicated `shadows` token group, so don't create one — describe in prose.

## If the MCP tool fails

If a Figma MCP tool errors with "file not found" or "no permission", the user's Figma Desktop probably isn't running, or Dev Mode isn't enabled, or the file is in a workspace they don't have access to. Tell the user, then **fall back to Path B (REST API)** — see `figma-api.md`.
