---
name: transitions
description: 'Give a Next.js 16 App Router app ONE motion system: a token layer (durations, easings, spring presets, distances) plus a curated library of production-ready, tokenized micro-interactions — entrance/exit, stagger, layout resize, modal/dropdown/panel/toast/accordion toggles, hover (lift/tilt/avatar-group), feedback (success check, error shake, number pop, skeleton shimmer), and route/page transitions. Governs motion the way `state-discipline` governs state: reach for the CHEAPEST technique first (Tailwind + tw-animate-css → CSS keyframes → View Transitions API → Motion runtime), always ship a `prefers-reduced-motion` fallback, animate only transform/opacity, and use tokens instead of magic-number durations/easings. Four modes: Setup (scaffold `lib/motion/` from the DESIGN.md motion block), Apply (add a best-fit transition to a component), Audit (find ad-hoc/hardcoded motion — `duration-[300ms]`, inline cubic-beziers, un-tokenized `transition:`), Refine (swap hardcoded values → tokens). Sits ABOVE `module-add motion` (which installs the Motion runtime) and reuses `tw-animate-css`; routes to `module-add motion` when a spring/layout/gesture effect actually needs JS. Inspired by the transitions.dev motion library (Jakub Antalík) — this is our token-driven, stack-native take, not a fork. Use when the user says "add a transition", "animate this", "aggiungi una transizione / animazione", "page transition", "stagger these cards", "make the modal open nicely", or "audit the motion in this codebase". Refuses outside `stack.framework ∈ {next, monorepo web}` + `stack.nextjs_version = "16"`. Not for: React Native motion (use `rn-animations-gestures`), installing the Motion runtime itself (use `module-add motion`), or defining the visual palette/type (that is DESIGN.md + design-md-to-app).'
---

# transitions — one tokenized motion system for a Next.js 16 app

This skill governs **how a web app moves**. Like `state-discipline` for state and `forms` for forms, it routes every animation through one shared, token-driven system so the product has a single, consistent motion feel — instead of scattered `duration-[237ms]` magic numbers and hand-tuned cubic-beziers that drift page to page.

