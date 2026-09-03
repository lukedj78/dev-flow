---
name: animated-icons
description: 'Add a Motion-animated icon to a Next.js app from a shadcn registry instead of hand-animating an SVG. Two registries, picked from the project''s icon set: **heroicons-animated** (316 icons, `shadcn add @heroicons-animated/<name>`) and **hugeicons-animated** (165 icons, `shadcn add @hugeicons-animated/<name>`, which also installs a shared `lib/use-icon-animation.ts`). Both MIT, both on the `motion` runtime, both copied into your repo as source. This skill owns the install plus the two things the raw components lack: a `prefers-reduced-motion` guard and timing aligned to the project motion tokens (`lib/motion/`). Use when the user says "animated icon", "animate this icon", "make the bell/heart/menu icon animate on hover", "aggiungi un''icona animata", or wants an icon micro-interaction. Refuses outside Next.js web — for React Native use `rn-animations-gestures`. Not for: static icons, a whole motion system (`transitions`), or installing the runtime itself (`module-add motion`).'
---

# animated-icons — Motion-animated icons via the shadcn registries

Adds one **pre-built, Motion-animated icon** to a Next.js app instead of hand-rolling an SVG animation. Two registries ship them as shadcn components, both MIT, both on `motion`, both copied into your repo as source you then own:

