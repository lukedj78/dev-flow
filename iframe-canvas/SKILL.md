---
name: iframe-canvas
description: 'Decide and build a pan/zoom canvas whose artboards are live `<iframe>` previews — the architecture behind AI site/app builders (Reweb, Sleek, Plasmic, Builder.io, Onlook), not the one behind Figma. Owns the decisions that fail late: how many live frames the tab can afford, same-origin vs cross-origin isolation, snapshot-vs-live per artboard, the interaction mode that gates pointer events, the camera and its two coordinate spaces, and the `postMessage` contract across the boundary. Use when the user says "infinite canvas", "canvas infinita", "tavolozza tipo Figma", "artboard", "live preview in an iframe", "visual editor", "click to select an element in the preview", "pan and zoom the workspace", or when a preview iframe gets slow, blurry, or stops receiving clicks. Refuses outside Next.js 16 web. Not for: WebGL/Konva canvas rendering (a different architecture — this skill says when to switch), React Native, or building the editor UI around the canvas.'
---

# iframe-canvas — the frame budget comes before the feature

A canvas of live `<iframe>` artboards is the architecture behind every AI site- and
app-builder: Reweb, Sleek, Plasmic, Builder.io, Onlook, v0. It is **not** the architecture
behind Figma, and starting from "like Figma" is how projects in this family go wrong.

The failure mode is late and looks like polish debt: it works with three artboards, drags
with twelve, and by then the camera, the protocol and the selection model all assume live
frames everywhere. Every decision below is cheap on day one and structural by month two.

## When this skill applies

- The user wants a workspace you can pan and zoom with more than one preview on it.
- The user wants to click an element **inside** a preview and edit it.
- A preview iframe went slow, blurry, or stopped receiving clicks.
- The user says "like Figma" about a DOM-and-iframe product — read *The Figma trap* first.
- The user is choosing between an iframe canvas and a rendered one (WebGL/Konva/2D).

## Contract

Follows the dev-flow contract — see `references/contracts.md`. Key facts:

- Reads `meta.json#stack.framework` and `stack.nextjs_version`. For monorepo, reads `stack.monorepo.web.*`.
- **Refuses** if `stack.framework ∉ {"next", "monorepo"}`. The camera maths and the iframe
  process model are framework-agnostic, but the guidance here is written against App Router
  routes serving the renderer document, and mis-applying it is worse than refusing.
- Records the chosen architecture in `stack.canvas` (`"iframe-live" | "iframe-snapshot" | "rendered"`).
- Appends `history`. Does **not** bump `phase`.

## Companion skills

| Need | Skill |
|---|---|
| The editor UI around the canvas (panels, toolbars, dialogs) | `screenshot-to-page` |
| Motion on the canvas chrome | `transitions` |
| State that is not the camera | `state-discipline` |
| Reads that populate the canvas | `data-fetching` |
| Shipping the product's API to coding agents | `product-to-agent-skill` |

## The Figma trap

Figma's canvas is not DOM. Evan Wallace's account of building it says HTML and SVG were
rejected for **"DOM access overhead"** and because browsers are optimised for scrolling
rather than zooming; the renderer is WebGL written from scratch, with the document model in
C++, and it moved to WebGPU in 2023.

So "like Figma" describes a *feel* — smooth zoom, many boards, direct manipulation — and
naming it as an architecture imports the wrong constraints. In an iframe canvas the
expensive resource is not draw calls, it is **browsing contexts**.

State this out loud when a user says "like Figma". It is a stack decision, and dev-flow's
golden rule is that stack decisions are never taken silently.

## Decision 1 — the frame budget

Every iframe is *"a complete document environment"* (MDN) and needs its own memory and
compute. Two facts set the ceiling:

- **Same-site iframes share the parent's renderer process and its main thread.** A long task
  in one degrades the other, because they interleave. Cross-site iframes get their own
  process.
- A browser tab has roughly **2 GB** of active memory.

Which means the budget is not a number you can look up — it is `frames × weight of each
frame`, on one thread, under one tab's ceiling. Measure it on the real content before you
design around it.

