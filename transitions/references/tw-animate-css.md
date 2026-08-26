# tw-animate-css — the Tier-0 animation engine

The CSS-first successor to `tailwindcss-animate` for **Tailwind v4**, and the engine behind every
Tier-0 entry in `references/motion-library.md`. shadcn's Tailwind v4 setup already imports it, so on a
dev-flow project it is normally **already installed** — check `globals.css` before adding it.

Doc-grounded against <https://github.com/Wombosvideo/tw-animate-css> (README + the shipped
`dist/tw-animate.css`), **v1.4.0, MIT** — still `latest` on **2026-08-26**, and every claim below re-checked against the shipped `dist/tw-animate.css` that day. `[VERIFY]` identifiers against the version in your lockfile:
the README carries a standing warning that **v2.0.0 will ship breaking changes** (with a migration
script + guide).

## Install + CSS entry (no JS plugin)

```bash
pnpm add -D tw-animate-css
```

```css
/* app/globals.css — CSS-first: there is NO tailwind.config plugin entry */
@import "tailwindcss";
@import "tw-animate-css";
```

A prefixed build is exposed as `tw-animate-css/prefix` (package `exports` → `dist/tw-animate-prefix.css`)
for Tailwind setups using a class prefix. **Diffed the two shipped files at v1.4.0: the utility set is
identical** — same names, same count — and the *only* difference is 24 fragments where the prefixed
build writes `--spacing(--value(integer))` instead of `calc(--value(integer) * var(--spacing))`, all on
the `slide-in-*` / `slide-out-*` translate values. So **you type the same class names either way**;
what the prefixed build avoids is the bare `var(--spacing)` reference, which is the thing a class prefix
renames out from under it.
Unused animations are tree-shaken by Tailwind, so importing the whole thing costs nothing.

## Base classes — nothing animates without these

| Class | Effect |
|---|---|
| `animate-in` | Runs the `enter` keyframe. **Required** for any `fade-in` / `zoom-in` / `slide-in-from-*` / `spin-in` / `blur-in`. |
| `animate-out` | Runs the `exit` keyframe. Required for the `*-out` / `slide-out-to-*` modifiers. |

The modifiers alone are inert — they only set custom properties (`--tw-enter-opacity`,
`--tw-enter-translate-y`, `--tw-exit-scale`, …) that the `enter`/`exit` keyframes read.

## Transform modifiers

| Class | Bare value | `-*` value syntax |
|---|---|---|
| `fade-in` / `fade-out` | opacity `0` | `fade-in-50` → number as **percentage** |
| `zoom-in` / `zoom-out` | scale `0` | `zoom-in-95` → number as **percentage** (`zoom-in-100` = no scale) |
| `spin-in` / `spin-out` | rotate `30deg` | `spin-in-45` → number as **degrees**; `-spin-in` negates |
| `slide-in-from-{top,bottom,left,right,start,end}` | `100%` | `slide-in-from-bottom-2` → integer × `--spacing` (so `-8` = `2rem`); `-full` = `100%` |
| `slide-out-to-{top,bottom,left,right,start,end}` | `100%` | same, e.g. `slide-out-to-right-full` |
| `blur-in` / `blur-out` | `20px` | `blur-in-4` → number as **px** |

`start` / `end` are the logical (RTL-aware) variants of `left` / `right` — prefer them in i18n'd UIs
(the shipped CSS resolves them with `:dir(ltr)` / `:dir(rtl)`).

## Parameter modifiers

