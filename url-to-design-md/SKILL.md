---
name: url-to-design-md
description: 'Measure a live website or a signed-in web app and turn it into a DESIGN.md (Google design.md spec) plus shadcn theme, a visual review page and social slides. Reads COMPUTED styles from the rendered DOM — colour roles with usage share, the type scale at two viewports, spacing grid, radii, shadows, motion, components and states — never the authored stylesheet, so it works on Tailwind and CSS-in-JS. Use when the user hands over a URL and wants to start a project from an existing design: "parti da questo sito", "estrai il design system da <url>", "rifacciamo questo sito", "measure this app''s design". Produces a review page with the decisions the measurement could not settle, then writes `.workflow/DESIGN.md` only after the user approves. Not for: Figma (use `figma-to-design-md`), raster images (use `image-to-design-md`), building the app (use `design-md-to-app` after), one page from a screenshot (use `screenshot-to-page`).'
---

# URL → DESIGN.md

Take a live site or a signed-in app, measure what it actually paints, and come back with a design
system the user can argue with before any of it enters the project.

The third entrance to `DESIGN.md`, beside `figma-to-design-md` and `image-to-design-md`. The exit is
identical, so nothing downstream changes: `wireframe-canvas` → `design-md-to-app`.

## Why this exists, in one measurement

`image-to-design-md` says it of itself, at line 79: *"This is the highest-confidence-loss step.
Vision LLMs cannot read fontFamily metadata that doesn't exist in raster pixels"*, and at 163:
*"everything is a guess"*. That is the honest cost of starting from a screenshot.

When the source is a URL, **none of it has to be guessed**. `getComputedStyle` gives the family, the
exact pixels, the line-height ratio, the tracking in em and — through a 1×1 canvas — the hex behind
an `oklch()`. This skill exists to replace an estimate with a measurement.

## When it applies

- The user gives a URL and wants to start from it: *"parti da questo sito"*, *"rifacciamo
  adastrasicily.com"*, *"estrai il design da questo"*.
- `dev-flow` routes here from `empty` or `prd_drafted` when there is a URL rather than a Figma or
  images.
- The source may be **their own site** (a redesign) or **somebody else's** (a reference). Ask which,
  because it changes what may be produced — see *Whose site is it* below.

If the user has a Figma, prefer `figma-to-design-md`: a Variables panel beats any measurement.

## Two modes, and it is not a flag

| | `site` | `app` |
|---|---|---|
| Repeated chrome | **deduplicated** — a header on every page would outvote the content | **never** — the sidebar *is* the product; deduplicating it throws away the reason for the run |
| Components read | hero, sections, bands, cards, nav, buttons | sidebar + collapsed width, topbar, table row and header height, field height and label position, modal and drawer widths, toast, status colours, focus ring, density |
| Section rhythm | light/dark bands | meaningless, omitted |
| Text kept | short UI labels and CTAs; five quotes **only** from public pages | **no strings at all** — counts, lengths, case statistics only |
| Responsive | `clamp()` from the 390/1440 pair | a table at 1440 and at 390 are **two components**, not one with a clamp |

The `app` text rule is not caution. A signed-in app shows customer names, invoice numbers and email
addresses, and without the rule they would travel into the snapshot, the review page and the slides.

## The six steps

### 1. The URL, and three questions before touching anything

Ask, in this order, and do not start until all three have an answer:

1. **Whose site is it?** Theirs, or somebody else's.
2. **`site` or `app`?** If it is behind a login, it is `app`.
3. **Which pages?** Home plus three or four that carry different furniture — a product page, a
   pricing page, a form. For an app: a list, a detail, a form, a settings screen.

### 2. Measure

Two delivery paths for the same `scripts/extract.js`. Pick by what the page is served over.

**Local or http (a dev server, a preview, the fixtures here).** Start the collector and let the page
POST straight to disk:

```bash
python3 url-to-design-md/scripts/collect.py --out .workflow/design-source --port 8781
```

It prints **the collect URL, which carries a per-run secret** — a loopback socket is not a
boundary, and without the secret any page the browser has open could write into the project. Copy
that URL; a wrong one is refused with a clean 404 rather than a dropped connection.

```js
window.__EXTRACT_OPTIONS__ = { mode: "site", collect: "<the URL it printed>" };
// load scripts/extract.js, then: await window.__SNAPSHOT__
```

**A remote https page.** Mixed content forbids that page from reaching a localhost collector, so the
only mechanism left is a download. **Ask the user first** — it writes into their Downloads folder —
then move the file into `.workflow/design-source/` immediately and confirm it arrived. Leaving files
in somebody's Downloads is not a side effect to take quietly. The user can also paste the script
into their own DevTools, which is the same file and the right answer when a login or a bot challenge
is in the way.

**Per page, do all of this:**

- `resize_window` to **1440×900**, then **390×844**. The pane's own width is the viewport otherwise,
  and a measurement at 474px is a measurement of the pane.
- Give the page **real focus** (one `Tab` keypress). Measured 2026-10-21: `.focus()` sets
  `:focus-visible` and the ring is readable, *but only while `document.hasFocus()`*. In a background
  tab the same call reports `outline: none`, which reads exactly like a site that ships no focus
  ring. The extractor refuses to write focus states without focus rather than inventing an
  accessibility finding.
- If the app has a **theme toggle**, run both themes. An app's dark theme is a real second system;
  a site's dark bands are not.

### 3. Analyse, and look at it

