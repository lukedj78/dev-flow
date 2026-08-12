# module-add → `motion` (Motion / framer-motion)

Wire **Motion** (the official rebrand of framer-motion, NPM package `motion`) as the JS animation layer of an existing scaffold. Defaults: a small set of opinionated wrapper components + shared spring presets, so the project has consistent motion feel out of the box.

Goal: when a project actually needs JS-driven motion (magnetic hover, shared-element transitions, scroll-triggered choreography), the building blocks are already there — typed, RSC-safe, and pre-tuned with sensible spring physics. For sites that only need fade/slide on enter, **don't run this module** — `tw-animate-css` (already installed via shadcn) does that with zero JS.

## Idempotency check

⚠️ **Motion 13 (2026-08) has exactly one breaking change**, and it does not affect a Tailwind project: it drops `@emotion/is-prop-valid` as an optional dependency "in favour of explicit injection". If the project *does* use styled-components or Emotion, styled `motion` components will start forwarding props to the DOM that used to be filtered — supply the validator via `<MotionConfig isValidProp={…}>`, or invert the composition so the styling library owns prop forwarding. `useReducedMotion` and `animateView` both survive the major (verified in `motion@13.1.0` / `framer-motion@13.1.0`).

Before doing anything, check whether Motion is already wired:

1. `<project-root>/package.json` contains `"motion"` (or `"framer-motion"` for legacy projects) in `dependencies`.
2. `<project-root>/components/motion/fade-in.tsx` exists.
3. `<project-root>/lib/motion-config.ts` exists.

If all three: tell the user it's installed, offer to regenerate the demo page or extend the wrapper set. Don't double-install. If only `motion` is in `package.json` but the wrappers are missing (a previous user installed framer-motion manually), re-run the file generation but skip `npm install`.

## Prerequisites

- `meta.json#stack.framework` should be set. Variants: Next App Router, Vite + React, Remix. Other frameworks not yet supported in this variant.
- No dependency on `auth`, `db`, or any backend module — motion is a pure UI concern.

**When to NOT run this module**:
- Editorial / content-heavy sites where animation = fade-in on scroll. `tw-animate-css` already covers that.
- Static dashboards where motion is noise. Adding 40kb gzip for nothing is waste.
- Server-component-heavy pages (Motion forces `"use client"` on every animated tree).

Run it when: you actually want **interactive** motion (magnetic hover, drag, gestures, shared-element transitions, scroll-driven choreography that needs `useScroll`/`useTransform`). If you're not sure, you don't need it yet.

## Install

```bash
cd <project-root>
npm install motion
```

`motion` is the current package name (rebranded from `framer-motion` in late 2024). The React API is imported from `motion/react`. Do NOT also install `framer-motion` — they're the same library and shipping both bloats the bundle.

If `package.json` already has `framer-motion` (legacy project), leave it — the wrappers below import from `framer-motion` instead. Detect at install time:

```bash
if grep -q '"framer-motion"' package.json; then
  echo "Detected legacy framer-motion — skipping install, wrappers will import from framer-motion"
else
  npm install motion
fi
```

## Files to write

### `lib/motion-config.ts`

Shared spring + transition presets so every animated component in the project feels consistent. Taste-skill's rule: never use linear easing for interactive elements; use spring physics with calibrated stiffness/damping.

```typescript
import type { Transition, Variants } from "motion/react";

/**
 * Project-wide motion presets.
 *
 * RULES (anti-slop):
 * - All interactive motion uses spring physics, not linear easing.
 * - Transitions animate `transform` + `opacity` only (hardware-accelerated).
 * - Never animate `top`, `left`, `width`, or `height` — use `x`, `y`, `scale`.
 *
 * Stiffness/damping calibration:
 * - `snappy`: UI feedback (button press, toggle). Fast, slightly bouncy.
 * - `smooth`: layout transitions, modal mount. Calm, settled.
 * - `gentle`: hero reveals, hover follow. Soft, organic.
 */
export const SPRING = {
  snappy: { type: "spring", stiffness: 400, damping: 30 } satisfies Transition,
  smooth: { type: "spring", stiffness: 100, damping: 20 } satisfies Transition,
  gentle: { type: "spring", stiffness: 60, damping: 18 } satisfies Transition,
} as const;

/**
 * Standard fade-in-from-bottom variant. Used by FadeIn, StaggerList children.
 * 24px lift = enough to feel intentional, not so much it triggers motion sickness.
 */
export const FADE_UP: Variants = {
  hidden: { opacity: 0, y: 24 },
  visible: { opacity: 1, y: 0, transition: SPRING.gentle },
};

/**
 * Container variant for staggered children reveal.
 *
 * `staggerChildren: 0.08` = 80ms between each child. Tuned to feel like a
 * waterfall, not a slow procession. Bump to 0.12 for hero sections; drop to
 * 0.04 for dense lists.
 */
export const STAGGER_CONTAINER: Variants = {
  hidden: {},
  visible: {
    transition: { staggerChildren: 0.08, delayChildren: 0.04 },
  },
};
```

