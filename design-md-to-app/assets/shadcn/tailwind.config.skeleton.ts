// Skeleton for tailwind.config.ts after DESIGN.md → shadcn mapping.
// Replace placeholders with values derived from DESIGN.md tokens.
// Delete any extend.* sections the DESIGN.md doesn't populate.
import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./pages/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./app/**/*.{ts,tsx}",
    "./src/**/*.{ts,tsx}",
  ],
  theme: {
    container: {
      center: true,
      padding: "/* TOKEN: spacing.gutter or spacing.margin-mobile */",
      screens: {
        "2xl": "/* TOKEN: spacing.container-max or 1280px */",
      },
    },
    extend: {
      colors: {
        // shadcn semantic palette — wired to globals.css CSS vars.
        border: "hsl(var(--border) / <alpha-value>)",
        input: "hsl(var(--input) / <alpha-value>)",
        ring: "hsl(var(--ring) / <alpha-value>)",
        background: "hsl(var(--background) / <alpha-value>)",
        foreground: "hsl(var(--foreground) / <alpha-value>)",
        primary: {
          DEFAULT: "hsl(var(--primary) / <alpha-value>)",
          foreground: "hsl(var(--primary-foreground) / <alpha-value>)",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary) / <alpha-value>)",
          foreground: "hsl(var(--secondary-foreground) / <alpha-value>)",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive) / <alpha-value>)",
          foreground: "hsl(var(--destructive-foreground) / <alpha-value>)",
        },
        muted: {
          DEFAULT: "hsl(var(--muted) / <alpha-value>)",
          foreground: "hsl(var(--muted-foreground) / <alpha-value>)",
        },
        accent: {
          DEFAULT: "hsl(var(--accent) / <alpha-value>)",
          foreground: "hsl(var(--accent-foreground) / <alpha-value>)",
        },
        popover: {
          DEFAULT: "hsl(var(--popover) / <alpha-value>)",
          foreground: "hsl(var(--popover-foreground) / <alpha-value>)",
        },
        card: {
          DEFAULT: "hsl(var(--card) / <alpha-value>)",
          foreground: "hsl(var(--card-foreground) / <alpha-value>)",
        },
        // Custom tokens — same names as DESIGN.md.
        // "primary-container": "hsl(var(--primary-container) / <alpha-value>)",
        // …
      },
      fontFamily: {
        // Wire each next/font CSS var here.
        // display: ["var(--font-display)", "ui-sans-serif", "system-ui"],
        // sans:    ["var(--font-sans)", "ui-sans-serif", "system-ui"],
      },
      fontSize: {
        // One entry per typography.<level>. Names match DESIGN.md tokens.
        // "headline-xl": ["72px", { lineHeight: "80px", letterSpacing: "-0.04em", fontWeight: "700" }],
        // "body-md":     ["16px", { lineHeight: "24px", letterSpacing: "0",       fontWeight: "400" }],
      },
      borderRadius: {
        // sm: "calc(var(--radius) - 4px)",
        DEFAULT: "var(--radius)",
        // md: "calc(var(--radius) - 2px)",
        // lg: "var(--radius)",
        // xl: "calc(var(--radius) + 4px)",
        // full: "9999px",
      },
      spacing: {
        // Custom named spacings from DESIGN.md.
        // gutter: "24px",
        // "margin-mobile": "16px",
        // "margin-desktop": "64px",
      },
      maxWidth: {
        // container: "1280px",
      },
      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
