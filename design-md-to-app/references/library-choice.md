# Suggesting shadcn/ui vs Base UI vs MUI

The user picks. This file is for **how to suggest** before they do.

The three libraries solve overlapping problems with three different philosophies. The DESIGN.md usually contains enough hints to pick a strong default — but always frame it as a suggestion, not a decision.

## One-line mental model

- **shadcn/ui**: you own the source. Every component lives in `components/ui/` and you edit it. Tailwind-based. No runtime theming layer — CSS variables + utility classes. CLI-managed (`shadcn@latest add ...`).
- **Base UI**: headless React library (installed dep, not copy-pasted source). Same Tailwind philosophy as shadcn for styling, but no CLI — you `import` each primitive from `@base-ui/react` on demand. Same accessibility quality as MUI.
- **MUI** (Material UI): runtime themed library. The source stays in `node_modules`. Emotion-based. A single `theme` object propagates everywhere through `ThemeProvider`.

Practical implication:
- shadcn = max flexibility (own the code) + ongoing source maintenance.
- Base UI = shadcn-like flexibility (headless + Tailwind) without source maintenance (it's a library).
- MUI = "good enough Material defaults" fast, resists deep customization unless disciplined with overrides.

## Strong signals for shadcn

Pick shadcn when the DESIGN.md shows any of:

- **Custom visual language** that's unlike Material: glassmorphism, brutalism, neumorphism, editorial, retro, cyberpunk, hand-drawn, etc.
- **Many invented component names** (`card-glass-level-2`, `badge-celestial`, `hero-headline`) — these will need source-level work, easier when you own the file.
- **Distinctive typography** with non-standard hierarchies (e.g. `headline-xl` 72px+, monumental display sizes) — Tailwind's per-size config is a cleaner fit than MUI's variant system.
- **Tailwind already in the project** or any mention of utility-first CSS.
- **Need for fine-grained light/dark or themed surfaces** — CSS variables + Tailwind opacity modifiers are very flexible here.
- The user says "I want to ship fast and customize later" with a custom-looking design.
- The user wants to **inspect, copy, and modify** UI source on a per-component basis (shadcn ships source you can edit; Base UI doesn't).

## Strong signals for Base UI

Pick Base UI when the DESIGN.md shows any of:

- **Headless + Tailwind philosophy preferred** (same as shadcn), BUT the user does NOT want to maintain copy-pasted source — they want a library they can `pnpm update` and not think about.
- **Strong accessibility requirements** (WCAG AA+, screenreader-first, keyboard navigation rigor) — Base UI inherits MUI team's a11y track record without Material's visual baggage.
- **Modest component surface** suffices: the DESIGN.md uses Buttons, Dialogs, Popovers, Tabs, Forms — none of the things Base UI hasn't shipped yet (Calendar / DatePicker / Drawer are NOT in Base UI as of 2026-05).
- The user has tried shadcn before and found CLI updates / `components.json` maintenance friction.
- **Tree-shake matters** — Base UI imports cleanly per-primitive; shadcn ships everything you `add --all` (negligible for most apps, mentionable for embedded / kiosks).
- **The project is part of an MUI shop** but the new app's visual identity wants to escape Material — Base UI is the smooth migration path because the headless layer is the same team.

## Strong signals for MUI

Pick MUI when the DESIGN.md shows any of:

- **Material Design heritage**: the `colors` block uses Material 3 token names (`surface-container-high`, `on-secondary-container`, `inverse-primary`) AND the visual identity is essentially Material — that's a strong "this design was authored against Material 3, ride that wave."
- **Dashboard / data-heavy / enterprise CRUD**: lots of tables, dialogs, drawers, autocomplete, date pickers, complex form controls — MUI ships these out of the box and well-tested. Building them in shadcn means installing 20 separate primitives.
- **Built-in component breadth matters more than visual distinctiveness**: the user wants "professional, gets out of the way" rather than "make it look unique."
- **The user already uses MUI in adjacent projects** and wants consistency.

## If shadcn: which primitive base — Base UI / Radix / React Aria (`--base`)

shadcn CLI v4 builds its components on **Base UI, Radix, or React Aria** primitives. After the user picks shadcn, ask the follow-up and record it as `stack.ui_base` (`"base"` | `"radix"` | `"aria"`). The component API and the blocks (login, sidebar, dashboard, …) are identical across all — only the underlying primitive library changes, and `shadcn add` pulls the matching variant.

- **Base UI** (default since 2026-07): shadcn's default for new projects — the MUI team's headless primitives, best-in-class a11y, full component + block coverage. Pick it unless there's a reason not to.
- **Radix**: the long-standing shadcn base, still fully supported. Pick it for existing Radix-specific code/presets or a preference for its ecosystem.
- **React Aria** (`--base aria`, first-class since 2026-07): Adobe's a11y-first primitives. Pick it when standardizing on React Aria / Adobe interaction patterns.

How to phrase it:

> Hai scelto shadcn. Lo costruiamo su **Base UI** (default, a11y del team MUI), **Radix** (la base storica) o **React Aria** (primitivi a11y-first di Adobe)? I componenti e i blocchi sono identici nei tre casi.

### Don't confuse the two "Base UI" options

There are two distinct ways "Base UI" appears, and they are NOT the same:

| Choice | meta.json | What you get |
|---|---|---|
| **shadcn on Base UI** | `ui="shadcn"` + `ui_base="base"` | shadcn's component set + blocks + owned source, on Base UI primitives. **Usually the better way** to get "shadcn philosophy on Base UI". |
| **Standalone Base UI** | `ui="base-ui"` | Headless Base UI library, no shadcn CLI, you import primitives directly (`@base-ui/react`). Pick only when the user explicitly wants no shadcn CLI / `components.json`. |

When a user says "I want Base UI", clarify which they mean — most people who like shadcn but want Base UI primitives want the **first** option now.

## When it's a coin flip

If the DESIGN.md is moderately custom + moderately broad:

- Default to **shadcn** if the user is solo / small team and wants to iterate on look (and edit source).
- Default to **Base UI** if the user wants the same flexibility without owning the source forever (library install, normal `pnpm update`).
- Default to **MUI** if the user is in a team where multiple people will theme the app and a single source of truth (`theme.ts`) helps coordination, OR the design is already Material.

## How to phrase the suggestion

Keep it tight. Two lines, with explicit "if not, try X" fallback to one of the other two:

> **Suggerisco shadcn/ui.** Il DESIGN.md descrive vetro/glassmorphism e usa molti nomi custom (`card-glass-level-2`, `badge-celestial`) — modificare il sorgente è la via più diretta. Se preferisci una libreria senza source-maintenance, Base UI è equivalente con `pnpm add @base-ui/react`. Dimmi.

Or:

> **Suggerisco Base UI.** Il design è custom (Tailwind tokens chiari, look distintivo) ma vuoi una libreria che si aggiorna sola — Base UI è shadcn-philosophy senza il CLI overhead. shadcn rimane valido se preferisci copy-pasted source, MUI se il design fosse stato Material.

Or:

> **Suggerisco MUI.** I tuoi token sono Material 3 puro (`surface-container-*`, `inverse-on-surface`) e il prodotto sembra una dashboard — la libreria già copre il 90% di quello che ti serve. shadcn o Base UI rimangono validi se vuoi più libertà visiva.

Then accept whatever the user picks without arguing.

## Dealbreakers (rare, but worth flagging)

- **Server Components everywhere**: shadcn integrates more naturally with React Server Components since most of its primitives are stateless. MUI works but needs the `AppRouterCacheProvider` setup and most components effectively become client. If the user is building a content-heavy site (docs, marketing) where SSR/RSC is critical, lean shadcn.
- **Non-Next.js framework** (Remix, Vite + React, Tanstack Start): both work, but MUI's `@mui/material-nextjs` helper obviously doesn't apply, and shadcn's docs / generators assume Next less aggressively now. Both fine; just don't follow the Next-specific snippets blindly.
- **No Tailwind, refuses to add it**: shadcn is off the table. MUI it is.
