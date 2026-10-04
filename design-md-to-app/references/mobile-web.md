# The web-on-a-phone layer — the tells that say "this is a website"

A separate concern from responsive layout and from motion. These are platform-layer fixes — viewport,
touch, scroll, safe areas, browser chrome — where **a handful of declarations decide whether the app
feels installed or embedded**. Almost every one is a single line.

Distilled 2026-10-04 from [emilkowalski/skills](https://github.com/emilkowalski/skills) (MIT);
`dev-flow/references/resources.md` has the row. For motion see `transitions`; for React Native see
`rn-animations-gestures`.

> ⚠️ **None of this reproduces in Chrome's device emulation.** Sticky hover, the tap highlight, the URL
> bar's effect on `vh`, input zoom, the click delay, overscroll, safe areas and the software keyboard
> are all real-hardware behaviours. If you only test in the device toolbar you ship every one of them.
> Say which fixes you verified from code and which need a phone — that is the same honesty rule as
> `dev-flow/references/before-you-build.md`.

## The baseline — ship this before the first component

```html
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover, interactive-widget=resizes-content" />
<meta name="theme-color" media="(prefers-color-scheme: light)" content="#ffffff" />
<meta name="theme-color" media="(prefers-color-scheme: dark)" content="#0a0a0a" />
```

```css
html {
  -webkit-tap-highlight-color: transparent;
  -webkit-text-size-adjust: 100%;   /* no font inflation in landscape */
  overscroll-behavior: none;
}
input, textarea, select { font-size: 16px; }
button, a, [role="button"] { touch-action: manipulation; user-select: none; -webkit-user-select: none; }
```

In Next.js the two `theme-color` tags go through the `viewport` export
(`themeColor: [{ media, color }]`). `interactive-widget=resizes-content` makes the Android keyboard
shrink the layout viewport, so `100dvh` and bottom-pinned inputs react the way they do on iOS. Drop
`overscroll-behavior: none` from `html` if the app is a scrolling document where pull-to-refresh is
welcome.

## The symptom table

| Problem | Fix |
|---|---|
| Hover state stuck after a tap | `@media (hover: hover) and (pointer: fine)` |
| Grey/blue flash on tap | `-webkit-tap-highlight-color: transparent` |
| Layout has the wrong height | `100dvh` (app shell) or `100svh` (hero) |
| Page zooms into an input | input `font-size: 16px` minimum |
| Tap feels laggy | feedback on pointer-down + `touch-action: manipulation` |
| Pull-to-refresh hijacks scroll | `overscroll-behavior: none` on `html, body` |
| Content stops at the notch | `viewport-fit=cover` + `env(safe-area-inset-*)` |
| Long-press selects a button's label | `user-select: none` on controls only |
| Carousel scrolls the page vertically | `touch-action: pan-y` on the gesture surface |
| Status bar colour doesn't match | one `theme-color` per colour scheme |
| Right in Chrome, wrong on the phone | test on real hardware |

## The ones with a why worth knowing

**Sticky hover.** Touch has no hover, so browsers fake one: the first tap applies `:hover` and leaves
it there until the user taps elsewhere. A button that scales on hover stays scaled after being
tapped. Both conditions in the query matter — `(hover: hover)` means the primary input can hover,
`(pointer: fine)` means it is precise, ruling out styluses and Android devices that over-claim.
**Tailwind v4's `hover:` variant already compiles to `@media (hover: hover)`**, so utility classes are
covered and hand-written `:hover` CSS is not. Touch users get their feedback from `:active`.

**Input zoom is never fixed with `maximum-scale`.** iOS Safari zooms when focus lands on an input
under 16px and does not zoom back out on blur. `user-scalable=no` and `maximum-scale=1` are
accessibility failures — **fix the font size, which was the cause.** While you are in the inputs, set
the keyboard too: `inputmode="numeric"` for codes, `inputmode="decimal"` for amounts, `type="email"`
and `type="tel"`, `autocapitalize="none"` and `autocorrect="off"` on usernames and codes, and
`enterkeyhint="send"` / `"search"` / `"done"` so the return key says what it does.

**Laggy taps are two causes stacked.** The **300 ms click delay**: browsers wait to see whether a
second tap is coming, because double-tap zooms. `touch-action: manipulation` says this element never
double-tap-zooms, so `click` fires immediately. And **feedback on release instead of press**: a native
button responds the instant your finger lands, so a web button that only changes on `click` reads as
lag even at 0 ms. Style `:active`; if you need JS, listen to `pointerdown`, not `click`.

**Overscroll: `none` on the root, `contain` on children.** `contain` keeps an inner scroller's own
bounce (which feels native) but stops the page behind it from moving. **Never** reach for
`touchmove` + `preventDefault()` — it blocks scrolling entirely and makes the listener non-passive,
which costs frames.

**Safe areas need both halves.** `viewport-fit=cover` lets the page under the notch; `env(safe-area-inset-*)`
pads the content back out. **Without the meta tag every `env()` value is `0px`** — which is why this
usually looks like "the insets don't work". Fixed headers, bottom tab bars, toasts and sheets are what
need it; give `env()` a fallback (`env(safe-area-inset-bottom, 0px)`) inside a `calc()`.

**`user-select: none` on controls, never on `body`.** Text that is a *control* should not be
selectable; text that is *content* must stay selectable — users copy addresses, error messages and
order numbers. Add `-webkit-touch-callout: none` on links or images used as controls.

**`touch-action` names what the *browser* may still do.** `pan-y` on a horizontal carousel means
"browser, you keep vertical panning; I handle horizontal". `none` means the element handles every
axis — only on elements that really do, or the user cannot scroll past them. And if the carousel is
native scroll rather than a JS gesture, prefer `scroll-snap-type: x mandatory` + `scroll-snap-align`:
the browser's own physics beat a hand-rolled spring and `touch-action` becomes unnecessary.

**`theme-color` matches the colour at the very top of the page** — the header background, not the
brand colour. If the app switches theme with a class rather than the OS setting, update the tag from
JS on toggle. For an installed PWA, `apple-mobile-web-app-status-bar-style` and the manifest's
`theme_color` / `background_color` are the same decision.

## Never ship

| Never | Instead |
|---|---|
| `user-scalable=no` / `maximum-scale=1` | 16px inputs — fix the cause |
| Ungated hand-written `:hover` | `@media (hover: hover) and (pointer: fine)` |
| `100vh` anywhere | `100dvh` (app) / `100svh` (hero) |
| `100dvh` on a marketing hero | `100svh` — no layout shift mid-scroll |
| Press feedback on `click` only | `:active` / `pointerdown` |
| `touchmove` + `preventDefault()` for overscroll | `overscroll-behavior` |
| `user-select: none` on `body` | controls only |
| `touch-action: none` on something the user must scroll past | `pan-x` / `pan-y` |
| `env(safe-area-inset-*)` without `viewport-fit=cover` | add the meta tag, or the value is `0` |
| One `theme-color` for both schemes | one per `prefers-color-scheme` |
| User-agent sniffing to detect touch | `(hover)` / `(pointer)` media queries |
| Declaring it fixed from device emulation | real hardware |

## Testing on hardware

Run the dev server on `0.0.0.0` and open it by the machine's LAN IP. iOS: Safari → Develop → the
device. Android: `chrome://inspect`. Test on a phone a few years old, not the newest one on the desk;
test with the keyboard open; test in landscape once. If a PWA is a target, test it installed —
standalone mode changes the viewport, the safe areas and the status bar.
