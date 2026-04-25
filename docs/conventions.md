# Conventions — folder structure, server actions, theme, showcase

These are the conventions that `design-md-to-app` enforces. Once a project is scaffolded, every subsequent skill (and human) follows them.

## Folder layout

The Next.js App Router 2026 convention this skill enforces:

| Path | What lives here |
|---|---|
| `components/ui/` | shadcn primitives. **Untouched** after `add --all` except for `cva` variant customization per DESIGN.md `components` block. |
| `components/<group>/` | **Cross-route shared** components. Layout shells (`app-shell`, `site-top-nav`, `wordmark-footer`), brand components, business components reused on 2+ routes. Group by domain: `components/site/`, `components/marketing/`, `components/forms/`. |
| `app/<route>/_components/` | **Page-scoped**. Sections unique to ONE route, NOT reused. The `_` prefix is a Next.js privacy marker. |
| `lib/server/<domain>.ts` | **Server actions** for a domain (`practices.ts`, `clients.ts`, `transfers.ts`). Always start with `"use server";`. |
| `lib/queries/<domain>.ts` | **Server-side reads** (separate from actions for clarity). Async functions called from RSC. |
| `lib/db/` | Drizzle (or equivalent) schema + connection — owned by `module-add db`. |
| `lib/auth.ts` + `lib/auth-client.ts` | better-auth — owned by `module-add auth`. |
| `lib/utils.ts` | Pure utilities (`cn()`, formatters, date helpers). |
| `hooks/` | Custom React hooks shared cross-route. |

### Key rules

- **Cross-route shared components do NOT go in `app/_components/`.** The `_` is a routing concern, not a "shared" marker. If a component is used on 2+ routes, it goes in `components/<group>/`.
- **Server actions do NOT go in `app/`.** They belong in `lib/server/<domain>.ts` so they can be imported from any route or component without circular imports.
- **One file per business domain in `lib/server/`** — `practices.ts`, not `practice-actions.ts`. The folder is the namespace; don't repeat it in the filename.
- **Group components by domain**, not by visual type. `components/site/` for layout shells, `components/forms/` for form pieces, `components/marketing/` for landing-only blocks. Never have a flat 30+ files in `components/`.

### Promotion rule

When `screenshot-to-page` builds a new route and notices it's reusing a component from another route, it **promotes** it: move from `app/<route>/_components/` to `components/<group>/`, update imports.

## Server actions

The shape of every server action across the codebase:

```typescript
// lib/server/<domain>.ts
"use server";

import { z } from "zod";
import { revalidatePath } from "next/cache";

// 1. ActionResult<T> discriminated union — never throw across the server boundary
export type ActionResult<T> =
  | { ok: true; data: T }
  | { ok: false; error: string; fieldErrors?: Record<string, string[]> };

// 2. Zod schema per action
const CreateXSchema = z.object({
  name: z.string().min(3).max(200),
  // ...
});

// 3. Helper to flatten Zod errors into form-friendly shape
function flattenZod(error: z.ZodError) {
  const flat = z.flattenError(error);
  return {
    message: "Invalid input",
    fieldErrors: flat.fieldErrors as Record<string, string[]>,
  };
}

// 4. Auth helper (stub until module-add auth wires it)
async function getCurrentUserId(): Promise<string> {
  throw new Error("getCurrentUserId() not yet wired — implement after `module-add auth` runs.");
}

// 5. The action
export async function createX(input: z.input<typeof CreateXSchema>): Promise<ActionResult<{ id: number }>> {
  const parsed = CreateXSchema.safeParse(input);
  if (!parsed.success) {
    const { message, fieldErrors } = flattenZod(parsed.error);
    return { ok: false, error: message, fieldErrors };
  }

  try {
    const userId = await getCurrentUserId();
    const [row] = await db.insert(...).values(...).returning({ id: ... });
    revalidatePath("/x");
    return { ok: true, data: { id: row.id } };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Unknown error" };
  }
}
```

