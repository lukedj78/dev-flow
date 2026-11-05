# When Decision 2 lands on `rendered` — Konva, and the two things that bite

`SKILL.md` gets you to the fork and then stops: *"if Decision 2 lands on rendered, this skill has
done its job by getting you there; the WebGL/Konva work is outside it."* That left
`stack.canvas = "rendered"` as the one value of four with nothing behind it, while the skill named
Konva three times as the thing to switch to.

**This file closes that, and deliberately stops short.** It carries what was measured on
2026-11-05 — the library choice, the Next.js wiring, and the two failures that are structural rather
than fixable — and it does **not** design your camera, hit-testing, layer model, transformer or
serialisation. Those follow the product's own document model, and inventing them before a PRD asks
produces a shape nobody needed. The first project to walk this branch writes them; this file makes
sure it starts from facts instead of from a search.

## The library: Konva, and why not the others

**`konva` + `react-konva`, both MIT.** The row in `dev-flow/references/resources.md` carries the
verdict and the date; the numbers behind it:

| | `konva` | `react-konva` | `@xyflow/react` | `fabric` |
|---|---|---|---|---|
| version measured | 10.9.1 | 19.3.2 | 12.12.1 | 7.4.0 |
| unpacked | 2.1 MB | 148 KB | 2.8 MB | **28 MB** |
| minified | **193 KB** | — | — | — |
| runtime dependencies | **0** | 4 | 3 | 0 |
| real `aria-` attributes | **0** | 0 | **64** | 0 |

`konva` has **no runtime dependencies at all** — the `canvas` and `skia-canvas` peers are for
rendering outside a browser and are not installed for a web app. It has shipped **252 releases since
2015**, the last on 2026-10-31, which is the longest continuous maintenance record of anything in
this class. Against `fabric`'s 28 MB unpacked it is 13× smaller for the same job.

**Do not reach for this when another answer already exists.** A node graph the user acts on is
**React Flow** (`stack.graphs`, adopted, and its nodes are real DOM). A workspace of HTML previews is
this skill's own iframe branches. Recolourable **SVG** artwork needs per-zone DOM click targets and
CSS `fill`, both of which a bitmap destroys — keep that in SVG. `rendered` is for content that **is**
a drawing: shapes a person drags, resizes and rotates, typically over an image.

## Next.js 16: `'use client'` is the whole setup

Most writing about Konva on Next still prescribes installing the `canvas` package or wrapping the
component in `dynamic(…, { ssr: false })`. **Both were Konva 9 workarounds.** `react-konva`'s own
shipped README, at 19.3.2:

> *"Konva 10+ works with Next.js without extra canvas setup. Use a Client Component (`'use client'`).
> Konva 9 and earlier need extra setup, such as installing `canvas` or disabling SSR."*

Verified in the shipped source: `konva/lib/Global.js` guards on `typeof window !== 'undefined'`
itself and derives `isBrowser` and `pixelRatio` from it. So a `'use client'` component is enough, and
an `ssr: false` dynamic import is a loading-waterfall you are paying for nothing.

```tsx title="components/annotation-canvas.tsx"
"use client";

import { Stage, Layer, Image as KonvaImage, Rect } from "react-konva";
```

## Failure 1 — there is no accessibility tree, and no flag turns one on

A Konva stage renders to **one `<canvas>` element**. Everything inside it — every shape, handle,
label and button you draw — is pixels. Measured in the shipped source: **zero real `aria-`
attributes**. (A naive grep reports 46; all of them are `fontVariant`, `Arial` and `variant`.)

The contrast that makes this structural rather than a gap someone will close: **`@xyflow/react`
ships 64**, because a React Flow node is a DOM element. Same category of product, opposite
consequence, and it follows from where the drawing happens.

Three things we have already committed to follow from it:

- **`shadscan` reads the DOM.** Canvas content is therefore neither passed nor failed — it is
  *absent*. A clean shadscan report on a page whose main surface is a canvas says nothing about that
  surface, and reading it as approval is the mistake to avoid.
- **Golden rule ②** still holds in the narrow sense: `Konva.Text` takes a string, so it goes through
  `next-intl` like any other. But it is not *text* to the platform — no selection, no browser find,
  no screen reader, no copy.
- **Every control inside the canvas needs a mirror in the DOM**, or for a keyboard and a screen
  reader it does not exist. Budget that layer when you choose `rendered`; discovering it at the
  accessibility review means rebuilding the interaction model.

This is not an argument against Konva. It is why `rendered` is a deliberate choice for a drawing and
never a default for an interface — and why the branch is worth naming in `meta.json`, since the rest
of the editor inherits the obligation.

## Failure 2 — `react-konva` is a custom React renderer, so React bumps wait on it

`react-konva` is not a wrapper around a DOM library. It is a **React reconciler**: its dependencies
are `react-reconciler@0.34.0` and `scheduler@0.28.0`, both pinned exactly, plus `its-fine`. Its own
README states the coupling:

> *"React Konva 19.3 requires React and React DOM `^19.3.0`. For React 19.2, install the latest
> React Konva 19.2 release. For React 18, install the latest React Konva 18 release."*

So **its major.minor mirrors React's**, and a React upgrade is gated on `react-konva` publishing the
matching line first. Fine at the web stack's React 19.3.1 as of 2026-11-05. Two consequences worth
writing into a project that adopts it: pin both together and bump them together, and treat a React
minor in the dependency sweep as a question about `react-konva` rather than as routine drift.

**React Flow carries none of this** — it renders through the ordinary DOM — which is the second
reason to prefer it wherever a graph will do.

## What this file deliberately does not decide

The camera and its two coordinate spaces are already in `SKILL.md`; they apply unchanged, because a
camera is arithmetic and does not care what draws. Everything below is product work, and the shapes
differ enough between an annotator, a diagrammer and a floor planner that a guess here would be
worse than nothing:

- the document model and its serialisation format,
- hit-testing and selection semantics (Konva's own `Transformer` is the starting point, not the
  answer),
- the layer split and what gets its own `<Layer>` for redraw cost,
- undo/redo, and whether it is per-shape or per-transaction,
- export, and whether the canvas or the server is the source of truth for it.

**Re-verify before leaning on the numbers above.** Konva ships roughly monthly and `react-konva`
tracks React, so the version table and the Next.js setup claim are the perishable parts. The method
is `npm pack` plus the shipped README and `lib/`, the same one `docs/vercel-changelog-watch.md` uses.