```bash
python3 url-to-design-md/scripts/analyze.py .workflow/design-source/snapshot-*.json \
  --out .workflow/design-source --mode site
python3 url-to-design-md/scripts/render_guide.py .workflow/design-source/tokens.json \
  --out .workflow/design-source
python3 url-to-design-md/scripts/verify.py .workflow/design-source/brand-guide.html \
  --inpage .workflow/design-source/verify-390.json
```

`cp tokens.json tokens.measured.json` before the first change: that frozen copy is what the
divergence record is computed against.

**Never show the user a guide that has not passed `verify.py`.** It reads the rebuilt controls'
computed styles back and fails when one does not equal its token — a guide with one literal where a
`var()` belongs looks perfect and has stopped representing the system.

### 4. The questionnaire — see `references/review.md`

Show the guide. Then work through the decisions the measurement raised, each with a picture.

### 5. Write it

```bash
python3 url-to-design-md/scripts/make_design_md.py .workflow/design-source/tokens.json \
  --out .workflow --measured .workflow/design-source/tokens.measured.json
```

`.workflow/DESIGN.md` is the only file that enters the flow. `design-source.md` sits beside it and
nothing downstream reads it.

### 6. Hand over

`update_meta.py set-phase` as the contract says, then `wireframe-canvas` → `design-md-to-app`.
The DESIGN.md uses the spec's own semantic names (`on-surface`, `surface-container`); turning those
into shadcn's slots is `design-md-to-app`'s job and is already written there. **Do not write
Tailwind slot names into the DESIGN.md** — it would break the consumer.

## Whose site is it

| | Theirs | Somebody else's |
|---|---|---|
| DESIGN.md, tokens, shadcn theme, guide | yes | yes |
| Slides (`render_media.py`) | yes — a deliverable | **no.** A carousel of a competitor's brand system is internal material, not something to publish |
| The divergence step | recommended | **obligatory** |

A rendered artefact that looks like the source is *more* tempting to ship unchanged, not less. The
tool that helps you diverge also makes the clone prettier, which is why the record is not optional.

## Never

- **Never bypass a bot check.** No user-agent spoofing, no pointer simulation, no "stealth" mode.
  When a page challenges, hand it to the user in their own browser.
- **Never handle credentials.** The user signs in; the script reads what is on the screen.
- **Never send a snapshot anywhere.** There is no `fetch` in `extract.js` except the localhost
  collector the caller names.
- **Never copy a logo, a font file or a photograph.** A logo becomes a dashed box at its measured
  size and colour; a font is named and linked.
- **Never fill a slot that was not observed.** A value nobody measured, sitting in a measured file,
  is indistinguishable from one that was.

## AI slop, and the one form of it this skill can produce

The repo already owns this: **`design-md-to-app/references/anti-slop-fallbacks.md`** — thirteen
rules, ported from taste-skill. Read it there; it is not repeated here.

**Most of it does not fire during a measurement, and that is by design.** Those rules apply when a
value is *missing* and something has to be invented. Here nothing is missing: every value was read
off a real page. Its own policy says so — a token the DESIGN.md defines explicitly wins over the
fallback. So adidas.it's pure `#000000` ink stays pure black, measured, against the "no pure black"
rule, because it is a fact about that site and not a default somebody reached for.

**The slop risk here is the opposite one, and it belongs to step 4.** When the user moves away from
the measurement, the generic look is where "be a bit more creative" lands: the cream ground with a
terracotta accent, Inter or Space Grotesk as the safe face, `rounded-lg` on everything, the
purple-to-blue gradient hero. The measurement protects against this while it is untouched; the
divergence is where the protection ends.

So `analyze.py#slop_drift` compares the final tokens with the frozen measured ones and reports what
moved **away from the source and towards the average**. Only drift counts: a site that genuinely
uses Inter on cream is that site, and flagging it would punish an accurate measurement. A value that
was something else and is now one of those is a question, and the answer goes in `design-source.md`
with everything else.

## What this produces

In `.workflow/design-source/`: `snapshot-*.json` (the raw evidence), `tokens.json` (the single
source), `tokens.measured.json` (frozen), `tokens.css`, `shadcn.css`, `tokens.dtcg.json`,
`brand-guide.html`, `verify-*.json`, `decision-*.html`, and `slide-*.png` when the site is the
user's own.

In `.workflow/`: `DESIGN.md`, and `design-source.md` beside it.

## Dev-flow contract

This skill participates in the dev-flow workflow. See `references/contracts.md` for the canonical
schema. Key facts:

- Reads and writes `.workflow/meta.json`; writes `.workflow/DESIGN.md`.
- Runs at phase `empty` or `prd_drafted`; it **never** changes `phase` by itself.
- `stack.ui` is not decided here. This measures a source; `design-md-to-app` builds with shadcn.

## References

- `references/measure.md` — what to measure, and the trap behind each correction
- `references/review.md` — the questionnaire: the derived questions, the pictures, the skip
- `references/artifacts.md` — the guide, the slides, and why the video is deferred
- `references/contracts.md` — the dev-flow contract (vendored, byte-identical)

## Scripts

- `scripts/extract.js` — the injectable extractor, one file for both delivery paths
- `scripts/collect.py` — the local collector, so nothing passes through Downloads or the agent
- `scripts/analyze.py` — snapshots → tokens, and the questions the review step asks
- `scripts/render_guide.py` — tokens → the review page
- `scripts/render_decision.py` — one decision, drawn side by side
- `scripts/render_media.py` — eleven scenes → twelve slides
- `scripts/verify.py` + `scripts/verify_page.js` — the gate, static and in-page
- `scripts/make_design_md.py` — the DESIGN.md and the divergence record
- `scripts/test_analyze.py` — 26 tests against a page whose true values are written down
