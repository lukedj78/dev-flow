---
name: vgpu-shaders
description: >-
  Decide whether a Next.js 16 page should carry a **WebGPU shader** at all, then wire `vgpu`
  (Vercel Labs, MIT) into it correctly: the `.wgsl` bundler loader for Turbopack/webpack, a
  `"use client"` canvas that survives SSR, a **`prefers-reduced-motion` path the library does not
  give you**, and a headless render snapshot in CI. Use when the user says "shader", "WGSL",
  "WebGPU", "vgpu", "animated hero", "generative background", "raymarch", "aggiungi uno shader",
  "sfondo generativo", "effetto WebGPU". **Deliberately does not restate the vgpu API** — 258
  symbols across 20 packages live in the first-party generated skill (`npx skills add
  vercel-labs/vgpu`) and its MCP; this skill is the decision layer and the dev-flow contract around
  it. Records `stack.shaders`; no phase bump. Not for: CSS/Motion animation (`transitions` owns the
  tier ladder and this is its top rung), icon micro-animation (`heroicons-animated`), maps
  (`mapcn`), React Native (no WebGPU rung — RN uses Reanimated), or learning WGSL from scratch.
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

## The decision — this is `transitions`' top rung, not a separate ladder

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
- `references/contracts.md` — the `.workflow/` dev-flow contract (vendored).

## Sources

- <https://vgpu.sh> · <https://github.com/vercel-labs/vgpu> (MIT) — checked **2026-08-26**, `vgpu@0.3.1`.
- First-party skill: `vercel-labs/vgpu` → `skills/vgpu/SKILL.md`, generated, frontmatter carries
  `vgpuVersion` + `gitSha`. `[VERIFY]` the API against it, never against this file.
