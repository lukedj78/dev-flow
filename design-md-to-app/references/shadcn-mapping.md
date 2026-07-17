# DESIGN.md → shadcn/ui mapping

shadcn/ui is not a runtime library — it's a CLI that copies component source into your repo. The theme lives in:

1. **CSS variables** in `app/globals.css` under `:root` (and `.dark` if you wire dark mode).
2. **An `@theme inline {}` block** in the same CSS file that exposes those variables to Tailwind.

Component-level customization happens by **editing the component source** in `components/ui/*` — usually the `cva` `variants` block.

> **Modern stack (current shadcn + Tailwind v4) is the default this reference assumes.** If you're integrating into an older project on Tailwind v3, see the **Tailwind v3 legacy notes** subsection at the end of "Color tokens".

## Project setup

shadcn works with any React framework. Always run `init` non-interactively and **always run `add --all`** so the user starts with the full kit pre-styled — every primitive in `components/ui/` is yours to customize per the DESIGN.md.

### Next.js (App Router) — default

```bash
pnpm create next-app@latest <dir> --typescript --tailwind --eslint --app --no-src-dir --import-alias "@/*" --use-pnpm --turbopack --yes
cd <dir>
pnpm dlx shadcn@latest init --defaults --no-monorepo
pnpm dlx shadcn@latest add --all --yes
```

This produces a Next.js 16 + Tailwind v4 + shadcn project. `init --defaults` uses the canonical preset (`--template=next --preset=base-nova`), enables CSS variables, writes `components.json`, installs dependencies, scaffolds `lib/utils.ts`, `components/ui/button.tsx`, and **rewrites `app/globals.css`** with `@theme inline {}` + neutral base palette. **Don't overwrite `globals.css` from scratch afterwards — read what's there and edit/extend it.**

### Vite + React

Tailwind v4 ships as a Vite plugin — no `tailwindcss init -p`, no `tailwind.config.ts` for the basic setup.

```bash
pnpm create vite@latest <dir> -- --template react-ts
cd <dir>
pnpm install
pnpm add tailwindcss @tailwindcss/vite
pnpm dlx shadcn@latest init --defaults --no-monorepo --template vite
pnpm dlx shadcn@latest add --all --yes
```

Configure `vite.config.ts`:

```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
});
```

The CSS imports go in `src/index.css` (shadcn init writes them):

```css
@import "tailwindcss";
@import "tw-animate-css";
@import "shadcn/tailwind.css";

@custom-variant dark (&:is(.dark *));

@theme inline {
  /* Tokens — see "Color tokens" section below */
}
```

### Remix

```bash
pnpm create remix@latest <dir>
cd <dir>
pnpm install
pnpm dlx shadcn@latest init --defaults --no-monorepo --template react-router
pnpm dlx shadcn@latest add --all --yes
```

Wrap `<Outlet />` in your `<ThemeProvider>` inside `app/root.tsx` if you want dark/light toggling.

### Monorepo (shared `packages/ui` — the official shadcn layout)

**When `meta.json#stack.framework == "monorepo"` and `stack.ui == "shadcn"`, do NOT run `--no-monorepo` and do NOT dump components into `apps/web/components/ui/`.** Use shadcn's official monorepo structure instead: the components live in a shared **`packages/ui`** package imported as **`@workspace/ui`**, and `apps/web` consumes them.

> **Why a branch.** dev-flow's default monorepo (see `monorepo-bootstrap`) keeps shadcn components in `apps/web/components/ui/` and shares only *tokens* via `packages/design/`. That model exists for **web + mobile** monorepos, where components can't be shared across React DOM and React Native anyway (mobile uses NativeWind), so only tokens are shareable. **For a web-centric monorepo with no NativeWind consumer** — web-only, **web + agent**, or multiple web apps — that rationale doesn't hold, and the canonical shadcn `packages/ui` (`@workspace/ui`) layout is correct: it's the official path, it lets multiple web surfaces share one component set, and `shadcn add` knows how to target it. Pick this branch whenever the monorepo has no mobile/NativeWind side.

