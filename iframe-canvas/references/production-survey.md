# What production actually does — sources behind every claim in SKILL.md

Read this before changing a number or a recommendation in the skill. Three of these
products changed their own answer at least once, so the survey is worth re-running rather
than trusted forever.

Last pass: **2026-09-06**.

---

## 1. Figma — the one that is *not* this architecture

**Source:** [Building a professional design tool on the web](https://www.figma.com/blog/building-a-professional-design-tool-on-the-web/) (Evan Wallace) ·
[Figma Rendering: Powered by WebGPU](https://www.figma.com/blog/figma-rendering-powered-by-webgpu/)

What it says, and it is unusually explicit: HTML and SVG were **considered and rejected**
for the canvas. The reasons given are DOM access overhead, browsers being optimised for
scrolling rather than zooming, inconsistent GPU acceleration, and uneven support for
masking, blurring and blend modes. Figma wrote a tile-based renderer from scratch on WebGL,
with the document model in **C++** and only the surrounding UI in JS/TS. Chromium shipped
WebGPU in 2023 and Figma moved onto it.

**Why it leads this file.** Users say "like Figma" meaning the feel. Taken as an
architecture it imports constraints Figma paid a rewrite to escape. In an iframe canvas the
scarce resource is browsing contexts, not draw calls — a different problem with different
answers.

## 2. Plasmic — the production team that retreated from multi-artboard

**Source:** [Introducing: New simplified canvas with interactive editing](https://plasmic.substack.com/p/introducing-new-simplified-canvas) ·
product pages at [plasmic.app/design](https://www.plasmic.app/design)

Architecture: isolated iframe sandboxes, with a subdeps injection system that loads the
user's own registered component bundles at runtime — which is what lets real production
React components be dragged onto the canvas without Plasmic understanding them at build
time.

The finding that matters: they **replaced the multi-artboard view with a single-artboard
editing mode**, stating it "delivers better performance and a simpler editing experience".
Multi-artboard was demoted to a separate **Design Mode** for comparing breakpoints or
variants side by side.

They also folded preview into the canvas: an **Interactive** toggle lets you click a real
button and watch state change, then exit and keep that state — replacing a separate preview
screen. Their stated reason for the old model being wrong is that "one variant per artboard"
became confusing once components had many dynamically-toggled variants.

**How to read it.** A team with the resources to do many-live-artboards well chose not to.
That is the strongest available evidence for the default in SKILL.md: one live artboard,
many static ones.

## 3. tldraw — the interaction model

**Source:** [Embed shape](https://tldraw.dev/sdk-features/embed-shape) ·
[Block events](https://tldraw.dev/examples/event-blocker) ·
[Creating a Zoom UI](https://www.steveruiz.me/posts/zoom-ui) (Steve Ruiz, tldraw's author)

The embed shape puts an iframe on an infinite canvas. The rule: **in editing mode pointer
events pass through to the iframe** — you scroll it, click its buttons — and outside that
mode the canvas owns the gesture. Two details worth stealing: embeds refuse to render a
nested tldraw canvas when the page is itself framed (no infinite nesting), and
`markEventAsHandled` stops internal handlers without disturbing non-tldraw listeners.

The zoom post is the camera maths: pan by the pointer delta **divided by the camera's zoom**,
which is what makes panning feel the same at every zoom level.

## 4. RapidNative — point-and-edit, written up in detail

**Source:** [Visual Editor for React Native: How Point-and-Edit Works Under the Hood](https://www.rapidnative.com/blogs/visual-editor-for-react-native-how-point-and-edit-works-under-the-hood)

The most concrete published description of the selection loop:

- Every component gets a `data-bx-path` attribute at bundle time, encoded `filename:line:column`.
- A script injected into the iframe walks the React Fiber tree to the nearest element carrying
  that attribute and posts `{ type, payload: { path, filePath, x, y, width, height } }`.
- **Overlays render in the editor layer, not inside the iframe** — a hover highlighter and a
  selection highlighter, both scaling outline width by `1 / zoomLevel`.
- An `inspectMode` flag gates the whole selection UI, explicitly *"to avoid conflicts with
  scrolling or dragging"*.
- For AI context they send ±5 lines around the target line, marking it with `^^`, to keep
  tokens down and remove ambiguity about which component to change.

Named gotchas: Fiber traversal resolves to the nearest *ancestor* with the attribute (not the
innermost wrapper), and bounding boxes must be translated from iframe space to canvas space
through the current zoom.

## 5. The iframe process model — where the budget comes from

**Source:** [Iframes and Process Allocation](https://webperf.tips/tip/iframe-multi-process/) ·
[`<iframe>` — MDN](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/iframe)

- Iframes that **differ in site** (eTLD+1) run in **separate renderer processes**: isolated
  threads and memory, one cannot degrade or crash the other, and `postMessage` is the only
  channel.
- Iframes that **share the site** run in the **parent's process**. Threads interleave, so
  *"a Long Task in one will degrade the other"*, and memory is shared — including crashes.
- `Origin-Agent-Cluster: ?1` forces origin-keyed isolation, giving same-site frames dedicated
  processes without changing the origin you deploy to.
- The guidance for hosting many same-site frames is to *"throttle execution or release memory
  of inactive iframes"* — which is the snapshot-and-hydrate pattern arrived at from the
  browser's side.
- MDN: every iframe is *"a complete document environment"* and costs memory and compute; a
  tab's active memory ceiling is roughly **2 GB**.

⚠️ Do not turn this into a magic frame count. The budget is `frames × weight`, on one thread,
under one ceiling — it has to be measured on the product's real content.

## 6. Snapshot for inactive, live on focus

Miro and FigJam keep inactive embedded content as **static screenshots** and only make it
live when it is the thing being used. It is the same conclusion as §5's throttling advice,
reached from the product side.

The cost the pattern hides: a snapshot is invalidated by **every** edit to its source, so on
a canvas where edits are frequent the capture cost can exceed what the live frames were
costing. Measure the capture, not just the render.

## 7. Reweb / Sleek — the direct comparables

**Source:** [Show HN: Sleek — AI mobile app mockup generator (our 3rd pivot, last shot)](https://news.ycombinator.com/item?id=45758944) ·
[v1.reweb.so](https://v1.reweb.so/)

Same team. Reweb is a visual builder for Next.js/Tailwind/shadcn with a three-pane editor —
component palette, centre canvas showing live output, right-hand properties panel, with
desktop/tablet/mobile switching. Sleek is their **third pivot**: an AI mobile-mockup
generator that exports to HTML, React or Figma.

The founders published **no architecture details**; the Show HN thread is about the pivot and
the business, not the rendering. So these are useful as *product references* — what the
category looks and feels like — and **not** as engineering sources. Treat screenshots of
their canvas as a spec for behaviour, never as evidence that an implementation works.

Worth keeping in view: Reweb reportedly plateaued around $2k MRR before the pivot. You are
looking at an attempt in progress, not a settled winner.

## 8. Other products in the category

- **Builder.io** — [Visual Editor tour](https://builder.io/c/docs/ui-ve-tour): loads your live
  site inside a central iframe for editing in place.
- **Onlook** — [Builder features](https://www.onlook.com/features/builder): reads code from a
  web container, indexes it, injects mapping metadata, and an edit updates preview and source
  together. The team states the approach generalises to any declarative DOM framework and that
  they targeted Next.js + Tailwind first.

Both are single-surface editors. Neither advertises many simultaneous live artboards — another
data point for the default.

## 9. Documented browser traps

- **Raster scale under `transform: scale` is not author-controllable.** Browsers pick the
  bitmap scale by their own heuristics; the request for control has been open at the CSSWG
  since 2016 — [Provide a way to specify rastered content scale for transformed content](https://lists.w3.org/Archives/Public/public-css-archive/2016Jun/0357.html).
  Consequence: scaled iframe content going soft is expected behaviour, not a CSS mistake.
- **WebKit bug [133801](https://bugs.webkit.org/show_bug.cgi?id=133801)** — a CSS scale
  transform makes content blurry when the iframe contains `position: fixed` content.
- **`visualViewport.scale` returns `1` inside an iframe** in every browser tested, so framed
  content cannot discover the zoom it is being displayed at. The parent must tell it.

## 10. On the horizon — html-in-canvas

**Source:** [WICG/html-in-canvas](https://github.com/WICG/html-in-canvas) ·
[render-html-to-canvas](https://html-in-canvas.dev/render-html-to-canvas/)

Five primitives: a `layoutsubtree` attribute, a `drawable` attribute (implies
`isolation: isolate`), a `paint` event that fires when a drawable's snapshot changes,
`drawElementImage()` for 2D (with `texElementSubImage2D` / `drawElementImageToTexture` for
WebGL/WebGPU), and `updateElementGeometry()`.

If it lands it collapses the snapshot-vs-live tension: live HTML drawn into a rendered canvas.
Today it is **behind a flag** (`chrome://flags/#canvas-draw-element`), in the WICG incubator,
no W3C standard. Stated limits: cross-origin content and other "sensitive information" will
not render, accessibility geometry needs explicit updates, and threaded effects such as
smooth scrolling are not supported yet.

**Rule:** track it, ship nothing on it, `[VERIFY]` every pass.

---

## What this survey still lacks

No source here is a post-mortem of an iframe canvas **at scale** — the closest is Plasmic's
change of direction, and they describe the decision, not the numbers behind it. Nobody
publishes "we hit N frames and it fell over".

So the honest state of this skill: the **decisions** are well grounded, the **thresholds**
are not. The first real measurement from one of our own products — frames, content weight,
memory, main-thread time, and what actually broke — is the most valuable thing that can be
added to this file, and it should be added as data, not as a rule of thumb.
