# Reconciling Coss/UI tokens with DESIGN.md

The single fact that makes Coss slot into dev-flow cleanly: **Coss's design tokens are CSS variables with the same names as shadcn/ui**, implemented with Tailwind and overridable in the global stylesheet. So the DESIGN.md → tokens pipeline that `design-md-to-app` already runs works unchanged — Coss just provides the **default** values, and DESIGN.md **overrides** them.

## The rule

**Override Coss's token *values*; never fork its token *structure*.** Coss ships `@coss/colors-neutral` (a neutral CSS-variable palette using the shadcn variable names: `--background`, `--foreground`, `--primary`, `--radius`, sidebar vars, etc.). DESIGN.md defines the project's real palette/typography/radius. Reconciliation = writing the DESIGN.md-resolved values into the **same variables** in `globals.css`, for both `:root` (light) and `.dark`.

## How it maps to `design-md-to-app`

`design-md-to-app` already has a **token-first install via `registry.json`**: it emits a `registry.json` from DESIGN.md tokens (`scripts/build_registry.py`) and runs `shadcn init ./registry.json`. With Coss:

1. Install Coss first (`init @coss/style` or `add @coss/style`) so the neutral tokens + components land.
2. Then apply the DESIGN.md overrides. Two equivalent routes:
   - **registry.json route** (preferred when a DESIGN.md exists): let `design-md-to-app` emit `registry.json` from the DESIGN.md tokens and install it *after* Coss, so its `cssVars.light` / `cssVars.dark` overwrite Coss's neutral defaults on the same variable names.
   - **direct globals.css route** (theme-only): edit `globals.css` in place, replacing the values of the Coss-provided variables with the DESIGN.md-resolved ones. Keep both light and dark blocks.
3. Do **not** rename or restructure the variables — Coss components read the shadcn variable names, so keeping the names is what makes the override transparent.

## Fonts

`init @coss/style` installs Inter + Geist Mono by default. If DESIGN.md declares a `typography.fontFamily`, override the font wiring the same way `design-md-to-app` does (`next/font/google` on Next) — the Coss defaults are just a starting point.

## Dark / light

Coss ships both modes (neutral). Keep the dark/light toggle from `design-md-to-app`'s mandatory theme-toggle step; the DESIGN.md canonical mode drives one block and the other is derived. Because the variable names are shared, the existing `ThemeProvider` (`next-themes`, `attribute="class"`) toggles Coss components with no extra work.

## When there is no DESIGN.md

Ship Coss's neutral tokens as-is and note it in the hand-off — the user can add a DESIGN.md later and re-reconcile. Don't invent a palette.
