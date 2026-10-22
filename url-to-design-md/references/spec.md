# The source specification

This skill exists to implement the prompt below, which the user supplied as the reference to work
from. It is kept here **verbatim** for one reason: the first version of this skill was written from
a reading of it rather than from it, and the difference showed up as a guide that was a report, a
`foreground` taken from a legal footer, and two pages of the thirteen simply absent.

**Rules for anyone changing this skill.**

1. A change is justified against a numbered point below, or it is a change to the spec and the user
   decides it. "It seemed better" is how the first version happened.
2. Where this skill deliberately differs, the difference is written down **here**, with the reason —
   see *Our deltas* at the end. Nothing silent.
3. §8 is not optional: *"Then screenshot every section, slide and video still, look at them, and fix
   what looks wrong."* Skipping it is how three rounds of measurement produced a report nobody had
   looked at.

---

Reverse-brand prompt for Claude (Opus, agentic coding mode)

Paste everything below the line into Claude Code (or any Claude setup with a shell, a browser and
file access). Replace the three settings at the top.

URL: https://example.com · IMAGES: `none` | `api` | `manual` · IMAGE PROVIDER (only if IMAGES =
api): e.g. Google Gemini (Nano Banana), OpenAI Images, fal, Replicate. The key goes in `.env`.
Never paste it into chat.

## Goal

Build `reverse-brand <url>`, a reusable CLI that turns a public brand website into an unofficial,
art-directed brand guide. Then run it on the URL above. The guide should look and feel like the
brand's own site, not like a report. Every value in it is measured, tokenised, and rebuilt to prove
the tokens work.

## Non-negotiables

- Mark everything "Unofficial analysis": the guide's cover, top bar and footer, every slide, and the
  video. Add "Not affiliated with or endorsed by <brand>. Trademarks belong to their owners."
- Never copy logos, font files or the brand's images. Describe them and link to the source pages. A
  logo becomes a dashed placeholder with its measured size and colour.
- Never bypass bot checks or CAPTCHAs. If headless capture gets a challenge, stop and offer two
  options: (a) `--headed`, where the user completes the check, or (b) a paste-into-DevTools snippet
  that runs the same extractor in same-origin iframes at 1440px and 390px and downloads
  `snapshot.json`.