### `components/motion/fade-in.tsx`

Single-element fade-in-from-bottom wrapper. Use for hero text, section headings, feature card mounts.

```tsx
"use client";

import { motion, useReducedMotion } from "motion/react";
import type { HTMLMotionProps } from "motion/react";
import { FADE_UP } from "@/lib/motion-config";

type FadeInProps = HTMLMotionProps<"div"> & {
  delay?: number;
};

/**
 * Fade in from below on mount (or on scroll into view if used inside an
 * `viewport={{ once: true }}` motion container).
 *
 * Respects `prefers-reduced-motion`: users with the OS-level setting see the
 * content instantly, no transform.
 */
export function FadeIn({ children, delay = 0, ...rest }: FadeInProps) {
  const reduce = useReducedMotion();

  if (reduce) return <div {...(rest as React.HTMLAttributes<HTMLDivElement>)}>{children}</div>;

  return (
    <motion.div
      variants={FADE_UP}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, margin: "-10% 0px" }}
      transition={{ ...FADE_UP.visible.transition, delay }}
      {...rest}
    >
      {children}
    </motion.div>
  );
}
```

### `components/motion/stagger-list.tsx`

Container that staggers its children's reveal. Wrap a `<ul>` or grid; each direct child is animated in sequence.

```tsx
"use client";

import { Children, isValidElement, cloneElement } from "react";
import { motion, useReducedMotion } from "motion/react";
import type { HTMLMotionProps } from "motion/react";
import { FADE_UP, STAGGER_CONTAINER } from "@/lib/motion-config";

type StaggerListProps = HTMLMotionProps<"div"> & {
  /** Override the default 80ms stagger interval. */
  stagger?: number;
};

/**
 * Stagger reveal of direct children.
 *
 * Each child must be a real React element (HTML or component) — strings/null
 * are passed through but won't animate. Children are wrapped in a motion.div
 * that uses the FADE_UP variant by default.
 *
 * Usage:
 *   <StaggerList className="grid grid-cols-3 gap-6">
 *     <Card />
 *     <Card />
 *     <Card />
 *   </StaggerList>
 */
export function StaggerList({ children, stagger, ...rest }: StaggerListProps) {
  const reduce = useReducedMotion();
  const containerVariants = stagger
    ? {
        ...STAGGER_CONTAINER,
        visible: { transition: { staggerChildren: stagger, delayChildren: 0.04 } },
      }
    : STAGGER_CONTAINER;

  if (reduce) return <div {...(rest as React.HTMLAttributes<HTMLDivElement>)}>{children}</div>;

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, margin: "-5% 0px" }}
      {...rest}
    >
      {Children.map(children, (child) =>
        isValidElement(child) ? (
          <motion.div variants={FADE_UP}>{child}</motion.div>
        ) : (
          child
        ),
      )}
    </motion.div>
  );
}
```

### `components/motion/magnetic-button.tsx`

Button that pulls slightly toward the cursor on hover. Uses `useMotionValue` + `useSpring` — never `useState` for hover, since per-frame state updates trigger React re-renders and tank performance on mobile.

```tsx
"use client";

import { useRef } from "react";
import { motion, useMotionValue, useSpring, useReducedMotion } from "motion/react";
import { cn } from "@/lib/utils";

type MagneticButtonProps = React.ComponentProps<"button"> & {
  /** Pixels of pull at the edge of the trigger area. Default: 12. */
  strength?: number;
};

/**
 * Magnetic hover effect — the button's content drifts toward the cursor while
 * the cursor is inside the trigger area, snaps back on leave.
 *
 * Implementation notes:
 * - Uses `useMotionValue` for the x/y offsets — these live OUTSIDE the React
 *   render cycle, so per-frame updates don't trigger renders.
 * - Wrapped in `useSpring` so the snap-back is physically calibrated.
 * - Falls back to a plain button when `prefers-reduced-motion` is set.
 *
 * For consistency, animate ONLY transform (translate) and opacity. Never
 * change width/height/top/left during interaction.
 */
export function MagneticButton({
  children,
  strength = 12,
  className,
  ...rest
}: MagneticButtonProps) {
  const reduce = useReducedMotion();
  const ref = useRef<HTMLButtonElement>(null);
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const springX = useSpring(x, { stiffness: 200, damping: 18 });
  const springY = useSpring(y, { stiffness: 200, damping: 18 });

  function onMove(e: React.MouseEvent<HTMLButtonElement>) {
    if (!ref.current || reduce) return;
    const rect = ref.current.getBoundingClientRect();
    const dx = (e.clientX - (rect.left + rect.width / 2)) / (rect.width / 2);
    const dy = (e.clientY - (rect.top + rect.height / 2)) / (rect.height / 2);
    x.set(dx * strength);
    y.set(dy * strength);
  }

  function onLeave() {
    x.set(0);
    y.set(0);
  }

  return (
    <button
      ref={ref}
      onMouseMove={onMove}
      onMouseLeave={onLeave}
      className={cn("inline-flex items-center justify-center", className)}
      {...rest}
    >
      <motion.span style={{ x: springX, y: springY }} className="contents">
        {children}
      </motion.span>
    </button>
  );
}
```