**The precedent that matters.** Plasmic — a production visual builder with isolated iframe
artboards and runtime injection of the user's own component bundles — *replaced* its
multi-artboard view with a **single-artboard editing mode**, citing performance and
simplicity. Multi-artboard survives as a separate "Design Mode" for comparing breakpoints
side by side.

Read that as the default, not as their local quirk: **one live artboard, many static ones.**
A product that needs twelve live previews at once should be able to say why it is not
Plasmic.

## Decision 2 — live, snapshot, or rendered

Pick per artboard, not per product. The four viable shapes:

| Shape | What an artboard is | Costs | Reach for it when |
|---|---|---|---|
| **All live** | every artboard an iframe, always | one process, N contexts, one thread | ≤ ~3 artboards, light content, and you have measured it |
| **Snapshot + hydrate** (default) | inactive = image/static HTML, focused = iframe | a snapshot invalidates on **every** edit to its source | more than a handful of artboards — what Miro and FigJam do for inactive content |
| **Single live** | one iframe, artboards are a selector | loses side-by-side comparison | editing is the main verb, comparison is occasional — Plasmic's answer |
| **Rendered** | no iframes; draw to WebGL/2D | you own layout, text, fonts, a11y | the content is *your* document model, not arbitrary HTML — Figma's answer |

The mistake is not choosing wrong. It is **not choosing**, shipping "all live" by default,
and discovering the budget at twelve artboards with a camera and a protocol already built
on the assumption.

## Decision 3 — same-origin or cross-origin

A real fork, not a detail:

| | Same-origin | Cross-origin |
|---|---|---|
| DOM access from the parent | direct | none — `postMessage` only |
| Process | **shares the parent's**, contends for the main thread | its own, isolated |
| A frame that hangs | can take the editor with it | contained |
| Untrusted / user-authored content | unsafe | the only safe answer |

There is a third position: `Origin-Agent-Cluster: ?1` on the renderer document forces
origin-keyed isolation, giving same-site frames their own process. You keep one origin and
one deployment, you pay in cross-context access.

**Write the protocol as if you were cross-origin even when you are not.** Direct DOM
reach across the boundary is the coupling that makes the isolation switch unaffordable
later, and it is exactly the switch you will want when the canvas gets slow or the content
gets untrusted.

Non-negotiable in either case: `sandbox` on the element, and an `event.origin` check on
**both** sides of every `message` handler. A renderer that trusts any origin is an XSS
surface with a nice UI.

## The interaction mode

The hardest interaction problem here, and it has one answer that production converged on
from two directions: **a declared mode, not scattered conditionals.**

- tldraw: in editing mode, pointer events **pass through** to the iframe — scroll it, click
  inside it. Outside that mode the canvas takes the events for pan and marquee.
- Plasmic ships it as an `Interactive` toggle *inside* the canvas, replacing what used to be
  a separate preview screen — you click a real button, watch state change, exit, and keep
  the state.
- RapidNative's visual editor calls the inverse flag `inspectMode`, and says plainly that
  hover and click detection are gated on it *"to avoid conflicts with scrolling or dragging"*.

In CSS the mechanism is one property — `pointer-events: none` on the frame while the canvas
owns the gesture — but the discipline is that **exactly one mode object decides it**, and
every overlay, cursor and shortcut reads that object. The moment the answer is computed
inline in three components, the modes drift and the canvas develops dead zones.

## The camera and its two coordinate spaces

Two spaces, one transform, and every bug in this area is a value used in the wrong one:

- **Canvas space** — where artboards live. Never changes when you pan or zoom.
- **Screen space** — pixels. What the pointer reports.

`screen = (canvas − pan) × scale`, and the inverse going back. A pan gesture moves the
camera by the pointer delta **divided by the scale**, which is what makes panning feel
identical at every zoom level.

Three consequences worth stating because they are the recurring bugs:

1. **Anything that must stay 1px on screen divides by the scale.** Selection outlines,
   marquee borders, handles, hairlines: `borderWidth: 1 / scale`. Otherwise a 1px outline is
   3px at 3× zoom.
