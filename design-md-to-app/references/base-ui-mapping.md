# DESIGN.md → Base UI mapping

Base UI is the unstyled component library from the MUI team (formerly known as Base UI / MUI Base, relaunched as standalone in 2025). It ships **headless, accessible primitives** — you bring the styling, like Radix Primitives, but with a different API and a more focused component set.

**When to pick Base UI over shadcn vs MUI**:
- vs **shadcn**: similar philosophy (headless, you own the styles), but Base UI is a *real library* (installed as a dep) rather than copy-pasted source. You don't have to maintain CLI updates and `components.json`. Use Base UI when you want headless + library, with a slightly smaller surface (no `Calendar`, no `Drawer` out of the box yet).
- vs **MUI**: Base UI has the same accessibility quality but **no** built-in look — the entire visual layer is yours. Use Base UI when you like MUI's a11y but want a *distinctive* visual identity that Material Design themes don't reach.

Base UI components are styled either with **Tailwind CSS** (recommended for this skill set, mirrors shadcn approach) or with the styling solution of your choice (CSS Modules, emotion, vanilla).

## Project setup

Base UI works with any React framework. The recommended pairing in 2025+ is **Base UI + Tailwind v4** (same Tailwind config you'd use for shadcn).

### Next.js (App Router) — default

```bash
pnpm create next-app@latest <dir> --typescript --tailwind --eslint --app --no-src-dir --import-alias "@/*" --use-pnpm --turbopack --yes
cd <dir>
pnpm add @base-ui-components/react
```

That's the entire install. No CLI step, no `components.json`, no `--all` import — you `import` each component on demand from `@base-ui-components/react`.

### Vite + React

```bash
pnpm create vite@latest <dir> --template react-ts
cd <dir>
pnpm add tailwindcss @tailwindcss/vite @base-ui-components/react
```

Then enable the Tailwind v4 Vite plugin in `vite.config.ts` and import the CSS:

```ts
import tailwindcss from "@tailwindcss/vite";
// ...
plugins: [react(), tailwindcss()],
```

### Theme provider — not needed

Base UI is **render-prop based**. Each component exposes "parts" (e.g. `<Dialog.Root>`, `<Dialog.Backdrop>`, `<Dialog.Popup>`) that you style individually. There is **no global `<ThemeProvider>`** — your Tailwind tokens drive every visual decision.

This means **the theme equation is identical to shadcn**: Tailwind tokens in `app/globals.css` (or `tailwind.config.js` for v3 holdouts).

## Token mapping — color

Base UI uses the same `:root` / `.dark` CSS variable pattern as shadcn. The DESIGN.md `colors` block translates 1:1 into CSS variables, then surfaced via `@theme inline {}` so Tailwind generates `bg-primary`, `text-foreground`, etc.

```css
/* app/globals.css */
@import "tailwindcss";

:root {
  --background: 0 0% 100%;
  --foreground: 240 10% 4%;
  --primary: 220 90% 56%;
  --primary-foreground: 0 0% 100%;
  --muted: 240 5% 96%;
  --muted-foreground: 240 4% 46%;
  --border: 240 5% 91%;
  --radius: 0.625rem;
}

.dark {
  --background: 240 10% 4%;
  --foreground: 0 0% 98%;
  --primary: 220 80% 65%;
  --primary-foreground: 240 10% 4%;
  --muted: 240 4% 16%;
  --muted-foreground: 240 5% 65%;
  --border: 240 4% 16%;
}

@theme inline {
  --color-background: hsl(var(--background));
  --color-foreground: hsl(var(--foreground));
  --color-primary: hsl(var(--primary));
  --color-primary-foreground: hsl(var(--primary-foreground));
  --color-muted: hsl(var(--muted));
  --color-muted-foreground: hsl(var(--muted-foreground));
  --color-border: hsl(var(--border));
  --radius-default: var(--radius);
}
```

Mapping from the DESIGN.md `colors:` block:

| DESIGN.md key | CSS variable | Tailwind class |
|---|---|---|
| `colors.primary` | `--primary` + `--primary-foreground` | `bg-primary` / `text-primary-foreground` |
| `colors.background` | `--background` + `--foreground` | `bg-background` / `text-foreground` |
| `colors.surface` (cards, popovers) | `--card` + `--card-foreground` | `bg-card` / `text-card-foreground` |
| `colors.muted` | `--muted` + `--muted-foreground` | `bg-muted` / `text-muted-foreground` |
| `colors.border` | `--border` | `border-border` |
| `colors.success` / `warning` / `danger` | `--success` / `--warning` / `--destructive` | semantic classes |

## Token mapping — typography

```css
@theme inline {
  --font-sans: "Inter", system-ui, sans-serif;
  --font-display: "Sora", "Inter", sans-serif;
  --font-mono: "JetBrains Mono", monospace;
}
```

Then `font-sans`, `font-display`, `font-mono` Tailwind classes are available. Load fonts via `next/font` (App Router) and pass the CSS variable to `<html className={...}>`.

## Component customization pattern

Base UI components are split into "parts". A Dialog looks like this:

```tsx
import * as Dialog from "@base-ui-components/react/dialog";

export function ConfirmDialog({ open, onClose, children }: Props) {
  return (
    <Dialog.Root open={open} onOpenChange={onClose}>
      <Dialog.Backdrop className="fixed inset-0 bg-black/40 backdrop-blur-sm" />
      <Dialog.Popup className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-xl border border-border bg-background p-6 shadow-xl">
        {children}
      </Dialog.Popup>
    </Dialog.Root>
  );
}
```

The skill should wrap commonly-used composites into `components/ui/*` files (`Button.tsx`, `Dialog.tsx`, `Popover.tsx`, etc.) so the rest of the app imports a single ergonomic primitive — same pattern as shadcn, but composed from Base UI primitives instead of generated source.

## Component coverage (as of 2026-05)

Base UI ships these primitives. Map each DESIGN.md component to one:

| DESIGN.md component | Base UI primitive | Notes |
|---|---|---|
| Button | `<button>` element (no Base UI primitive needed) | Compose with `cva` for variants |
| Toggle | `Switch.Root` / `Toggle.Root` | |
| Checkbox | `Checkbox.Root` | |
| Radio | `RadioGroup.Root` + `RadioGroup.Item` | |
| Select | `Select.Root` | |
| Dialog / Modal | `Dialog.Root` + `Dialog.Backdrop` + `Dialog.Popup` | |
| Popover | `Popover.Root` | |
| Tooltip | `Tooltip.Root` | |
| Tabs | `Tabs.Root` + `Tabs.List` + `Tabs.Tab` + `Tabs.Panel` | |
| Accordion | `Accordion.Root` + `Accordion.Item` + `Accordion.Trigger` + `Accordion.Panel` | |
| Slider | `Slider.Root` | |
| Menu | `Menu.Root` / `ContextMenu.Root` | |
| Number input | `NumberField.Root` | |
| Form / field validation | `Form.Root` + `Form.Field` | optional Zod / RHF on top |
| Toast | (use a third-party like `sonner` — Base UI doesn't ship one) | |
| Calendar / date picker | (not yet in Base UI as of 2026-05 — fall back to `react-day-picker`) | |
| Toggle group | `ToggleGroup.Root` | |
| Avatar | (compose with `<img>` + fallback — no primitive) | |

## `/showcase` page expectations

Same 9 sections as shadcn version. Compose using the table above + Tailwind for visuals.

## Anti-patterns to avoid

- ❌ Mixing Base UI and shadcn primitives in the same project. Either-or.
- ❌ Importing all of `@base-ui-components/react` upfront. Each primitive imports cleanly tree-shakes.
- ❌ Using Base UI's `Provider` (deprecated) — it does nothing; remove if you find it.
- ❌ Skipping the styling — Base UI without styles is a screenreader's dream and a user's nightmare.
- ❌ Using Base UI for design systems that match Material exactly — go MUI for that.

## When NOT to pick Base UI

- The project genuinely matches **Material Design** (banking, enterprise admin, Google ecosystem) → use MUI.
- The project needs a Calendar/Date Picker out of the box → use shadcn (has it) or pair Base UI with `react-day-picker`.
- The team strongly prefers copy-pasted source they can edit → use shadcn.
- The project uses CSS-in-JS already (emotion/styled-components) → Base UI works there too but loses the "Tailwind tokens stream into both" benefit.

## Sources

- https://base-ui.com — official docs
- https://github.com/mui/base-ui — repo
- DESIGN.md spec: see `references/spec.md`