- AI images are generated from text prompts only (never from the brand's photos as input). Each one
  is labelled "AI-generated image" wherever it appears.
- Copy is plain and technical. Section titles are standard brand-book names: Overview, Contents,
  Typography, Fonts, Colour, Layout and spacing, Components, Imagery, Voice and tone, Design tokens,
  Method. No manifestos or slogans.

## 1. Capture

- Use Playwright with an installed Chrome (launch with `--disable-gpu`; some machines hang on the
  first canvas call without it).
- Capture the home page plus 3–5 key pages, chosen by scoring same-origin links. Nav links and
  product, pricing, business and company pages score highest. Skip legal, help, login and locale
  duplicates, and take one page per top-level path.
- Use a 1440×900 viewport, plus a 390×844 pass of the home page for responsive type.
- Scroll each page to trigger lazy content. Then walk every visible element and record computed
  font, size, weight, line-height and tracking; text, background, border and fill colours
  (normalised to hex through a 1px canvas, so `oklch()`/`lab()` work); padding, margin and gap;
  radius; shadows; max-width containers; grid columns; and media stats.
- Also record button and card candidates (the painted layer can be a child of the `<a>`), header and
  nav (height, sticky, link style, logo size and colour), form fields, h1–h3, paragraphs, CTA
  labels, `:root` custom properties and media-query breakpoints.
- Exclude cookie and consent UI by id/class and by dialog text.

## 2. Analyse

- Dedupe repeated chrome: any count that is identical on every page (header and footer) is counted
  once.
- Type: cluster heading sizes within 12%, then assign roles: display, h1–h4, lead, body, small.
  Record size, line-height ratio, weight and tracking in em. Match the mobile size per role and emit
  `clamp()`. Report the scale ratio and its nearest named interval.
- Colour: report roles (background, surface, surface-inverse, text, text-muted, text-inverse,
  action, on-action, action-alt, accent, border) as hex plus OKLCH, with usage share. Weight text by
  characters and backgrounds by painted area. List gradients and the WCAG contrast of the most-read
  pairs.
- Layout: derive the spacing base unit (8/4/2) and separate the on-grid and off-grid values. Also
  record radii (pill vs px), container width, columns and gutter, breakpoints, and the home page's
  section rhythm (light/dark bands).
- Components: button variants (filled, outline, translucent), card variants (fill, backdrop, radius,
  padding, media) and the nav. If no forms were found, infer an input and flag it "inferred".
- Imagery: describe it in words: formats, crops, full-bleed share, object-fit, media share of page
  area, and alt-text themes.
- Voice: quote 5 lines from the site (each 15 words or fewer, with source links). Derive 3 rules
  from measurable stats: headline length, case, "you" vs "we", numbers, the "X, Y" pattern, CTA
  verbs and exclamation marks. Show the stats.

## 3. Tokens

Export CSS custom properties (fonts, type roles, colour roles, spacing, layout, radii, button, card,
input, nav) and the same set as W3C design-tokens JSON, with OKLCH next to hex. Every brand sample
in the guide must use only these variables.

## 4. The guide (this is where most of the value is)

Derive the art direction from the brand's own tokens instead of hard-coding it. Use its fonts, its
alternating light and dark grounds, its card radius, its button shape, its gradient and its declared
motion easing. The guide's own controls are the brand's rebuilt buttons.

Build it as a sequence of full pages that mirror the site's own layout patterns:

1. **Cover**: a full-bleed photo (or the brand-gradient fallback), "<brand> brand guidelines" as a
   big headline on the image, a one-line factual lede, a pill CTA, and a frosted-glass card showing
   one token (as the site's balance cards do). Add the Unofficial pill and disclaimer at the bottom.
2. **Overview**: centred headline and 4 big stats (typefaces, colours, spacing base, button
   variants).
3. **Contents**: 8 image cards, styled like the site's product cards: title bottom-left, number
   top-left, arrow top-right, slow zoom on hover.
4. **Token rebuild test**: a button and two cards built only from tokens, on the site's light and
   dark grounds, with real images in the card media.
5. **Typography**: a full-bleed chapter photo with a glass specimen card and chip tabs (Display,
   Heading, Subhead, Lead, Body). Each tab shows the role at its real size, weight, leading and
   tracking; never one size for all.
6. **Fonts**: a family card per typeface with a giant "Aa", weights and share, and a check whether
   the font is installed locally. Below it: the character set, the type scale with mobile→desktop
   values, sizes in use, and the site's declared type variables.
7. **Colour (dark page)**: a chrome or product image next to a proportional palette bar, role tiles
   (hex, OKLCH, contrast), the gradient, contrast pairs, and the full palette in a collapsible.
8. **Layout and spacing**: big facts (base, columns, gutter, container), a column diagram, a spacing
   staircase, radius tiles, breakpoints and the section rhythm.
9. **Components (dark page)**: an ordered material image beside the title, then a gallery of
   measured button variants on their grounds, the nav mock, cards and the form input.
10. **Imagery**: a photo mosaic with labelled AI images, the measured facts, and source-page links.
11. **Voice and tone**: a split page (photo plus facts), then large quoted lines and 3 numbered rule
    cards.
12. **Design tokens (dark page)**: copy, copy-JSON and download buttons, plus code panels.
13. **Method**: assumptions, run log and the image prompts table.

Motion: subtle rise-in reveals and a slow zoom on photos, using the brand's easing; honour
`prefers-reduced-motion`. Use a sticky top bar that is transparent over the cover and frosted after.
Make it responsive with no horizontal scroll at 390px.

Write two editions:

- `brand-guide.html`: no images (CSS-gradient fallbacks in every image slot), at most 150 KB, works
  offline.
- `brand-guide-hero.html`: the same guide with images embedded as WebP, each embedded once and
  reused through CSS classes.

## 5. Images (optional, depends on IMAGES)

- First study the site's photography (look, don't copy). Write `prompts.json` with ~9 slots: `hero`
  (cover), `horizon` (typography chapter), `object` (studio render for colour), `street` (lifestyle
  for voice), `sky` (clean background), `glass` (orderly material for components), `grid` (layout),
  `tokens` (tokens), plus whatever the brand needs. Use new subjects in the brand's photographic
  style, and append a suffix: "photorealistic, no text, letters, logos, brand marks, cards or app
  screens".
- `IMAGES = none`: skip; the gradient fallbacks are the design.
- `IMAGES = api`: write a small provider adapter `generate({prompt, aspectRatio, resolution}) →
  image bytes` for the chosen provider. Read the key from `.env` and never log it. Save job ids
  before polling so a crash never loses a paid image, stream downloads to disk, check the balance
  first, and log the cost per image.
- `IMAGES = manual`: print the prompts. The user generates images in any tool and drops them into
  `images/<slot>.png`. Add an `--import` step that builds the manifest from those files.
- Re-encode everything to WebP (2000px for wide images, 1400px for others) and review the results
  yourself; regenerate anything off-brand or noisy.

## 6. Social slides

Export an Instagram carousel (8 × 1080×1350: cover, typography, colour, layout, components, voice,
tokens, outro) and X images (4 × 1600×900). They use the same tokens and images. Every slide carries
an Unofficial badge, plus an AI credit when it shows a photo. Put text-heavy content beside the
image, not on top of busy areas.

## 7. Video

Produce a 1920×1080 presentation at real 60 fps (~45 s, 11 scenes from intro to outro). Scenes
cross-dissolve with a slight scale and blur, photos get a slow Ken Burns zoom, and text, bars and
columns animate in with a staggered ease-out.

Render it frame-accurately: keep all CSS animations paused, seek every animation to `i/fps` through
`document.getAnimations()`, capture each frame, and pipe the frames into ffmpeg (libx264, CRF 14,
`yuv420p`, TV range, BT.709, faststart). Also write `--stills` (one frame per scene) for review.

## 8. Verify, then review visually

Write `verify.js` and make it pass. It checks that the guide opens offline with zero network
requests, the size budgets (150 KB light, 4 MB hero), that the required sections exist, the
Unofficial label, that the token JSON parses, five quotes and three rules, that the rebuild button
and card computed styles equal the token values, AI labels on every image, and no horizontal scroll
at 390px.

Then screenshot every section, slide and video still, look at them, and fix what looks wrong before
you finish: truncation, low contrast, collisions, crops, washed-out images.

## 9. Log

Write `run-log.md` with the timing per phase, pages and elements, sizes, image cost per image, LLM
token usage if known, and every assumption (viewports, page picks, role inference, inferred
components, fallbacks).

## Deliverables

`out/<host>/`: `brand-guide.html`, `brand-guide-hero.html`, `tokens.css`, `tokens.json`,
`snapshot.json`, `prompts.json`, `images/`, `slides/`,
`video/<host>-presentation-1920x1080-60fps.mp4`, `run-log.md`, and the screenshots from
verification.

Finish with a short summary of what you measured, what you assumed and what it cost.

---

# Our deltas

Every difference between this skill and the spec above, with the reason. Anything not listed here
is a defect, not a decision.

1. **A DESIGN.md is produced at the end, and it is a reading of the guide.** The spec stops at the
   guide; dev-flow needs a `DESIGN.md` to feed `design-md-to-app`. So the chain is
   `URL → spec §1–§9 → brand guide → read the guide → DESIGN.md`. It is written from the guide's
   *computed* values, not from the raw tokens, which means a token the guide could not rebuild does
   not reach the next skill. The user asked for exactly this.
2. **Type roles use the shadcn numeric scale** (`text-xs`…`text-9xl`) rather than the spec's
   `display/h1–h4/lead/body/small`. Repo rule, confirmed by the user: shadcn is the component
   system and a parallel set of semantic type names is forbidden
   (`design-md-to-app/SKILL.md:51`). The colour roles keep shadcn's names for the same reason, and
   every role the spec lists has an equivalent.
3. **An `app` mode exists** for signed-in products, where the spec only addresses public sites. It
   never crawls (a signed-in app cannot be scored), never keeps strings, and never deduplicates the
   chrome — in an app the sidebar *is* the product.
4. **The review questionnaire** (`references/review.md`) sits between the guide and the DESIGN.md.
   The spec has no such step because its output is the guide itself; ours feeds a build.