| Registry | Icons | Namespace | Extra file |
|---|---:|---|---|
| [heroicons-animated](https://www.heroicons-animated.com/) | 316 | `@heroicons-animated/<name>` | — each icon is self-contained |
| [hugeicons-animated](https://hugeicons-animated.com/) | 165 | `@hugeicons-animated/<name>` | **`lib/use-icon-animation.ts`**, a shared hook installed once |

**Pick the one that matches the project's static set**, not the one with more icons: an animated Heroicon next to Hugeicons outlines reads as a different drawing, because it is. Read `meta.json#stack.icon_library` (or the DESIGN.md icon block) before choosing, and say which you picked and why.

This is the **ecosystem-first** move for animated icons — the same rule as everywhere in dev-flow: don't hand-animate a bell/heart/menu SVG when a maintained, tokenizable component exists. This skill owns the **install** plus the two things the raw components *don't* give you: an **accessibility guard** (they animate unconditionally) and **timing aligned to your motion tokens**.

## When this skill applies

- "animated icon", "animate this icon", "make the bell/heart/menu icon animate on hover", "aggiungi un'icona animata", an icon micro-interaction (notification bell shake, menu↔close morph, heart like).

If the user wants a **whole motion system** (durations/easings/tiers), that's `transitions`. If they want a **static** icon, that's the plain heroicons/lucide set from the UI library. If the `motion` runtime isn't wired yet, this skill routes to `module-add motion` first (the components import from `motion/react`).

## Contract

Follows the dev-flow contract — see `references/contracts.md`. Key facts:

- Reads `meta.json#stack.framework` — **refuses** if not `{"next", "monorepo"}` (web). React Native → `rn-animations-gestures`.
- Requires the **`motion`** runtime (each icon `import`s from `motion/react`). If absent, route to `module-add motion` first.
- Requires a **shadcn-configured** project (`components.json`). If the project uses Base UI/MUI without shadcn CLI, the components still work (they're plain `motion` + SVG) but you install them by hand — see `references/usage.md`.
- Records nothing structural and **does not bump `phase`** — appends a `history` entry per install. Horizontal capability.

## Install one icon

1. **Ensure the `motion` runtime** — `package.json` has `motion` (or run `module-add motion`; the components `import { motion, useAnimation } from "motion/react"`).
2. **Register the namespaced registry once** in `components.json` (shadcn CLI v4 namespaced registries, the same mechanism as `coss-ui`'s `@coss/*`):
   ```jsonc
   // components.json
   "registries": {
     "@heroicons-animated": "https://www.heroicons-animated.com/r/{name}.json",
     "@hugeicons-animated": "https://hugeicons-animated.com/r/{name}.json"
   }
   ```
3. **Add the icon** — `pnpm dlx shadcn@latest add @heroicons-animated/<name>` (e.g. `bell`, `heart`, `bars-3`) or `@hugeicons-animated/<name>` (e.g. `add-circle`, `alarm-clock`, `arrow-right-02`). It writes one `.tsx` to your components dir and installs `motion` (the item's only dependency).

**Flags confirmed at `shadcn@4.19.0`** from the CLI's own `add` definition: `-o, --overwrite`
(*"overwrite existing files"*), plus three worth knowing for a copy-in registry —
**`--view [path]`** (*"show file contents"*), **`--diff [path]`** (*"show diff for a file"*) and
**`--dry-run`** (*"preview changes without writing files"*). Since the component becomes *your* file
the moment it lands, `--view` before the first add and `--diff` before an `--overwrite` are the two
that save you. Also available: `-y/--yes`, `-a/--all`, `-p/--path`, `-s/--silent`, `-c/--cwd`.

## Use it (real component API — read off the registry source, 2026-08-26)

Each icon exports a `<Name>Icon` component **and** a `<Name>IconHandle` ref type. Props extend `HTMLAttributes<HTMLDivElement>` plus `size` (default `28`).

```tsx
"use client"; // motion forces a client component
import { BellIcon, type BellIconHandle } from "@/components/ui/bell";
import { useRef } from "react";

// (a) hover — animates automatically on pointer-enter, no wiring
<BellIcon size={20} className="text-muted-foreground" />

// (b) controlled — trigger from your own event (e.g. a new notification)
const bell = useRef<BellIconHandle>(null);
bell.current?.startAnimation();   // and .stopAnimation()
<BellIcon ref={bell} />
```

## The two value-adds this skill enforces

1. **`prefers-reduced-motion` guard (a11y).** ⚠️ **Check the registry before assuming, because the two differ** — verified by installing from both at `shadcn@4.19.0`:
   * **hugeicons-animated** — the shared `lib/use-icon-animation.ts` it installs alongside the first icon **already calls `useReducedMotion()`** and makes `startAnimation()` a no-op when it is set. The hook is the guard.
   * **heroicons-animated** — each icon is self-contained and animates on hover **unconditionally**; the guard is yours to add.

   Either way, **the trigger you write needs its own check**: hover mode is the component's business, but `bell.current?.startAnimation()` fired from your own event is your call, and calling it for a user who opted out is your bug, not the hook's. So keep the guard at the call site regardless of registry:
   ```tsx
   import { useReducedMotion } from "motion/react";
   const reduce = useReducedMotion();
   // hover mode: pass a prop / conditionally render the static heroicon when `reduce`
   // controlled mode: `if (!reduce) bell.current?.startAnimation()`
   ```
   Where an animated icon is purely decorative and `reduce` is set, prefer the **static** heroicon of the same name.
2. **Token the timing.** The components hardcode their own durations/easings. When you control an icon's transition (wrappers, follow-on effects), align it to the project's `lib/motion/tokens.ts` (see `transitions`) so icon motion matches the system feel instead of drifting.

## Companion skills — what this owns vs reuses

- **`module-add motion`** — installs the `motion` runtime these icons depend on. This skill routes there; it never re-installs the runtime.
- **`transitions`** — owns the motion **discipline** (tiers, tokens, reduced-motion). this skill is a **Tier-3 (Motion) icon source** under that discipline; `transitions` is where the reduced-motion + tokenization rules live.
- **shadcn** (`design-md-to-app` / the UI library) — owns `components.json` and the static icon set. Animated icons **complement** the static heroicons; mix freely (static in dense UI, animated for a few meaningful affordances).
- **`rn-animations-gestures`** — the React Native counterpart (this registry is web/DOM-only).

## Definition of Done

- The requested icon's `.tsx` exists in the components dir; `motion` is in `package.json`.
- Usage includes the **reduced-motion guard** (no unconditional animation).
- Decorative-only icons fall back to the static heroicon under `prefers-reduced-motion`.
- `history` appended; **no `phase` bump**.

## What this skill does NOT do

- **Doesn't install the runtime** — that's `module-add motion`.
- **Doesn't define a motion system** — that's `transitions`.
- **Doesn't do React Native** — use `rn-animations-gestures`.
- **Doesn't replace static icons** — it adds a few animated affordances; most icons stay static.

## Reference files

- `references/usage.md` — the real per-icon component API (hover + imperative handle), the reduced-motion patterns, hand-install (non-shadcn) path, and the icon-name list pointer.
- `references/contracts.md` — the `.workflow/` dev-flow contract (vendored).