| Class | Sets | Default |
|---|---|---|
| `duration-*` | `animation-duration` (via Tailwind's `--tw-duration`) | `150ms` |
| `ease-*` | `animation-timing-function` (via Tailwind's `--tw-ease`) | `ease` |
| `delay-*` | `animation-delay` | `0s` |
| `repeat-*` | `animation-iteration-count` — `repeat-0`, `repeat-1`, `repeat-infinite`, any number | `1` |
| `direction-*` | `animation-direction` — `normal`, `reverse`, `alternate`, `alternate-reverse` | `normal` |
| `fill-mode-*` | `animation-fill-mode` — `none`, `forwards`, `backwards`, `both` | `none` |
| `running` / `paused` / `play-state-*` | `animation-play-state` | `running` |
| `animation-duration-*` | `animation-duration` **only** (leaves `--tw-duration` / transitions alone) | — |

> ⚠️ **`delay-*` is redefined.** In the shipped v1.4.0 CSS, `delay-*` is an `@utility` that sets
> `animation-delay` — not Tailwind core's `transition-delay`. If you need a *transition* delay in a
> file that also imports this package, use an arbitrary property or inline style instead of assuming
> `delay-150` still delays a transition. **Proved at v1.4.0**: the shipped `dist/tw-animate.css`
> contains **zero occurrences of `transition-delay`** — its `@utility delay-*` sets `animation-delay`
> and `--tw-animation-delay`, nothing else. Two definitions of the same utility name now exist in the
> build; the one that ships nothing for transitions is the package's.
>
> ⚠️ **There is no built-in shimmer.** The only ready-made animations are `animate-accordion-down` /
> `animate-accordion-up`, `animate-collapsible-down` / `animate-collapsible-up`, and
> `animate-caret-blink`. A skeleton shimmer is either Tailwind core's `animate-pulse` or your own
> Tier-1 `@keyframes` — do not reach for a `shimmer` class from this package; it does not exist.

## The token bridge — point it at `lib/motion/tokens.ts`

The `enter` / `exit` animations are composed as (from `dist/tw-animate.css`):

```css
--animate-in: enter var(--tw-animation-duration, var(--tw-duration, .15s))
                    var(--tw-ease, ease)
                    var(--tw-animation-delay, 0s)
                    var(--tw-animation-iteration-count, 1)
                    var(--tw-animation-direction, normal)
                    var(--tw-animation-fill-mode, none);
```

So the timing seam is **`--tw-duration` and `--tw-ease`** — exactly the two knobs `duration-*` and
`ease-*` write. Feed them the motion tokens per element (this is what `motion-library.md` does):

```tsx
className="animate-in fade-in slide-in-from-bottom-2
           duration-[var(--motion-duration-base)] ease-[var(--motion-ease-standard)]"
```

For a named utility, register the easing in the **documented Tailwind `--ease-*` theme namespace**:

```css
@theme { --ease-standard: cubic-bezier(0.2, 0, 0, 1); }   /* → `ease-standard` utility */
```

**Durations answered at v1.4.0, and the answer is better than the question.** There is no `--duration-*`
namespace here, and the `--animation-duration-*` namespace the `animation-duration-*` utility reads from
**ships empty** — so `animation-duration-500` resolves nothing from the theme.

But you don't need it: every animation in the package is declared as

```css
--animate-in: enter var(--tw-animation-duration, var(--tw-duration, .15s)) …
```

— so **Tailwind core's own `duration-*` drives it**, through `--tw-duration`, with `.15s` as the final
fallback (`.2s` for the accordion/collapsible pairs). `duration-300 animate-in fade-in` works with no
theme entry and no arbitrary value. Reach for `animation-duration-[…]` only when you need the animation
to run at a different length than the element's transitions.

## Composing with `data-[state]` on Radix / Base UI primitives

The README documents variant-gating the **base class** and leaving the modifiers unprefixed:

```html
<div class="data-[state=show]:animate-in data-[state=hide]:animate-out
            fade-in slide-in-from-top-8 fade-out slide-out-to-top-8 duration-500">
```

shadcn primitives emit `data-state="open" | "closed"`, so the project form is:

```tsx
className="data-[state=open]:animate-in  data-[state=open]:fade-in  data-[state=open]:zoom-in-95
           data-[state=closed]:animate-out data-[state=closed]:fade-out data-[state=closed]:zoom-out-95
           duration-[var(--motion-duration-base)]"
```

Prefixing every modifier (as above) is safe and is what shadcn ships; prefixing only `animate-in` /
`animate-out` also works and is what the upstream README shows. Pick one and stay consistent.

**Accordion / collapsible** need the primitive's measured height variable — `animate-accordion-down`
reads `--radix-accordion-content-height` (with `--bits-` / `--reka-` / `--kb-` / `--ngp-` fallbacks
built in, so Bits UI and friends work unchanged). Set it, or the height animates to `auto` and jumps.

## Reduced motion

`motion-reduce:` is a **Tailwind core variant**, not a tw-animate-css feature — it is how every entry
in `motion-library.md` degrades:

```tsx
// kill the animation entirely
className="animate-in fade-in slide-in-from-bottom-2 motion-reduce:animate-none"
// or keep the fade, neutralize the movement
className="… data-[state=open]:zoom-in-95 motion-reduce:data-[state=open]:zoom-in-100"
```

Neutralizing a single modifier (`zoom-in-100`, `slide-in-from-bottom-0`) is usually kinder than
`animate-none`, which can leave `fill-mode`-dependent elements in their pre-animation state. The
global `@media (prefers-reduced-motion: reduce)` guard in `globals.css` is the floor, **not** a
substitute for these per-effect fallbacks.