> **Inspired by [transitions.dev](https://transitions.dev/) (Jakub Antalík)** — a curated library that teaches agents about product motion. This is **our own** take: token-driven, wired to the DESIGN.md contract and our Next.js 16 + Motion + `tw-animate-css` stack. Not a fork, not an install of their package — we credit the idea and build our own.

## When this skill applies

- The user says "add a transition / animation", "animate this", "aggiungi una transizione", "make the modal open nicely", "stagger these cards", "page transition between routes".
- You're about to write an inline `transition:` / `animate={{…}}` / `@keyframes` / a Tailwind `duration-[Xms]` arbitrary value.
- The user asks to **audit** a codebase for ad-hoc motion.
- A component needs entrance/exit, hover, feedback, layout, or route motion.

If the effect genuinely needs JS physics (spring, layout/shared-element, drag/gesture, scroll choreography) and the Motion runtime isn't wired, this skill **routes to `module-add motion`** first, then applies the tokenized pattern on top.

## Contract

Follows the dev-flow contract — see `references/contracts.md`. Key facts:

- Reads `meta.json#stack.framework`, `stack.nextjs_version`, `stack.motion`. For monorepo, reads `stack.monorepo.web.*` and operates in `apps/web/`.
- **Refuses** if `stack.framework ∉ {"next", "monorepo"}` or `stack.nextjs_version != "16"`. Principles transfer to other React setups but the View-Transitions/RSC rungs don't — refuse rather than mis-apply.
- Records `meta.json#stack.motion` (see block below) + appends `history` per run.
- Does **not** bump `phase`. Horizontal capability — invoke any time.

## Companion skills — what this owns vs reuses

- **`module-add motion`** — installs the **Motion** runtime (`motion/react`, `components/motion/*`, `lib/motion-config.ts`). This skill sits *above* it: it owns the token layer + the curated library + the discipline; it never re-installs the runtime, it routes there when Tier 3 is needed.
- **`tw-animate-css`** — already shipped by shadcn; it's this skill's **Tier 0** engine (fade/slide/scale/shimmer, zero JS). Reuse it, don't reinvent.
- **`design-md-to-app`** — owns DESIGN.md and the visual tokens. This skill reads the **`motion` block** of DESIGN.md for the *values*; if absent, it scaffolds sane defaults and writes them back (DESIGN.md stays the source of truth for values).
- **anti-slop fallbacks** (`design-md-to-app/references/anti-slop-fallbacks.md`) — the "animate only transform/opacity", hardware-acceleration, content-shaped-skeleton, CSS-stagger rules live there. This skill enforces them; it doesn't duplicate them.
- **`rn-animations-gestures`** — the **mobile** counterpart (Reanimated + Gesture Handler). This skill is web-only.

## The technique ladder — cheapest tier that does the job

Reach for the **lowest** tier that achieves the effect. Higher tiers cost bundle size, force `"use client"`, or add JS the interaction doesn't need.

| Tier | Engine | Use for | Cost |
|---|---|---|---|
| **0** | Tailwind + `tw-animate-css` | enter/exit fade·slide·scale, hover lift, CSS stagger (`animationDelay`), skeleton shimmer | zero JS, RSC-safe |
| **1** | Hand-written CSS `transition` / `@keyframes` (tokened) | bespoke feedback (success check draw, error shake, number pop), state-swap crossfades | zero JS, RSC-safe |
| **2** | **View Transitions API** | route/page transitions (Next 16 App Router), same-document DOM swaps (list reorder, tab underline) | tiny JS, mostly RSC-safe |
| **3** | **Motion** (`motion/react`) | spring physics, layout / shared-element, drag & gesture, scroll-driven choreography (`useScroll`/`useTransform`) | ~40kb, forces `"use client"` → routes to `module-add motion` |

**Never jump to Tier 3 for a fade.** A `<Suspense>` fallback, a hover lift, a dropdown open — all Tier 0/1. Reserve Motion for interactions that genuinely need physics or layout animation.

## Non-negotiables (the discipline)

1. **Tokens, not magic numbers.** Every duration/easing/spring/distance comes from `lib/motion/tokens.ts`. No inline `duration-[237ms]`, no ad-hoc `cubic-bezier(...)` in components.
2. **`prefers-reduced-motion` always.** Every transition ships a reduced-motion fallback (opacity-only or instant). Tier 0/1 use the `motion-reduce:` Tailwind variant or a media query; Tier 3 uses `useReducedMotion()`. A transition without a reduced-motion path is incomplete.
3. **Animate only `transform` and `opacity`** (+ `filter` sparingly). Never animate `width`/`height`/`top`/`left`/`box-shadow` — layout thrash. Use `transform: scale/translate` and, for layout, Tier 2/3.
4. **Don't force `"use client"` for motion that doesn't need it.** Prefer Tiers 0–2 to keep Server Components server-rendered.
5. **Motion has meaning.** Entrance ≠ decoration: it should clarify hierarchy, direction, or causality. If it doesn't, cut it.

## `lib/motion/tokens.ts` — the token layer

Setup mode scaffolds this from the DESIGN.md `motion` block (or defaults). Illustrative shape:

```ts
// Durations (ms) — the only durations the app uses.
export const duration = { instant: 0, fast: 120, base: 200, slow: 320, slower: 480 } as const;
// Easings — named curves; components reference these, never raw beziers.
export const ease = {
  standard: "cubic-bezier(0.2, 0, 0, 1)",   // enter/exit, most UI
  emphasized: "cubic-bezier(0.3, 0, 0, 1)", // hero, page
  exit: "cubic-bezier(0.4, 0, 1, 1)",       // leaving the screen
} as const;
// Distances (px) — how far things slide in.
export const distance = { sm: 4, md: 8, lg: 16 } as const;
// Spring presets (Tier 3 only) — mirrors module-add motion's lib/motion-config.ts if present.
export const spring = {
  soft: { type: "spring", stiffness: 300, damping: 30 },
  snappy: { type: "spring", stiffness: 500, damping: 32 },
} as const;
```

CSS consumers get the same values as custom properties (`--motion-duration-base`, `--motion-ease-standard`, …) so Tailwind arbitrary values reference `var(--motion-*)` instead of literals. The full token→CSS-var bridge and the reduced-motion wiring are in `references/motion-library.md`.

## Modes

Read state, then pick a mode:

1. Read `meta.json#stack`. Refuse if not Next 16 (web). Check whether `lib/motion/tokens.ts` exists.
2. If the requested effect is Tier 3 and Motion isn't installed (`package.json` has no `motion`/`framer-motion`), **route to `module-add motion`**, then continue.
3. Choose the mode.

### Setup (first run)
Scaffold `lib/motion/` : `tokens.ts` (from DESIGN.md `motion` block or defaults), the CSS-var bridge in the global stylesheet, and `transitions.ts` (the tokenized variant/classname library — the curated set from `references/motion-library.md`). Idempotent: detect existing files, offer to extend, never double-write. Record `stack.motion`.

### Apply (add a transition)
Pick the **best-fit** transition from the library for the component/context, at the **lowest viable tier**, propose it in one line with the rationale (which tier + why), then wire it using the tokens. Always include the reduced-motion fallback. Never introduce a new magic number — if the library lacks a fit, add a *tokenized* entry to `transitions.ts` rather than inlining.

### Audit (find ad-hoc motion)
Run `python scripts/scan_motion.py <root>` for a first-pass signal, then verify each hit in code. Report un-tokenized durations/easings, `duration-[Xms]`/`ease-[…]` Tailwind arbitraries, inline `cubic-bezier`, `@keyframes` animating layout props, transitions with no `prefers-reduced-motion` path, and Tier-3 usage where Tier 0/1 would do. See `references/audit-recipe.md`. The scan is a **signal, not a verdict**.

### Refine (swap to tokens)
In a given file, replace hardcoded durations/easings with the nearest token (round to the token scale) and add any missing reduced-motion fallback. Every change is a reviewable diff.

## `meta.json#stack.motion` block

```jsonc
"motion": {
  "runtime": "tw-animate-css" | "motion" | "both",   // Tier 0 only, or Motion also wired
  "tokens": true,                                      // lib/motion/tokens.ts scaffolded
  "view_transitions": true | false,                   // route transitions enabled
  "last_audit_at": "<ISO>" | null
}
```

## Definition of Done

- **Setup**: `lib/motion/tokens.ts` + CSS-var bridge + `transitions.ts` exist; `stack.motion.tokens = true`; values trace to the DESIGN.md `motion` block.
- **Apply**: the effect uses the lowest viable tier, references tokens (no magic numbers), and has a `prefers-reduced-motion` fallback.
- **Audit/Refine**: report lists only verified hits; refines land as diffs; a re-run is a no-op for already-tokenized code.
- Script green: `cd transitions/scripts && python3 -m unittest test_scan_motion`.

## What this skill does NOT do

- **Doesn't install the Motion runtime** — that's `module-add motion` (this skill routes there for Tier 3).
- **Doesn't define the palette/type** — DESIGN.md + `design-md-to-app` own visual tokens; this owns *motion* tokens.
- **Doesn't do React Native** — use `rn-animations-gestures`.
- **Doesn't bump `phase`.**

## Reference files

- `references/motion-library.md` — the curated, tokenized transition library: each entry → tier, tokens used, code snippet, and its `prefers-reduced-motion` fallback. Grouped enter/exit · toggle · hover · feedback · layout · route.
- `references/tw-animate-css.md` — the **Tier-0 engine how-to** (doc-grounded): the `animate-in`/`animate-out` class set and modifiers, `data-[state]` composition, the CSS variables to point at `lib/motion/tokens.ts`, and the `motion-reduce:` pattern. Read it before writing Tier-0 classes — don't guess class names.
- `references/audit-recipe.md` — "audit my codebase for ad-hoc motion" recipe (patterns, verify steps, refine order).
- `references/contracts.md` — the `.workflow/` dev-flow contract (vendored).
