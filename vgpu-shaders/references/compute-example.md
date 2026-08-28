> Grounded in the generated API docs of **`vgpu@0.3.1`** (`skills/vgpu/references/vgpu/compute.docs.md`,
> `frame.docs.md`, `core/storage-buffer.docs.md`), fetched **2026-08-26**.
> ⚠️ **Two things are deliberately absent because they are not documented** where I looked — see
> §"What this example avoids, and why" at the end. `[VERIFY]` with `npx -y vgpu docs cat compute`
> before extending it.

# A complete compute-shader example — and whether it was worth it

The skill's rule is that **the GPU wins on massively parallel arithmetic and loses on transfer**, so the
real case is *simulation with the data resident*, not aggregation. This is that case, worked end to end.

## The feature

**Gym SaaS, ops dashboard — "Gym Pulse".** Not a hero: an operational view. One point per check-in over
the last four hours (~10k), flowing toward the areas members are actually moving into, so the manager
sees *where the floor is thickening* rather than a bar chart of it.

Why the GPU: 10k particles × 60fps = 600k integrations per second, and **the positions never travel back
to the CPU** — they are written by the simulation and read by the draw, both on the device.

## `sim.wgsl`

```wgsl
struct Params {
  count:   u32,
  dt:      f32,
  damping: f32,
  attract: vec2f,      // centroid of the hot zone, derived from check-ins
};

@group(0) @binding(0) var<uniform> p: Params;
@group(0) @binding(1) var<storage, read>       src: array<vec4f>;   // xy = position, zw = velocity
@group(0) @binding(2) var<storage, read_write> dst: array<vec4f>;

override WG: u32 = 64;

@compute @workgroup_size(WG)
fn cs_step(@builtin(global_invocation_id) id: vec3u) {
  let i = id.x;
  if (i >= p.count) { return; }        // see "the two guards" below — this one is not optional

  let s   = src[i];
  var pos = s.xy;
  var vel = s.zw;

  let to = p.attract - pos;
  let d  = max(length(to), 0.001);     // no division by zero at the centre
  vel   += normalize(to) * (1.0 / d) * p.dt;
  vel   *= p.damping;
  pos   += vel * p.dt;

  dst[i] = vec4f(pos, vel);
}
```

## `gym-pulse.ts`

```ts
import { init, compute, pingPongStorage, frameLoop } from "vgpu";
import simSource from "./sim.wgsl";

const COUNT = 10_000;
const WG = 64;                                    // ⬅️ one value, two consumers (below)

export async function startPulse(canvas: HTMLCanvasElement, seed: Float32Array) {
  const gpu = await init();

  // pingPongStorage takes BYTES: one vec4f (4 × f32) per particle.
  const particles = pingPongStorage(gpu, COUNT * 4 * 4);
  particles.write.write(seed);                    // StorageBuffer.write(BufferSource)

  const step = compute(gpu, simSource, {
    label: "gym-pulse",
    constants: { WG },                            // ⬅️ drives @workgroup_size
    entry: "cs_step",
  });

  const handle = frameLoop(gpu, (frame) => {
    step.set({
      p:   { count: COUNT, dt: 1 / 60, damping: 0.96, attract: hotZone() },
      src: particles.read,
      dst: particles.write,
    });
    step.dispatch(Math.ceil(COUNT / WG));         // ⬅️ …and the dispatch maths
    particles.swap();
    // …then a draw that reads particles.read as a vertex buffer, inside the same frame
  });

  return () => { handle.stop(); gpu.dispose(); };  // both, on unmount
}
```

## The two guards, and why neither is decoration

**`constants: { WG }` + `Math.ceil(COUNT / WG)`.** One JS value drives the shader's `@workgroup_size`
*and* the dispatch arithmetic. In raw WebGPU those are two numbers in two files, and changing one
without the other makes the simulation skip part of the array **silently** — no error, just a wrong
result. The docs put it as: retuning `wg` "cannot desynchronize them".

**`if (i >= p.count) { return; }`.** `ceil(10000 / 64) = 157` workgroups = **10,048** invocations. The
48 extra would write past the data. This is not defensive habit; it is arithmetic.

## Testing it — on CI, without a GPU

The compute API's own examples are written against **`vgpu/mock`**, which is the point: a simulation
step is a pure function of its buffers, so it is unit-testable with no device, no SwiftShader, no
`--headed` browser.

```ts
import { init, compute, storage } from "vgpu/mock";

test("a stationary particle accelerates toward the attractor", async () => {
  const gpu = await init();
  const src = storage(gpu, 16, "read");
  const dst = storage(gpu, 16, "read-write");
  src.write(new Float32Array([0, 0, 0, 0]));      // at rest, at the origin

  const step = compute(gpu, simSource, {
    constants: { WG: 1 },
    entry: "cs_step",
    set: { p: { count: 1, dt: 1, damping: 1, attract: [1, 0] }, src, dst },
  });
  step.dispatch(1);

  const [x, , vx] = new Float32Array(await dst.read());
  expect(vx).toBeGreaterThan(0);
  expect(x).toBeGreaterThan(0);
});
```

A test of the **physics**, not of pixels. It is the cheapest test in the whole vgpu surface, and it is
the one worth writing first.

## ⚠️ Was it worth it? Usually not

Be honest at the point of decision, because the code above looks impressive and that is the trap:

- **10k particles run fine in a Web Worker** with a plain `Float32Array`. The GPU becomes the obvious
  answer somewhere north of ~100k, and "obvious" still depends on the device.
- **If the Gym Pulse shows 300 check-ins, it is a 2D `<canvas>`.** Nothing here applies.
- **The moment any frame does `await dst.read()` to hand data to React, the advantage is gone** — you
  paid the transfer you built all of this to avoid. If the UI needs the numbers every frame, the
  numbers should never have been on the GPU.

The criterion is not "is the data big" but **"does the data stay"**.

## What this example avoids, and why

Both would have made a better demo and neither is documented where I looked (`compute.docs.md`,
`core/storage-buffer.docs.md`, `core/texture.docs.md`, 2026-08-26):

- **`atomic<u32>` in a storage buffer.** A colour histogram or any reduction wants atomics, and vgpu's
  reflection may well handle them — but "may well" is not a reference. Written with atomics, this file
  would have been a guess dressed as an example.
- **Uploading an `ImageBitmap` into a `Texture`.** No `write` / `copyExternalImage` path appears in the
  texture doc, so every image-processing example is out of reach here.

If you need either, ask the first-party skill — `npx -y vgpu docs grep -i atomic` — rather than
extending this file from inference.
