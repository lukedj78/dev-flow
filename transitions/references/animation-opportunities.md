# Animation opportunities — where it should move, and where it must not

Audit mode finds motion that is wrong. This finds motion that is **missing**: the places where an interface would read
better, feel more alive or stop teleporting if something moved — and rejects everything that should stay still.
Adapted from emilkowalski/skills' `find-animation-opportunities` (MIT, read 2026-10-19), rewritten onto our tokens and
our Step 0 gate (`animation-standards.md`).

It is a filter as much as a finder. A list of motion everywhere produces the sluggish, over-animated interface the
gate exists to prevent; **expect to reject most candidates**, and report at most **5–7 for a whole app** (fewer for one
view), ordered by leverage. Read-only: it proposes exact values, Apply mode implements the ones the user picks.

## The gate — every candidate, all four, in order

1. **Frequency** (Step 0). 100+ times a day — keyboard shortcuts, a command palette, core navigation — **never**.
   Tens of times a day (hover, list navigation, frequent toggles): reject, or near-imperceptible only. Occasional
   (modals, drawers, toasts, settings): standard motion. **Rare or first-time** (onboarding, empty states, success,
   celebration): this is where the delight budget lives.
2. **Purpose**, named in one word: *feedback*, *spatial* (where it came from or went), *state* (a change made
   legible), *bridge* (content that would otherwise teleport), *explanation* (marketing and onboarding), or *delight*
   (rare and first-time only). "It looks good" is not a purpose.
3. **Speed.** It must work inside the duration tokens — press 100–160 ms, tooltips 125–200 ms, menus 150–250 ms,
   modals and drawers 200–500 ms; only marketing and explanation may run longer. A moment that only works slow fails.
4. **Function.** Data the user is reading or acting on does not move for style: a mouse-tracking flourish belongs on a
   marketing page, never on a chart in a banking dashboard.

## Where to look

- **Feedback gaps** — a pressable element with no `:active` (anti-slop rule 8: `active:scale-[0.97]`, press
  duration); a destructive action on a plain click where a hold-to-confirm fill would prevent slips
  (`clip-path: inset()` fill over the button, `animation-standards.md` §clip-path).
- **Teleporting state** — conditional renders (`{open && …}`), route content, expanding sections, list items added or
  removed with no bridge: fade + `scale(0.95–0.97)` from `opacity: 0`, never `scale(0)`; `@starting-style` or
  `tw-animate-css` entrances; CSS transitions rather than keyframes where a rapid re-trigger must retarget.
- **Missing spatial story** — a popover or menu with no connection to its trigger (scale from
  `var(--transform-origin)`, which Base UI sets; modals stay centred); a toast or sheet that leaves by a different
  edge than it came in (symmetric paths, `translateY(100%)`).
- **Group entrances** — an occasional grid that pops in at once: anti-slop rule 10's stagger, 30–80 ms, never blocking.
- **Gesture seams** — a draggable or swipeable element that snaps without physics: springs from the token layer,
  velocity-based dismissal, rubber-banding at the edges (`animation-standards.md` §Gestures and drag).
- **The delight budget** — first-run, empty states, success and completion rendered flat: the only places bounce, a
  generous stagger or a longer beat are welcome — and the answer to "make it feel more alive" on a product people use
  every day.

Useful sweeps: `{isOpen &&` and `display: none` toggles; `onClick` on elements with no `:active` or transition;
`<details>` and accordion markup; drag handlers; `.map(` over entering lists; empty-state and success components.

## The report

1. **Opportunities** — one row each, by leverage: `file:line` · what happens today · purpose · frequency · the motion
   with exact token values (`ease.*`, `duration.*`, `spring.*` from `lib/motion/tokens.ts`; never a parallel set),
   `transform`/`opacity` only, the reduced-motion version (gentler, not zero) and hover gating where it applies.
2. **Rejected candidates — required.** Two to five places considered and deliberately left still, each with the gate
   question that stopped it ("command palette — keyboard, 100+/day"; "analytics chart line-draw — data being read").
   This is what separates the audit from a wishlist.
3. **Verdict** — how much motion this interface needs, whether it is close already, the single highest-leverage
   suggestion. If nothing survives, say so: that is a good result.
