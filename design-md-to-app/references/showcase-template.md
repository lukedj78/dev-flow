# /showcase — structural template

This is the **load-bearing structural template** for the `/showcase` page that `design-md-to-app` produces in full-scaffold mode. The pattern was distilled from three independently-shipped projects (airbnb-clone, aetherfield, devops-graphite, notarius-crm) that converged on the same skeleton — only the brand-specific contents inside the bands change.

**This file is the structural authority, and it tracks shadcn's own `skills/shadcn/design-system-page.md` (MIT) deliberately — when they change it, we diff and follow.** `references/showcase-template.tsx` is **not** a page skeleton any more: it encodes the earlier nine-section layout, and it is kept as a **styling reference** for how one of our sections looks — the `Eyebrow`, the section rules, and the data shapes behind the colour, type, radius and spacing ladders. Take the look from there and the structure from here. The three helpers the state matrix and the contrast pairs need are vendored at `assets/showcase/` (see its README).

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

## The sections (fixed order)

> **Widened 2026-10-09, because the page was demonstrating a fraction of what the scaffold installs.**
> We run `shadcn add --all` — sixty-odd components — and the old nine sections showed about nine of
> them. A design system page that omits every overlay, every feedback component and all of navigation
> is a colour-and-type page with a misleading name. The tier list below is adapted from shadcn's own
> `design-system-page.md` (MIT, 2026-10-09); the **brand voice, the real-product copy and the
> taglines stay ours** — their section headings are labels, and labels are what make a showcase read
> as a template.

**1. Header** — h1 72px, brand tagline, source attribution, back-link, **section anchors** and a
**light/dark toggle**. The toggle is not decoration: it is how anyone checks the `.dark` tokens
without editing code.

**2. Overview** — the DESIGN.md's hero recipe: the display face, the one-line personality, and the
system's signature artifact. One screenful that answers "what is this supposed to feel like".

**3. Foundations** — in one section, not scattered:

- **Colour roles as contrast-checked pairs.** Every pair below is rendered with its measured ratio,
  and **a pair under 4.5:1 is reported, including when the DESIGN.md itself specifies it** — that is
  a finding about the design, not a licence to silently fix it. Required pairs:
  `background`/`foreground`, `card`/`card-foreground`, `popover`/`popover-foreground`,
  `primary`/`primary-foreground`, `secondary`/`secondary-foreground`, `muted`/`muted-foreground`,
  `accent`/`accent-foreground`, `destructive` on `background`, and every extra text token on
  `background` that the DESIGN.md defines.
- **Palette** — the raw swatches behind the roles.
- **Typography** — the ladder as a table: token · spec (size / line-height / weight / tracking) ·
  **use** (taken from the DESIGN.md, e.g. "section heads") · specimen in real product copy.
- **Spacing, radius, elevation** ladders — visual, each step labelled with its token.
- **Motion** when the DESIGN.md specifies it (`transitions` owns the tokens), and **icons**: the set
  actually installed, which the shadcn style decides (`shadcn-styles.md`).

**4. Actions** — Button, ButtonGroup, Toggle, ToggleGroup, Badge, Kbd.
**5. Inputs** — Field, Input, InputGroup, Textarea, Select, NativeSelect, Combobox, Checkbox,
RadioGroup, Switch, Slider, InputOTP, Calendar, Label.
**6. Navigation** — Tabs, Breadcrumb, Pagination, NavigationMenu, Menubar, Sidebar.
**7. Data display** — Card, Table, Chart, Item, Avatar, Accordion, Collapsible, Carousel, ScrollArea,
Resizable, AspectRatio, Separator.
**8. Feedback** — Alert, toast (and Sonner in Base UI projects, which `add --all` installs too),
Progress, Spinner, Skeleton, Empty.
**9. Overlays** — Dialog, AlertDialog, Sheet, Drawer, Popover, HoverCard, Tooltip, DropdownMenu,
ContextMenu, Command. **Each gets a real trigger, labelled with what it opens** — a screenshot of a
closed dialog proves nothing.
**10. Conversation** — when the project has a chat surface: MessageScroller, Message, Bubble,
Attachment, Marker, Questionnaire. `references/chat-and-typeset.md` owns these.
**11. Do's and Don'ts** — **rendered pairs**, not quoted prose. Each "Don't" from the DESIGN.md built
as a component beside the version that obeys the rule. A rule you can see broken is a rule people keep.
**12. Recipes and one example screen** — the DESIGN.md's named components rebuilt from the installed
primitives, then one realistic screen that uses them together.
**13. Footer** — the DESIGN.md's footer recipe.

