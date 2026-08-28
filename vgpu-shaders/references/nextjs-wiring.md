> Sources: <https://github.com/vercel-labs/vgpu> → `skills/vgpu/references/guides/{nextjs,getting-started,browser-testing,agent-browser-webgpu,external-ticker}.docs.md`.
> Fetched **2026-08-26** against **`vgpu@0.3.1`** (npm `latest`, MIT). `[VERIFY]` against the
> first-party skill — it is generated from source and stamped with `vgpuVersion` + `gitSha`, so it is
> always more current than this file.

# vgpu in a Next.js 16 app — the wiring

## Install

```bash
pnpm add vgpu
```

That is the whole install. `@vgpu/wgsl` (the loaders) and `@vgpu/wgsl-std` (pure-WGSL standard
modules — noise, hash, color, fullscreen) are **dependencies of `vgpu`**, so
`import { voronoi3d } from "@vgpu/wgsl-std/noise";` resolves with no second install — including under
pnpm's isolated `node_modules` and Yarn PnP, where transitive packages never appear in your tree.

Resolution order for a WGSL package import: **your own `node_modules` first** (a copy you installed
wins), then next to `@vgpu/wgsl` itself. `VGPU-WGSL-PKG-NOTFOUND` therefore means *neither* — install
it, or fix the specifier.

## Do you even need the loader?

**No, not necessarily.** `effect(gpu, source)` and `draw(gpu, { shader })` take WGSL as a **plain
string**. The loader earns its place only when you want shaders in their own `.wgsl` files with
`import` between them — then it resolves that graph at build time and hands `effect()` one finished
shader.

Start without it. Add it when the shader outgrows one file.

## Turbopack (the Next 16 default)

```ts
// next.config.ts
const nextConfig = {
  turbopack: {
    rules: {
      "*.wgsl": {
        loaders: ["@vgpu/wgsl/loader-webpack"],
        as: "*.js",                    // ⚠️ required — without it Turbopack won't treat the
      },                               //    loader output as a JavaScript module
    },
  },
};
export default nextConfig;
```

- The top-level `turbopack` key needs **Next 15.5+**. We scaffold Next 16, so this holds; a project
  pinned to 15.0–15.2 needs the deprecated `experimental.turbo.rules`.
- Turbopack runs webpack-compatible loaders through a bridge where `this.addDependency()` is **not**
  honoured — `@vgpu/wgsl` compensates by tracking transitive `.wgsl` reads through Turbopack's patched
  `fs.readFile`, so editing an imported module still invalidates. Worth knowing when HMR looks wrong:
  the compensation is the library's, not the bundler's.

## webpack (`next dev` / `next build` without `--turbopack`)

Push a rule from the `webpack` hook — the loader registers itself for `test: /\.wgsl$/`.

## TypeScript

`.wgsl` imports need an ambient declaration or `tsc` will not know the module shape. Take the exact
form from the first-party guide (`vgpu docs cat nextjs`) rather than hand-writing it.

## The client component

**WebGPU is browser-only.** The canvas lives in a `"use client"` component and `init()` runs in an
effect after mount. There is no server path — so the server-rendered markup *is* your no-WebGPU
fallback, and it should be designed, not empty.

```tsx
"use client";
import { effect, frame, init, surface } from "vgpu";

// Keep the vgpu work in a plain function — easier to test than a hook.
export async function render(canvas: HTMLCanvasElement) {
  const gpu = await init();
  const output = surface(gpu, canvas, { dpr: 1 });
  const shader = effect(gpu, shaderSource);
  shader.set({ uniforms: { resolution: output.size } });
  frame(gpu, (f) => f.pass(output, shader));
  return () => gpu.dispose();          // ⚠️ always return the teardown
}
```

Two contract points from this repo, not from vgpu:

- **`gpu.dispose()` on unmount is not optional.** A GPU device leaked across a client-side navigation
  is a device the next page also pays for.
- **The reduced-motion path is yours to write** — see `SKILL.md`. `advance(0)` freezes the clock while
  frames still render, which keeps the composition and drops the motion.

## Error table (the ones that come from the wiring, not the shader)

| Error | Meaning | Fix |
|---|---|---|
| `VGPU-WGSL-PKG-NOTFOUND` | a WGSL package import is in neither `node_modules` | install it, or fix the specifier |
| `VGPU-WGSL-RUNTIME-IMPORT` | the bundler ran the loader synchronously while the `.wgsl` has top-level imports | let the loader use async mode (webpack/Turbopack/Vite all do by default) |
| `VGPU-RESOLVE-MODULE-BINDING` | an imported `.wgsl` module declares `@group`/`@binding` | keep resources in the **entry** shader; modules export only structs and functions |
| `VGPU-R1-BINDING-NEVER-SET` | a binding declared in WGSL was never `set()` | set every declared binding |

The shader-side diagnostics are a much longer list and vgpu publishes them as a self-correction map:
`vgpu docs cat shader-fix-its`.

## Testing

```ts
// One deterministic frame — never assert inside requestAnimationFrame.
const gpu = await init();
const out = surface(gpu, canvas, { dpr: 1, autoResize: false });
frame(gpu, (f) => f.pass({ target: out, clear: [0, 0, 0, 1] }, (p) => p.draw(fx)));
const pixels = await out.read();
```

- Fixed `dpr` / `autoResize: false` / explicit `size` — a snapshot at a floating DPR is not a snapshot.
- `vgpu/mock` for deterministic unit tests; `vgpu/node` only when Dawn/WebGPU behaviour is under test.
- `@vgpu/render/perf` exports **`pixelDiff`**, which is the comparison a snapshot test wants.

### CI on Linux — the trap

```bash
npm i -g agent-browser@latest
apt-get install -y libvulkan1 mesa-vulkan-drivers xvfb xauth
agent-browser doctor --webgpu --headed
```

⚠️ **`--webgpu` is mandatory** (plain headless Chrome does not expose WebGPU and *"can silently produce
a black canvas"*), and on Linux **`--headed` is mandatory too**: headless captures the canvas as black,
an upstream limitation. If `DISPLAY` is absent, Xvfb covers it.

SwiftShader needs no GPU and no `/dev/dri`, but it is slow — the guide says to wait **~6 seconds and
two `requestAnimationFrame` calls** before capturing heavy previews. A screenshot taken too early is a
passing test of a black frame, which is exactly the failure this whole setup exists to catch.
