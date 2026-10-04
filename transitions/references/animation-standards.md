# Animation standards — the values, and the gate in front of them

This skill's **ladder** answers *how* to animate. This file answers the two questions that come
first — **should it animate at all**, and **with which exact values** — so neither gets improvised.

Distilled 2026-10-04 from [emilkowalski/skills](https://github.com/emilkowalski/skills) (MIT, 43.2k★
— Emil Kowalski, author of Sonner and Vaul, ex Vercel and Linear), read against our own tokens and
verified against shipped packages where a claim was about behaviour. `dev-flow/references/resources.md` has
the row. Where their system and ours disagreed, the disagreement is named below rather than resolved
by seniority.

## Step 0 — the frequency gate. Run it before the ladder.

The ladder starts at Tier 0, but **Tier 0 is still not the cheapest answer. No animation is.** The
single most useful thing in this whole file is a table that produces zero lines of code:

| How often a user sees it | Decision |
|---|---|
| **100+ times/day** — keyboard shortcuts, the command palette, core navigation | **No animation. Ever.** Stop here. |
| **Tens of times/day** — hover states, list navigation, frequent toggles | Near-imperceptible only: fast and subtle, or nothing |
| **Occasional** — modals, drawers, toasts, settings | Standard animation — the ladder applies |
| **Rare / first-time** — onboarding, empty states, success, celebration | This is where the delight budget lives |

**Keyboard-initiated actions are a disqualifier, not a judgment call.** Raycast has no open/close
animation, and that is the correct design for something opened hundreds of times a day. An animation
on a `⌘K` palette makes the product feel *slower* every single time.

Then name the **purpose** in one of these words, or don't build it:

**feedback** (the interface heard you) · **spatial consistency** (where it came from or went) ·
**state indication** (a change made legible) · **preventing a jarring change** (bridging content that
would teleport) · **explanation** (marketing and onboarding only) · **delight** (rare tier only).

"It looks cool" is not on the list. And one last check — **function**: data the user is reading or
acting on must not move for style. A decorative mouse-tracking effect is fine on a marketing page and
wrong on a chart in a banking app.

This replaces nothing in non-negotiable ⑤ ("motion has meaning"); it makes it answerable.

## Easing — and the one place our tokens disagreed

Decision order:

| Situation | Easing |
|---|---|
| Entering **or exiting** | `ease-out` |
| Moving / morphing **on screen** | `ease-in-out` |
| Hover, colour change | `ease` |
| Constant motion (marquee, progress, spinner) | `linear` |
| Anything else | `ease-out` |

**Never `ease-in` on UI.** It starts slow, delaying the exact moment the user is watching; `ease-out`
at 200 ms *feels* faster than `ease-in` at 200 ms even though both take 200 ms.

> ### ⚠️ Our `ease.exit` token was `ease-in` shaped, and it is gone
>
> Until 2026-10-04 the token layer shipped `exit: "cubic-bezier(0.4, 0, 1, 1)"` — an accelerate
> curve, Material Design's prescription for an element leaving the screen. Emil's rule says entering
> and exiting are both `ease-out`. **Both schools are coherent**, and the argument that settled it is
> neither's:
>
> **It depends on who is waiting, and the token's name hid that.** When an exit is on the critical
> path — the user closed the dialog to reach the page underneath, closed the dropdown to click behind
> it — the exit animation *is* latency, and an accelerate curve holds the overlay at near-full
> opacity through the half of the duration the user cares about. When it is not on the critical path —
> a toast auto-dismissing — accelerating reads as "thrown away" and costs nobody anything.
>
> A token named `exit` is about **direction**, so whoever reaches for it applies it to both cases,
> including the one where it is wrong. And the non-critical case never needed its own curve: a toast
> leaving on a strong `ease-out` at 200 ms is fine, and nobody has ever filed a bug about it. A modal
> that feels sticky on close is a real, repeated complaint.
>
> So `exit` was removed rather than re-tuned, `standard` now serves **both** directions, and
> `inOut` was added for the on-screen movement our three curves could not express — they were all
> decelerate or accelerate, with nothing for a morph. The curve **values** were already strong and
> did not change: `cubic-bezier(0.2, 0, 0, 1)` is the same family as his `cubic-bezier(0.23, 1, 0.32, 1)`.

Built-in CSS easings are too weak for deliberate motion. If a project has no token layer yet, these
are known-good starting curves — and `--ease-drawer` is the curve Vaul actually uses:

```css
--ease-out:    cubic-bezier(0.23, 1, 0.32, 1);     /* strong ease-out for UI */
--ease-in-out: cubic-bezier(0.77, 0, 0.175, 1);    /* on-screen movement */
--ease-drawer: cubic-bezier(0.32, 0.72, 0, 1);     /* the iOS-like drawer curve */
```

