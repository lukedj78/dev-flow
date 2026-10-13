# The layer under the camera — pointer, frames, and teardown

`SKILL.md` owns the decisions: the frame budget, live vs snapshot, the origin, the declared
interaction mode, the two coordinate spaces. Those are what you get wrong on a whiteboard.

**This file is what you get wrong in the browser.** None of it changes the architecture; all of it
decides whether the canvas feels broken. The seven below are where a pan/zoom surface actually
fails, in the order they tend to bite.

> Merged from **ibelick/ui-skills** `component-canvas` (MIT, read 2026-10-13), the way
> `transitions` absorbed emilkowalski's material: the knowledge, rewritten in our words, inside
> the skill that already owns the subject. We did not install it — see
> `dev-flow/references/resources.md`.

## 1. `touch-action: none` is not a gesture strategy

The canvas shell owns pan and zoom. The content inside a preview owns its own scrolling, its text
selection and its typing. Put `touch-action: none` on interactive content and you have taken the
second away to get the first.

Same for a broad `preventDefault` on pointer or wheel events: it buys you a clean gesture and
silently removes nested scroll, selection and native pinch inside the preview. Cancel narrowly, on
the surface that is actually panning — empty canvas space — and let the rest through. This is the
mechanical half of the **declared interaction mode** in `SKILL.md`: the mode decides *who* owns the
gesture, this decides *how little* you take to own it.

## 2. One transform per animation frame, and never interleaved with layout reads

A pointer emits far more events than the screen has frames. Applying the camera transform on every
event burns work nobody sees.

Coalesce: accumulate the delta, apply it once in a `requestAnimationFrame`.

The sharper rule is the second one: **do not alternate layout reads and writes in the same pass.**
A `getBoundingClientRect()` after a style write forces synchronous layout, and in a gesture loop
that is a stutter you can feel but cannot find in a profile's flame graph, because it is spread
across every frame. Read all the geometry you need, then write all the transforms.

## 3. The pointer does not always finish what it starts

`pointerdown → pointermove → pointerup` is the happy path, and a canvas that only handles it keeps
panning after you alt-tab. Handle, each with its own exit:

- **`pointercancel`** — the browser took the gesture (a system swipe, a scroll takeover).
- **Lost capture** (`lostpointercapture`) — the element stopped receiving the stream.
- **A pointer-count change** — a second finger lands mid-pan, and a pan is now a pinch. Decide
  which gesture wins and switch deliberately; do not let both run.
- **`blur`** on the window and **`visibilitychange`** on the document — the user left. A gesture in
  flight must end, not pause.

On teardown release every capture and clear every listener, observer, timer and animation frame.
A canvas unmounted mid-gesture that left a `requestAnimationFrame` loop running is a route that
costs CPU for the rest of the session.

## 4. A portal does not live under your transform

This is the trap that looks like a component bug and is not.

A dialog, a popover, a tooltip renders into its **native root** — `document.body`, usually — which
is outside the canvas's transformed subtree. So it is laid out in **screen space**, at screen size,
while its trigger is inside a scaled, translated world. The positioning library computes against
the viewport and is right by its own lights; the result lands somewhere the user is not looking,
or looks correct and takes clicks in the wrong rectangle.

Check the **clickable area**, not just the appearance: a portal can render in the right place and
still be hit-tested against an untransformed box.

What not to do: patch the component, inject a container, or move portals into the canvas subtree.
A preview whose portals you had to modify is no longer a preview of the real component. Use the
library's public container option if it has one; otherwise report the limit and show that component
outside the canvas. `SKILL.md` §Overlays render in the parent is the same principle from the other
side — our chrome goes in the parent, their portals stay in their root.

## 5. A camera with no bounds is a canvas you can lose

Validate every camera value and clamp it. The failure is mundane and total: a user pans into empty
space, the content is a thousand units away, and there is nothing on screen to click.

So: **fit-all and reset are reachable even when the view is lost** — fixed to the shell, not placed
in the world, with accessible names. They are the canvas's undo, and they are the one piece of
chrome a component canvas cannot omit.

## 6. The camera follows focus, and the page never moves

Keyboard focus can land on something outside the visible area. The camera moves to reveal it —
otherwise the canvas is unusable by keyboard and inaccessible by law.

The inverse matters as much: **native page scrolling must not move the canvas.** If focusing an
off-screen element scrolls the document instead of moving the camera, the shell leaves the viewport
and the user is looking at the page's margins. Keep the canvas viewport fixed and move the world.

## 7. Fit after the layout settles, and fitting never rearranges

Fit computed while content is still arriving frames the wrong rectangle. Measure after layout
settles, and ignore rendering-containment placeholders — the empty boxes `content-visibility`
reserves before real content renders — because their size is a promise, not a measurement.

Two rules keep this from becoming a loop:

- **Fitting moves the camera, never the groups.** A fit that reflows content changes what it was
  fitting and runs again.
- **Prevent overlap on resize without a layout loop.** Recompute positions from measured bounds in
  one pass, do not nudge iteratively until nothing overlaps.

## A divergence worth keeping

`component-canvas` says to exercise hover, focus and pressed states through **real pointer and
keyboard input**, never through added classes. On an interactive canvas that is correct, and it is
the stronger test: a class says the state was styled, input says the state is reachable.

Our **showcase** does the opposite on purpose — `data-preview="hover"` plus a redefined Tailwind
variant (`design-md-to-app/references/showcase-template.md`). A *static* page cannot hover itself,
and a variant × state matrix exists precisely to show at rest what a reader could otherwise only
discover by pointing at it.

Both are right on their own surface. Do not reconcile them.
