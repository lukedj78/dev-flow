# The motion library — tokenized, tiered, reduced-motion-safe

Our curated set of production micro-interactions (inspired by [transitions.dev](https://transitions.dev/), rebuilt token-driven for Next.js 16 + Tailwind v4 + `tw-animate-css` + Motion). Each entry lists its **tier** (cheapest engine that does the job — see SKILL.md ladder), the **tokens** it uses, a **snippet**, and its **`prefers-reduced-motion` fallback**. Add new entries to `lib/motion/transitions.ts` as *tokenized* variants — never inline a magic number.

## The token → CSS-var bridge (Setup writes this)

`lib/motion/tokens.ts` (see SKILL.md) is the TS source of truth. Setup also emits matching CSS variables into the global stylesheet so Tailwind arbitraries and hand-written CSS read `var(--motion-*)` instead of literals:

```css
/* app/globals.css */
:root {
  --motion-duration-fast: 120ms;  --motion-duration-base: 200ms;  --motion-duration-slow: 320ms;
  --motion-ease-standard: cubic-bezier(0.2, 0, 0, 1);
  --motion-ease-emphasized: cubic-bezier(0.3, 0, 0, 1);
  --motion-ease-exit: cubic-bezier(0.4, 0, 1, 1);
  --motion-distance-md: 8px;
}
/* Global reduced-motion guard — the floor, not a substitute for per-effect fallbacks. */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important; animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important; scroll-behavior: auto !important;
  }
}
```

`tw-animate-css` exposes its own `--tw-duration`/`--tw-ease`; point them at the tokens in the Tailwind layer so `animate-in`/`fade-in` inherit the system's timing.

---

## Enter / exit (Tier 0)

### fade-in / fade-up on mount
Tokens: `duration.base`, `ease.standard`, `distance.md`. Engine: `tw-animate-css`.
```tsx
<div className="animate-in fade-in slide-in-from-bottom-2 duration-[var(--motion-duration-base)] ease-[var(--motion-ease-standard)] motion-reduce:animate-none">
```
Reduced-motion: `motion-reduce:animate-none` (content appears instantly, no slide).

### staggered reveal of N items
Tokens: `duration.base`. Engine: CSS `animationDelay` (Tier 0, no JS — reuses the anti-slop stagger rule).
```tsx
{items.map((it, i) => (
  <li key={it.id}
      className="animate-in fade-in slide-in-from-bottom-2 fill-mode-both motion-reduce:animate-none"
      style={{ animationDelay: `calc(${i} * 60ms)`, animationDuration: "var(--motion-duration-base)" }}>
```
Reduced-motion: `motion-reduce:animate-none` drops both the fade delay and the slide.

### exit (unmount) — pair with a presence wrapper
Tier 0 handles enter; a clean **exit** needs presence tracking. Tier 2 (View Transitions) for same-doc swaps, or Tier 3 `<AnimatePresence>` when already on Motion. Don't add Motion solely for an exit fade — a CSS `data-[state=closed]:` variant on a Radix/Base-UI primitive (below) covers most.

## Toggle / open-close (Tier 0–1)

Most toggles ride the underlying primitive's `data-[state]` attribute (Radix/Base UI/shadcn) — no JS beyond the primitive.

### modal / dialog open-close
Tokens: `duration.base`/`ease.standard` (in), `duration.fast`/`ease.exit` (out). Engine: Tailwind `data-[state]` variants.
```tsx
// content
className="data-[state=open]:animate-in data-[state=open]:fade-in data-[state=open]:zoom-in-95
           data-[state=closed]:animate-out data-[state=closed]:fade-out data-[state=closed]:zoom-out-95
           duration-[var(--motion-duration-base)] motion-reduce:data-[state=open]:zoom-in-100"
// overlay: fade only
```
Reduced-motion: keep the fade, drop the zoom (`zoom-in-100`).

### dropdown / popover / tooltip
Same `data-[state]` pattern with `slide-in-from-top-1` keyed to `side`. Tooltip: `duration.fast`. Reduced-motion: fade-only.

### accordion / collapsible
Tokens: `duration.base`, `ease.standard`. Engine: CSS grid-rows or the primitive's `--radix-accordion-content-height`.
```tsx
className="data-[state=open]:animate-accordion-down data-[state=closed]:animate-accordion-up motion-reduce:transition-none"
```
Reduced-motion: instant show/hide.

### toast open-close
`slide-in-from-right-full` (in, `ease.standard`) / `slide-out-to-right-full` (out, `ease.exit`). Reduced-motion: fade-only.

### panel / drawer reveal
`translate-x` via `data-[state]`, `duration.slow`, `ease.emphasized`. Animate `transform`, never `width`.

## Hover (Tier 0–1)

### lift
Tokens: `duration.fast`, `ease.standard`. `transition-transform` on transform only.
```tsx
className="transition-transform duration-[var(--motion-duration-fast)] ease-[var(--motion-ease-standard)]
           hover:-translate-y-0.5 active:translate-y-0 motion-reduce:transition-none motion-reduce:hover:translate-y-0"
```

### 3D tilt (pointer-follow)
**Tier 3** — needs pointer math. Route to `module-add motion`; use `useMotionValue` + `useTransform`, `spring.snappy`. Reduced-motion: `useReducedMotion()` → return the static card. Don't ship tilt at Tier 0.

### avatar-group / card-stack hover spread
Tier 1 CSS: sibling `hover:` translate with a per-index `--i` custom property; `duration.fast`. Reduced-motion: `transition-none`.

## Feedback (Tier 1)

### success check draw
Tokens: `duration.slow`, `ease.emphasized`. Engine: CSS `stroke-dashoffset` keyframe on the SVG path.
```css
@keyframes check-draw { from { stroke-dashoffset: 24 } to { stroke-dashoffset: 0 } }
.check-draw { animation: check-draw var(--motion-duration-slow) var(--motion-ease-emphasized) forwards; }
@media (prefers-reduced-motion: reduce) { .check-draw { animation: none; stroke-dashoffset: 0 } }
```

### error shake
Tokens: `duration.base`, `ease.standard`. `@keyframes` on `translateX` (±`distance.md`), 3 cycles. Reduced-motion: no shake, show the error color/text only.

### number pop / count roll
Tier 1 (scale keyframe on change) or Tier 3 for a rolling odometer. Reduced-motion: set final value instantly.

### skeleton shimmer
Tier 0 — content-shaped `<Skeleton>` (per anti-slop rule) with Tailwind's core **`animate-pulse`**. ⚠️ `tw-animate-css` ships **no shimmer utility** (its only ready-made animations are accordion/collapsible/caret-blink — see `references/tw-animate-css.md`); for a true sweeping shimmer write a Tier-1 `@keyframes` on `transform: translateX()` over a gradient overlay, not `background-position`. Reduced-motion: static muted block.

## Layout (Tier 2–3)

### card resize / list reorder / shared-element
Tier 2 (**View Transitions API**) for same-document DOM changes without React overhead; Tier 3 (`layout` / `layoutId` in Motion) when already on Motion and you need spring. Never animate `width`/`height` by hand.
```tsx
// Tier 2 — same-doc swap
document.startViewTransition?.(() => flushSync(() => setState(next)));
```
Reduced-motion: guard with `if (!matchMedia("(prefers-reduced-motion: reduce)").matches)` — else swap instantly.

**Sitting on the Tier-2/Tier-3 seam: Motion's `animateView`** (graduated from Motion+ into the main library in 12.41.0; still present in **`motion@13.1.0`**, verified in the package). It's a first-party choreography layer *over* the browser's View Transitions — `.add()`, `.new()`/`.old()`, `.layout()`, `.group()`, `.crop()`, `.class()` — so you keep the native API's cheapness but get scriptable control over which elements pair up and how. Reach for it when a plain `document.startViewTransition` can't express the pairing you need, **before** escalating to Motion `layout`/`layoutId` (which re-renders through React). Requires the `motion` runtime (`module-add motion`). `[VERIFY]` the API against the installed version — it's young.


## Route / page transitions (Tier 2)

Next.js 16 App Router route transitions via the View Transitions API — Tier 2, no Motion needed.

**For production, drive it from the stable browser API** — wrap the navigation in `document.startViewTransition(...)` (the same primitive shown above for same-doc swaps) and name shared regions with `view-transition-name`. This is the path the Next.js docs recommend for route transitions today.

The React `<ViewTransition>` component below is React's **experimental** `unstable_ViewTransition` — treat it as opt-in, not production-ready. It requires enabling the flag in `next.config.js`, and the Next.js docs explicitly flag it as experimental / not recommended for production:
```js
// next.config.js
const nextConfig = { experimental: { viewTransition: true } };
```
```tsx
// EXPERIMENTAL — opt-in only; prefer document.startViewTransition() for production route transitions
// wrap navigations in a view transition; name the shared regions with `view-transition-name`
import { unstable_ViewTransition as ViewTransition } from "react";
<ViewTransition><main>{children}</main></ViewTransition>
```
Tokens: `duration.slow`, `ease.emphasized` via `::view-transition-group(*)` CSS. Reduced-motion: the global guard neutralizes the group animation; keep a plain crossfade or nothing.

---

## Choosing tier — quick rules

- Enter/exit fade/slide/scale, hover, skeleton, stagger → **Tier 0**.
- Bespoke feedback (draw/shake/pop), state crossfade → **Tier 1**.
- Route change, same-doc reorder/shared-element → **Tier 2**.
- Spring, drag/gesture, pointer-follow, scroll choreography, Motion `layout` → **Tier 3** (route to `module-add motion` first).

If two tiers both work, pick the lower one. If you're adding Motion for a single fade, stop — that's a Tier 0 job.
