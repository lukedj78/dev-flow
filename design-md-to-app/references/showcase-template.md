# /showcase — structural template

This is the **load-bearing structural template** for the `/showcase` page that `design-md-to-app` produces in full-scaffold mode. The pattern was distilled from three independently-shipped projects (airbnb-clone, aetherfield, devops-graphite, notarius-crm) that converged on the same skeleton — only the brand-specific contents inside the bands change.

A reference TypeScript file with all 9 sections wired up lives at `references/showcase-template.tsx` (vendored from the Notarius implementation). When generating a new `/showcase` for a fresh project, copy that file and replace the contents — do not improvise the structure.

## Design intent

The showcase is **a document about the design system**, not a route inside the app. It is read by:
- Designers verifying that tokens landed correctly.
- Engineers who need to find "the right way to compose a card / a button / a status pill" while building feature pages.
- The user themselves, the morning after a scaffold, to see "did the brand actually land, or do I need to iterate the DESIGN.md?".

So it must read as a magazine, not as a Storybook gallery. Every section starts with an Eyebrow, has a brand-voice h2 ending in a period, and is bordered top-and-bottom from its neighbors.

## The skeleton

```tsx
<main className="bg-surface text-on-surface min-h-screen">

  {/* 1. Header — slightly taller, h1 at 72px */}
  <section className="border-b border-outline">
    <div className="mx-auto max-w-[1280px] px-6 lg:px-12 py-20">
      <div className="space-y-5">
        <Eyebrow>{ project } design system</Eyebrow>
        <h1 style={{ fontSize: "72px", lineHeight: "80px", letterSpacing: "-0.02em", fontWeight: 600 }}>
          { brand-voice tagline ending in period }
        </h1>
        <p className="text-on-surface-variant max-w-2xl" style={{ fontSize: "18px", lineHeight: "28px" }}>
          Generated from <code>.workflow/DESIGN.md</code> by <code>design-md-to-app</code>…
        </p>
        <Link href="/">← Torna alla dashboard</Link>
      </div>
    </div>
  </section>

  {/* 2–9. Each section uses this exact wrapper */}
  <section className="border-b border-outline">
    <div className="mx-auto max-w-[1280px] px-6 lg:px-12 py-20 space-y-10">
      <div className="space-y-3">
        <Eyebrow>{ section }</Eyebrow>
        <h2 style={{ fontSize: "48px", lineHeight: "56px", letterSpacing: "-0.02em", fontWeight: 600 }}>
          { brand-voice tagline ending in period }
        </h2>
        <p className="text-on-surface-variant" style={{ fontSize: "16px" }}>
          { 1–2 sentence description with <code> token references }
        </p>
      </div>
      { section content }
    </div>
  </section>

  {/* Footer */}
  <footer className="border-t border-outline">
    <div className="mx-auto max-w-[1280px] px-6 lg:px-12 py-10 text-center font-mono text-[12px] tracking-wide uppercase text-on-surface-variant">
      Generated from .workflow/DESIGN.md · See registry.json + .workflow/screenshots
    </div>
  </footer>

</main>
```

## The 9 sections (fixed order)

1. **Header** — h1 72px, brand tagline, source attribution, back-link.
2. **Colors** — color-as-card grid, 3 lines per card (hex / name / role-note).
3. **Typography** — ladder `[name][spec mono][sample]`, samples are real product copy.
4. **Buttons** — single `flex-wrap` with domain-specific copy (NOT one card per variant).
5. **Cards & containers** — 3 cards demonstrating different surface levels with real product blocks.
6. **Inputs & forms** — uppercase mono labels, one input in error state.
7. **Badges** — status pills mapping 1:1 to product statuses.
8. **Radius + Spacing scales** — visual demos of both.
9. **Do's and Don'ts** — verbatim from DESIGN.md `## Do's and Don'ts` section.

## Brand-voice taglines — examples

The h2 of each section is a brand-voice short statement, not a label. Pattern: subject + state, ends with period.

| Project | Header h1 | Colors h2 | Typography h2 | Buttons h2 |
|---|---|---|---|---|
| Aetherfield | `Aetherfield design tokens.` | `The palette.` | `The voice.` | `Black is the primary. The lime is for banners, not buttons.` |
| Airbnb-clone | `Airbnb-style design tokens` | `Colors` | `Typography` | `Buttons` |
| DevOps Graphite | `Production: Healthy` | `Colors` | `Typography` | `Buttons` |
| Notarius CRM | `Quietly opinionated CRM for notary studios.` | `The palette.` | `The voice.` | `One purple primary per viewport.` |

(Airbnb-clone and DevOps Graphite use plainer h2s — both are valid. The rule is **no lorem ipsum, no "Click me" placeholder copy**, and brand-specific h1.)

## Sample copy by domain

The typography ladder, the button copy, the badge labels, the form fields — all of it must be drawn from the actual product. Examples:

| Slot | Notary CRM | Airbnb | DevOps |
|---|---|---|---|
| Display sample | `Buongiorno, Studio Marini` | `Inspiration for future getaways` | `Production: Healthy` |
| Headline sample | `Pratiche più attive degli ultimi 7 giorni` | `What this place offers` | `Build Pipeline` |
| Body-md sample | `P.IVA 01234567890 · 3 pratiche aperte` | `Soak up the sun on a private yacht…` | `Last deployment 14 minutes ago — 240 tests passed` |
| Caption sample | `Dati protetti — segreto professionale` | `You won't be charged yet` | `STATUS: PROD-2025.10.31-A4F1` |
| Primary button | `Nuova pratica` | `Reserve` | `Deploy to production` |
| Secondary button | `Filtra pratiche` | `Become a host` | `Cancel` |
| Destructive button | `Annulla pratica` | `Cancel reservation` | `Roll back` |
| Status badges | `Firmata` / `In corso` / `In scadenza` / `Errore` / `Archiviata` | `Guest Favorite` / `New` | `healthy` / `building` / `degraded` |

When generating a new project's showcase, **extract real candidates from PRD.md and tasks.md**:
- The user stories (`As a … I want …`) tell you the product's verbs → button copy.
- Features mentioned by name → typography samples.
- Statuses mentioned in acceptance criteria → badge labels.

If after reading PRD.md and screenshots you still don't have enough candidates, **ask the user for 3 product-specific phrases** before writing the showcase. Don't fall back to generic gallery copy.

## How to use this template

1. Copy `showcase-template.tsx` into `<project-root>/app/showcase/page.tsx`.
2. Replace each constant array (`COLORS`, `TYPES`, `RADII`, `SPACING`) with values from the project's DESIGN.md.
3. Replace every domain-contextual sample with copy extracted from PRD.md, screenshots, or asked from the user.
4. Replace the brand-voice taglines (h1 + each h2) with brand-specific wording.
5. Update the `Eyebrow` text in section 1 to `<PROJECT NAME> design system`.
6. Replace the Do's/Don'ts cards' bullets with the literal list from DESIGN.md `## Do's and Don'ts`.
7. Run `pnpm run build` and verify HTTP 200 on `/showcase`.