### Why this pattern

- **`ActionResult<T>` instead of throws**: Next.js streams server-action results to the client. Throws are converted to generic 500s and lose context. A discriminated union preserves shape and field-level errors.
- **Zod first**: every input is validated before doing anything. `safeParse` keeps the function exception-free.
- **`revalidatePath` after mutations**: caches don't lie.
- **Auth stub at top**: every action checks user identity / tenant scope. The stub is a hard error so tests catch missing wiring.

## Theme system

Every project includes a runtime light/dark toggle by default.

### Setup (done by `design-md-to-app` Step 4.6)

```bash
pnpm add next-themes
```

```tsx
// components/site/theme-provider.tsx
"use client";
import { ThemeProvider as NextThemesProvider } from "next-themes";
export function ThemeProvider(props: React.ComponentProps<typeof NextThemesProvider>) {
  return <NextThemesProvider {...props} />;
}
```

```tsx
// app/layout.tsx
<html lang="..." suppressHydrationWarning>
  <body>
    <ThemeProvider attribute="class" defaultTheme="light" enableSystem disableTransitionOnChange>
      {children}
    </ThemeProvider>
  </body>
</html>
```

### Toggle component

```tsx
// components/site/mode-toggle.tsx
"use client";
import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { Button } from "@/components/ui/button";
import * as React from "react";

export function ModeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = React.useState(false);

  React.useEffect(() => { setMounted(true); }, []);

  const toggle = React.useCallback(() => {
    setTheme(resolvedTheme === "dark" ? "light" : "dark");
  }, [resolvedTheme, setTheme]);

  // Global keyboard shortcut: D toggles theme (except when typing).
  React.useEffect(() => {
    function isTyping(target: EventTarget | null) {
      if (!(target instanceof HTMLElement)) return false;
      if (["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName)) return true;
      if (target.isContentEditable) return true;
      return false;
    }
    function onKey(e: KeyboardEvent) {
      if (e.key !== "d" && e.key !== "D") return;
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      if (isTyping(e.target)) return;
      e.preventDefault();
      toggle();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [toggle]);

  if (!mounted) {
    return <Button variant="ghost" size="icon" aria-label="Toggle theme"><Sun className="size-4" /></Button>;
  }
  return (
    <Button variant="ghost" size="icon" onClick={toggle}
      aria-label={`Toggle theme (current: ${resolvedTheme}). Shortcut: D`}>
      {resolvedTheme === "dark" ? <Sun className="size-4" /> : <Moon className="size-4" />}
    </Button>
  );
}
```

### Where to mount it

`<ModeToggle />` goes in **both** the public site shell (`SiteTopNav` next to the primary CTA) and the internal app shell (`AppShell` topbar next to notifications/help). Users hit it from either context.

### Default mode

Use `defaultTheme="light"` unless the source DESIGN.md explicitly declares dark as canonical. `enableSystem` lets the user's OS preference win on first visit.

## Showcase template

Every full-scaffold run produces a `/showcase` route. The structure is **non-negotiable** — same shape across every project, only the brand-specific content changes.

### Skeleton

```tsx
<MarketingShell>
  {/* 1. Header, py-20, h1 ≈ 72px, eyebrow on top, brand-voice tagline ending in period */}
  <section className="border-b border-outline">
    <div className="mx-auto max-w-[1280px] px-6 lg:px-12 py-20">
      <Eyebrow>{ project } design system</Eyebrow>
      <h1 style={{ fontSize: "72px", lineHeight: 0.85, ... }}>{ tagline }</h1>
      <p>...</p>
    </div>
  </section>

  {/* 2-9. Each section uses this exact wrapper */}
  <section className="border-b border-outline">
    <div className="mx-auto max-w-[1280px] px-6 lg:px-12 py-20 space-y-10">
      <div>
        <Eyebrow>{ section name }</Eyebrow>
        <h2 style={{ fontSize: "48px", ... }}>{ tagline }</h2>
        <p>{ description }</p>
      </div>
      { content }
    </div>
  </section>
</MarketingShell>
```

