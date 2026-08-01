# heroicons-animated — usage, API, accessibility

The real component surface (verified against a registry item; still `[VERIFY]` each generated `.tsx`, the registry evolves).

## Anatomy of one icon

Each `@heroicons-animated/<name>` item is a single `.tsx` that:
- `import { motion, useAnimation } from "motion/react"` (Tier-3 — forces `"use client"`).
- Exports `<Name>Icon` (default + named) with `displayName`, and a `<Name>IconHandle` interface.
- Props: `extends HTMLAttributes<HTMLDivElement>` + optional `size` (default `28`).
- Renders an SVG (`strokeWidth="1.5"`, Heroicons outline geometry) with `motion.path`/`motion.g` driven by `useAnimation()` controls.
- Wrapper `<div>` starts the `"animate"` sequence on hover **unless externally controlled** via the ref.

Example shapes (bell shakes `rotate: [0,-10,10,-10,0]`; menu morphs to X; heart scales/beats). The animation values live **inside** the component.

## Two ways to trigger

```tsx
"use client";
import { BellIcon, type BellIconHandle } from "@/components/ui/bell";
import { useRef } from "react";

// 1) Hover (default) — zero wiring
<BellIcon size={20} className="text-muted-foreground" aria-hidden />

// 2) Controlled — drive from your own state/event
function NotificationsButton({ hasNew }: { hasNew: boolean }) {
  const bell = useRef<BellIconHandle>(null);
  return (
    <button
      onMouseEnter={() => bell.current?.startAnimation()}
      onMouseLeave={() => bell.current?.stopAnimation()}
      aria-label="Notifications"
    >
      <BellIcon ref={bell} />
    </button>
  );
}
```

Controlled mode is the useful one: shake the bell **when a notification actually arrives**, morph the menu icon **on `open` state**, beat the heart **on like** — tie `startAnimation()` to real events, not just hover.

## Accessibility — the guard the library omits

The components animate unconditionally; add the guard yourself (this is the `transitions` discipline applied to icons):

```tsx
import { useReducedMotion } from "motion/react";

function LikeButton() {
  const heart = useRef<HeartIconHandle>(null);
  const reduce = useReducedMotion();
  return (
    <button
      aria-label="Like"
      onClick={() => { like(); if (!reduce) heart.current?.startAnimation(); }}
    >
      <HeartIcon ref={heart} />
    </button>
  );
}
```

- **Controlled mode**: `if (!reduce) ref.current?.startAnimation()`.
- **Hover mode**: when `reduce` and the icon is decorative, render the **static** heroicon of the same name instead of `<NameIcon>` (the animated component gives no prop to disable hover animation cleanly).
- Always give interactive icon buttons an `aria-label`; mark purely decorative icons `aria-hidden`.

## Tokenizing (consistency with `transitions`)

The library hardcodes its own timing. You can't easily rewrite each component's internal values, but you **can** keep everything you wrap around them on the system tokens (`lib/motion/tokens.ts`): the button hover-lift, the container transition, any follow-on effect. Reserve animated icons for **a few meaningful affordances** — a screen full of self-animating icons reads as noise (and multiplies `"use client"` boundaries).

## Non-shadcn install (Base UI / MUI projects without the shadcn CLI)

The components are plain `motion` + SVG — no shadcn runtime dependency. If `components.json` isn't present:
1. `npm i motion` (or `module-add motion`).
2. Copy the icon's `.tsx` from `https://www.heroicons-animated.com/r/<name>.json` (the `files[0]` content) into your components dir by hand.
3. Import and use as above. You own updates manually (no `shadcn add` upgrade path).

## Picking an icon

316 icons, Heroicons naming (e.g. `bell`, `heart`, `bars-3`, `arrow-path`, `check-circle`, `x-mark`, `chevron-down`, `magnifying-glass`, `trash`, `bookmark`, `cog-6-tooth`). Browse the grid at <https://www.heroicons-animated.com/>; the machine-readable list is the registry index. Match the name to the static heroicon you'd otherwise use so the two are visually consistent.