Need one that isn't here? Take it from [easing.dev](https://easing.dev/) — don't hand-roll a bezier.

## Duration — UI stays under 300 ms

| Element | Duration |
|---|---|
| Button press feedback | 100–160 ms |
| Tooltips, small popovers | 125–200 ms |
| Dropdowns, selects | 150–250 ms |
| Modals, drawers | 200–500 ms |
| Marketing / explanatory | can be longer |

A 180 ms dropdown feels more responsive than a 400 ms one. Over 300 ms on a UI element needs a stated
reason or it is a finding.

**Perceived performance is a real lever, not a metaphor.** A faster spinner makes the same load feel
shorter. And the tooltip detail almost nobody implements: the *first* tooltip in a toolbar delays
before appearing, to prevent accidental activation — but once one is open, neighbours should open
**instantly, with no delay and no animation**. That one rule makes a whole toolbar feel faster.

```css
.tooltip[data-instant] { transition-duration: 0ms; }
```

## Physicality

- **Never `scale(0)`.** Start at `scale(0.9–0.97)` + `opacity: 0`. Nothing in the real world appears
  from nothing, and `scale(0)` reads as "came from a point", which no object does.
- **Origin-aware popovers.** A dropdown, menu, select or tooltip scales **out of its trigger**, not
  out of its own centre. We are on Base UI, which supplies the value — this is a free win we were not
  taking: `transform-origin: var(--transform-origin)`. **Modals are exempt**: they are not anchored to
  a trigger, so `transform-origin: center` is correct there and must not be reported as a defect.
- **Press feedback on anything pressable.** `transform: scale(0.97)` on `:active`, 100–160 ms
  `ease-out`. Subtle (0.95–0.98). `scale()` takes the label and icons with it, which is exactly what
  makes it read as a physical press — and `:active` is a real press on touch, so it needs no gating.
- **Percentages in `translate()` are relative to the element's own size.** `translateY(100%)` moves a
  sheet by its own height whatever its content is — which is how Sonner and Vaul position things.
  Prefer it to a hardcoded pixel value.

## Interruptibility — transitions and keyframes are not interchangeable

**CSS transitions retarget from the current value; `@keyframes` restart from zero.** So anything a
user can trigger twice in a second — toasts stacking, a toggle, an expand/collapse — must be a
transition or a spring. This is a correctness property, not a preference: keyframes on a toast make
it visibly jump.

`@starting-style` gives an entry animation with no JS and no mount flag:

```css
.toast {
  opacity: 1; transform: translateY(0);
  transition: opacity 400ms ease, transform 400ms ease;
  @starting-style { opacity: 0; transform: translateY(100%); }
}
```

Legacy fallback: `useEffect(() => setMounted(true), [])` plus a `data-mounted` attribute.

**Exit the way you entered.** A toast that slides up from the bottom leaves through the bottom.
Symmetric paths are what make swipe-to-dismiss feel obvious rather than learned.

**Asymmetric *timing*, though — slow where the user is deciding, fast where the system responds:**

```css
.overlay { transition: clip-path 200ms var(--ease-out); }          /* release: snappy */
.button:active .overlay { transition: clip-path 2s linear; }        /* press: deliberate */
```

`linear` is right there: the fill is a progress indicator, and progress should not ease.

## `clip-path: inset()` — the tool we had no mention of

`inset(top right bottom left)` eats in from each side, animates on the GPU, and solves four problems
that are awkward any other way:

- **Reveal on scroll** — `inset(0 0 100% 0)` → `inset(0 0 0 0)`. Marketing surfaces only, fired once.
- **Hold-to-confirm** — an overlay filling left to right over 2 s while the finger is down, snapping
  back in 200 ms on release. The honest alternative to a confirm dialog for a destructive action.
- **A tab indicator whose colours change in perfect sync** — duplicate the tab list, style the copy
  as the active state, and clip the copy to the active tab. The text and background change together
  because they are *one element being revealed*, not two colours being interpolated. Timing individual
  colour transitions across a tab list never quite lands; this does.
- **Comparison sliders** — a draggable divider wiping between two overlaid images.

## Gestures and drag

- **Dismiss on velocity, not only on distance.** `Math.abs(distance) / elapsedMs > ~0.11` dismisses.
  A flick should be enough; requiring the finger to cross a threshold makes a drawer feel heavy.
- **Project where the flick was going** before choosing a snap target — Apple's exponential-decay
  form, *not* the `v²/2a` from physics class:
  ```js
  const project = (velocity, decelerationRate = 0.998) =>
    ((velocity / 1000) * decelerationRate) / (1 - decelerationRate);
  ```
