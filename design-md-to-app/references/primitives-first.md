# Primitives first — read this before writing any component

> Golden rule 3 (`dev-flow/references/contracts.md`), **«the primitive renders the design»**. Mandatory
> reading for `design-md-to-app`, `screenshot-to-page` and any agent about to write a `.tsx` that renders UI.
> Written 2026-10-12 after smart-travel's audit (§Why), and corrected the same day (§Why the primitive is
> tuned).

## The rule

1. **Every piece of UI is a primitive from `components/ui/`.** List the directory first
   (`ls components/ui` — in a shadcn monorepo `packages/ui/src/components`). Domain components are
   compositions of primitives, nothing else.
2. **The primitive renders the design.** When the board (wireframe canvas, screenshot, Figma) or a screen
   the user already approved differs from the primitive — 16 px radius against the Card's 12, a border
   against its ring, a hover tint, the background of a selected item, a weight, a padding — **tune the
   primitive**: change its `cva` variants and the DESIGN.md tokens it reads until it renders the board,
   and verify it pixel by pixel. Never accept the drift, never write the element by hand, never rebuild the
   look with classes at the call site.
   - **A difference the whole design shares** (every card on the board is 16 px) is a **token or a default
     variant**: record it in DESIGN.md (`rounded`, `components`), then change the default in the `cva`.
   - **A difference one role has** (the selected chip of a filter bar) is a **new variant**: first in
     DESIGN.md's `components` block, then in the `cva`, then used by name. Say in the report which variant
     was added.
   - **The board changes only when the user decides to change the design.** Never "correct" a board to
     match what a primitive happens to render.
3. **Stop and ask the user only when the primitive cannot be tuned**: no primitive covers the pattern at
   all, or rendering the board would change the primitive's markup, handlers, state or ARIA wiring (a fork).
   Name the pattern, the closest primitive and what it would take. Never an element by hand, never
   `eslint-disable`, never "for now".

## Converting existing screens — pixel parity

A screen already built (hand-made elements, a retrofit, a screen the user approved) is converted with a
before/after proof, so the conversion cannot change what the user sees:

1. **Before** touching the file, screenshot the route at every width and state the board has (1440 and 390,
   plus empty/error/selected/hover where it matters), with fixed data, fonts loaded and motion reduced:
   Playwright `page.screenshot({ fullPage: true, animations: "disabled" })`.
2. Convert to primitives. Where a primitive renders differently, tune it (rule 2) — not the call site.
3. **After**, the same screenshots, then a pixel diff of each pair:
   `npx pixelmatch before.png after.png diff.png 0.1`, or ImageMagick
   `compare -metric AE before.png after.png diff.png`. **The target is zero changed pixels**
   (anti-aliasing tolerance only). Read `diff.png`: every red area is a token or a variant still to tune.
4. A diff left on purpose is a design change: it needs the user's yes, and the board changes with it.

Tuning a default variant changes every screen that uses it: re-run the parity check on the other routes
that render that primitive before calling the conversion done.

## Pattern → primitive

shadcn names (any base). Coss/UI: `CardPanel` for the card body, `Menu` for `DropdownMenu`, `TabsTab` /
`TabsPanel`, `Radio`, `Meter`, `Frame`. Standalone Base UI: the project's wrapper in `components/ui/` of the
same name. `render={<x/>}` is Base UI's composition prop; on a Radix base it is `asChild`.