### Reference UI: `app/motion-demo/page.tsx`

A short demo page showing all three primitives in real use. The user keeps it as a reference, deletes it once they've copied the patterns into real pages.

```tsx
import { FadeIn } from "@/components/motion/fade-in";
import { StaggerList } from "@/components/motion/stagger-list";
import { MagneticButton } from "@/components/motion/magnetic-button";

export default function MotionDemoPage() {
  return (
    <main className="mx-auto max-w-4xl px-6 py-20 space-y-24">
      <section className="space-y-4">
        <FadeIn>
          <h1 className="text-5xl font-black tracking-tight">FadeIn</h1>
        </FadeIn>
        <FadeIn delay={0.15}>
          <p className="text-foreground/70 max-w-prose">
            Single-element reveal. Use for hero text and section headings.
            Respects prefers-reduced-motion.
          </p>
        </FadeIn>
      </section>

      <section className="space-y-6">
        <h2 className="text-3xl font-black tracking-tight">StaggerList</h2>
        <StaggerList className="grid grid-cols-1 sm:grid-cols-3 gap-6">
          {[1, 2, 3, 4, 5, 6].map((n) => (
            <div key={n} className="border border-foreground/15 rounded-2xl p-6">
              <p className="font-mono text-xs uppercase tracking-wider text-foreground/50">
                Card {n.toString().padStart(2, "0")}
              </p>
              <p className="mt-2 text-foreground/80">
                Children mounted with 80ms cascade.
              </p>
            </div>
          ))}
        </StaggerList>
      </section>

      <section className="space-y-6">
        <h2 className="text-3xl font-black tracking-tight">MagneticButton</h2>
        <MagneticButton className="rounded-full bg-foreground text-background h-12 px-8 text-sm font-bold uppercase tracking-wider">
          Hover me
        </MagneticButton>
      </section>
    </main>
  );
}
```

The demo route is **not** linked from the main nav — the user finds it at `/motion-demo` and removes it once they've internalized the patterns.

## Environment variables

None — Motion is a client-side library, no API keys.

## RSC + Client Component discipline

Every component this module writes starts with `"use client"`. Document this in the user-facing summary:

> Motion is a client-side library. The wrappers (`FadeIn`, `StaggerList`, `MagneticButton`) are leaf client components — you can use them inside Server Components, but the wrappers themselves render on the client. If you wrap a large RSC tree in a motion container, that whole tree becomes client. Keep the boundary tight: animate the leaf, not the section.

## Update meta.json

```json
{
  "stack": {
    "motion": "motion"
  }
}
```

(Use `"framer-motion"` instead if the legacy package is in use.)

## Known caveats

- **Bundle size**: Motion adds ~40kb gzip. For sites that only need fade-in-on-scroll, `tw-animate-css` (CSS-only) is lighter. Don't run this module unless you actually use `useMotionValue`, gestures, or shared-element transitions.
- **Server Component boundary**: every component that imports from `motion/react` must be a Client Component. If you wrap an entire page section, that section becomes client and loses RSC benefits (data fetching, smaller bundle). Keep motion at the leaf.
- **`useReducedMotion`**: respect it. Users with vestibular disorders enable the OS-level setting; ignoring it is hostile. All three wrappers in this module already check it.
- **No mixing with GSAP**: don't run GSAP and Motion in the same component tree. Motion's `useScroll` covers 90% of GSAP's ScrollTrigger use cases without the ecosystem split. If you need GSAP for a specific full-page sequence, isolate it in its own route and don't mount Motion components inside.
- **Spring presets are project-wide**: edit `lib/motion-config.ts` to retune. Don't pass arbitrary `{ stiffness, damping }` inline in components — that's how feel drifts across the project.
- **Layout animations** (`layout`, `layoutId` props) require both source and target components to mount in the same React tree at the same time. They're powerful but the debugging cost is real — use sparingly, only for hero-detail or modal-card transitions where the effect is worth it.

## Anti-slop motion rules (encoded above)

The wrappers and presets bake in the rules from `taste-skill`'s motion philosophy that are **portable** to our stack:

- ✅ Spring physics, never linear easing — `SPRING` presets in `motion-config.ts`.
- ✅ Animate `transform`/`opacity` only — wrappers use `x`, `y`, `opacity`, never `width`/`height`/`top`/`left`.
- ✅ `useMotionValue` for hover, never `useState` — `MagneticButton` uses motion values + spring.
- ✅ Stagger via container variant, parent + children in same Client tree — `StaggerList` enforces this.
- ✅ Respect `prefers-reduced-motion` — every wrapper checks `useReducedMotion`.

What's NOT covered (out of scope for v1, add when needed):
- GSAP / ScrollTrigger / Locomotive Scroll — different module if it ever becomes a need.
- Three.js / WebGL canvas — different module.
- `layout` / `layoutId` shared-element transitions — Motion supports them, but the demo doesn't show them. Add to the demo on first request.
