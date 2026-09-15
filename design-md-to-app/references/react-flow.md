# Node graphs — React Flow (`@xyflow/react`)

Verified 2026-09-15 against `@xyflow/react@12.11.6` (types in `dist/esm/`) and reactflow.dev (theming,
performance, layouting, SSR, accessibility, React Flow UI). MIT, maintained by xyflow. `[VERIFY]` prop
names against the installed version before relying on them — the library moves every few weeks.

It is already in five of our projects (bidmaster, agentos, agentic-orchestrator, idea-validator,
agenticflow), and each wired it differently: three layouts written by hand, `colorMode` handled three
ways, a mobile fallback in one. This file is the one way.

## When to reach for it — and when not

| The screen shows… | Use |
|---|---|
| A graph the user **acts on**: drag, connect, select a node, open its detail, zoom a large pipeline | **React Flow** |
| A process, DAG or org chart the user only **reads**, at a size that fits the screen | a composition of shadcn primitives (cards + a CSS grid/flex rail), or static SVG — no pan/zoom runtime |
| A free-form **workspace** where the content inside is a live page or a document (design tool, canvas editor) | `iframe-canvas` — a different architecture, owned by that skill |
| A chart | `chart.tsx` (shadcn + Recharts) |

A read-only status graph that fits the viewport does not need a pan/zoom engine. Say which row applied
when you pick it.

## Wiring in Next.js 16

- The flow is a **client component** (`"use client"`): it measures the DOM. Server components pass it
  plain data (nodes/edges derived on the server); the canvas itself renders on the client.
- The parent **must have a height** — React Flow fills its container. Give the wrapper a size with
  Tailwind classes (`h-[…]` is an arbitrary value the design lint will flag; prefer `h-96`, `min-h-0
  flex-1` in a flex column, or `aspect-video`).
- `nodeTypes` and `edgeTypes` are declared **at module scope** (or `useMemo`), never as an object literal
  inside the render. Custom node components are wrapped in `memo`. From the performance guide:
  *"Components provided as props to the `<ReactFlow>` component … should either be memoized using
  `React.memo` or declared outside the parent component."* Handlers go through `useCallback`, option
  objects (`defaultEdgeOptions`, `fitViewOptions`) through `useMemo` or module constants.
- Read the store with **narrow selectors** (`useStore((s) => s.selectedNodeIds)`), not the whole `nodes`
  array — every node update re-renders whatever reads it.
- Server rendering of the flow itself (static HTML, OG images) needs explicit node `width`/`height` and
  `handles` positions: *"React Flow only renders nodes if they have a width and height."* Not needed for a
  normal client canvas.

## Theme from the DESIGN.md tokens

The package ships two stylesheets (both present in `dist/`):

- `@xyflow/react/dist/base.css` — *"required for React Flow to function correctly"*.
- `@xyflow/react/dist/style.css` — base plus default looks for the built-in nodes, controls, minimap.

**With shadcn + Tailwind v4, import it in `globals.css`, in the base layer, before Tailwind** — the form
the theming guide gives:

```css
@import "@xyflow/react/dist/style.css" layer(base);
@import "tailwindcss";
```

Then map React Flow's variables onto the project tokens once, so every built-in piece follows DESIGN.md
in both themes. **Set the names without `-default`.** `style.css` reads each colour as
`var(--xy-node-background-color, var(--xy-node-background-color-default))`, and it redefines the
`-default` names under `.react-flow.dark` — a mapping written on the `-default` names loses to that
selector in dark mode. The un-suffixed names are read first and nothing in the stylesheet sets them:

```css
.react-flow {
  --xy-background-color: var(--background);
  --xy-node-background-color: var(--card);
  --xy-node-color: var(--card-foreground);
  --xy-node-border: 1px solid var(--border);
  --xy-edge-stroke: var(--border);
  --xy-edge-stroke-selected: var(--primary);
  --xy-handle-background-color: var(--primary);
  --xy-handle-border-color: var(--background);
  --xy-selection-background-color: color-mix(in oklch, var(--primary) 8%, transparent);
  --xy-controls-button-background-color: var(--background);
  --xy-controls-button-color: var(--foreground);
  --xy-controls-button-border-color: var(--border);
  --xy-minimap-background-color: var(--muted);
}
```

Every name above was checked against `style.css` in 12.11.6 (85 `--xy-*` variables in all). `[VERIFY]`
them on upgrade — a misspelt variable fails silently and the stock grey stays.

Custom nodes are **compositions of shadcn primitives** (`Card`, `Badge`, `Button`, `Tooltip`) styled with
Tailwind tokens — never a hand-rolled box with raw colours. Edge colours set in JS use the tokens too
(`style: { stroke: "var(--primary)" }`), which is what our projects already do right.

### `colorMode`

`colorMode` is `"light" | "dark" | "system"` (default `"light"`) and adds a class to `.react-flow`.
Follow the app's theme, not the OS and not a constant:

```tsx
const { resolvedTheme } = useTheme()             // next-themes, already wired by the scaffold
<ReactFlow colorMode={resolvedTheme === "dark" ? "dark" : "light"} … />
```

