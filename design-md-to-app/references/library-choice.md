# Suggesting shadcn/ui vs MUI

The user picks. This file is for **how to suggest** before they do.

The two libraries solve overlapping problems but with very different philosophies. The DESIGN.md usually contains enough hints to pick a strong default — but always frame it as a suggestion, not a decision.

## One-line mental model

- **shadcn/ui**: you own the source. Every component lives in `components/ui/` and you edit it. Tailwind-based. No runtime theming layer — CSS variables + utility classes.
- **MUI**: you import components and theme them. The source stays in `node_modules`. Emotion-based. A single `theme` object propagates everywhere through `ThemeProvider`.

Practical implication: shadcn lets you go arbitrarily custom (because you're editing the code), MUI gets you to "good enough material defaults" fast and resists deep visual customization unless you're disciplined about overrides.

## Strong signals for shadcn

Pick shadcn when the DESIGN.md shows any of:

- **Custom visual language** that's unlike Material: glassmorphism, brutalism, neumorphism, editorial, retro, cyberpunk, hand-drawn, etc.
- **Many invented component names** (`card-glass-level-2`, `badge-celestial`, `hero-headline`) — these will need source-level work, easier when you own the file.
- **Distinctive typography** with non-standard hierarchies (e.g. `headline-xl` 72px+, monumental display sizes) — Tailwind's per-size config is a cleaner fit than MUI's variant system.
- **Tailwind already in the project** or any mention of utility-first CSS.
- **Need for fine-grained light/dark or themed surfaces** — CSS variables + Tailwind opacity modifiers are very flexible here.
- The user says "I want to ship fast and customize later" with a custom-looking design.

## Strong signals for MUI

Pick MUI when the DESIGN.md shows any of:

- **Material Design heritage**: the `colors` block uses Material 3 token names (`surface-container-high`, `on-secondary-container`, `inverse-primary`) AND the visual identity is essentially Material — that's a strong "this design was authored against Material 3, ride that wave."
- **Dashboard / data-heavy / enterprise CRUD**: lots of tables, dialogs, drawers, autocomplete, date pickers, complex form controls — MUI ships these out of the box and well-tested. Building them in shadcn means installing 20 separate primitives.
- **Built-in component breadth matters more than visual distinctiveness**: the user wants "professional, gets out of the way" rather than "make it look unique."
- **The user already uses MUI in adjacent projects** and wants consistency.

## When it's a coin flip

If the DESIGN.md is moderately custom + moderately broad:

- Default to **shadcn** if the user is solo / small team and wants to iterate on look.
- Default to **MUI** if the user is in a team where multiple people will theme the app and a single source of truth (`theme.ts`) helps coordination.

## How to phrase the suggestion

Keep it tight. Two lines:

> **Suggerisco shadcn/ui.** Il DESIGN.md descrive vetro/glassmorphism e usa molti nomi custom (`card-glass-level-2`, `badge-celestial`) — modificare il sorgente è la via più diretta. Se vuoi MUI lo stesso, dimmelo.

Or:

> **Suggerisco MUI.** I tuoi token sono Material 3 puro (`surface-container-*`, `inverse-on-surface`) e il prodotto sembra una dashboard — la libreria già copre il 90% di quello che ti serve. shadcn rimane valido se vuoi più libertà visiva.

Then accept whatever the user picks without arguing.

## Dealbreakers (rare, but worth flagging)

- **Server Components everywhere**: shadcn integrates more naturally with React Server Components since most of its primitives are stateless. MUI works but needs the `AppRouterCacheProvider` setup and most components effectively become client. If the user is building a content-heavy site (docs, marketing) where SSR/RSC is critical, lean shadcn.
- **Non-Next.js framework** (Remix, Vite + React, Tanstack Start): both work, but MUI's `@mui/material-nextjs` helper obviously doesn't apply, and shadcn's docs / generators assume Next less aggressively now. Both fine; just don't follow the Next-specific snippets blindly.
- **No Tailwind, refuses to add it**: shadcn is off the table. MUI it is.
