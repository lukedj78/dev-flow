---
name: vgpu-shaders
description: >-
  Decide whether a Next.js 16 project should reach for **WebGPU** at all, then wire `vgpu` in: the
  `.wgsl` loader (Turbopack/webpack), a `"use client"` canvas that survives SSR, a
  `prefers-reduced-motion` path the library omits, a headless render snapshot in CI. Non-visual uses
  too — **compute shaders** (`compute`/`dispatch`, storage ping-pong), `pixelDiff` for visual
  regression, `gpuFrameTime` as a CI perf gate, server-side image generation, `vgpu/scene`. Triggers:
  "shader", "WGSL", "WebGPU", "vgpu", "compute shader", "GPU compute", "animated hero", "generative
  background", "raymarch", "aggiungi uno shader", "sfondo generativo", "calcolo su GPU". **Does not
  restate the vgpu API** — that is the first-party generated skill (`npx skills add
  vercel-labs/vgpu`) and its MCP. Records `stack.shaders`; no phase bump. Not for CSS/Motion
  animation (this is the top rung of that ladder), animated icons, maps, React Native, or WGSL
  tutorials.
---

# vgpu-shaders — should this page have a shader, and what does that cost?

[`vgpu`](https://vgpu.sh) is Vercel Labs' WebGPU library "designed for agents": one shader renders in
the browser, headless in Node, to a PNG at any resolution, to video, and in CI. WGSL becomes a module
graph you `import` like TypeScript — the loader resolves it, reflects bindings, drops unused
declarations and emits compact source at build time.

## ⛔ First: this skill does not document the vgpu API, on purpose

The API is **258 symbols across 20 packages**, and Vercel ships a **first-party skill generated from
the source docs**, stamped with `vgpuVersion` and a `gitSha` in its own frontmatter. Restating it here
would duplicate an artefact that regenerates itself, and would be wrong within a release.

```bash
npx skills add vercel-labs/vgpu                      # the generated API skill
npx -y add-mcp https://vgpu.sh/api/mcp -g            # or the MCP
npx -y vgpu docs find <query> | grep -i <term> | cat <symbol>
```

⚠️ **Their skill is named `vgpu`; this one is `vgpu-shaders`** precisely so both can be installed.

What follows is the half nobody else writes: **whether to reach for it, and what you owe the user once
you do.**

## It is not only graphics — but for a dev-flow project it almost always is

WebGPU is a **GPU compute** API of which rendering is one use, and vgpu exposes both. `Compute`,
`ComputeOptions`, `StorageBuffer` and `PingPongStorage` are first-class, and **`initFromDevice(device)`**
adopts a `GPUDevice` another library already created — the documented case being **ONNX Runtime Web's
WebGPU execution provider**, so a model's output stays on the GPU and a shader consumes it with
`gpu.device.wrapBuffer(output.gpuBuffer)`, zero copies. It runs in Node too, with Dawn supplying
WebGPU. Ownership is explicit: vgpu never calls `destroy()` on a device it did not request.

**Know that path exists; then note it is almost never ours.** In this skill set the model runs
server-side, through eve and the AI Gateway — client-side inference is a different architecture with
its own bill (model download weight, WebGPU availability, a device the page now owns). It earns
consideration only when the data genuinely must not leave the machine *and* the client is a browser.
`[VERIFY]` the ML matrix against the first-party skill (`vgpu docs cat ml`) before pricing that;
it pins specific `webgpu`, `onnxruntime-web` and Dawn versions.

Everything below is the graphics path, because that is the one a dev-flow project actually reaches.

## The decision — this is the motion ladder's top rung, not a separate ladder

`transitions` grades motion in tiers, cheapest first. vgpu is a **new Tier 4**, above Motion:

| Tier | Tool | Cost |
|---|---|---|
| 0 | `tw-animate-css` | a class |
| 1–2 | CSS transitions · View Transitions API | no JS runtime |
| 3 | Motion | a JS runtime, main-thread |
| **4** | **vgpu / WebGPU** | **a GPU device, a compile step, a render loop, and a battery** |

**Do not skip rungs.** A gradient that breathes is Tier 0. A hero that morphs between two states is
Tier 2. Reach for Tier 4 only when the artefact *is* the effect — raymarching, fluid, volumetric
lighting, real-time generative texture — and when the page can afford it.

Three questions before you write a line of WGSL:

1. **Is the effect the product, or decoration?** Decoration does not justify a GPU device.
2. **Who is on the page?** A marketing hero seen once tolerates it. A dashboard someone keeps open for
   eight hours does not — a shader loop is a permanent thermal and battery cost.
3. **What happens when it doesn't run?** WebGPU is browser-only and not universal. There must be a
   design for the no-WebGPU case, not a blank canvas.

## Five uses that are not a hero

The Tier-4 framing above is about *decoration*. These are the ones where vgpu is the tool because of
what it computes or produces, not because the page needs to look alive. All signatures below are read
off the generated API docs at **`vgpu@0.3.1`**.

**1 · Compute — no pixels involved.** `compute(gpu, wgsl, { set, constants, entry })` is a pipeline
with the same reflection and `set()` ownership rules as a draw, then `dispatch(x, y?, z?)`. Storage is
`storage(gpu, bytes, "read" | "read-write")` with `read(): Promise<ArrayBuffer>` and `write(data)`.
Two things the raw WebGPU API makes you hand-roll:

- **`override` constants** let one JS value drive both `@workgroup_size` and the dispatch maths, so
  "retuning `wg` cannot desynchronize them".
- **`dispatch({ indirect })`** takes the workgroup counts from a buffer *the GPU wrote*, so the CPU
  never has to learn how many elements survived a compaction pass.

⚠️ **The GPU wins on massively parallel arithmetic and loses on transfer.** Aggregating 200k dashboard
rows is almost always faster in a Web Worker. The real case is simulation — particles, physics, fields
— where `pingPongStorage(gpu, n)` + `.swap()` keeps the data resident between frames and it never makes
the return trip. A complete worked example — WGSL, the loop, the `vgpu/mock` test, and the
question of whether it was worth it — is in `references/compute-example.md`.

**2 · `pixelDiff` — visual regression as a utility.** Not graphics: QA.

```ts
import { pixelDiff } from "@vgpu/render/perf";
const r = await pixelDiff(before, after);       // Texture | Uint8Array
if (r.maxByte > 2) throw new Error(`regression (max delta ${r.maxByte})`);
```

Returns `{ maxByte, meanByte, changedBytes, totalBytes, changedFraction }`. **`maxByte <= 2` is driver
rounding noise** — the threshold that stops a snapshot suite flapping. It accepts plain `Uint8Array`,
so it compares any two pixel buffers, whatever drew them.

**3 · `gpuFrameTime` — a performance gate in CI.**
`gpuFrameTime(device, encode, { frames: 120, warmup: 30 })` → `{ medianMs, meanMs, … }`, timestamp
queries where supported and wall clock otherwise. `medianMs` is "the main number to compare across
builds". Failing a build on frame-time regression is an engineering practice, not an effect.

**4 · Server-side image generation from data.** The headless path renders to an offscreen target in
Node; `target.read()` hands back pixels. An OG image *per listing*, generated from the record, instead
of three hand-made variants that drift. ⚠️ **vgpu renders the pixels, not the file** — encoding to PNG
is yours (`sharp`, `pngjs`).

**5 · `vgpu/scene` — a small scene graph.** `perspectiveCamera`, `orbitControls`, `box`/`sphere`/
`torus`/`icosphere`, `directionalLight`, `lambertMaterial`, `mesh`, `group`. A product configurator or
a navigable room, which is a different job from an animated background.

⚠️ **Two honest gaps, both checked 2026-08-26.** The compute API's examples in the generated docs all
import from **`vgpu/mock`** (the deterministic test entry), not from `vgpu` — good news for testability,
but `[VERIFY]` the runtime entry with `vgpu docs cat compute` before copying an import. And the landing
page advertises **MP4 at 60 fps** while the shipped docs contain **zero** occurrences of
video/mp4/encoder/ffmpeg/webm; the headless example is `examples/by-example-s13-headless`. Treat video
as "read frames, encode them yourself" until proven otherwise.

## ⚠️ The obligation the library does not give you: reduced motion

**Checked 2026-08-26 across vgpu's getting-started, Next.js and external-ticker guides: they never
mention `prefers-reduced-motion`.** That is not a criticism of the library — it is a gap you inherit.
This repo's golden rule (`transitions`) is that *every* transition ships a reduced-motion path, and a
60fps GPU loop is the most aggressive motion we can ship.

The mechanism exists; only the connection is missing. vgpu's external-ticker guide documents
`advance(0)` as *"the honest way to pause: the clock stops, frames still render"* — so a reduced-motion
path is **render one frame, then stop advancing the clock**, not "hide the canvas":

```tsx
"use client";
// Render the shader's first frame, then hold it. The composition stays; the motion stops.
const reduce = useReducedMotion();                 // motion/react, or a matchMedia listener
// … inside the frame loop: advance(reduce ? 0 : deltaSeconds)
```

A still frame of a good shader is a good image. Hiding the canvas is a worse outcome than never
adding it.

Also clamp the delta — the guide's own example does: `Math.min(0.25, deltaMs / 1000)`, because
*"a hidden tab must not spiral"*.

## Next.js wiring (the parts that actually bite)

Full guide: `references/nextjs-wiring.md`. The three that break a build:

- **`.wgsl` needs a loader**, and Turbopack needs `as: "*.js"` or it will not treat the loader output
  as a module. Top-level `turbopack.rules` requires **Next 15.5+**; we are on 16, so that holds.
- **`init()` is browser-only** — the canvas lives in a `"use client"` component and `init()` runs in an
  effect after mount. There is no SSR path; design the server-rendered fallback deliberately.
- **Bindings live in the entry shader.** An imported `.wgsl` module that declares `@group`/`@binding`
  fails with `VGPU-RESOLVE-MODULE-BINDING`. Modules export structs and functions; nothing else.

You do **not** need the loader at all: `effect(gpu, source)` takes WGSL as a plain string. Reach for it
only when shaders want their own files with imports between them.

## Testing — the reason this is worth wiring at all

A shader is the one visual artefact that can be regression-tested **exactly**, and vgpu is built for
it. This is the strongest argument for choosing it over a hand-rolled canvas effect.

- **Deterministic frame, not a loop**: fixed `dpr: 1`, `autoResize: false`, one `frame(gpu, …)`, then
  `target.read()`. Never assert inside `requestAnimationFrame`.
- **`vgpu/mock`** for deterministic unit tests; **`vgpu/node`** only when Dawn/WebGPU behaviour is
  itself under test.
- **In CI on Linux**, WebGPU needs help: `agent-browser --webgpu --headed` (SwiftShader, no GPU
  required). ⚠️ **headless Chrome captures the canvas as black** — an upstream limitation, so `--headed`
  plus Xvfb is not optional. A green headless test that never rendered is the failure mode here.

Hand off the test itself to `write-tests`; this skill decides that the snapshot exists.

## `meta.json`

```jsonc
"stack": { "shaders": "vgpu" }          // only when a shader actually ships
"shaders": {
  "surface": "app/(marketing)/page.tsx",   // where it renders
  "reduced_motion": "clock-freeze",         // how the reduced-motion path is served
  "fallback": "static-poster",              // what a no-WebGPU visitor sees
  "snapshot_test": "e2e/hero-shader.spec.ts"
}
```

No phase bump — a shader is a capability on an existing page, not a stage.

## What this skill does NOT do

- **Doesn't teach WGSL or the vgpu API** — that is the first-party skill and the MCP.
- **Doesn't write the shader.** Use their `npx vgpu docs` / examples / `check` / `doctor` loop.
- **Doesn't apply to React Native.** RN has no WebGPU rung in this skill set; motion there is
  Reanimated.
- **Doesn't override `transitions`.** If a cheaper tier does the job, that is the answer.

## Reference files

- `references/nextjs-wiring.md` — loader config, the client component, the error table.
- `references/compute-example.md` — a complete worked compute shader (simulation with resident data),
  its `vgpu/mock` unit test, the two guards that stop it desynchronising — **and an honest verdict that
  the same feature usually belongs in a Web Worker**.
- `references/contracts.md` — the `.workflow/` dev-flow contract (vendored).

## Sources

- <https://vgpu.sh> · <https://github.com/vercel-labs/vgpu> (MIT) — checked **2026-08-26**, `vgpu@0.3.1`.
- First-party skill: `vercel-labs/vgpu` → `skills/vgpu/SKILL.md`, generated, frontmatter carries
  `vgpuVersion` + `gitSha`. `[VERIFY]` the API against it, never against this file.