2. **Overlays render in the parent, never inside the iframe.** The frame reports a bounding
   box by message; the parent transforms it through the camera and draws the outline on top.
   Injecting outlines into the renderer document couples your chrome to the user's content
   and breaks the moment the frame is cross-origin.
3. **The frame does not know the zoom.** `visualViewport.scale` returns `1` inside an iframe
   in every browser. If the rendered content must react to zoom, the parent has to tell it.

## Documented traps

Real, reported, and not your bug to fix:

- **Rasterisation scale under `transform: scale` is not controllable.** Each browser picks
  the bitmap scale with its own heuristics; a request for author control has been open at the
  CSSWG since 2016. Scaled iframe content going soft is expected. If crispness at high zoom
  is a requirement, re-render the content at the target size instead of scaling the frame.
- **WebKit renders `position: fixed` content inside a scaled iframe blurry** (bug 133801) —
  worth knowing before you spend a day on your own CSS.
- **Cross-origin content cannot be captured.** Screenshot/export from a frame you do not
  control is closed by the same-origin policy, not by an API you have not found yet.

## On the horizon — do not build on it

The WICG is incubating **html-in-canvas**: `drawElementImage()` (plus WebGL/WebGPU
equivalents), a `drawable` attribute and a `paint` event, to render live HTML into a canvas.
It would collapse the snapshot problem. It is behind `chrome://flags/#canvas-draw-element`,
in the incubator, no standard. Track it; ship nothing on it. `[VERIFY]` on every pass.

## Common mistakes

| Mistake | What actually happens |
|---|---|
| "Like Figma", so we render DOM and expect Figma's smoothness | Figma rejected DOM for exactly this; you inherited the constraint it escaped |
| All artboards live from day one | fine at three, unusable at twelve, and by then the camera and protocol assume it |
| Same-origin because DOM access is convenient | every frame contends for the editor's main thread, and untrusted content is now in your origin |
| The parent reaches into `iframe.contentDocument` | the isolation switch you will want later is now a rewrite |
| Selection outline drawn with a fixed `1px` | 3px at 3× zoom; every chrome element needs `1 / scale` |
| Overlays injected into the renderer document | breaks on cross-origin, and your chrome inherits the content's CSS |
| Pointer gating decided inline per component | modes drift, the canvas grows dead zones nobody can reproduce |
| Fighting blurry scaled content with CSS | the browser picks the raster scale; open at the CSSWG since 2016 |
| A `message` handler without an origin check | any page that can frame you now drives your editor |
| Snapshots treated as free | every edit invalidates one; the capture cost is the real budget |

## Workflow

1. **Name the architecture out loud** and get agreement — it is a stack decision. Say which
   of the four shapes, and why not the others.
2. **Measure before designing.** Put the real content in N frames, watch memory and main-thread
   time. The number you get is the budget; do not design past it.
3. **Choose the isolation** (same-origin / cross-origin / `Origin-Agent-Cluster`) and write
   the protocol as if cross-origin regardless.
4. **Define the camera once** — one module owning both transforms, with the `1 / scale` rule
   documented where the chrome is drawn.
5. **Define the mode once** — one state object every overlay and shortcut reads.
6. **Type the protocol** as a discriminated union, origin-checked on both sides, with a
   `ready` handshake before the first push.
7. Record `stack.canvas` in `meta.json` and append `history`.

## What this skill does NOT do

- **Does not build a rendered canvas.** If Decision 2 lands on "rendered", this skill has
  done its job by getting you there; the WebGL/Konva work is outside it.
- **Does not design the editor UI.** Panels, toolbars, layer trees are `screenshot-to-page`.
- **Does not own export.** Capturing, serialising or exporting artboards is product work.
- **Does not cover React Native.** No iframes there.

## Sources

Every claim above traces to `references/production-survey.md`, which carries the URLs and
what each source actually says. Re-check it on a cadence: three of the sources describe
products that changed their answer at least once.
