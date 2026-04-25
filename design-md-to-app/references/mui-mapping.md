# DESIGN.md → MUI (Material UI) mapping

MUI is a runtime themed library: a single `createTheme()` object drives every primitive. The whole app sits inside `<ThemeProvider>` + `<CssBaseline>`. Customization happens in three places:

1. `palette` — colors.
2. `typography` — type scale.
3. `shape` + `spacing` + `breakpoints` — layout primitives.
4. `components.MuiXxx.styleOverrides` / `defaultProps` / `variants` — component-level look.

There's no source-edit equivalent of shadcn — you don't own the components, you theme them.

## Project setup

MUI is a runtime library — installation is the same across frameworks, only the provider wiring differs.

### Next.js (App Router) — default

```bash
pnpm create next-app@latest <dir> --ts --eslint --app --src-dir --import-alias "@/*"
cd <dir>
pnpm add @mui/material @emotion/react @emotion/styled @mui/icons-material
pnpm add @mui/material-nextjs   # for AppRouterCacheProvider (SSR-safe Emotion)
```

`app/layout.tsx`:

```tsx
import { AppRouterCacheProvider } from "@mui/material-nextjs/v15-appRouter";
import { ThemeProvider, CssBaseline } from "@mui/material";
import { theme } from "@/lib/theme";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${displayFont.variable} ${bodyFont.variable}`}>
      <body>
        <AppRouterCacheProvider>
          <ThemeProvider theme={theme}>
            <CssBaseline />
            {children}
          </ThemeProvider>
        </AppRouterCacheProvider>
      </body>
    </html>
  );
}
```

### Vite + React

```bash
pnpm create vite@latest <dir> -- --template react-ts
cd <dir>
pnpm install
pnpm add @mui/material @emotion/react @emotion/styled @mui/icons-material
```

Wrap the root in `src/main.tsx`:

```tsx
import { ThemeProvider, CssBaseline } from "@mui/material";
import { theme } from "./lib/theme";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <App />
    </ThemeProvider>
  </StrictMode>,
);
```

No SSR cache provider needed (Vite is client-rendered by default).

### Remix

```bash
pnpm create remix@latest <dir>
cd <dir>
pnpm add @mui/material @emotion/react @emotion/styled @mui/icons-material
```

Remix is SSR. Use the Emotion server pattern: install `@emotion/server`, create a custom `entry.server.tsx` and `entry.client.tsx` per the MUI Remix integration guide, then wrap `<Outlet />` in `app/root.tsx` with `<ThemeProvider>` + `<CssBaseline>`. Note this in `STYLE_NOTES.md` because it's the most invasive setup of the three.

### Theme module

The theme goes in `lib/theme.ts` (Next/Vite) or `app/lib/theme.ts` (Remix). It must be `"use client"` in Next when imported by a server component graph — easiest is to make `theme.ts` itself a `"use client"` module since it depends on `createTheme`.

## Dark + light always

MUI gives you `palette.mode` plus `useColorScheme()` (CssVarsProvider) to support both modes. Always wire both:

1. Build the canonical theme from the DESIGN.md (most often `mode: "dark"`).
2. Build a light counterpart by inverting the L channel in surface families and keeping brand colors stable (see SKILL.md §Dark + light for the derivation rule).
3. Use `extendTheme` from `@mui/material/styles` so the consumer can pick:

```ts
import { experimental_extendTheme as extendTheme, CssVarsProvider } from "@mui/material/styles";