- **Rubber-band at boundaries** instead of stopping dead — the further past the edge, the less the
  element follows. A hard stop reads as frozen; rising resistance reads as "responsive, but there is
  nothing more here":
  ```js
  const rubberband = (overshoot, dimension, constant = 0.55) =>
    (overshoot * dimension * constant) / (dimension + constant * Math.abs(overshoot));
  ```
- **Pointer capture** (`setPointerCapture`) once the drag starts, so it survives the pointer leaving
  the element's bounds.
- **Multi-touch protection** — `if (isDragging) return` on new touch points, or switching fingers
  mid-drag makes the element jump.
- **Respect the grab offset.** Snapping the element's centre to the finger on grab breaks the illusion
  immediately; track from where they actually grabbed it.
- **Hand the release velocity to the spring**, so there is no seam between dragging and animating.
  Some APIs want it normalised: `gestureVelocity / (target − current)`. Motion takes raw px/s.
- **Springs, not durations, for anything a finger touched** — a spring carries velocity through an
  interruption, keyframes restart. And animate from the **presentation** (live, on-screen) value on
  interrupt, never from the logical target, or the motion visibly jumps.

Spring config, in the form that is easier to reason about:

```js
{ type: "spring", duration: 0.5, bounce: 0.2 }              // Apple-style — prefer this
{ type: "spring", mass: 1, stiffness: 100, damping: 10 }    // physics triplet — more control
```

Keep bounce at **0.1–0.3**, and **only when the gesture itself carried momentum**. Overshoot on a
menu that faded in feels wrong; overshoot on a card you flicked feels right. Default most UI to no
bounce at all.

## Stagger — 30–80 ms, and never blocking

Stagger a group entrance on a surface the user sees *occasionally*; never on a list they scroll past
all day. Longer than 80 ms between items feels slow. Stagger is decorative, so **it must never block
interaction while it plays**.

## Masking a crossfade that will not settle

When two states visibly overlap during a transition and no amount of easing or duration tuning fixes
it, blur the seam — `filter: blur(2px)` during the transition blends them into one perceived
transformation instead of two objects swapping. **Keep animated blur under 20 px**: heavy blur is
expensive, especially in Safari.

## Accessibility — two gates, not one

Non-negotiable ② already requires `prefers-reduced-motion`. Two refinements:

- **Reduced motion means fewer and gentler, not zero.** Keep the opacity and colour transitions that
  aid comprehension; drop movement, position changes, parallax and overshoot. A hard `animation: none`
  removes the feedback a reduced-motion user still needs.
- **Gate hover motion on capability, which we were not doing at all.** Touch has no hover, so browsers
  fake one: the first tap applies `:hover` and **leaves it there** until the user taps elsewhere. A
  button that scales up on hover stays scaled up after being tapped.
  ```css
  @media (hover: hover) and (pointer: fine) { .button:hover { transform: scale(1.02); } }
  ```
  Both conditions matter — `(hover: hover)` means the primary input can hover, `(pointer: fine)` means
  it is precise, which rules out styluses and Android devices that over-claim. **In Tailwind v4 the
  `hover:` variant already compiles to `@media (hover: hover)`**, so a project using `hover:` utilities
  is covered; hand-written `:hover` CSS is not. Touch users get their feedback from `:active` instead.

Two more media queries worth honouring, from Apple's own guidance and absent from our rules:
**`prefers-reduced-transparency: reduce`** (raise background opacity, drop the blur on translucent
chrome) and **`prefers-contrast: more`** (near-solid backgrounds, a defined contrasting border).

## Cohesion — the part that is taste, stated as a rule

Match the motion to the component's personality and to the product's. A playful component can be
bouncier; a professional dashboard stays crisp and fast. Sonner reads as elegant partly because it is
*slightly slower* than the generic UI budget and uses `ease` rather than `ease-out` — tuned to the
component rather than to the table. That is a legitimate deviation from the durations above, and the
test is whether you can say which personality it serves.

The one pair with no formula: **opacity against height** when items enter and exit a list. Adjust
until it feels right, then look again tomorrow.

## When feel cannot be judged from code — the checks to name instead of guessing

A reviewer (human or agent) who cannot run the UI should say so and point at these rather than
approving on inspection:

- **Slow motion.** Multiply the duration by 2–5×, or use the DevTools Animations panel at 10% speed.
  Check that colours crossfade cleanly, the easing does not stop abruptly, `transform-origin` is
  right, and coordinated properties stay in sync.
- **Frame by frame.** The Animations panel reveals timing drift between properties that are supposed
  to move together.
- **A real device for gestures.** Drawers and swipes cannot be judged with a mouse — connect a phone,
  hit the dev server by LAN IP, use Safari's Web Inspector or `chrome://inspect`.
- **Fresh eyes the next day.** Imperfections invisible during development surface immediately later.
  This is the cheapest check on the list and the one most often skipped.