Official layout (per <https://ui.shadcn.com/docs/monorepo>):

```
apps/web/
├── components.json          # ui alias → "@workspace/ui/components", utils → "@workspace/ui/lib/utils"
├── components/              # app-specific blocks only (not primitives)
└── package.json             # depends on "@workspace/ui": "workspace:*"

packages/ui/
├── components.json          # ui alias → "@workspace/ui/components" (install target = local)
├── src/
│   ├── components/          # shadcn primitives land HERE (add --all)
│   ├── hooks/
│   ├── lib/utils.ts
│   └── styles/globals.css   # @theme inline + DESIGN.md token vars live HERE
└── package.json             # name "@workspace/ui" (or "@<slug>/ui")
```

Scaffold it with the monorepo flow (verify flags against `pnpm dlx shadcn@latest init --help`):

```bash
# from the monorepo root — uses the next-monorepo template
pnpm dlx shadcn@latest init --monorepo --base <radix|base> -d
# then add primitives FROM apps/web; the CLI routes them into packages/ui
cd apps/web && pnpm dlx shadcn@latest add --all --yes
```

Rules specific to this branch:
- **Both** `components.json` files must share identical `style`, `iconLibrary`, `baseColor`. For Tailwind v4, leave the `tailwind.config` empty in `components.json`.
- DESIGN.md tokens (the `@theme inline {}` + `:root`/`.dark` vars) go in **`packages/ui/src/styles/globals.css`**, which `apps/web/app/globals.css` imports. Don't duplicate the palette in the app.
- Imports become `import { Button } from "@workspace/ui/components/button"` (not `@/components/ui/button`).
- The web app's `next.config` must `transpilePackages: ["@workspace/ui"]` (or the `@<slug>/ui` name).
- The "library primitive priority" and folder-convention rules below still apply; just read primitives from `@workspace/ui/components/*` instead of `components/ui/*`.

### Helpers — single source of truth (mandatory)

Generic helpers (`cn`, hooks like `use-mobile`, DOM/React utilities) live in **exactly one
place** and every consumer imports from there — never copy an implementation into an app:

- **Monorepo (`packages/ui`)**: `@workspace/ui/lib/utils` (`cn`) and `@workspace/ui/src/hooks/*`.
  The `components.json` aliases already point there; `shadcn add` may still drop a hook into
  `apps/web/hooks/` (CLI quirk) — if the same hook exists in `packages/ui/src/hooks/`, the
  app-side copy is dead code: delete it.
- **Single app**: `lib/utils.ts` (`cn`) + `hooks/` — the shadcn defaults.
- **App-specific utilities** (formatters, domain helpers, slugify…) stay in the app's
  `lib/utils.ts` or a domain module — they are NOT generic helpers and don't move.

> ⚠ **`@shadcn/helpers` is NOT a generic-utils package.** The npm package `@shadcn/helpers`
> (official, shadcn, published 2026-07) exports ONLY AI-chat mock builders — `createChat`
> from `@shadcn/helpers/ai-sdk` and `@shadcn/helpers/tanstack-ai` (scripted user/assistant
> turns, simulated reasoning/tool calls/streaming with `sleep`). Use it to prototype chat
> UIs or build showcase demos **before a real backend exists**. It does NOT export `cn`,
> `composeRefs`, `useControllableState` or any DOM/React utility — never "migrate" generic
> helpers to it, and never install it for that purpose. Verify with `npm view @shadcn/helpers`
> if in doubt (the package is young; its surface may grow).

### About the `init` and `add` commands

The CLI changed in 2024-2025. **There is no `--base-color`, `--style`, or interactive "Style: New York / Default" prompt anymore.** Current flags:

- `init --defaults` — equivalent to `--template=next --preset=base-nova`. Use for new projects.
- `init --template <next|vite|react-router|laravel|astro|start>` — pick framework explicitly.
- `init --base <radix|base>` — choose the underlying primitive library. Default `base` (uses `@base-ui/react`).
- `init --no-monorepo` — skip the monorepo prompt. **Single-app projects only.** In a `stack.framework == "monorepo"` project use `--monorepo` instead (see the "Monorepo (shared `packages/ui`)" section above) — `--no-monorepo` there produces the non-canonical layout that dumps primitives into `apps/web/components/ui/`.
- `init --css-variables` / `--no-css-variables` — opt in/out of CSS variable theming. Default: yes.
- `add --all --yes` — install every component non-interactively. **This is the default in this skill** because the workflow is "customize all primitives per DESIGN.md".

`init` writes `components.json` at the project root — the anchor file `add` reads on every invocation. Don't rename or move it.

Standard dependencies installed by `init`: `clsx`, `tailwind-merge`, `class-variance-authority`, `lucide-react`, `tw-animate-css`, plus `@base-ui/react` (or `@radix-ui/react-*` if `--base radix` was chosen) packages added per-component. In theme-only mode (no `init` run), you can assume these are present if `package.json` lists them; if not, document the gap in `STYLE_NOTES.md`.

### Token-first install via `registry.json` (recommended for DESIGN.md projects)

shadcn's CLI accepts a **registry URL or local file path** as input to `init`. A registry is a JSON file that declares CSS variables, theme colors, dependencies, and (optionally) component recipes. When the user has a DESIGN.md, **emit a `registry.json` first**, then point `init` at it. This is more declarative, idempotent, and reproducible than running `init` and patching `globals.css` afterward.

**Three-step flow (use this in dev-flow mode for shadcn):**

The codebase lives at the **project root** (alongside `.workflow/`, NOT inside it). All commands run from the project root.

```bash
# 0. cd into the project root (where .workflow/ already exists)
cd <project-root>

# 1. Scaffold framework into the current directory (the project root).
#    `.` as the target means "scaffold here, alongside .workflow/".
pnpm create next-app@latest . --typescript --tailwind --eslint --app --no-src-dir --import-alias "@/*" --use-pnpm --turbopack --yes

# 2. Generate registry.json from DESIGN.md tokens (skill writes this file at the root).
python3 scripts/build_registry.py <project-root>
#    → <project-root>/registry.json

# 3. shadcn init using our registry (applies tokens) + add --all (installs every primitive)
pnpm dlx shadcn@latest init ./registry.json --yes
pnpm dlx shadcn@latest add --all --yes
```

**Important — `pnpm create next-app .` and `.workflow/`**: the Next.js scaffolder is happy to scaffold into a non-empty directory as long as the existing files don't clash with what it wants to write (`package.json`, `app/`, etc.). `.workflow/` is unknown to Next so it's left alone. If your scaffolder version refuses (rare), the workaround is: scaffold to a temp dir, then `mv temp/* temp/.* <project-root>/` (taking care not to overwrite `.workflow/`).

**`add --all` STAYS — the registry replaces only the *theme* portion of `init`, not component installation.** All primitives still land in `components/ui/*` and get customized per DESIGN.md `components` block in the customization step (`cva` blocks).

#### `registry.json` schema (the subset we use)

shadcn's full registry schema is at https://ui.shadcn.com/schema/registry.json. We write a `registry:style` item that carries the theme:

```json
{
  "$schema": "https://ui.shadcn.com/schema/registry.json",
  "name": "<project-slug>-design-system",
  "homepage": "<optional>",
  "items": [
    {
      "name": "design-system",
      "type": "registry:style",
      "cssVars": {
        "theme": {
          "font-display": "var(--font-display)",
          "font-body": "var(--font-body)",
          "radius": "0.5rem"
        },
        "light": {
          "background": "0 0% 100%",
          "foreground": "240 10% 3.9%",
          "primary": "55 98% 64%",
          "primary-foreground": "60 80% 8%",
          "secondary": "215 80% 53%",
          "muted": "240 5% 96%",
          "muted-foreground": "240 4% 46%",
          "border": "240 6% 90%",
          "ring": "55 98% 64%",
          "...": "..."
        },
        "dark": {
          "background": "240 10% 4%",
          "foreground": "0 0% 98%",
          "...": "..."
        }
      },
      "tailwind": {
        "config": {
          "theme": {
            "extend": {
              "borderRadius": {
                "lg": "var(--radius)",
                "md": "calc(var(--radius) - 2px)",
                "sm": "calc(var(--radius) - 4px)"
              },
              "fontFamily": {
                "display": ["var(--font-display)", "serif"],
                "body": ["var(--font-body)", "sans-serif"]
              }
            }
          }
        }
      }
    }
  ]
}
```

#### Mapping DESIGN.md → registry.json

| DESIGN.md frontmatter | registry.json target |
|---|---|
| `colors.<name>: "#hex"` | `cssVars.light.<name>: "<H S% L%>"` (HSL channels, no `hsl()` wrapper — that's how shadcn cssVars work) and an inverted derivation for `cssVars.dark.<name>` (see SKILL.md "Dark + light" section) |
| `typography.<level>.fontFamily: "Inter"` | `cssVars.theme.font-<level>: "var(--font-<level>)"` plus a `tailwind.config.theme.extend.fontFamily.<level>` entry |
| `typography.<level>.fontSize` etc. | applied later in the per-component `cva` step or in `globals.css` extra rules — registry.json's primary job is the color/font-family/radius layer |
| `rounded.<level>: "<dim>"` | `cssVars.theme.radius` (use the `md` value as canonical) plus `tailwind.config.theme.extend.borderRadius` derivations |
| `spacing.<level>: "<dim>"` | tailwind config `theme.extend.spacing.<level>` |
| `components.<name>.<prop>: "{ref}"` | not in registry.json — applied as a `cva` `variants` edit in `components/ui/<name>.tsx` after `add --all` (the customization step) |

**Rule of thumb**: registry.json carries the *theme atoms* (colors, fonts, radii, spacing). The per-component customization (Button variants, Card surfaces, Input states) is **not** baked into the registry — it's a follow-up edit on the source files installed by `add --all`. This separation keeps the registry small, reusable, and aligned with shadcn's own opinions.

#### Generating registry.json — script

There's a helper in `scripts/build_registry.py`. It reads `<root>/.workflow/DESIGN.md`, parses the YAML frontmatter, and writes `<root>/registry.json`. Use it instead of hand-writing the JSON. If a DESIGN.md token has no clean shadcn equivalent (e.g., a custom `surface-tint` not in the standard scale), preserve it under `cssVars.light` / `cssVars.dark` anyway — shadcn passes through unknown CSS variable names without errors.

#### Why this matters

Without the registry approach: skill runs `init` (writes neutral defaults), then patches `globals.css` to overwrite. Two writes, one of which is "fix what `init` just did". Fragile, hard to re-run.

With the registry approach: skill writes one declarative file, `init` reads it once. Re-running the skill (e.g., after the user edits DESIGN.md) regenerates the registry and re-runs `init` cleanly — no editing, no merging.

### About the modern Button component

shadcn's current Button uses `@base-ui/react/button` (not `@radix-ui/react-slot`). The `cva` shape is similar but the size names changed:

```tsx
import { Button as ButtonPrimitive } from "@base-ui/react/button"
import { cva, type VariantProps } from "class-variance-authority"

const buttonVariants = cva(
  "group/button inline-flex shrink-0 items-center justify-center …",
  {
    variants: {
      variant: { default: "…", outline: "…", secondary: "…", ghost: "…", destructive: "…", link: "…" },
      size:    { default: "h-8 …", xs: "h-6 …", sm: "h-7 …", lg: "h-9 …", icon: "size-8", "icon-xs": "…", "icon-sm": "…", "icon-lg": "…" },
    },
  }
)
```

When customizing, **read the file shadcn just wrote** — copy its existing structure and edit only the variant strings to match the DESIGN.md `components` block. Don't replace the file with a simpler Radix-era stub.

### Install all primitives

`add --all --yes` is part of the standard setup commands above. The reason is intentional: this skill's job is to customize the entire kit per DESIGN.md, not to pick components à la carte. Even if the DESIGN.md only names a handful of components in §4, the user will compose the app from the full kit (button, card, input, dialog, dropdown-menu, table, sheet, tabs, toast, form, command, calendar, popover, tooltip, accordion, alert-dialog, separator, avatar, label, etc.), so everything must be present and themed.

The DESIGN.md `components` block (or its prose equivalent) then drives **per-variant overrides** (see §Components below) — you decide which variants of which already-installed components to customize.

## Color tokens → CSS variables (dark + light)

### Color value format

**Hex literals are the path of least resistance.** Tailwind v4 + the modern shadcn init both accept any CSS color format in custom properties — hex, rgb, hsl, oklch — and the `@theme inline {}` block exposes them through `var(--X)` references regardless of the underlying format. Read the file shadcn just wrote and match its convention:

- **Current shadcn (post-2024) writes OKLCH** for the base palette (e.g. `--primary: oklch(0.205 0 0)`). It's the modern P3-aware default. If you keep OKLCH, copy the format.
- **Earlier shadcn (and most existing repos) used HSL channel triplets** (e.g. `--primary: 49 100% 94%`) so opacity modifiers like `bg-primary/80` worked. If the existing repo uses this format, stay with it.
- **Hex (e.g. `--primary: #ff385c`) works too in v4** and is the most readable when the DESIGN.md gives you raw hex values directly. This is the recommended format when the spec lists hexes literally and you want one-to-one traceability.

Don't mix formats within a single file. **Read the existing `globals.css` and use what's there.** If you're rewriting from a literal-hex DESIGN.md, hex is fine — Tailwind v4's `bg-primary/80` opacity modifier works on hex variables when they're declared without a wrapper (`--primary: #ff385c`, then `var(--primary)` is colorspace-aware).

### Dark + light modes

**Generate both modes by default**, but **respect explicit single-mode declarations.** If the DESIGN.md says (in prose, in §Known Gaps, or anywhere): "no dark mode", "single light-mode theme only", "dark mode out of scope", "this is a light-only design" — **don't auto-derive the opposite mode**. Skip the `.dark` block entirely, omit `prefers-color-scheme`, and document the choice in `_design-md-mapping.json` and `STYLE_NOTES.md`. Forcing a mode the spec rejects is worse than missing one the spec wants.

For specs that don't make this declaration, generate both:

- Canonical mode = light → write tokens directly under `:root`, derive dark under `.dark`.
- Canonical mode = dark → write the **derived** light values under `:root` (so the default mode is still light unless the user opts into dark), and the canonical dark values under `.dark`. Add a hint in `STYLE_NOTES.md` explaining that dark is the source of truth.

### Where the variables live (Tailwind v4 + modern shadcn)

**`init` already wrote `globals.css` with the structure you need — extend it, don't replace it.** The file looks like this after `init`:

```css
@import "tailwindcss";
@import "tw-animate-css";
@import "shadcn/tailwind.css";

@custom-variant dark (&:is(.dark *));

@theme inline {
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --color-primary: var(--primary);
  /* …shadcn semantics… */
}

:root {
  --background: oklch(1 0 0);
  --foreground: oklch(0.145 0 0);
  /* …neutral defaults… */
}

.dark {
  /* …inverted neutrals… */
}
```

Your job is to:

1. Inside the existing `@theme inline {}` block, **add named entries for every DESIGN.md custom color** so they become Tailwind utilities (`bg-rausch`, `text-ink-black`, etc.):
   ```css
   @theme inline {
     /* keep all the shadcn semantic mappings the init wrote */
     --color-background: var(--background);
     --color-foreground: var(--foreground);
     /* …existing… */

     /* add: one entry per custom DESIGN.md token */
     --color-rausch: var(--rausch);
     --color-ink-black: var(--ink-black);
     --color-ash-gray: var(--ash-gray);
     /* … */
   }
   ```
2. Inside `:root`, **replace the neutral defaults with DESIGN.md values** AND **add the raw color variables** for the custom names:
   ```css
   :root {
     /* DESIGN.md raw values */
     --rausch: #ff385c;
     --ink-black: #222222;
     --ash-gray: #6a6a6a;
     /* … */

     /* shadcn semantic mapping (point at the raw values) */
     --background: var(--canvas-white);
     --foreground: var(--ink-black);
     --primary: var(--rausch);
     --primary-foreground: var(--canvas-white);
     /* … */
   }
   ```
3. If both modes are needed, repeat the mapping inside `.dark` with appropriate inverts. If single-mode only, **delete the `.dark` block** the init wrote.

This is the v4 way. There's no separate `tailwind.config.ts`. Don't try to add one — Tailwind v4 ignores it unless you opt in via `@config`.

### Tailwind v3 legacy notes

If integrating into an existing Tailwind v3 project (check `package.json` for `tailwindcss` version starting with `3`), the convention is different:
- Variables go in `:root` / `.dark` in `globals.css` using HSL channel triplets (`H S% L%`, no wrapper).
- Tailwind reads them via `extend.colors` in `tailwind.config.ts` using `hsl(var(--X) / <alpha-value>)`.
- The `<alpha-value>` placeholder is required for opacity modifiers to work.

In this case, write the colors as HSL triplets, keep the `tailwind.config.ts` extend block, and don't try to migrate the project to v4 unless the user explicitly asks.

### Derivation rule for the non-canonical mode

- For surfaces (`background`, `card`, `popover`, `muted`): invert the L channel within the same H/S family. A 9% L surface becomes a 96% L surface; a 14% L muted becomes an 88% L muted. Keep the relative ladder intact.
- For `foreground` / `*-foreground`: invert L symmetrically so contrast is preserved.
- For brand colors (`primary`, `secondary`, `accent`, `destructive`, `ring`): keep them. Only adjust their `*-foreground` if the inverted contrast demands it.
- For `border` / `input`: shift L towards the opposite mode's neutral (e.g. dark border at 22% → light border at 90%).

```css
:root {
  /* Auto-derived light values (canonical mode = dark in DESIGN.md) */
  --background: 230 9% 96%;
  --foreground: 240 6% 12%;
  --primary: 49 100% 94%;
  --primary-foreground: 47 100% 11%;
  --secondary: 191 100% 87%;
  --secondary-foreground: 191 100% 12%;
  --card: 232 9% 12%;
  --card-foreground: 240 6% 90%;
  --muted: 232 9% 14%;
  --muted-foreground: 240 6% 65%;
  --accent: 191 100% 50%;
  --accent-foreground: 191 100% 12%;
  --destructive: 4 100% 84%;
  --destructive-foreground: 358 100% 21%;
  --border: 234 6% 22%;
  --input: 234 6% 22%;
  --ring: 49 100% 50%;
  --radius: 0.5rem;
}

.dark {
  /* Canonical mode from DESIGN.md (e.g. dark) */
  --background: 230 9% 9%;
  --foreground: 240 6% 90%;
  --primary: 49 100% 94%;
  --primary-foreground: 47 100% 11%;
  --secondary: 191 100% 87%;
  --secondary-foreground: 191 100% 12%;
  --card: 232 9% 12%;
  --card-foreground: 240 6% 90%;
  --muted: 232 9% 14%;
  --muted-foreground: 240 6% 65%;
  --accent: 191 100% 50%;
  --accent-foreground: 191 100% 12%;
  --destructive: 4 100% 84%;
  --destructive-foreground: 358 100% 21%;
  --border: 234 6% 22%;
  --input: 234 6% 22%;
  --ring: 49 100% 50%;
  --radius: 0.5rem;
}
```

Wire the toggle: in Next.js use `next-themes` (`<ThemeProvider attribute="class" defaultTheme="dark">` if dark is canonical), in Vite/Remix use a small custom hook that toggles `.dark` on `<html>` based on `localStorage` + `prefers-color-scheme`. shadcn's docs show both patterns.

Mapping rule of thumb (DESIGN.md → shadcn semantic names):

| design.md token             | shadcn variable                       |
|-----------------------------|---------------------------------------|
| `colors.background`         | `--background`                        |
| `colors.surface`            | `--background` (if no separate bg)    |
| `colors.on-surface`         | `--foreground`                        |
| `colors.surface-container`  | `--card`, `--popover`                 |
| `colors.on-surface-variant` | `--muted-foreground`                  |
| `colors.primary`            | `--primary`                           |
| `colors.on-primary`         | `--primary-foreground`                |
| `colors.secondary`          | `--secondary`                         |
| `colors.on-secondary`       | `--secondary-foreground`              |
| `colors.tertiary`           | `--accent`                            |
| `colors.on-tertiary`        | `--accent-foreground`                 |
| `colors.error`              | `--destructive`                       |
| `colors.on-error`           | `--destructive-foreground`            |
| `colors.outline`            | `--border`, `--input`                 |
| `colors.surface-tint`       | `--ring`                              |

For tokens that don't have a clean semantic counterpart (e.g. `primary-fixed`, `secondary-container`, custom names), add **extra variables** in `:root` and reference them via Tailwind's `extend.colors` so they remain usable:

```js
// tailwind.config.ts (excerpt)
extend: {
  colors: {
    "primary-container": "hsl(var(--primary-container) / <alpha-value>)",
    "on-primary-container": "hsl(var(--on-primary-container) / <alpha-value>)",
    // ...
  },
}
```

### Handling Material 3-style token sets

When the DESIGN.md uses the full Material 3 palette (you'll spot it from the long list of `surface-container-lowest/low/.../highest`, `*-fixed`, `*-fixed-dim`, `inverse-*`, `outline-variant` etc.), the spec is going to define 40-50 colors instead of shadcn's ~14 semantics. **Expose every extra token as its own named Tailwind color** pointing at a CSS variable — don't try to fold them into the closest shadcn semantic.

The reasoning: the user will want to write `bg-tertiary-container` or `text-on-surface-variant` directly on their components. Shadcn's 14 semantics are only for the primitives that ship with the library — they're not a "complete palette," they're "the names shadcn's own components read." Everything outside that set is the user's API surface and must be named clearly.

So for a M3-style DESIGN.md, the workflow is:

1. Map the 14 shadcn semantics from the table above (so the stock `Button`, `Card` etc. look right).
2. Then write **one CSS variable + one Tailwind color entry per remaining DESIGN.md color**, keeping the original kebab-case names. Don't drop, don't merge.

### Sanity checks before declaring colors done

Run these checks after writing the variables. They catch the failure modes that the spec → CSS pipeline produces silently:

1. **Identical colors across different roles.** If two `colors.X` resolve to the same hex (e.g. `surface-tint: #e9c400` equals `primary-fixed-dim: #e9c400`), and they map to roles meant to be visually distinct (focus ring vs. brand highlight), flag the collision in `_design-md-mapping.json` under a `collisions` key. The user may want to nudge one of them by a few percent L for distinguishability.

2. **`tertiary` is near-white or near-black with non-default mode.** `colors.tertiary` → `--accent` is the recommended map, but shadcn primitives like `Command`, `DropdownMenu`, `Select` use `bg-accent` for hover states. If `--accent` ends up near-foreground (e.g. tertiary `#fcf3ff` in a dark theme), those hovers become invisible. Either remap to a different M3 token (`tertiary-container` is often safer for hover surfaces) or leave the shadcn semantic at its default and expose `tertiary` only as a custom Tailwind color. Document the choice in `_design-md-mapping.json` under `inferred`.

3. **`on-X` contrast is reasonable against `X`.** If the parsed `on-error` ends up *darker* than `error` in dark mode (a literal port of M3 light values into a dark spec), text on the destructive surface will be unreadable. Spot-check the worst-case pairs with a quick contrast estimate (luminance diff > 0.5 is fine; below that, flag in `STYLE_NOTES.md` so the user reviews).

These don't have to block writing the files — but they have to land in `_design-md-mapping.json` so a reviewer (human or future agent) can see what was inferred.

## Typography → @theme + font loading

For each typography level the DESIGN.md defines:

### Step 1 — Resolve which fonts to load

The DESIGN.md will list font families. Sort them into three buckets:

**A. Google Fonts** (Inter, Space Grotesk, Public Sans, Manrope, Geist, etc.):
- **Next.js**: `next/font/google` in `app/layout.tsx`. Expose as a CSS variable on `<html>`.
- **Vite**: add a `<link rel="stylesheet" href="https://fonts.googleapis.com/css2?...&display=swap">` in `index.html`, then map to a CSS variable in `src/index.css`.
- **Remix**: add the Google Fonts link via `links()` in `app/root.tsx`.

**B. System fallbacks** (`system-ui`, `ui-sans-serif`, `-apple-system`): no loading — pass through directly in the font-family chain.

**C. Custom / proprietary / non-Google fonts** (Airbnb Cereal VF, Circular Std, Söhne, F37 Glare, brand-licensed fonts): **STOP and ASK THE USER** before substituting. See "Missing font policy" below.

### Missing font policy — ASK, don't silently substitute

When the DESIGN.md specifies a custom or proprietary font that isn't a Google Font:

1. **Check the project for `.woff2` files** under `public/fonts/<family>/` or any sibling location. If present, use them via `next/font/local` (Next) or `@font-face` (Vite/Remix). Done.

2. **If no font files are found**, **explicitly ask the user** before falling back:

   > Il DESIGN.md menziona **`<Brand Font>`**, che è proprietario / non disponibile su Google Fonts. Tre opzioni:
   >
   > 1. **Hai i file `.woff2`** (e/o `.woff`, `.ttf`)? Se sì, dimmi il path o droppali in `public/fonts/<brand-font>/` e procedo.
   > 2. **Vuoi che usi il fallback documentato dal DESIGN.md** (di solito menzionato in §Typography sotto "Note on Substitutes" o simile — es. Inter per Cereal, Inter per Circular)?
   > 3. **Vuoi che suggerisca un fallback** in base al carattere (geometrico → Inter / Manrope; humanist → Source Sans 3 / Public Sans; serif → Lora / Source Serif)?
   >
   > Se procedi con un fallback, lo annoto in `STYLE_NOTES.md` come gap esplicito così l'utente potrà sostituire più tardi senza perdere il riferimento.

   Wait for the user's answer before generating any font code. Don't pick silently — the user may have the licensed file on disk, may want to hold off until they purchase, or may have a strong opinion about the substitute. Silent fallback hides the cost of the choice.

3. **When using a fallback**, document the deviation explicitly in:
   - `STYLE_NOTES.md` under "Known gaps" with a short paragraph: which font was requested, which is being used, why, and how to swap later.
   - `_design-md-mapping.json` under `fallbacks` with `{ token, fallback, reason }`.
   - Add a `.tracking-display-tight` (`-0.01em` letter-spacing) utility if the substitute is visibly looser than the original at display sizes — most geometric sans-serif substitutes are.

### Step 2 — Load only the weights the DESIGN.md declares

**Read the typography table.** If the DESIGN.md says "weights observed: 500, 600, 700. No 400-regular — body weight is 500", **load only those weights**. Don't default to `["400", "500", "600", "700"]` for safety.

```tsx
// app/layout.tsx — Next.js example
const cereal = Inter({
  variable: "--font-cereal",
  subsets: ["latin"],
  weight: ["500", "600", "700"], // exactly what DESIGN.md §3 lists
  display: "swap",
});
```

Loading every weight "just in case" doubles or triples the font payload and silently allows code to render in 400-regular when the design system explicitly forbids it. The DESIGN.md is your contract.

### Step 3 — Wire fonts in `@theme inline {}`

In `globals.css`:

```css
@theme inline {
  --font-sans:    var(--font-cereal), Inter, "ui-sans-serif", "system-ui", "-apple-system", sans-serif;
  --font-display: var(--font-cereal), Inter, "ui-sans-serif", "system-ui", sans-serif;
  --font-mono:    var(--font-geist-mono);
}
```

Tailwind v4 reads `--font-X` directly to generate `font-X` utilities. **Always include a fallback chain** so layout doesn't shift before the variable resolves.

### Step 4 — Type scale tokens

For each typography level, write a `--text-<name>` set in `@theme inline {}`. Tailwind v4 reads these to generate `text-<name>` utilities:

```css
@theme inline {
  --text-headline-xl: 72px;
  --text-headline-xl--line-height: 80px;
  --text-headline-xl--letter-spacing: -0.04em;
  --text-headline-xl--font-weight: 700;

  --text-body-md: 16px;
  --text-body-md--line-height: 24px;
  --text-body-md--font-weight: 500;
  /* …one block per DESIGN.md typography level… */
}
```

Now `<h1 className="text-headline-xl font-display">…</h1>` resolves to the full size + line-height + tracking + weight.

Keep names identical to the DESIGN.md tokens for traceability.

### Tailwind v3 legacy — type scale

If the project is v3, the equivalent goes in `tailwind.config.ts`:

```ts
extend: {
  fontFamily: {
    display: ["var(--font-display)", "Inter", "ui-sans-serif", "system-ui", "sans-serif"],
    sans:    ["var(--font-sans)",    "Inter", "ui-sans-serif", "system-ui", "sans-serif"],
  },
  fontSize: {
    "headline-xl": ["72px", { lineHeight: "80px", letterSpacing: "-0.04em", fontWeight: "700" }],
    // one entry per level
  },
}
```

## Rounded → @theme radius scale

In Tailwind v4, write radius tokens directly into `@theme inline {}`:

```css
@theme inline {
  --radius-tag:    4px;
  --radius-button: 8px;
  --radius-card:   14px;
  --radius-pill:   20px;
  --radius-search: 32px;
  --radius-circle: 9999px;

  /* If the DESIGN.md declares a shadcn-compatible scale, also set: */
  --radius: var(--radius-button); /* shadcn's components consume this */
}
```

Then `rounded-card`, `rounded-pill`, etc. work as utilities. Use the DESIGN.md's literal values — don't compute from a base unless the spec uses relative math.

### Tailwind v3 legacy — radius

```ts
extend: {
  borderRadius: {
    sm: "calc(var(--radius) - 4px)",
    DEFAULT: "var(--radius)",
    lg: "var(--radius)",
    xl: "calc(var(--radius) + 4px)",
    full: "9999px",
  },
}
```

## Spacing → @theme spacing extension

Tailwind v4's default spacing scale (4px base) is kept; **don't replace it**. Add named tokens for DESIGN.md custom values inside `@theme inline {}`:

```ts
extend: {
  spacing: {
    gutter: "24px",
    "container-max": "1280px",
    "margin-mobile": "16px",
    "margin-desktop": "64px",
  },
  maxWidth: {
    container: "var(--container-max, 1280px)",
  },
}
```

## Components → variant overrides

The `components` block describes **how a named component should look**. In shadcn, that means editing the `cva` definition in `components/ui/<name>.tsx`.

Pattern: group the spec keys per component (`button-primary`, `button-primary-hover` → `Button` `default` variant + its hover state).

Example for `button-primary` / `button-primary-hover`:

```tsx
// components/ui/button.tsx (excerpt)
const buttonVariants = cva(
  "inline-flex items-center justify-center font-display uppercase tracking-wider transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50",
  {
    variants: {
      variant: {
        default:
          "bg-primary text-primary-foreground rounded-lg hover:bg-primary-fixed",
        secondary:
          "bg-transparent text-secondary border border-secondary/40 rounded-lg hover:bg-secondary/10",
        // ...
      },
      size: {
        default: "h-12 px-3",
        // ...
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  },
);
```

Mapping rules:

- `backgroundColor` → `bg-<token>` (use the exact extend name).
- `textColor` → `text-<token>`.
- `rounded` → `rounded-<scale>`.
- `padding` → `p-[12px]` literal, or a Tailwind shorthand if it lines up with the scale.
- `height` / `width` → `h-12` / `w-…` (use arbitrary values when no scale match).
- `typography` → corresponding `text-<level> font-<family>` combo.

**When the markdown body contradicts or extends the YAML, trust the body.** The YAML is the schema-bound subset; the body is the human-readable rationale and often carries detail the spec can't express. Examples: the YAML says `button-secondary: { backgroundColor: transparent }` with no `borderColor`, but the body says "secondary buttons remain ethereal with a cyan outline" — add the border. Body says "subtle text-shadow glow on headline-xl on dark backgrounds", spec doesn't have a `textShadow` field — encode it as a `.headline-glow` utility. In every such inference, write it down in `_design-md-mapping.json` under `inferred` so the next reader knows it wasn't in the YAML.

If the DESIGN.md component name has no obvious shadcn counterpart (e.g. `card-glass-level-2`, `badge-celestial`, `hero-headline`), don't force-fit. Instead:

- Add a new variant to the closest shadcn component (e.g. `Card` gets a `glass` variant).
- If it's purely decorative (hero headline, custom badge), create `components/styled/<name>.tsx` as a thin wrapper component the user can import.

## Markdown body → STYLE_NOTES.md + Tailwind plugins

Many qualitative rules in the body don't map to tokens. Translate them as follows:

| Body says…                                   | Encoding                                                              |
|----------------------------------------------|-----------------------------------------------------------------------|
| "Use radial gradients for hero backgrounds"  | Add `.bg-hero-radial` utility in `globals.css` `@layer utilities`.    |
| "Glassmorphism: 20px blur, 1px inner stroke" | Add `.glass` utility (`backdrop-blur-xl bg-white/5 border-white/10`). |
| "Ambient glow on hover"                      | Add `.glow-primary` utility with `box-shadow: 0 0 24px hsl(var(--primary)/0.6)`. |
| "Tight letter spacing on monumental headers" | Already encoded in `fontSize` `letterSpacing` if the spec defined it. Otherwise note in STYLE_NOTES. |
| "Do/Don't" rules                             | Verbatim into `STYLE_NOTES.md`. |

Always create `STYLE_NOTES.md` at the project root with:
- a one-paragraph summary of the brand (from Overview),
- the verbatim Do's and Don'ts,
- any rules that couldn't be encoded mechanically,
- a link back to `DESIGN.md` as the source of truth.

## Showcase page

Generate `app/showcase/page.tsx` (or `src/app/showcase/page.tsx`). Render:

1. A grid of color swatches (one per `colors.*`).
2. A typography ladder (one paragraph per `typography.*` level showing the actual font + size + leading).
3. Every defined `components.*` rendered in its real Tailwind classes — both base and hover states (you can use `:hover` group classes or a "hovered" state flag for the static page).
4. The radius scale and the spacing tokens visualized as boxes.

Keep it visual, no business logic. This is the verification surface.

## Sanity checklist before declaring done

- `pnpm dev` runs without errors.
- `/showcase` renders.
- A spot check of 3 colors and 2 typography levels matches the DESIGN.md visually (use a color picker on the screenshot if uncertain).
- Buttons defined in the spec have the right hover state.
- `STYLE_NOTES.md` is present and references `DESIGN.md`.