Skip a section only when the project installed none of its components, and say which you skipped.

### How to show each tier

| Tier | How |
|---|---|
| **Primitives** (Button, Badge, Toggle, Input, Select, Checkbox, Radio, Switch, Slider, Tabs…) | Variant × state matrix, size ladder smallest to largest, icon row (leading, trailing, icon-only) |
| **Fields** (Field, InputGroup, Combobox, InputOTP, Calendar, Label) | The typical field, then description, error, disabled, required |
| **Composed** (Card, Table, Item, Avatar, Alert, Empty, Accordion, Progress, Chart…) | Typical example, then one element added at a time, then the edge cases |
| **Overlays** | One real trigger each, labelled with what it opens |
| **Shell** (Sidebar) | Inline in a framed preview — `<SidebarProvider className="min-h-0">` + `<Sidebar collapsible="none">`, or the default `fixed` sidebar escapes the frame |
| **Conversation** | One realistic thread, then the variant rows |

Each block, in this order, skipping what does not apply: **name + one line on when to use it**
(take the wording from the DESIGN.md recipe when there is one) · typical example in real content ·
variants in priority order, each with a one-line "when" · sizes as a ladder · with icon · states ·
edge cases. Wide components (Table, NavigationMenu, Menubar, Sidebar, Chart, MessageScroller) span
the full row.

### Pin the interaction states — `data-preview`

A static page cannot hover itself, so a state matrix needs the states to be *addressable*. Redefine
the Tailwind variants so each also matches an attribute, in `tailwindCssFile`:

```css
@custom-variant hover {
  @media (hover: hover) { &:hover { @slot; } }
  &[data-preview~="hover"] { @slot; }
}
@custom-variant focus-visible (&:focus-visible, &[data-preview~="focus"]);
@custom-variant active (&:active, &[data-preview~="active"]);
```

Then a row of `<Button data-preview="hover">` renders the hover state at rest. ⚠️ **If the theme added
an unlayered focus rule** (the solid-outline treatment in `shadcn-mapping.md` §Focus), add
`[data-preview~="focus"]` to that selector too, or the focus column shows nothing.

Note the `hover` variant keeps its `@media (hover: hover)` guard — which is the same capability gate
`transitions` requires, so the matrix does not reintroduce a sticky hover on touch.

### Coverage: the page must demonstrate what the scaffold installed

Because we install **everything**, "which components are missing from the showcase" is a question
with a mechanical answer. List the component files that no showcase file imports, and work the list
to zero:

```bash
comm -23 \
  <(ls components/ui/*.tsx | xargs -n1 basename | sed 's/\.tsx$//' | sort) \
  <(grep -rhoE 'from "@/components/ui/[a-z-]+"' app/showcase components 2>/dev/null \
      | sed 's|.*/||; s|"||' | sort -u)
```

`add --all` installs both `toast` and `sonner` on Base UI projects, so show `sonner` in Feedback
beside `toast` rather than leaving it as a permanent orphan on the list.

### The page is a server component — four things need a client wrapper

The sections are `async` server components, which is what lets them read copy with
`getTranslations`. Four kinds of demo cannot live there, and each is one small `"use client"` file
under the route, not a reason to make the section a client component:

| What | Why it cannot be rendered from the section |
|---|---|
| **Chart** | the chart elements come from recharts, which is client-only; a server file cannot import them |
| **Calendar** | a react-day-picker locale object carries functions, and functions cannot cross the server→client boundary. Without the locale the day cells hydrate with two different date formats (measured: `data-day="27/09/2026"` server, `9/27/2026` client) |
| **toast** | there is nothing to show until something calls `toast.add` — it needs a trigger, and the `Toaster` has to be mounted in the app's own layout |
| **Command** | see the scroll item below: it needs `open` state |

Everything else — dialogs, sheets, popovers, menus, accordions, carousels, the questionnaire — renders
straight from the server section as long as no handler is passed, because the primitive's own file
carries `"use client"`.

### Compose the primitives, do not restyle them

The design-system lint (`design-system-lint.md`) runs on the showcase too, and `shadcn/no-restyle`
is where a showcase gets caught: a frame around a primitive is layout, a border or a padding **on**
it is a restyle. Put the border, the radius and the padding on a wrapping `div`
(`ScrollArea`, `ResizablePanelGroup`, `Empty`, `Command`, `MessageScrollerViewport`, `TabsContent`,
`Skeleton`, `TableCell`, `AvatarFallback` all trip the rule otherwise). If a demo needs a treatment
no variant provides, that is the signal to add a variant to the primitive — which is the rule's
whole point.

### Before declaring it done

Beyond the visual comparison in `SKILL.md` §Visual verification:

1. The page **loads at `scrollY === 0`**, checked on a **cold tab** — a reload restores the previous
   position and hides the defect. Anything else means a component is stealing scroll on mount. An
   inline command palette does exactly this: measured on fit-room, 2026-10-09, the page landed
   **12 458px down**, at the top of the section holding it. Don't fight it with a sentinel
   `value` — give Command the `CommandDialog` and a real ⌘K trigger, which is where a product puts
   it anyway, and the overlay tier gets its trigger for free.
2. **No horizontal overflow** at 375px and 1280px: `document.documentElement.scrollWidth <= innerWidth`.
   Check it in a browser that really is 375 wide — an emulated viewport clamped to the pane width
   (577px, in the Claude browser pane) reports no overflow when there is some. Two recurring
   offenders: **the carousel arrows**, positioned `-left-12 / -right-12` *outside* the frame, so the
   carousel needs `mx-12` on a phone; and **any wide table**, which needs its own
   `overflow-x-auto` wrapper (shadcn's `Table` already has one, a hand-written `<table>` does not).
3. **Toggle dark once** and look at it. The contrast pairs re-measure themselves on the theme
   change — if a pair shows the same ratio in both themes, its tokens are not theme-aware.
4. No console errors. `MISSING_MESSAGE` counts: a key that only the showcase uses is a key nobody
   else will notice is absent.

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

1. **Build the page from the sections above, against the components the project actually installed** — not by copying a skeleton. Route: `app/showcase/page.tsx` (or `app/design-system/`), one file per section under it (`_sections/`) from the start — thirteen sections do not fit in one readable file. Copy `assets/showcase/preview-states.css` into `tailwindCssFile` and the two helpers into `_components/` beside them (**its README says why that folder and not the shared one**), then read `showcase-template.tsx` for how a section should *look* in our voice.
   ⚠️ **Do not ship a generic sixty-component skeleton.** The page is built from this project's set and this project's copy; a template that renders every component with lorem labels is the thing that makes a showcase read as generated, which is what `anti-slop-fallbacks.md` exists to prevent.
2. Replace each constant array (`COLORS`, `TYPES`, `RADII`, `SPACING`) with values from the project's DESIGN.md.
3. Replace every domain-contextual sample with copy extracted from PRD.md, screenshots, or asked from the user.
4. Replace the brand-voice taglines (h1 + each h2) with brand-specific wording.
5. Update the `Eyebrow` text in section 1 to `<PROJECT NAME> design system`.
6. Replace the Do's/Don'ts cards' bullets with the literal list from DESIGN.md `## Do's and Don'ts`.
7. Run `pnpm run build` and verify HTTP 200 on `/showcase`.
