# The eight shadcn styles — the layer a DESIGN.md's tokens cannot reach

Our preset path went straight from DESIGN.md to CSS variables. That skips a decision, and shadcn's
own `design-system` skill states it in one line worth keeping verbatim in spirit:

> **The theme gets replaced by the DESIGN.md anyway. The style decides the geometry the CSS variables
> can't reach** — control padding, density, how rounded and how raised the components are.

Variables carry colour, radius values, shadows and type. They do **not** carry the padding baked into
`button.tsx`, the control heights, the table density, or how many layers a card's shadow has before
you override it. That lives in the **style**, chosen once at `init`, and getting it wrong means
fighting the component source for the rest of the project.

Sources: `skills/shadcn/design-system.md` (MIT, shadcn-ui/ui, landed 2026-10-09) for the distinction
and the character column; **everything in the configuration table below is read from
`shadcn@4.21.4`'s own bundle** on 2026-10-09, because that is where the real values are — their own
table does not list them.

## The eight, with what each one actually sets

| Style | Character — pick it when the DESIGN.md shows | Icon library | Body font | Heading font |
|---|---|---|---|---|
| `vega` | The classic shadcn look. Neutral, conventional SaaS geometry; nothing extreme. | `lucide` | `inter` | inherit |
| `nova` | Reduced padding and margins, compact. 32–36px controls, 6–8px radius, hairlines over shadows. | `lucide` | `geist` | inherit |
| `maia` | Soft and rounded, generous spacing. 40px+ controls, 12px+ card radius, editorial pacing. | **`hugeicons`** | `figtree` | inherit |
| `lyra` | Boxy and sharp. 0–4px radius, hard edges, mono or technical type. | **`phosphor`** | `jetbrains-mono` | inherit |
| `mira` | Compact. Dense data UIs, 28–32px controls, tight tables. | **`hugeicons`** | `inter` | inherit |
| `luma` | Rounded geometry, soft elevation, breathable. Pill buttons, layered shadows, glassy surfaces. | `lucide` | `inter` | inherit |
| `rhea` | Luma's softness at product-UI density. | `lucide` | `inter` | inherit |
| `sera` | Editorial and typographic. Serif display, magazine hierarchy. | `lucide` | `noto-sans` | **`playfair-display`** |

All eight also set `baseColor`, `theme` and `chartColor` to `neutral`, `radius: "default"`,
`menuAccent: "subtle"`, `menuColor: "default"` and `rtl: false` — the knobs a preset code encodes and
a style leaves at its default.

## ⚠️ The style sets `icon_library`, and one value is outside our contract

This is the consequence that matters for `meta.json`, and it is not in their skill: **choosing a
style chooses an icon library.** `maia` and `mira` ship **hugeicons** — which the contract gained on
2026-10-03 for an unrelated reason — and **`lyra` ships `phosphor`, which `icon_library` cannot
express**: the enum is `"lucide" | "radix-icons" | "tabler" | "hugeicons" | string`.

So:

- **Record the style's library in `stack.icon_library`** after `init`, read from `info --json` rather
  than assumed. A style silently deciding a stack key and nobody writing it down is how `meta.json`
  stops describing the project.
- **`"phosphor"` is in the enum as of 2026-10-09**, promoted for the same reason as `"hugeicons"`:
  a contract that cannot name a value the toolchain itself chooses is the thing that is wrong. Facts
  read from the package: `@phosphor-icons/react` **2.1.10**, MIT, **1,512 icons**, **six weights per
  icon** (thin, light, regular, bold, fill, duotone), **31.5 MB** installed — between `lucide`
  (34.0) and `@tabler/icons-react` (16.7), and well under `@hugeicons/core-free-icons` (76.7) —
  tree-shakeable (`sideEffects: false`, real `exports`), peer `react >= 16.8`.
- **The six weights are why `lyra` picks it.** No other library in our enum offers a weight axis:
  `lucide` has one stroke, `@tabler/icons-react` has outline and filled. A technical, mono-typed
  design system gets a real `thin`/`regular`/`bold` ladder here, which is exactly `lyra`'s character.
- ⚠️ **But `animated-icons` has registries for heroicons and hugeicons only.** An animated-icon
  request on a `phosphor` project needs a different answer — hand-rolled on the `motion` runtime,
  per that skill's own rules, or a deliberate second library for the one animated case.

## Picking one from a DESIGN.md

Read four things out of the DESIGN.md — **radius scale, control heights, shadow treatment, layout
density** — and match them against the character column. Then **state the choice and the reason in
one line** before writing any code:

> *Picked `maia`: 40px controls, 12–16px card radius, generous padding.*

If the user names a style, use theirs without arguing. If the DESIGN.md gives a **preset code**
(`b0`) or a style name or URL, pass it through and **never decode it by hand** — `preset decode` is
the only thing that reads one correctly.

## Two `init` facts that cost an hour each

**`init` with neither `--preset` nor `--base` stops at an interactive library prompt, even with
`-y`.** Always pass one of them. Ours always passes `--base` from `stack.ui_base`, so we are covered
— but a hand-run `init` in a terminal is not.

**Then read the project before writing code:**

```bash
npx shadcn@latest info --json
```

It reports `base`, `style`, `iconLibrary`, `tailwindCssFile` and `aliases`. `base` is what decides
**`render` vs `asChild`** on every component you touch (see `base-ui-mapping.md`) — read it, do not
infer it from what you passed.

> **Our default is not theirs.** Their skill defaults the template to **Vite** and reaches for Next
> only when asked. We are **Next 16 App Router only** (`nextjs_version` must be `"16"`; the web
> skills refuse anything else), so the template is never a decision here and their Vite-specific
> notes — the root `tsc --noEmit` checking nothing because the root tsconfig holds only project
> references, `src/showcase/` instead of `app/design-system/` — do not apply to us. Read their file
> for the reasoning, not for the paths.

## Where this sits in the two paths

- **Preset path** (`stack.shadcn_preset` set) — the preset already encodes style, fonts, icon
  library and colour. Pass it through; the style table is then for *reading* what you got, not for
  choosing.
- **DESIGN.md-first path** (the default) — there is no preset code, so **pick a style and pass it
  with `--base`**, which is the step this file adds. Without a style the scaffold takes `vega`'s
  geometry by default, and a DESIGN.md asking for 44px pill buttons then fights `vega`'s padding in
  every component.
