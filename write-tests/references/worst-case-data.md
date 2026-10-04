# Worst-case data — the test that finds what unit tests can't

A unit test asserts the logic. This finds what breaks when the *data* is realistic: a hyphenated
surname, an unbreakable email, a count of exactly 1, an empty list, a translated label. The component
is not badly built — **it was built against kind data, which is how nearly everything gets built.**

Distilled 2026-10-04 from [emilkowalski/skills](https://github.com/emilkowalski/skills) (MIT);
`dev-flow/references/resources.md` has the row. It is the data-shaped sibling of
`design-md-to-app/references/anti-slop-fallbacks.md` §3, which already insists on realistic
placeholder names — same instinct, opposite purpose: that rule makes a demo look real, this one makes
it break.

## Two rules that decide whether this is worth doing

1. **Plausible or schema-backed, never random.** `"aaaaaaaaaaaaaaaa"` proves nothing — the designer
   will rightly say "that never happens" and stop listening. Every value is either a realistic example
   or **the actual limit from the Zod schema, the DB column, or the form's `maxLength`**. If you find
   no limit, that is itself a finding: say "unbounded".
2. **Change the data, not the component.** The worst case enters through the same boundary the demo
   data does — the fixture, the mock, the props, the API stub. **Hand-editing markup or CSS to produce
   a break tests your edit, not the component.**

And one that decides whether anyone acts on it: **report before fixing**. Several breaks are design
decisions (truncate or wrap? what does an empty role show?). List them, propose a fix for each, stop.

## Phase 1 — map every rendered value

| Field | Source | Type | Limit | Optional? |
|---|---|---|---|---|
| `name` | `member.name` | string | 255 (`schema.ts:14`) | No |
| `email` | `member.email` | string | **none found** | No |
| `count` | `workspace.memberCount` | int | — | No |

Include the values people forget: counts in headers, relative timestamps, badge and status text,
button labels that come from data, tooltips, avatar images — and **the list itself, because its length
is a value too**. Note where frontend and backend disagree: a 50-character input saving into a
255-character column means something longer *will* arrive, through an import or the API.

## Phase 2 — one fixture, many failures

Assemble a single worst-case fixture beside the existing demo data, same shape and same file
conventions. **Spread the failures across the first few rows** rather than stacking them all into row
1 — the first rows are what is on screen, and real data mixes.

Plus the three that are not one dataset: **empty** (zero items, the no-results state), **one** (a
single item, and every count at exactly 1 — pluralization), **huge** (the realistic upper bound; 1,000+
rows if the list is unpaginated, which is a performance break as well as a visual one).

### The catalog

**People and names** — `Aleksandra Wiśniewska-Kowalczyk` (long, hyphenated, diacritics; the hyphen is
a line-break point) · `Christopher Alexander Montgomery III` (naive first+last initials give `CI`) ·
`Jo` and `J` (two letters and one; naive initials, and a tiny click target if the name is the link) ·
`Đặng Thị Ngọc Hân` (stacked diacritics, clipped by a tight `line-height` + `overflow: hidden`) ·
`王秀英` (CJK, no spaces — "first + last word" logic finds one word) · `نور الهدى عبد الرحمن` (RTL;
icons land on the wrong side without `dir="auto"`) · `María José de la Cruz y Fernández` (lowercase
particles break initials and "sort by last name") · `dana` (initials should still uppercase) ·
`🦊 Fox` (`.charAt(0)` returns half a surrogate pair → `�`) · `👩🏽‍💻 Priya` (a ZWJ sequence whose
`.length` is 7+) · `  Sam   Lee ` (leading, trailing and repeated spaces) · *no name at all, only an
email*.

**Unbreakable strings** — they have no spaces, so the browser has nowhere to wrap:
`bartholomew.fitzgerald@northwind-industries-holdings.example.com` (the classic — pushes every sibling
off the row) · `a@b.co` (shortest realistic; a layout that assumed long looks empty) ·
`first.last+billing@example.com` (validation that rejects `+`) · a long URL with a query string
(end-truncation hides the part that differs) · a UUID · `Q3 Board Deck — FINAL (revised) v12.pdf`
(end-truncation hides the version *and* the extension). Use `example.com` / `.test` domains so a
fixture never points at a real inbox.

**Labels from data** — `Senior Product Design Engineer, Platform Infrastructure` ·
`Benachrichtigungseinstellungen` (a 30-character German compound with no spaces) ·
`Paramètres de confidentialité et de sécurité` (**UI copy runs ~30% longer in translation** — and
golden rule ② means every project has at least two locales, so this is not hypothetical) · twelve
tags on one item (needs a `+8` overflow) · one tag wider than its container · `Untitled`, `""`, `"   "` ·
`<script>alert(1)</script>` and `&amp;` and `**bold**` (must render as literal text) · a newline in a
single-line field · a 2,000-character pasted description.

**Numbers** — `0` (zero states, division by zero in a percentage) · `1` ("1 members", "1 days ago") ·
`1284` (needs a separator) · `12345678.9` as currency · `-42.5` · `0.1 + 0.2` rendered raw ·
`142%` / `-3%` (a progress bar past its bounds) · `null` / `undefined` / `NaN` · `1.284` in `de-DE`
vs `1,284` in `en-US` · a value changing live `99` → `100` (a width jump without `tabular-nums`).

**Collections** — 0 · 1 · exactly page size, and page size + 1 (off-by-one in "Showing 40 of 40", an
empty page 2) · 1,000+ unpaginated · one item 10× the size of the others · items with identical names.

**Time** — now ("0 seconds ago" instead of "just now") · 12 days / 11 months / 3 years ago (switch to
an absolute date after a week) · a future date · `1970-01-01` · `2025-12-31T23:30:00-08:00` (a
different day in UTC and the user's timezone) · `1,284 hours`. Use `Intl.RelativeTimeFormat` and
`Intl.DateTimeFormat`, never hand-built strings.

**Images** — an avatar URL that 404s · no avatar at all (test the fallback itself) · a 4000×200
panorama and a 200×4000 tall image (distortion without `object-fit: cover`) · a dark logo in dark
mode · a slow-loading image (layout shift without `aspect-ratio`).

**States** — loading (skeletons that don't match the final layout) · an API error (or worse, a raw
`TypeError` shown to the user) · partial data, some optional fields filled and others not in the same
list · every enum value at once (badge widths vary) · no permission · **the current user in the list**
("You" labels, actions that shouldn't apply to yourself).

**Environment** — not data, but checked the same way: the container at **320px**, in a narrow sidebar
(a component designed full-width reused in a 280px column), at 2560px, at **browser zoom 200%**, in
dark mode, with `dir="rtl"`, and on a touch device (**hover-only actions — the `•••` that appears on
hover — are unreachable**).

## Phase 3 — the toggle, dev-only

A segmented control, **Demo data / Worst case / Empty / One / 1,000 rows**, swapping the fixture at
the data boundary. A `?data=worst` URL param read where the fixture is chosen keeps the selection
across a reload. Fixed bottom-centre, plainly chrome — **it is not part of the design under test**, so
a grey track, a white pill, system font, and no animation on the content when switching.

**It never ships to production**: gate it on the dev environment or keep it inside a prototype route.

## Phase 4 — the failure signatures

Each of these is visible in a screenshot, and the cause in the middle column is almost always it.

| What you see | Cause | Fix |
|---|---|---|
| Avatar or icon squished into an oval | a flex child shrinking | `flex-shrink: 0` on the avatar, icon, any fixed-size box |
| Text overflows instead of wrapping or truncating | flex/grid child has `min-width: auto` | `min-width: 0` on the text column (`minmax(0, 1fr)` in grid) |
| An email or URL runs past the edge | no break opportunities in the string | `overflow-wrap: anywhere` on that element |
| The trailing `•••` pushed off-screen or clipped | the middle took all the space | `min-width: 0` on the middle, `flex-shrink: 0` on the action |
| A badge wraps onto two lines | the badge was allowed to shrink | `white-space: nowrap; flex-shrink: 0` — and decide what yields instead |
| An avatar centred against a three-line name looks adrift | `align-items: center` on rows of varying height | top-align once text can wrap |
| The last row cut off mid-glyph | fixed height, no fade or scroll affordance | a visible scrollbar or a fade mask; check the `overflow` was intended |
| A long word breaks mid-word in a heading | `word-break: break-all` | `overflow-wrap: anywhere` breaks only when it must |
| Wrong initials (`J` for "Jo", `CI` for "… III", `�` for an emoji) | `.split(' ')[0][0]`-style code | grapheme clusters (`Intl.Segmenter`), first + last word, icon fallback |
| An orphaned `—` where the role was | a placeholder rendered for a missing optional field | omit the line, or reserve its height on purpose |
| "1 members", "0 member" | a hardcoded plural | `Intl.PluralRules` |
| Numbers jitter as they update, columns misalign | proportional figures | `font-variant-numeric: tabular-nums` |
| `1284`, `NaN`, `undefined` rendered | a raw number | `Intl.NumberFormat` with the user's locale; guard null |
| A long translated button label overflows | a fixed-width button | width from content with `min-width`, never a fixed `width` |
| Vietnamese or Thai diacritics clipped | tight `line-height` with `overflow: hidden` | looser leading, or no clipping on text boxes |
| A broken-image icon in the avatar | no `onError` fallback | fall back to initials; `object-fit: cover` |
| Truncated text with no way to read it | `text-overflow: ellipsis` and nothing else | a `title` or tooltip, and the full value in a detail view |
| 1,000 rows stutter | every row rendered | virtualize (Virtuoso) or paginate — and say which |
| Raw `<b>`, `&amp;` or `**text**` on screen | the wrong escaping layer | escape once, at render; never `dangerouslySetInnerHTML` on user data |

### Truncate, wrap, or clamp — decide per field, never globally

- **Wrap** what the user needs in full to identify something: names, titles in a detail view. Two
  lines is fine; four means the column is too narrow.
- **Truncate at the end** for secondary metadata where the start carries the meaning: a role, a
  description, a last-message preview. Always pair it with a way to see the full value.
- **Truncate in the middle** when items differ at the *end*: file names, emails sharing a long domain,
  paths, hashes. End-truncation makes them identical.
- **Clamp** (`line-clamp: 2`) for multi-line previews in cards, so card heights stay predictable.
- **Never truncate** numbers, amounts, dates, or anything the user compares.

## Phase 5 — report, in three parts

**① What broke**, worst first, with a severity: **Broken** (content unreadable, action unreachable,
wrong data shown) · **Ugly** (readable but visibly wrong) · **Fragile** (fine now, one realistic step
away — no limit, no fallback). One row each, with `file:line` for the fix.

**② Decisions for you** — the breaks with more than one right answer, one line each with a
recommendation.

**③ What held up** — the worst cases the component already handles. This proves the test was real and
tells the user what not to touch.

## Afterwards: keep the fixture

It is the regression test for the next person who touches the component, and it costs nothing to
leave. Re-run **every** state after a fix, Demo included — a fix for the worst case must not regress
the demo. The toggle stays dev-only either way.
