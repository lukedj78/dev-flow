# Path B — Figma REST API

Use this when no Figma MCP is available but the user has (or can generate) a personal access token. The REST API gives you the full file tree, styles, variables, and image exports.

## Get a token

1. The user goes to https://www.figma.com/developers/api#access-tokens
2. Generates a personal access token with at minimum:
   - `File content: Read`
   - `Library content: Read` (if they want library variables/styles)
   - `Variables: Read`
3. Pastes it back. Use it for the session only — **do not write it to disk, do not echo it back, do not include it in any committed file.**

If `FIGMA_ACCESS_TOKEN` is already set in the env (`printenv FIGMA_ACCESS_TOKEN`), use that.

## Resolve URL → file key

Figma URL shape:
```
https://www.figma.com/design/<FILE_KEY>/<file-name>?node-id=<NODE_ID>
https://www.figma.com/file/<FILE_KEY>/<file-name>
```

Pull `<FILE_KEY>`. Optionally pull `<NODE_ID>` to focus on a specific frame/page.

## The helper script

There's a Python helper at `scripts/figma_api_fetch.py` that wraps the most common calls and prints results as JSON to stdout. Run it like:

```bash
export FIGMA_ACCESS_TOKEN="<token>"
python3 scripts/figma_api_fetch.py <file_key> --section styles
python3 scripts/figma_api_fetch.py <file_key> --section variables
python3 scripts/figma_api_fetch.py <file_key> --section components
python3 scripts/figma_api_fetch.py <file_key> --section file       # full tree (large)
python3 scripts/figma_api_fetch.py <file_key> --section meta       # name, version, last modified
```

Read the JSON it prints, extract what you need, then move on. Don't dump the full file tree into context — it can be huge.

## Endpoints (reference, in case you need to call directly)

All endpoints accept the header `X-Figma-Token: <token>`.

| Endpoint | What it returns |
|----------|-----------------|
| `GET /v1/files/:file_key` | Whole file tree (document → pages → frames → nodes). Big. |
| `GET /v1/files/:file_key/nodes?ids=<id1>,<id2>` | Specific subtrees. Use this when you have a `node-id` from the URL. |
| `GET /v1/files/:file_key/styles` | Color, text, effect, grid styles (metadata: name, key, style_type). |
| `GET /v1/files/:file_key/variables/local` | Local variables (Variables, modes, collections). **Most useful for tokens.** |
| `GET /v1/files/:file_key/components` | Components in the file. |
| `GET /v1/files/:file_key/component_sets` | Component sets (variant groups). |
| `GET /v1/images/:file_key?ids=<id>&format=png&scale=2` | Render a node as PNG. Returns a temporary S3 URL. |

## Mapping REST → design.md tokens

### Colors

From `/variables/local`, find variables of `resolvedType: "COLOR"`. Each has a `valuesByMode` map. Take the default mode value and convert from Figma's normalized RGBA (`{r: 0..1, g: 0..1, b: 0..1, a: 0..1}`) to hex:

```python
def to_hex(c):
    r = round(c['r'] * 255)
    g = round(c['g'] * 255)
    b = round(c['b'] * 255)
    return f"#{r:02x}{g:02x}{b:02x}"
```

If the variable name is hierarchical (`color/primary/60`), flatten with hyphens (`primary-60`). Strip the leading `color/`.

If the file has no Variables but has color **styles**, use `/styles` to list them, then for each style ID look up its `paints` in the file tree (in the file response, `styles[styleId]` references the node where it's used; the actual fill is on the node).

### Typography

From `/variables/local` look for variables of `resolvedType: "STRING"` (font names) and `"FLOAT"` (font sizes). Most files don't put typography in Variables — they use **text styles** instead.

Text styles in the file tree appear on text nodes. For each unique text style:
- `fontFamily`: from the text node's `style.fontFamily`
- `fontSize`: from `style.fontSize` (add `px`)
- `fontWeight`: from `style.fontWeight`
- `lineHeight`: from `style.lineHeightPx` (add `px`) or `style.lineHeightPercent` (compute multiplier)
- `letterSpacing`: from `style.letterSpacing` (Figma uses px or %)

The text style's *name* in Figma (e.g., `Heading/Display Large`) becomes the token name (`display-lg`). Flatten with hyphens, lowercase.

### Rounded

Look for number variables named like `radius/*` or `corner/*`. Otherwise scan component frames and collect their `cornerRadius` values; pick the recurring distinct values and map to `sm/md/lg/xl/full`.

### Spacing

Look for number variables named like `space/*`, `spacing/*`, `gap/*`. Otherwise infer from auto-layout `itemSpacing` and `paddingLeft/paddingRight/...` values across components.

### Components

For each entry in `/component_sets` and `/components`, fetch the underlying nodes (`/nodes?ids=<id>`). Read the topmost frame's `fills`, `strokes`, `cornerRadius`, `paddingLeft/Top/Right/Bottom`. Map to `backgroundColor`, `textColor` (from the inner text node), `rounded`, `padding`.

**Padding**: design.md only accepts a single dimension per key — no CSS shorthand. If the component's `paddingLeft`/`Right`/`Top`/`Bottom` are all equal, emit it (`padding: 12px`). If they differ (e.g. 12 vertical, 24 horizontal), pick the larger one (or the visually dominant axis) and mention the asymmetry in the prose; do NOT emit `"12px 24px"`. Same for any other dimension key.

Use token references where the value matches a known token, e.g.:

```yaml
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    rounded: "{rounded.md}"
    padding: 12px
```

### Variants

Component sets in Figma have variants (`State=Default`, `State=Hover`, etc.). Emit each as a separate component key with a hyphen suffix:

```yaml
button-primary:        # State=Default
button-primary-hover:  # State=Hover
button-primary-active: # State=Pressed
```

Only include variants that *differ* from the base — if `State=Hover` only changes `backgroundColor`, the variant entry should contain only that property.

## Rate limits

Figma rate-limits per token at roughly 6000 requests / minute, but file fetches are slow (1-15s). Don't loop over hundreds of nodes individually; batch with `?ids=`.

## When this fails

- 403 → token missing scope or file is in a workspace the token can't see. Ask user for a token with file access.
- 404 → wrong file key. Re-extract from URL.
- Empty `/variables/local` → file has no Variables (older file or designer didn't use them). Fall back to scanning styles + nodes.

If everything fails, drop to **Path C (manual export)** — see `figma-manual.md`.