`resolvedTheme` is `undefined` until mount. Render the wrapper with its final size and the flow once
mounted (bidmaster's pattern), so there is no flash and no layout shift. `"system"` ignores a user who
picked a theme in the app's toggle; a hard-coded `"dark"` breaks the light theme.

## Layout

Pick by the shape of the data, using the guide's own comparison (`reactflow.dev/learn/layouting`):

| Data | Library | Why, in the guide's terms |
|---|---|---|
| Tree or DAG, nodes of different sizes | **`@dagrejs/dagre`** | *"If you need to organize your flows into a tree, we highly recommend dagre"*; handles dynamic sizes and sub-flows (with an open issue when sub-flow nodes connect outside) |
| Strict tree, one root, uniform nodes | `d3-hierarchy` | needs a single root and gives every node the same size |
| Sub-flows, ports, edge routing, many constraints | `elkjs` | the most configurable and the hardest to support |
| A network with no hierarchy | `d3-force` | iterative, runs continuously — costly |
| Waves/levels already computed by the domain (e.g. a DAG grouped by execution wave) | a small pure function | legitimate when the grouping *is* the data; keep it pure and tested |

Lay out **after nodes are measured** when sizes vary: `useNodesInitialized()` becomes true once every
node has `measured` dimensions; run the layout then and `fitView`. Never guess sizes that the DOM knows.

## Nodes and edges from React Flow UI

xyflow publishes **React Flow UI** — *"Ready-to-use React Flow components built with shadcn/ui
components and Tailwind CSS"*, MIT, React 19 + Tailwind 4: Base Node, Status Indicator, Tooltip,
Database Schema, Labeled Group, Base/Labeled/Button Handle, edges with button or data, Node Search, Zoom
Slider, DevTools, and two workflow-editor templates. Prefer them to writing a status badge node for the
fifth time.

They are a third-party registry, so they go through **`registry-intake`**, not a bare `shadcn add`:

```bash
python3 <skills>/registry-intake/scripts/registry_intake.py allow <root> @reactflow 'https://ui.reactflow.dev/{name}' --reason "node UI for <feature>"
python3 <skills>/registry-intake/scripts/registry_intake.py review  <root> @reactflow/node-status-indicator
```

Checked 2026-09-15: items are served at `https://ui.reactflow.dev/<name>` (no `.json`), without a
`$schema`, depend on `@xyflow/react`, and `labeled-group-node` pulls `base-node` by URL. The review of
`node-status-indicator` came back low tier, clean (one R2 note: no `$schema`).

## Attribution

React Flow renders a small attribution link. The prop that hides it says, in the installed types:
*"Please only remove the attribution if you have a React Flow subscription."* The licence is MIT, so this
is xyflow's request, not a legal bar — but it is a decision, not a default. **Keep the attribution**
unless the project has a React Flow Pro subscription; if it does, set `proOptions={{ hideAttribution: true }}`
and record it in `meta.json#stack_config`. (All six flows in our projects hide it today, none recorded why.)

## Accessibility and i18n

- Keyboard support is on by default: `nodesFocusable` and `edgesFocusable` default to `true`; Tab moves
  through nodes and edges, Enter/Space selects, Escape deselects, arrows move a selected draggable node.
  Do not set `disableKeyboardA11y` to silence a design complaint.
- A node that behaves like a link or a button gets `ariaRole` (default `role="group"`) and a real
  `<Link>`/`<Button>` inside — clicking a node to navigate is not keyboard-reachable on its own.
- **`ariaLabelConfig` localises the built-in labels** (*"Allows localization, customization of ARIA
  descriptions, control labels, minimap labels, and other UI strings"*). Feed it from next-intl — golden
  rule 2 covers the canvas too.
- Motion: `fitView({ duration })` and animated edges animate. Under `prefers-reduced-motion`, pass no
  duration and drop `animated` (see `transitions`).

## Mobile

Pan, zoom and drag fight the page scroll on a phone. Below `md:`, render the same data **without** the
canvas — a vertical list or a horizontally scrollable rail of the same node components — as
agentic-orchestrator's `variant="scroll"` does. A read-only graph on mobile is a list with connectors,
not a tiny zoomable canvas.

## Performance at size

- `onlyRenderVisibleElements` (default `false`) renders only what is in the viewport — the types note it
  *"might improve performance … but also adds an overhead"*: turn it on for hundreds of nodes, not twenty.
- Collapse big subtrees with the node `hidden` flag instead of removing and re-adding nodes.
- Keep node styles cheap: shadows, gradients and animations multiply by the node count.

## Checklist

- [ ] The "when to reach for it" row is stated; a read-only graph that fits is not a canvas.
- [ ] `"use client"` component, container with a real height, `nodeTypes` at module scope, custom nodes `memo`.
- [ ] `style.css` imported `layer(base)` before Tailwind; `--xy-*` mapped to tokens; nodes built from shadcn primitives.
- [ ] `colorMode` from `resolvedTheme`, rendered after mount.
- [ ] Layout library chosen by data shape; sized layouts run after `useNodesInitialized()`.
- [ ] React Flow UI items installed through `registry-intake`.
- [ ] Attribution kept, or hidden with a recorded subscription.
- [ ] Keyboard path works; `ariaLabelConfig` localised; reduced motion respected; mobile gets a list, not a canvas.