export const theme = extendTheme({
  colorSchemes: {
    light: { palette: { /* derived light values */ } },
    dark:  { palette: { /* canonical dark values from DESIGN.md */ } },
  },
  // typography / shape / spacing / radius / layout / components live OUTSIDE colorSchemes
  // (they're shared across both modes)
});
```

Wrap the app in `<CssVarsProvider theme={theme} defaultMode="dark">` (or `"light"` based on which is canonical) instead of `<ThemeProvider>`. Everything else (`<CssBaseline>`, the `theme.components` overrides, `useTheme()`) keeps working. The user gets `useColorScheme()` for free to flip modes at runtime.

If `extendTheme` feels heavy for the project, fall back to two `createTheme` calls picked by a tiny context — but `CssVarsProvider` is the modern way and it's worth defaulting to it.

## Font loading

`typography.fontFamily` values fall into three buckets:

1. **Google Fonts**:
   - **Next.js**: `next/font/google` in `app/layout.tsx`, expose CSS vars, reference them in `theme.typography.fontFamily` strings.
   - **Vite**: add `<link>` to Google Fonts in `index.html`, set `theme.typography.fontFamily` to the literal string `"Space Grotesk", "Inter", system-ui, sans-serif`.
   - **Remix**: serve the Google Fonts `<link>` via the `links()` export in `app/root.tsx`.

2. **System fallbacks**: pass through directly in `theme.typography.fontFamily` strings.

3. **Custom / non-Google fonts**: self-host. Drop `woff2` files in `public/fonts/<family>/`, declare `@font-face` in a global CSS module imported once at the root (Next: `app/globals.css`; Vite: `src/index.css`; Remix: `app/tailwind.css` or any imported CSS), then reference the family name in `theme.typography.fontFamily`. For Next, `next/font/local` is preferable when feasible.

   If the font file isn't yet on disk, **don't** silently substitute — note the gap in `STYLE_NOTES.md` and fall back to a Google font that approximates the brand.

Always declare a fallback chain in `theme.typography.fontFamily` so layout doesn't shift before the font loads:

```ts
typography: {
  fontFamily: '"Inter", "ui-sans-serif", "system-ui", "-apple-system", "sans-serif"',
  h1: { fontFamily: '"Space Grotesk", "Inter", "ui-sans-serif", "system-ui", "sans-serif"', /* … */ },
}
```

## Color tokens → palette

MUI's palette has fixed buckets: `primary`, `secondary`, `error`, `warning`, `info`, `success`, plus `background`, `text`, `divider`, `action`. Each bucket has `main` + optional `light`, `dark`, `contrastText`.

Mapping rule of thumb:

| design.md token             | MUI palette path                |
|-----------------------------|---------------------------------|
| `colors.primary`            | `palette.primary.main`          |
| `colors.on-primary`         | `palette.primary.contrastText`  |
| `colors.primary-container`  | `palette.primary.light`         |
| `colors.on-primary-container` | (no slot — keep as custom)    |
| `colors.secondary`          | `palette.secondary.main`        |
| `colors.on-secondary`       | `palette.secondary.contrastText`|
| `colors.tertiary`           | `palette.info.main` *or* extend |
| `colors.error`              | `palette.error.main`            |
| `colors.on-error`           | `palette.error.contrastText`    |
| `colors.background`         | `palette.background.default`    |
| `colors.surface`            | `palette.background.paper`      |
| `colors.on-surface`         | `palette.text.primary`          |
| `colors.on-surface-variant` | `palette.text.secondary`        |
| `colors.outline`            | `palette.divider`               |

`tertiary` and Material-3-style tokens (`*-container`, `surface-tint`, `inverse-*`) have no native slot. **Extend the theme**:

```ts
declare module "@mui/material/styles" {
  interface Palette {
    tertiary: Palette["primary"];
    surfaceContainer: { lowest: string; low: string; default: string; high: string; highest: string };
  }
  interface PaletteOptions {
    tertiary?: PaletteOptions["primary"];
    surfaceContainer?: { lowest?: string; low?: string; default?: string; high?: string; highest?: string };
  }
}
```

Then expose the exotic tokens through these augmented buckets so component overrides can read `theme.palette.tertiary.main`, `theme.palette.surfaceContainer.high`, etc.

If the DESIGN.md is dark-themed (e.g. `colors.background` is near-black, `on-background` is near-white), set `mode: "dark"` so MUI's defaults flip correctly.

## Typography → theme.typography

Map each `typography.<level>` to MUI's nearest type slot, plus add custom variants for what doesn't fit.

| design.md level     | MUI variant     |
|---------------------|-----------------|
| `headline-xl`       | `h1`            |
| `headline-lg`       | `h2`            |
| `headline-md`       | `h3`            |
| `headline-sm`       | `h4`            |
| `title-lg`          | `h5`            |
| `title-md`          | `h6`            |
| `body-lg`           | `body1`         |
| `body-md`           | `body2`         |
| `label-lg` / `label-md` | `button` / `overline` |
| `caption`           | `caption`       |

```ts
typography: {
  fontFamily: "var(--font-body), Inter, system-ui, sans-serif",
  h1: { fontFamily: "var(--font-display)", fontSize: 72, lineHeight: "80px", letterSpacing: "-0.04em", fontWeight: 700 },
  h2: { fontFamily: "var(--font-display)", fontSize: 48, lineHeight: "56px", letterSpacing: "-0.02em", fontWeight: 600 },
  body1: { fontSize: 18, lineHeight: "28px", letterSpacing: 0, fontWeight: 400 },
  body2: { fontSize: 16, lineHeight: "24px", letterSpacing: 0, fontWeight: 400 },
  button: { fontFamily: "var(--font-display)", fontSize: 14, lineHeight: "20px", letterSpacing: "0.1em", fontWeight: 500, textTransform: "uppercase" },
}
```

Load the fonts through `next/font` in `app/layout.tsx` and pass the CSS variables into the typography `fontFamily` strings — that way SSR and theme stay aligned.

## Rounded → theme.shape + per-component overrides

`theme.shape.borderRadius` is a single number. Set it to `rounded.DEFAULT` (or `rounded.md`) in pixels. For a multi-step scale, use `theme.shape` augmented or just inline values in component overrides.

```ts
shape: { borderRadius: 8 },
```

If the DESIGN.md uses many radius levels, add an extension:

```ts
declare module "@mui/material/styles" {
  interface Theme  { radius: { sm: number; md: number; lg: number; xl: number; full: number } }
  interface ThemeOptions { radius?: { sm?: number; md?: number; lg?: number; xl?: number; full?: number } }
}
```

```ts
radius: { sm: 2, md: 6, lg: 8, xl: 12, full: 9999 },
```

## Spacing → theme.spacing

MUI uses an 8px base by default — perfect if DESIGN.md says `spacing.unit: 8px`. If different, override:

```ts
spacing: 4,   // 4px base
```

Custom named spacing (e.g. `gutter`, `container-max`) doesn't fit in `theme.spacing` (which is a function returning multiples). Put them on a custom `theme.layout` extension:

```ts
declare module "@mui/material/styles" {
  interface Theme  { layout: { containerMax: number; gutter: number; marginMobile: number; marginDesktop: number } }
  interface ThemeOptions { layout?: { containerMax?: number; gutter?: number; marginMobile?: number; marginDesktop?: number } }
}
```

## Components → components overrides

For each entry in the DESIGN.md `components` block, find the nearest MUI component and override its `styleOverrides` (and optionally `defaultProps` / `variants`).

Mapping:

| design.md component name pattern | MUI component        |
|----------------------------------|----------------------|
| `button-primary` (default)       | `MuiButton` `contained` |
| `button-secondary`               | `MuiButton` `outlined` (or `text`) |
| `input-field`                    | `MuiTextField` / `MuiInputBase` |
| `card-*` / `card-glass-*`        | `MuiCard` / `MuiPaper` |
| `chip-*` / `badge-*`             | `MuiChip`            |
| `list-item-*`                    | `MuiListItem` / `MuiMenuItem` |
| `dialog-*`                       | `MuiDialog`          |
| `nav-*`                          | `MuiAppBar` / `MuiTabs` |

Pattern: group sibling spec keys (`button-primary`, `button-primary-hover`) into one MUI override.

```ts
components: {
  MuiButton: {
    defaultProps: { disableElevation: true, variant: "contained" },
    styleOverrides: {
      root: ({ theme }) => ({
        height: 48,
        padding: "0 12px",
        borderRadius: theme.radius.lg,
        fontFamily: "var(--font-display)",
        fontSize: 14,
        letterSpacing: "0.1em",
        textTransform: "uppercase",
      }),
      contained: ({ theme }) => ({
        backgroundColor: theme.palette.primary.main,
        color: theme.palette.primary.contrastText,
        "&:hover": {
          backgroundColor: theme.palette.primary.light, // primary-fixed
        },
      }),
      outlined: ({ theme }) => ({
        backgroundColor: "transparent",
        color: theme.palette.secondary.main,
        borderColor: theme.palette.secondary.main,
        "&:hover": {
          backgroundColor: alpha(theme.palette.secondary.main, 0.1),
        },
      }),
    },
  },
  MuiCard: {
    styleOverrides: {
      root: ({ theme }) => ({
        backgroundColor: alpha(theme.palette.background.paper, 0.2),
        backdropFilter: "blur(20px)",
        border: `1px solid ${alpha("#fff", 0.1)}`,
        borderRadius: theme.radius.xl,
        padding: theme.layout.gutter,
      }),
    },
  },
  // ... continue for every grouping defined in DESIGN.md
}
```

For variants the spec invents (e.g. `card-glass-level-2`, `badge-celestial`), use MUI's `variants` array:

```ts
MuiCard: {
  variants: [
    {
      props: { variant: "glass" as any },
      style: ({ theme }) => ({ /* ... */ }),
    },
  ],
}
```

…and augment the prop types so TS accepts the new variant string.

## Markdown body → STYLE_NOTES.md + sx helpers

Same idea as the shadcn flow:

| Body says…                                   | Encoding                                                              |
|----------------------------------------------|-----------------------------------------------------------------------|
| "Use radial gradients for hero backgrounds"  | Export an `sx` helper / `<HeroBackground/>` component using `background-image`. |
| "Glassmorphism: 20px blur, 1px inner stroke" | Encode in `MuiCard` / a custom `<GlassPanel/>` MUI component.         |
| "Ambient glow on hover"                      | `boxShadow` in component override `&:hover`.                          |
| Do/Don't rules                               | Verbatim into `STYLE_NOTES.md`.                                       |

Always create `STYLE_NOTES.md` (same content rules as the shadcn flow).

## Showcase page

Generate `app/showcase/page.tsx`. Render:

1. A grid of `<Box>` swatches for every `palette.*` (and the augmented buckets).
2. `<Typography variant="h1">` … `<Typography variant="caption">` ladder for every variant.
3. `<Button variant="contained">` / `outlined` / `text`, plus any custom `variants`.
4. `<Card>`, `<TextField>`, `<Chip>`, `<Dialog trigger>`, `<MenuItem>` for whatever else the DESIGN.md defined.
5. A radius and spacing visualization (boxes with `borderRadius={theme.radius.X}`, `p={theme.layout.X}`).

Mark it `"use client"` if it uses any state for hover demos; otherwise it can stay server.

## Sanity checklist before declaring done

- `pnpm dev` runs.
- `/showcase` renders.
- Type-check passes (`tsc --noEmit`) — palette/theme augmentations are a common source of TS errors here.
- A spot check of 3 colors, 2 typography levels, and the primary button hover matches the DESIGN.md visually.
- `STYLE_NOTES.md` is present.
