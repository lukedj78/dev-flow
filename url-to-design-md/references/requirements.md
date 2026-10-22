# What this skill must do

## Where this comes from, and why it is written in our words

The behaviour below was derived from a public prompt by **Amir Mushichge**
(<https://gist.github.com/amirmushichge/ede82d51439e4bd70817c329e36c4cc7>), read on 2026-10-22,
which describes a `reverse-brand <url>` tool.

**That gist carries no licence**, so by our own rule — `registry-intake` K8: *no licence means all
rights reserved, so only the idea travels, rewritten in our own words, never the text, into a repo
we deliver* — none of it is copied here. This file is a restatement: every requirement that was in
it is in here, in our words, numbered so it can be cited in a commit or an argument. The original
is linked above and should be read there.

**Where this skill stands against each number is recorded below**, in the *State* table at the end.
A requirement with no mark is one nobody has checked since it was written.

Two notes on using this file:

1. **A change to this skill is justified against a number below, or it is a change to the
   requirements and the user decides it.** "It seemed better" is how the first version happened:
   that one was written from a *reading* of the source, and the difference showed up as a guide
   that was a report, an ink colour taken from a legal footer, and two of the thirteen pages simply
   absent.
2. **R8.2 is not optional.** Look at what came out, with your eyes, before calling it done. Three
   rounds of measurement produced a report nobody had looked at.

---

## R0 — The goal, and the shape of the output

**R0.1** The input is one public URL. The output is an unofficial, art-directed **brand guide** for
that site, plus the tokens it is built from.

**R0.2** The guide must read as though the brand had made it. A document that reads as an analysis
report has failed this requirement even if every number in it is right.

**R0.3** Every value shown is measured from the live site, turned into a token, and then **rebuilt
from that token** inside the guide, so the guide is its own proof.

**R0.4** It is a repeatable tool, not a one-off: the same command run on another URL produces the
same kind of artefact.

## R1 — Non-negotiables

**R1.1** Label the whole thing as an unofficial analysis: on the guide's cover, its top bar, its
footer, every slide, and the video.

**R1.2** Carry a disclaimer naming the brand: no affiliation, no endorsement, trademarks belong to
their owners.

**R1.3** Never copy a logo, a font file or a photograph from the site. Describe them in words and
link to the page they came from. A logo is drawn as a dashed placeholder at its measured size and
colour.

**R1.4** Never defeat a bot check or a CAPTCHA. If an automated capture is challenged, stop and
offer the user two ways through: run the browser visibly so they can answer it themselves, or hand
them a snippet to paste into their own DevTools that runs the same extractor at both viewports and
saves the snapshot.

**R1.5** Any AI-generated image is made from a text prompt only — never from the brand's own
pictures — and is labelled as AI-generated wherever it appears.

**R1.6** The writing is plain and technical, and the section names are the ordinary ones a brand
book uses: Overview, Contents, Typography, Fonts, Colour, Layout and spacing, Components, Imagery,
Voice and tone, Design tokens, Method. No slogans, no manifesto.

## R2 — Capture

**R2.1** Drive a real browser. (Some machines hang on the first canvas call unless the GPU is
disabled, so disable it.)

**R2.2** Read the home page plus three to five further pages, **chosen by scoring the site's own
same-origin links**. Rank the navigation and the product, pricing, business and company pages
highest. Skip legal, help and login pages and locale duplicates, and take only one page per
top-level path.

**R2.3** Read at 1440×900, and read the home page again at 390×844 for responsive type.

**R2.4** Scroll each page fully first, so lazy content paints before it is measured.

**R2.5** For every visible element record: the computed font, size, weight, line-height and
tracking; the text, background, border and fill colours; padding, margin and gap; corner radius;
shadows; container max-widths; grid columns; and media statistics. Colours are normalised to hex by
painting them, so modern colour syntax resolves rather than being stored as text.

**R2.6** Record as well: button and card candidates — noting that the painted layer may be a child
of the link rather than the link itself; the header and nav, with height, stickiness, link style
and logo size and colour; form fields; the first three heading levels; paragraphs; call-to-action
labels; the custom properties declared on the root; and the breakpoints declared in media queries.

**R2.7** Exclude cookie and consent interfaces, recognised both by their identifiers and by the
text of the dialog.

## R3 — Analyse

**R3.1** Deduplicate repeated furniture: anything that is identical on every page — the header, the
footer — is counted once, not once per page.

**R3.2** Type: cluster heading sizes that are within 12% of each other, then name the roles
(display, the heading levels, lead, body, small). For each, record the size, the line-height as a
ratio, the weight, and the tracking in em. Pair each role with its mobile size and emit a fluid
value between them. Report the ratio between the steps and the nearest named interval.

**R3.3** Colour: report the roles — page ground, surface, inverted surface, text, quiet text, text
on the inverted ground, action, text on the action, second action, accent, border — each as hex and
OKLCH with its share of use. Weight text by characters and backgrounds by the area they paint. List
the gradients, and the contrast ratio of the pairs most often read.

**R3.4** Layout: derive the spacing base (8, 4 or 2) and separate the values that sit on that grid
from those that do not. Record the corner radii, distinguishing a pill from a measured radius; the
container width, the column count and the gutter; the breakpoints; and **the rhythm of the home
page's bands, light against dark**.

**R3.5** Components: the button variants (filled, outlined, translucent), the card variants (fill,
backdrop, radius, padding, media) and the nav. If the pages read carry no form, infer an input and
mark it as inferred rather than measured.

**R3.6** Imagery, described in words: the formats, the crops, how much is full-bleed, how the images
are fitted, what share of the page's area is media, and the themes of the alt text.

**R3.7** Voice: quote five lines from the site, each fifteen words or fewer, each linked to its
page. Derive three rules from statistics that can be checked — headline length, capitalisation,
whether it says "you" or "we", the use of numbers, the "X, Y" construction, the verbs on the
call-to-action buttons, exclamation marks. Show the statistics the rules came from.

## R4 — Tokens

**R4.1** Export CSS custom properties covering fonts, type roles, colour roles, spacing, layout,
radii, and the button, card, input and nav.

**R4.2** Export the same set as design-tokens JSON in the W3C format, with OKLCH beside each hex.

**R4.3** Every brand sample inside the guide is drawn using **only** these variables. A literal
value anywhere in a sample is a defect.

## R5 — The guide (most of the value is here)

**R5.1** The art direction is **derived from the measured tokens**, never hard-coded: the brand's
typefaces, its alternating light and dark grounds, its card radius, its button shape, its gradient,
its declared easing. The guide's own controls are the brand's buttons, rebuilt.

**R5.2** It is a sequence of **full pages** that mirror the site's own layout patterns — not
sections stacked in a column:

| # | Page | What is on it |
|---|---|---|
| 1 | **Cover** | a full-bleed photograph, or the brand's gradient when there are no images; the brand's name and "brand guidelines" set large over it; a one-line factual lede; a pill-shaped call to action; a frosted-glass card showing a single token. The unofficial label and the disclaimer sit at the bottom |
| 2 | **Overview** | a centred headline and four large figures: typefaces, colours, spacing base, button variants |
| 3 | **Contents** | eight image cards in the style of the site's own product cards — title lower left, number upper left, arrow upper right, a slow zoom on hover |
| 4 | **Token rebuild test** | one button and two cards built from the tokens alone, shown on both the light and the dark ground, with real images in the card media |
| 5 | **Typography** | a full-bleed chapter photograph with a glass specimen card and chip tabs, one per role; each tab shows that role at its real size, weight, leading and tracking — never one size standing in for all |
| 6 | **Fonts** | one family card per typeface with a giant "Aa", its weights and its share, and whether the font is installed locally; below, the character set, the scale from mobile to desktop, the sizes in use, and the type variables the site itself declares |
| 7 | **Colour** *(dark page)* | a product or chrome image beside a palette bar drawn in proportion to use; role tiles with hex, OKLCH and contrast; the gradient; the contrast pairs; and the full palette behind a disclosure |
| 8 | **Layout and spacing** | the big facts (base, columns, gutter, container), a column diagram, a spacing staircase, radius tiles, the breakpoints, and the section rhythm |
| 9 | **Components** *(dark page)* | an image of ordered material beside the title, then the measured button variants shown **on the grounds they were measured on**, the nav, the cards and the form input |
| 10 | **Imagery** | a mosaic, with any AI images labelled, the measured facts, and links to the pages they describe |
| 11 | **Voice and tone** | a split page of photograph and facts, then the quoted lines set large, and three numbered rule cards |
| 12 | **Design tokens** *(dark page)* | copy, copy-as-JSON and download controls, with the code panels |
| 13 | **Method** | the assumptions, the run log, and the table of image prompts |

**R5.3** Motion: restrained rise-in reveals and a slow zoom on photographs, using the brand's own
easing. Honour a reduced-motion preference.

**R5.4** The top bar is sticky, transparent over the cover, and frosted once past it.

**R5.5** It is responsive, with no horizontal scrolling at 390px.

**R5.6** Two editions are written: one with **no images at all**, using gradient fallbacks in every
image slot, which opens offline and stays under 150 KB; and one with the images embedded as WebP,
each embedded once and reused by class.

## R6 — Images (optional)

**R6.1** Study the site's photography first — look at it, never copy it. Write a prompts file with
about nine slots: the cover, the typography chapter, a studio object for colour, a lifestyle scene
for voice, a clean sky, ordered material for components, something for layout, something for the
tokens page, and whatever else the brand needs. Each prompt describes a **new** subject in the
brand's photographic style, and carries a suffix forbidding text, letters, logos, brand marks,
cards and app screens, and asking for photorealism.

**R6.2** With images off, the gradient fallbacks are the design and nothing is generated.

**R6.3** With images from an API: write a small adapter per provider taking a prompt, an aspect
ratio and a resolution and returning bytes. Read the key from the environment file and never log
it. Record the job identifier before polling, so a crash cannot lose a paid image. Stream downloads
to disk. Check the balance before spending. Log the cost of each image.

**R6.4** With images supplied by hand: print the prompts, let the user drop files into the images
folder, and provide an import step that builds the manifest from what is there.

**R6.5** Re-encode everything to WebP — 2000px for wide images, 1400px for the rest — then **look at
the results** and regenerate anything that is off-brand or noisy.

## R7 — Slides

**R7.1** An eight-card Instagram carousel at 1080×1350: cover, typography, colour, layout,
components, voice, tokens, outro.

**R7.2** Four images for X at 1600×900.

**R7.3** They use the same tokens and the same images. Every slide carries the unofficial badge, and
an AI credit wherever a generated photograph appears.

**R7.4** Text-heavy content sits **beside** the image, never on top of a busy area.

## R8 — Video, verification, and looking

**R8.1** A 1920×1080 presentation at a true 60 frames per second, about 45 seconds, eleven scenes
from intro to outro. One scene dissolves into the next while scaling very slightly and blurring; photographs
drift slowly across the frame; text, bars and columns animate in with a staggered ease-out. Render it frame-accurately:
hold every CSS animation paused, seek each one to the exact frame time, capture frame by frame, and
encode with a high-quality, widely-playable profile. Also write one still per scene for review.

**R8.2** Write a verification script and make it pass. It checks that the guide opens offline with
no network requests at all; the size budgets; that every required section is present; the unofficial
label; that the token JSON parses; that there are five quotes and three rules; that the **computed**
styles of the rebuilt button and card equal their token values; that every image carries its AI
label; and that nothing scrolls sideways at 390px.

**R8.3** **Then look.** Screenshot every section, every slide and every video still, look at them,
and fix what is wrong before finishing: truncation, low contrast, collisions, bad crops, washed-out
images. A passing verification is not a substitute for this.

## R9 — The log and the deliverables

**R9.1** Write a run log: the time each phase took, how many pages and elements were read, the sizes
of what was produced, the cost per image, token usage where it is known, and **every assumption** —
the viewports, which pages were chosen, which roles were inferred, which components were inferred,
which fallbacks were used.

**R9.2** Deliver, under a folder named for the host: both editions of the guide, the tokens as CSS
and as JSON, the raw snapshot, the prompts, the images, the slides, the video, the run log, and the
screenshots taken during verification.

**R9.3** Finish by saying what was measured, what was assumed, and what it cost.

---

# State — what is done, what is not, measured on 2026-10-22

Checked by running the skill on **apple.com** (three pages), **gov.uk** and **stripe.com**, and by
executing the source prompt separately to produce a reference artefact to compare against.

| | Requirement | State |
|---|---|---|
| R0.1–0.4 | one URL in, an art-directed guide out, measured and rebuilt | **partly** — the guide exists and is built from the tokens; R0.2 ("not a report") is half met, see R5 |
| R1.1–1.3 | unofficial labels, disclaimer, no copied assets | **done** |
| R1.4 | bot check: `--headed` or a paste-into-DevTools snippet | **missing** — prose only, no snippet. The reference run shipped one (24 KB) |
| R1.5–1.6 | AI labels, plain copy, standard section names | **done** |
| R2.1–2.7 | capture: Playwright, scored pages, two viewports, computed styles | **done** — `pick_pages.js` ranks by the visible nav bar; the extractor goes in through `evaluate`, since gov.uk's CSP refuses an injected script |
| R3.1 | dedupe the chrome | **done** — by region, so it works on one capture too |
| R3.2 | type: clusters, roles, `clamp()`, ratio | **done** — `clamp()` is omitted, never invented, when a step has no mobile measure |
| R3.3 | colour: eleven roles, hex + OKLCH, share, contrast | **done** — translucent values composited onto the ground; roles weighted by how many pages saw them |
| R3.4 | layout: base, radii, container, breakpoints, section rhythm | **done** — bases 10/8/5/4 (never 2); rhythm measured by geometry |
| R3.5 | components: button, card, nav, inferred input | **done** |
| R3.6 | **imagery described in words** | **MISSING** — the extractor counts formats, crops, full-bleed share, object-fit and media area; `analyze.py` never reads them |
| R3.7 | voice: five quotes, three rules, the statistics | **done** |
| R4.1–4.3 | tokens as CSS and W3C JSON, used everywhere in the guide | **done** |
| R5.1 | art direction derived from the tokens | **partly** — type, colour, radius and button shape come from the measurement; motion and the gradient do not yet |
| R5.2.1 Cover | full page, name, lede, pill, frosted card | **done** |
| R5.2.2 Overview | centred headline, four figures | **done** |
| R5.2.3 Contents | eight cards in the site's own card shape | **done** — ours are flat where the reference gives each one a composed gradient |
| R5.2.4 Rebuild | controls from tokens on both grounds | **done** |
| R5.2.5 Typography | chapter photo, specimen card, **chip tabs per role** | **MISSING** — the tabs |
| R5.2.6 Fonts | giant "Aa", weights, share, local-font check | **partly** — the specimen and weights are in; the local-font check is not |
| R5.2.7 Colour (dark) | palette bar in proportion, role tiles, contrast | **done** |
| R5.2.8 Layout | facts, column diagram, staircase, radii, rhythm | **partly** — the diagram and the staircase are tables, not drawings |
| R5.2.9 Components (dark) | **variants on the grounds they were measured on** | **MISSING** |
| R5.2.10 Imagery | mosaic, measured facts, source links | **MISSING** — waits on R3.6 |
| R5.2.11 Voice | split page, quoted lines, three rule cards | **partly** |
| R5.2.12 Tokens (dark) | copy, copy-JSON, download, code panels | **done** |
| R5.2.13 Method | assumptions, run log, prompts table | **done** |
| R5.3 | motion: rise-in, slow zoom, the brand's easing | **partly** — reveals and reduced-motion are in; the measured easing is not used |
| R5.4 | top bar transparent over the cover, frosted after | **MISSING** — the bar is sticky, the transition is not |
| R5.5 | no horizontal scroll at 390px | **done**, and checked |
| R5.6 | two editions, 150 KB, offline | **partly** — the light edition is in budget; the hero edition contradicts R6.2, see below |
| R6.1–6.5 | prompts, the three modes, WebP, review | **partly** — nine prompts and the three modes exist; nothing has been generated or reviewed |
| R7.1–7.4 | slides: 8 + 4, same tokens, badges | **UNTESTED** — `render_media.py` exists and has never been run |
| R8.1 | video, 60 fps, frame-accurate | **UNTESTED** — `make_video.py` exists and has never been run |
| R8.2 | verify.js and its checks | **done** — 15 checks, and two of them had to stop forbidding R5.2.2 and R5.2.1 |
| R8.3 | **screenshot everything, look, fix** | **partly** — done by hand on the pages built so far, not wired into the flow |
| R9.1–9.3 | run log, deliverables, closing summary | **partly** — the run log is written; the `out/<host>/` layout is not what we produce |

## Known contradictions in the requirements, and what we do about them

1. **R5.6 against R6.2.** Two editions must differ by embedded WebP, and `none` forbids producing
   any image. They cannot both hold. **Undecided** — the reference run shipped them identical and
   said so in the file. We currently skip the hero edition, which is the other reading.
2. **R3.3's character weighting against role assignment.** Weighting text by characters hands the
   ink role to the longest text on the page, which is the legal footer. We scope the rule to
   content characters; the reference picks the body by element count instead. Same hole, two
   patches.
3. **R3.4's "8/4/2" is not every grid.** gov.uk is on 5px. We added 10 and 5, and refuse 2 as an
   answer because every integer system satisfies it.
4. **R2.2's "one page per top-level path" under-specifies product families.** `/mac`,
   `/macbook-air`, `/macbook-pro` are three paths and one product. **Not handled** — the reference
   added a second grouping on the first hyphen-token, and we should.
5. **R3.4's rhythm assumes dark bands exist.** A site with one ground has no rhythm to report, and
   R5.2.7/9/12 still demand dark pages. We fall back to `surface-inverse`; a site with no inverse
   at all is **unhandled**.

## Known defects, measured, not yet fixed

- **gov.uk**: `primary` takes a pale blue panel instead of the green button, and `surface-inverse`
  takes the link blue instead of the black header. Button detection on that site finds the wrong
  painted layer.
- **apple.com**: the 80px step has no mobile measure, because only the home page is read at 390px.
  R2.3 says to read the home page at 390, so reading the other pages there too is a change to the
  requirements, not a bug fix — but every `clamp()` for the big steps is the poorer for it.

# Our deltas

Everything this skill does differently, and why. Anything not listed here is a defect, not a
decision.

**D1 — A DESIGN.md is produced at the end, as a reading of the guide.** The requirements stop at the
guide; dev-flow needs a `DESIGN.md` to feed `design-md-to-app`. So the chain is: URL → R2…R9 →
brand guide → **read the guide** → DESIGN.md. It is written from the guide's *computed* values
rather than from the raw tokens, which means a token the guide could not rebuild never reaches the
next skill. The user asked for exactly this.

**D2 — Type roles use shadcn's numeric scale** (`text-xs` … `text-9xl`) instead of the semantic
names in R3.2. Repo rule, confirmed by the user: shadcn is the component system, and a parallel set
of semantic type names is forbidden (`design-md-to-app/SKILL.md:51`). The colour roles likewise
carry shadcn's names; every role R3.3 lists has an equivalent, and `references/measure.md` maps
them.

**D3 — An `app` mode exists** for signed-in products, where the requirements address public sites
only. It never crawls (a signed-in app cannot be link-scored), never keeps strings, and never
deduplicates the furniture — in an app the sidebar *is* the product.

**D4 — A review questionnaire** (`references/review.md`) sits between the guide and the DESIGN.md.
The source has no such step because its output is the guide itself; ours feeds a build, and a value
that is about to become code is worth a question first.
