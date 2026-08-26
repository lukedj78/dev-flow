# heroicons-animated — usage, API, accessibility

The real component surface, **read off the registry source on 2026-08-26** — five items fetched and
compared (`bell`, `heart`, `bars-3`, `arrow-path`, `x-mark`), all identical in shape: `size` defaults
to `28`, `strokeWidth` is a hardcoded `1.5`, the only dependency is `motion`, and the ref-controlled
switch below is present in every one. Still `[VERIFY]` each generated `.tsx` — the registry evolves,
and once copied in **your repo owns that file**: no `add` will come back to update it.

## Anatomy of one icon

Each `@heroicons-animated/<name>` item is a single `.tsx` that:
- `import { motion, useAnimation } from "motion/react"` (Tier-3 — forces `"use client"`).
- ⚠️ **Exports `<Name>Icon` as a *named* export only** — `export { BellIcon }`, with `displayName` set
  and a `<Name>IconHandle` interface. **There is no default export**, and this file used to claim
  there was. `import BellIcon from "@/components/ui/bell"` gives you `undefined`, which fails at render
  rather than at import. Checked across `bell`, `heart`, `bars-3`, `arrow-path`, `x-mark` on
  2026-08-26 — none of the five has one.
- Props: `extends HTMLAttributes<HTMLDivElement>` + optional `size` (default `28`).
- Renders an SVG (`strokeWidth="1.5"`, Heroicons outline geometry) with `motion.path`/`motion.g` driven by `useAnimation()` controls.
- Wrapper `<div>` starts the `"animate"` sequence on hover **unless externally controlled** — and the
  switch is subtler than it looks: `useImperativeHandle` sets `isControlledRef.current = true` as a
  side effect, so **merely attaching a ref flips the component out of self-animating mode**. From then
  on hover no longer animates; the component calls *your* `onMouseEnter`/`onMouseLeave` instead. That
  is why the controlled example below wires the hover handlers on the `<button>`: without them the
  icon goes inert.
- Imports `cn` from `@/lib/utils` — see the non-shadcn note at the bottom, it matters there.

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

The components are `motion` + SVG, with **one shadcn-shaped import**: every file does
`import { cn } from "@/lib/utils"`. That is not a runtime *package* dependency, but it is a path that
only exists in a shadcn-initialised project — so a Base UI / MUI repo has to provide a `cn` at that
alias or edit the import. Verified on all five icons sampled, 2026-08-26.

If `components.json` isn't present:
1. `npm i motion` (or `module-add motion`).
2. Copy the icon's `.tsx` from `https://www.heroicons-animated.com/r/<name>.json` (the `files[0]` content) into your components dir by hand.
3. **Give it a `cn`** — either add the two-line `clsx` + `tailwind-merge` helper at `@/lib/utils`, or replace `cn(className)` with `className` (the components pass nothing else to it).
4. Import and use as above. You own updates manually (no `shadcn add` upgrade path).

## Picking an icon

**316 icons** — counted from `https://www.heroicons-animated.com/r/registry.json` on 2026-08-26, which is also the machine-readable index. Heroicons naming (e.g. `bell`, `heart`, `bars-3`, `arrow-path`, `check-circle`, `x-mark`, `chevron-down`, `magnifying-glass`, `trash`, `bookmark`, `cog-6-tooth`). Browse the grid at <https://www.heroicons-animated.com/>; the machine-readable list is the registry index. Match the name to the static heroicon you'd otherwise use so the two are visually consistent.
