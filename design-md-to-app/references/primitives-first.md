# Primitives first — read this before writing any component

> Golden rule 3 (`dev-flow/references/contracts.md`), **«the primitive wins»**. Mandatory reading for
> `design-md-to-app`, `screenshot-to-page` and any agent about to write a `.tsx` that renders UI. Written
> 2026-10-12 after smart-travel's audit (§Why).

## The rule

1. **Every piece of UI is a primitive from `components/ui/`, used as it is.** List the directory first
   (`ls components/ui` — in a shadcn monorepo `packages/ui/src/components`). Domain components are
   compositions of primitives, nothing else.
2. **The primitive wins.** When the board (wireframe canvas, screenshot, Figma) differs slightly from the
   primitive — 16 px radius against the Card's 12, a border against its ring, a hover tint — use the
   primitive unchanged and **correct the board**. A visual difference never justifies an element by hand,
   and never a set of classes that redraws the primitive.
3. **No primitive or variant fits → stop and ask the user.** Name the pattern, the closest primitive and
   the variant you would add, and propose it for DESIGN.md. A new variant is added only for a role that
   truly does not exist, first in DESIGN.md, with the user's yes, then in the primitive's `cva`. Until then
   the work on that piece **stops**. Never an element by hand, never `eslint-disable`, never "for now".

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
that matches the board says nothing either: a hand-made button identical to the board passes it. The proof is
`design/no-handmade-ui` at zero on the files you touched, and no raw element in the diff
(`spec-review`, Standards axis, check 4).

## Why

smart-travel (Next 16, shadcn on Base UI), 2026-10-12: after three days of building, an audit found 238
hand-made elements where a primitive existed — 84 div-cards, 62 `<button>`, 34 `<label>`, 22 alert boxes,
14 `<a>`, 11 span-badges, plus hand-written tab/radio roles, `<hr>`, `<img>`, `<details>`. The rule was text
only; the lint banned imports, which a raw element does not make; `shadcn/no-restyle` punished restyling a
primitive, so when a board did not match a variant the agent wrote the element by hand — one left the
comment «the Button's ghost turns light grey on hover, wrong here», another reported «the badge is a span…
because Badge has no variant», and the orchestrator read it and moved on. 57 of the 71 buttons came in one
night of 24 parallel PRs, each copying the neighbouring file. The boards themselves were drawn with radii and
borders the primitives do not have. Each of those is now closed: the rule in the lint, the guard at write
time, this table before writing, the boards drawn with the primitives' real measures, and «stop and ask».
