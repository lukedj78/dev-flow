---
name: heroicons-animated
description: 'Add a Motion-animated Heroicon to a Next.js app from the heroicons-animated registry (316 icons, MIT, by Aniket Pawar, backed by Vercel OSS) instead of hand-animating an SVG. Each icon is a shadcn-registry component installed with `shadcn add @heroicons-animated/<name>`, built on the `motion` runtime, that animates on hover and exposes an imperative ref handle (`<Name>IconHandle.startAnimation()/stopAnimation()`) for external control. This skill owns the registry install + the two things the raw components lack: a `prefers-reduced-motion` guard (accessibility — the components animate unconditionally by default) and timing aligned to the project motion tokens (`lib/motion/`). Ecosystem-first counterpart for icons: it sits alongside `transitions` (the motion discipline), `module-add motion` (installs the `motion` runtime it depends on), and shadcn (the `@heroicons-animated/*` namespaced registry, same mechanism as coss-ui). Use when the user says "animated icon", "animate this icon", "make the bell/heart/menu icon animate on hover", "aggiungi un icona animata", or wants an icon micro-interaction. Refuses outside `stack.framework ∈ {next, monorepo}` (web) — for React Native use `rn-animations-gestures`. Not for: static icons (use the plain heroicons/lucide set via the UI library), a whole motion system (use `transitions`), or installing the animation runtime itself (use `module-add motion`).'
---

# heroicons-animated — Motion-animated Heroicons via the shadcn registry

Adds one **pre-built, Motion-animated Heroicon** to a Next.js app instead of hand-rolling an SVG animation. The [heroicons-animated](https://www.heroicons-animated.com/) registry ships **316 icons** (MIT, by Aniket Pawar, backed by the Vercel OSS program), each a shadcn-registry `registry:ui` component built on `motion` that animates on hover and can be driven imperatively.

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
   "registries": { "@heroicons-animated": "https://www.heroicons-animated.com/r/{name}.json" }
   ```
3. **Add the icon** — `pnpm dlx shadcn@latest add @heroicons-animated/<name>` (e.g. `bell`, `heart`, `bars-3`). It writes one `.tsx` to your components dir and installs `motion` if needed. `--overwrite` to replace. `[VERIFY]` the exact CLI flags against the installed shadcn version.

## Use it (real component API — `[VERIFY]` against the generated `.tsx`)

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

1. **`prefers-reduced-motion` guard (a11y).** The registry components animate **unconditionally** — there is no built-in reduced-motion handling. Wrap usage in the `transitions` discipline: gate the animation with Motion's `useReducedMotion()` so it no-ops for users who opted out.
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
- **`transitions`** — owns the motion **discipline** (tiers, tokens, reduced-motion). heroicons-animated is a **Tier-3 (Motion) icon source** under that discipline; `transitions` is where the reduced-motion + tokenization rules live.
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