| Pattern on the board | Primitive | Not this |
|---|---|---|
| A link inside a sentence | `Button variant="link"` (with `size="inline"` where the project defines it) and `render={<Link/>}` | `<a className="underline">` |
| A link styled as a button | `Button render={<Link href/>}` | `<Link className="h-9 rounded-md bg-primary">` |
| A download, `tel:`, `mailto:` | `<a className={buttonVariants({ variant })}>` | a raw `<a>` with classes |
| An action | `Button` with its variant and size | `<button className=…>` |
| A clickable row or tile | `Item render={<button/>}` or `render={<Link/>}` (`ItemMedia`, `ItemContent`, `ItemActions`) | `<div onClick>`, `<button className="flex rounded-xl border…">` |
| A chip / filter pill / segmented control | `ToggleGroup` + `ToggleGroupItem` (single or multiple) | `<button aria-pressed>` |
| A choice tile (radio or checkbox as a card) | `FieldLabel` around `Field orientation="horizontal"` with `RadioGroupItem` / `Checkbox` | `<label className="rounded-xl border has-[:checked]:…">` |
| A form label | `Label`, or `FieldLabel` inside `Field` | `<label>` |
| A field's error | `FieldError` | `<p className="text-destructive">` |
| A text input, number, OTP | `Input`, `InputGroup`, `InputOTP` | `<input>` |
| A select | `Select`, `NativeSelect`, `Combobox` | `<select>`, `role="listbox"` |
| A section, panel, summary box | `Card` (`CardHeader`, `CardContent`, `CardFooter`; `size="sm"`) | `<div className="rounded-xl border p-4">` |
| A dashed placeholder / nothing yet | `Empty` (`EmptyMedia`, `EmptyTitle`, `EmptyDescription`) | `<div className="border-dashed …">` |
| A notice, warning, error box, banner | `Alert` with its variant | `<div className="bg-destructive/10 p-3">`, `role="status"` on a tinted div |
| A status label / count / tag | `Badge` with one of the variants in `badge.tsx` | `<span className="rounded-full px-2 text-xs bg-…">` |
| A divider / column rule | `Separator` (`orientation="vertical"`) | `<hr>`, `<div className="h-px bg-border">` |
| Tabs | `Tabs`, `TabsList`, `TabsTrigger`, `TabsContent` | `role="tab"` |
| A menu of actions | `DropdownMenu` | `role="menu"` |
| A disclosure / FAQ | `Collapsible`, `Accordion` | `<details>`, `<summary>` |
| A modal / side panel | `Dialog`, `Sheet`, `Drawer`, `AlertDialog` | `<dialog>`, `role="dialog"` |
| Progress | `Progress` | `<progress>`, `<meter>`, `role="progressbar"` |
| Tabular data | `Table` | `<table>` (an `sr-only` table for a chart is allowed) |
| A person or organisation | `Avatar` | `<img className="rounded-full">` |
| Any other image | `next/image` | `<img>` |
| A hint on hover | `Tooltip` | `role="tooltip"` |
| A loading placeholder | `Skeleton` (or the project's loader from DESIGN.md) | a pulsing `div` |
| A card inside a card | rows with `Separator`, a titled section, or a soft background (`bg-muted`, no border, no shadow) | a bordered box inside a `Card` |

## Allowed raw elements — the complete list

- an element passed as a primitive's `render` prop (or the child of an `asChild` primitive): the primitive
  owns its behaviour and styling;
- an `<a>` styled by `buttonVariants(…)` — downloads, `tel:`, `mailto:`;
- `<input type="file">` (hidden behind a `Button`) and `<input type="hidden">`;
- a `<table className="sr-only">` that gives a chart its accessible data;
- a file that renders no DOM: `next/og` / Satori images, react-email, react-pdf / Forme;
- an exception recorded in the preset's `designExceptions` block with its reason, e.g. map marks drawn
  inside MapLibre's own markers. Never for a missing variant.

Everything else is reported by `design/no-handmade-ui` (lint, `error`) and refused at write time by the
guard (`scripts/guard/primitives-guard.mjs`, a PreToolUse hook): the message names the primitive to use.

## What not to take as proof

A green lint before 2026-10-12 said nothing about primitives: a raw element imports nothing. A screenshot
that matches the board says nothing about primitives either: a hand-made button identical to the board passes
it. And a lint at zero says nothing about the design: primitives used as they ship pass it while the screen
drifts from the board. The proof is both halves — `design/no-handmade-ui` at zero on the files you touched
with no raw element in the diff (`spec-review`, Standards axis, check 4), **and** the pixel diff at zero
against the board or the screen before the change.

## Why

smart-travel (Next 16, shadcn on Base UI), 2026-10-12: after three days of building, an audit found 238
hand-made elements where a primitive existed — 84 div-cards, 62 `<button>`, 34 `<label>`, 22 alert boxes,
14 `<a>`, 11 span-badges, plus hand-written tab/radio roles, `<hr>`, `<img>`, `<details>`. The rule was text
only; the lint banned imports, which a raw element does not make; `shadcn/no-restyle` punished restyling a
primitive, so when a board did not match a variant the agent wrote the element by hand — one left the
comment «the Button's ghost turns light grey on hover, wrong here», another reported «the badge is a span…
because Badge has no variant», and the orchestrator read it and moved on. 57 of the 71 buttons came in one
night of 24 parallel PRs, each copying the neighbouring file. The boards were drawn with radii and borders the
primitives did not have, and nobody tuned the primitives to them. Each of those is now closed: the rule in the lint, the guard at write
time, this table before writing, and tuning the primitive instead of writing around it.

## Why the primitive is tuned

The first version of this rule (same day) said «the primitive wins, the board is corrected». smart-travel
then converted the 238 elements to primitives **used as they ship**, and the screens changed — radii,
selected backgrounds, font weights, padding. The user rejected them: the boards were the approved design.
So the direction is the other way: the design is the target, the primitive is how it is rendered, and every
difference is closed in the primitive's `cva` and DESIGN.md's tokens — checked by a pixel diff, not by eye.