### The 9 sections (fixed order)

1. **Header** — h1 72px brand tagline, source attribution to `.workflow/DESIGN.md`, back-link.
2. **Colors** — color-as-card grid, 3 lines per card (hex / token name / role-note).
3. **Typography** — ladder `[name][spec mono][sample]`, samples from real product copy.
4. **Buttons** — single `flex-wrap` with domain-specific copy (NOT one card per variant).
5. **Cards & containers** — 3 cards demonstrating different surface levels with real product blocks.
6. **Inputs & forms** — uppercase mono labels, ONE input in error state.
7. **Badges** — status pills mapping 1:1 to product statuses.
8. **Radius + Spacing** — visual demos of both.
9. **Do's and Don'ts** — verbatim from DESIGN.md `## Do's and Don'ts` section.

### Sample copy by domain

The typography ladder, button copy, badge labels — all of it must come from the actual product. Never lorem ipsum, never "Default / Secondary / Click me".

| Slot | Notary CRM | Wisely fintech | DevOps console |
|---|---|---|---|
| Display sample | `Buongiorno, Studio Marini` | `Money beyond borders.` | `Production: Healthy` |
| Primary button | `Nuova pratica` | `Send money` | `Deploy to production` |
| Status badge | `Firmata` / `In scadenza` | `Completed` / `In transit` | `healthy` / `degraded` |

When generating a new project's showcase, extract candidates from `PRD.md` (user-story verbs → button copy; statuses in acceptance criteria → badge labels). If still not enough, ASK the user for 3 product-specific phrases.

### Anti-patterns

- ❌ Wrapping `/showcase` in the same `AppShell` used by the rest of the app. The showcase is a document about the system, not a route inside the app.
- ❌ Sections without `border-b` full-width wrapper.
- ❌ Sections without an Eyebrow above the h2.
- ❌ h2 at 28px or smaller. The h2 is **48px display**, always.
- ❌ Color swatches with only hex + name. The role-note is mandatory.
- ❌ Typography samples like "Body Medium 16/400". Use real product copy.
- ❌ One-card-per-variant buttons. Use a single flex-wrap.
- ❌ Generic h1 like "Showcase UI" or "Visual identity, applied". Use a brand-voice tagline.
- ❌ Skipping Spacing scale or Do's/Don'ts because "they take time".

## Site-shell components

`design-md-to-app` produces 5 site-shell components in `components/<group>/` (typically `components/site/`):

| Component | Purpose |
|---|---|
| `SiteTopNav` | Public-marketing topbar: brand-left + nav-middle + ModeToggle/CTA-right. |
| `WordmarkFooter` | Brand-iconic footer: meta row + GIANT wordmark + mono micro-row. |
| `MarketingShell` | Wrapper combining `SiteTopNav` + `<main>` + `WordmarkFooter` for public pages. |
| `AppShell` | Internal app layout: vertical sidebar + topbar + content area, for authenticated routes. |
| `Eyebrow` | Reusable uppercase mono label, used above every section h2. |

The site-shell is what makes the showcase **a complete branded surface**. Without it, the page reads as a free-floating gallery.

## Anti-patterns to avoid

- ❌ Putting cross-route shared components in `app/_components/`.
- ❌ Throwing inside server actions instead of returning `{ ok: false, error }`.
- ❌ Hardcoding hex / px values in components instead of using DESIGN.md tokens.
- ❌ Skipping the `<ModeToggle>` keyboard shortcut, OR skipping the typing-guard so it fires while users type.
- ❌ Multi-line lorem ipsum in `/showcase` typography ladder.
- ❌ Drop shadows on cards when the DESIGN.md says the system is flat.
