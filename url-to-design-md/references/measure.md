# What to measure, and the traps that each cost a correction

Every trap below was found by running the extractor against `scripts/fixtures/known-site.html`, a
page whose true values are written in the file itself. None of them came from re-reading the code.
That is the method: a measuring instrument is checked against a known quantity, never against a
screenshot and never against its own output.

## Read what is painted, never what is declared

`getComputedStyle` on the rendered DOM, not the authored stylesheet. A stylesheet declares what is
*possible*; the DOM says what is *painted*. On a Tailwind or CSS-in-JS site the stylesheet carries
the whole utility palette, so a source reader reports the framework's defaults as the brand's
system.

The declared layer is still read, for the three things the DOM cannot give: custom-property
**names**, `@media` breakpoints and `@font-face` sources. Cross-origin stylesheets throw on
`.cssRules`, and that is **reported as opaque**, never silently dropped — a channel that could not
be read must never look like a channel that said nothing.

## Colour

**Normalise by painting, not by reading back.** `ctx.fillStyle = v; ctx.fillStyle` round-trips CSS
Color 4 — assign `oklch(0.55 0.21 258)` and you get that same string back. Only `getImageData`
forces sRGB. **Measured: the first version returned the colour unconverted.**

**Two probes with opposite resets.** Paint over `#000000` and over `#ffffff`. A value the engine
rejects leaves the reset in place, so the two reads disagree and the value is discarded. Resetting
to the same colour twice reports every typo as that colour.

**A translucent value stays as authored.** Flattening it to hex bakes the ground in and loses the
alpha, which is the token.

**Weight: text by characters, grounds by painted area.** A one-pixel border repeated on four hundred
rows and a hero are both "one colour, many elements", and only the weight separates them.

**Read a border side only when that side has width.** `borderTopColor` is defined even at width 0,
where it falls back to the element's `color`. **Measured: a header with only a bottom border
reported its text colour as a 1440px-wide border and outvoted the real grey.**

**Exclude the consent UI** by id, class and dialog text. Measured with it in, the CMP's greens and
its 4px radius land in the palette and the radius scale.

## Type

**Cluster within 12%.** A real page sets 17, 17.6 and 18px for one role because a rem lands between
pixels. Three steps nobody designed otherwise.

**Two viewports, 1440 and 390, give the `clamp()`.** One viewport gives a guess. And emit a clamp
only where the two differ: 16px at both is not a ramp, and writing one invents a behaviour the page
does not have.

**A ratio is a fact only when the steps agree.** Averaging 2.25, 1.6, 1.25 and 1.143 produced 1.561
— a number that names no interval and describes nothing. Report every step, the median and the
spread; name an interval only when the spread is small, and say so when it is not.

**Map onto Tailwind's own slots** (`text-sm` … `text-9xl`), redefining them. Never a parallel set of
semantic names: shadcn's primitives are written with the numeric ones, and a scale they cannot see
never reaches them.

## Spacing

**The largest base that still explains the page, not the base with the best coverage.** Every system
is on a 2px grid; the question is the step a designer reaches for. **Measured: "highest coverage
wins" answered 2px for a page that is plainly a 4px system.** Take the largest of 8, 4, 2 that
covers ≥ 80%, and list the off-grid values rather than hiding them.

## Components and states

**The painted layer is often a child of the `<a>`.** Read the anchor and a pill-shaped primary
button reports no background and no radius. Walk down to the descendant that carries the paint, and
widen the candidate selector: a first version matched `btn` and `button` and missed `a.cta`.

**A page shows one state at a time.**

- `focus`: `el.focus()` sets `:focus-visible` and the ring is readable — **but only while
  `document.hasFocus()`**. In a background tab the same call reports `outline: none`, which reads
  exactly like a site that ships no focus ring. The extractor refuses to write focus states without
  focus rather than inventing an accessibility finding.
- **A browser default is not a design token.** Every focusable element has an outline, because when
  the page authors none the browser draws its own. Accept a ring only when the page declares a
  `:focus` rule for that kind of control. **Measured: `#e59700`, the OS accent, was nearly written
  into the theme as the site's focus colour.**
- `hover` cannot be forced from script. It is read from the declared rules where the stylesheets are
  same-origin, and driven with a real pointer over a short list where they are not. Declared hover
  is labelled declared and never merged with a measured value.
- `disabled`: read a genuinely disabled control, or mark it inferred.

## Mode

Everything above is the same in `site` and `app` except three things, and they invert:

| | `site` | `app` |
|---|---|---|
| repeated chrome | deduplicated | **never** — the sidebar is the product |
| section rhythm | light/dark bands | omitted |
| text | labels, CTAs, five public quotes | **no strings**, only shape |

## The viewport is not the pane

`resize_window` to 1440×900 and 390×844 explicitly. **Measured: a run taken without it measured the
browser pane at 474px**, and every value in it was a true measurement of the wrong thing.

## When something was not found

Mark it `inferred` or leave it out and name it. Never a plausible default. A value nobody measured,
sitting in a measured file, is indistinguishable from one that was — and that is the single failure
this whole skill is built to avoid.
