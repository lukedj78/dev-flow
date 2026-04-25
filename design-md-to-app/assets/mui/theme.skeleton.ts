// Skeleton for lib/theme.ts after DESIGN.md → MUI mapping.
// Replace placeholders with values derived from DESIGN.md tokens.
// Drop any augmentations the DESIGN.md doesn't justify.
"use client";

import { createTheme, alpha, Theme, ThemeOptions } from "@mui/material/styles";

// ---------------------------------------------------------------------------
// Module augmentations — extend MUI's typed theme with custom tokens that
// don't have a native slot. Add only what the DESIGN.md actually defines.
// ---------------------------------------------------------------------------
declare module "@mui/material/styles" {
  interface Palette {
    tertiary: Palette["primary"];
    surfaceContainer: {
      lowest: string;
      low: string;
      default: string;
      high: string;
      highest: string;
    };
  }
  interface PaletteOptions {
    tertiary?: PaletteOptions["primary"];
    surfaceContainer?: Partial<Palette["surfaceContainer"]>;
  }

  interface Theme {
    radius: { sm: number; md: number; lg: number; xl: number; full: number };
    layout: {
      containerMax: number;
      gutter: number;
      marginMobile: number;
      marginDesktop: number;
    };
  }
  interface ThemeOptions {
    radius?: Partial<Theme["radius"]>;
    layout?: Partial<Theme["layout"]>;
  }
}

// ---------------------------------------------------------------------------
// Tokens — fill these from the parsed DESIGN.md frontmatter.
// ---------------------------------------------------------------------------
const tokens = {
  colors: {
    // primary:                "/* TOKEN: colors.primary */",
    // onPrimary:              "/* TOKEN: colors.on-primary */",
    // primaryContainer:       "/* TOKEN: colors.primary-container */",
    // secondary:              "/* TOKEN: colors.secondary */",
    // onSecondary:            "/* TOKEN: colors.on-secondary */",
    // tertiary:               "/* TOKEN: colors.tertiary */",
    // onTertiary:             "/* TOKEN: colors.on-tertiary */",
    // background:             "/* TOKEN: colors.background or colors.surface */",
    // surface:                "/* TOKEN: colors.surface */",
    // onSurface:              "/* TOKEN: colors.on-surface */",
    // onSurfaceVariant:       "/* TOKEN: colors.on-surface-variant */",
    // outline:                "/* TOKEN: colors.outline */",
    // error:                  "/* TOKEN: colors.error */",
    // onError:                "/* TOKEN: colors.on-error */",
    // surfaceContainerLowest: "/* TOKEN: colors.surface-container-lowest */",
    // surfaceContainerLow:    "/* TOKEN: colors.surface-container-low */",
    // surfaceContainer:       "/* TOKEN: colors.surface-container */",
    // surfaceContainerHigh:   "/* TOKEN: colors.surface-container-high */",
    // surfaceContainerHighest:"/* TOKEN: colors.surface-container-highest */",
  },
  fonts: {
    display: "var(--font-display), system-ui, sans-serif",
    body:    "var(--font-body), system-ui, sans-serif",
  },
};

// ---------------------------------------------------------------------------
// Detect mode from the DESIGN.md (dark if the background is dark, else light).
// Hardcode this when you generate — don't try to compute at runtime.
// ---------------------------------------------------------------------------
const themeOptions: ThemeOptions = {
  palette: {
    mode: "dark", // or "light" — set based on DESIGN.md
    // primary:    { main: tokens.colors.primary,   contrastText: tokens.colors.onPrimary },
    // secondary:  { main: tokens.colors.secondary, contrastText: tokens.colors.onSecondary },
    // tertiary:   { main: tokens.colors.tertiary,  contrastText: tokens.colors.onTertiary },
    // error:      { main: tokens.colors.error,     contrastText: tokens.colors.onError },
    // background: { default: tokens.colors.background, paper: tokens.colors.surface },
    // text:       { primary: tokens.colors.onSurface, secondary: tokens.colors.onSurfaceVariant },
    // divider:    tokens.colors.outline,
    // surfaceContainer: {
    //   lowest: tokens.colors.surfaceContainerLowest,
    //   low:    tokens.colors.surfaceContainerLow,
    //   default: tokens.colors.surfaceContainer,
    //   high:   tokens.colors.surfaceContainerHigh,
    //   highest:tokens.colors.surfaceContainerHighest,
    // },
  },

  typography: {
    fontFamily: tokens.fonts.body,
    // One entry per typography.<level>. Map to nearest MUI variant; use
    // module augmentation if you need custom variants.
    // h1: { fontFamily: tokens.fonts.display, fontSize: 72, lineHeight: "80px", letterSpacing: "-0.04em", fontWeight: 700 },
    // h2: { fontFamily: tokens.fonts.display, fontSize: 48, lineHeight: "56px", letterSpacing: "-0.02em", fontWeight: 600 },
    // body1: { fontSize: 18, lineHeight: "28px", fontWeight: 400 },
    // body2: { fontSize: 16, lineHeight: "24px", fontWeight: 400 },
    // button: { fontFamily: tokens.fonts.display, fontSize: 14, lineHeight: "20px", letterSpacing: "0.1em", fontWeight: 500, textTransform: "uppercase" },
  },

  shape: { borderRadius: 8 },
  spacing: 8,

  radius: { sm: 2, md: 6, lg: 8, xl: 12, full: 9999 },
  layout: { containerMax: 1280, gutter: 24, marginMobile: 16, marginDesktop: 64 },

  components: {
    // ----- Buttons -----
    // MuiButton: {
    //   defaultProps: { disableElevation: true },
    //   styleOverrides: {
    //     root: ({ theme }) => ({
    //       height: 48,
    //       padding: "0 12px",
    //       borderRadius: theme.radius.lg,
    //       fontFamily: tokens.fonts.display,
    //       fontSize: 14,
    //       letterSpacing: "0.1em",
    //       textTransform: "uppercase",
    //     }),
    //     contained: ({ theme }) => ({
    //       backgroundColor: theme.palette.primary.main,
    //       color: theme.palette.primary.contrastText,
    //       "&:hover": { backgroundColor: theme.palette.primary.light },
    //     }),
    //     outlined: ({ theme }) => ({
    //       backgroundColor: "transparent",
    //       color: theme.palette.secondary.main,
    //       borderColor: theme.palette.secondary.main,
    //       "&:hover": { backgroundColor: alpha(theme.palette.secondary.main, 0.1) },
    //     }),
    //   },
    // },

    // ----- Cards / surfaces -----
    // MuiCard: {
    //   styleOverrides: {
    //     root: ({ theme }) => ({
    //       backgroundColor: alpha(theme.palette.surfaceContainer.high, 0.2),
    //       backdropFilter: "blur(20px)",
    //       border: `1px solid ${alpha("#fff", 0.1)}`,
    //       borderRadius: theme.radius.xl,
    //       padding: theme.layout.gutter,
    //     }),
    //   },
    // },

    // ----- Inputs -----
    // MuiTextField: {
    //   defaultProps: { variant: "outlined", size: "medium", fullWidth: true },
    //   styleOverrides: {
    //     root: ({ theme }) => ({
    //       "& .MuiOutlinedInput-root": {
    //         backgroundColor: theme.palette.surfaceContainer.lowest,
    //         color: theme.palette.text.primary,
    //         borderRadius: theme.radius.lg,
    //         "& fieldset": { borderColor: theme.palette.divider },
    //       },
    //     }),
    //   },
    // },

    // ----- Add the rest based on the DESIGN.md components block -----
  },
};

export const theme: Theme = createTheme(themeOptions);
