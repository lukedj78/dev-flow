# The artefacts — what they are for, and the one rule that makes them work

The guide, the decision pages and the slides are not deliverables. They are **the surface the
divergence decision is made on**, which is a different job and makes different demands.

A measurement in a markdown file cannot be judged: nobody reads `--text-7xl: 72px` and says "too
heavy, lighten it". Rendered, they can — and then they can move it, look again, and keep going.

## The rule everything rests on

**Nothing in an artefact is a literal.** Every colour, size, radius, shadow and easing is
`var(--x)`, and the only place a value appears is the `:root` block generated from `tokens.json`.

That is what makes it a loop instead of a document: move a token, regenerate, look again. One
hard-coded value breaks it *silently* — the page still looks fine, and the person deciding what to
change is now arguing with a picture. `verify.py` reads the rebuilt controls' computed styles back
and fails when one does not equal its token, which is why that check is the gate and not a nicety.

## brand-guide.html

Twelve sections: the review band, cover, overview, the token rebuild test, typography, fonts,
colour, layout and spacing, components, imagery, voice, the tokens themselves, method.

Two editions from the same markup: the light one carries no images, uses CSS-gradient fallbacks,
opens offline with zero network requests and fits in 150 KB; the hero one embeds WebP once each and
reuses them through classes.

Three things it must always carry: the **Unofficial analysis** label on bar, cover and footer; the
disclaimer naming the owner of the marks; and the **dashed logo box** at the measured size and
colour — the logo is never copied, and neither are font files or photographs.

**`.reveal` is gated on `.js`.** Ungated, the whole guide is invisible when the script fails — and
it would still pass an "opens offline with no requests" check, which is how a blank page gets
shipped as a verified one.

## decision-*.html

One decision, side by side, generated per question and screenshotted into the conversation. Six
kinds: `contrast`, `type`, `scale`, `colour`, `spacing`, `fallback`.

Two things learned building them, both from the comparison being wrong rather than the data:

- **A ground is judged by what sits on it.** Showing a background token as a swatch and a button
  filled with it means a button the colour of the page — invisible, and it made both candidates look
  equally bad for a reason that had nothing to do with either. A ground gets a miniature page:
  heading, body, secondary text, the real primary button, and the measured contrast.
- **A caption must say something true.** A first version printed "at 390px this line is 35px of a
  390px screen", which is not a fact about anything. Characters per line is.

## slides

Eight 1080×1350 and four 1600×900, drawn on a canvas by the same scene engine, exported straight to
the collector. **Only when the site is the user's own**: a carousel of a competitor's brand system
is internal material, not something to publish. Every slide carries the Unofficial badge.

## The video is deferred, and this is the reason

Not because it was hard. Because it was **wrong**.

It drew its own scenes on a canvas with its own layout rules — sharing the tokens with the guide but
not the form — so it showed a design that exists nowhere: not the measured site, not the guide. A
chart deck about the tokens, and you cannot judge density or rhythm from a bar chart. It also broke
the one rule above, by being a second renderer.

Two measurements from the attempt, kept because they will be needed:

- **`MediaRecorder` is not frame-accurate.** `captureStream(0)` plus `requestFrame()` makes the
  *drawing* exact; the recorder still stamps frames with the wall clock. Measured on a 22-second
  1080p clip: **1320 frames drawn, 1151 recorded, 12.8% lost.** `make_video.py` prints that
  accounting rather than claiming accuracy it does not have.
- **The right approach is to record the guide**, which is already the artefact built from the
  tokens, with its real type, components, rhythm and reveal animations. One renderer, scripted
  scroll. That is the shape to build when it is wanted.

## What no artefact may become

**Prettier than the decision it serves.** A rendered artefact that looks like the source is *more*
tempting to ship unchanged, not less. The tool that helps someone diverge also makes the clone
prettier — which is why `design-source.md` is written at the moment of approval and not optional.
