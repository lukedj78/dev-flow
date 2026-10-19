# Skeleton audit — size each skeleton to the UI it stands for

A skeleton is a promise about the shape of what is coming. When it is guessed — the scaffold's generic heading and
six cards, a single grey bar for a list of twelve rows — the page **jumps** when the data lands: everything below
the skeleton moves, the reader loses their place, a tap lands on the wrong row. The cure is not a better guess: it is
to **measure the loaded UI, then build the skeleton from those measures**, and prove the jump is gone.

The probe measures the jump as cumulative layout shift (CLS): **target ≤ 0.05** per route and width (web-vitals calls
≤ 0.1 "good"; a skeleton built from measures should do better than good).

## When

- After `design-md-to-app` scaffolds and a route gets real data — the template `loading.tsx` is a **placeholder
  shape** until this runs.
- When a route's layout changes (a new column, a filter bar), and when `screenshot-to-page` builds a page with async
  data.
- When the probe reports `layout-shift` on a route.

## Where skeletons live

Every `loading.tsx` (route-level, the streaming fallback) and every `<Suspense fallback={…}>` inside a page. List them
first: `grep -rln "loading.tsx\|fallback=" app components`.

## The procedure

1. **The states that change size.** For each route, the data states it really has: **empty**, **a few items**, **many
   items**, **long text** (a long name, a long title), **error**. Reach each one the way the verify manual says
   (`.claude/skills/verify-<app>/`: the seed, the test account, a query parameter) — never by editing the component.
   A state you cannot reproduce is listed in the report, not guessed.
2. **Measure the loaded UI** at **1440, 768 and 390 px**, in **en and it** (Italian runs longer and wraps more), with
   Playwright (or the browser tools you have): the bounding box of each main block — the heading, the toolbar, each
   card or row, the table, the pagination — and the container around them (its grid, padding and gaps).
3. **Measure the jump as it is now:**

   ```bash
   node <skills>/app-verification/scripts/render_probe.mjs http://localhost:3000/en/orders \
       --widths 1440,768,390 --throttle fast-3g --json
   ```

   `--throttle` keeps the skeleton up long enough to be measured; the report's `cls` is per width, and a
   `layout-shift` finding names the elements that moved.
4. **Rebuild the skeleton from the measures:**
   - **The loaded UI's own containers** — the same grid, the same padding and gaps, the same number of columns per
     breakpoint. Share the layout component when you can, so the two cannot drift.
   - **shadcn `<Skeleton>` only** (golden rule 3): never a hand-made grey `div`.
   - **Sizes on the scale**: each measured height to its nearest step (`h-4`, `h-10`, `h-32`, `size-12`), widths as
     fractions (`w-3/4`) or the container's own; never `h-[37px]`. A 2–4 px rounding moves nothing a reader notices;
     a wrong block count moves everything.
   - **Size for the most common state**, not the extremes: the usual number of rows the first page shows, a typical
     line count. The empty and error states have their own components, sized the same way, not a skeleton.
   - **Text lines as text**: a two-line title is two `h-*` bars at the title's line height, not one tall block.
   - **Reduced motion**: shadcn's `Skeleton` pulses with `animate-pulse`; add `motion-reduce:animate-none` where the
     project's Skeleton does not already stop.
5. **Re-measure** with the same command. The route is done when CLS ≤ 0.05 at every width, in both locales.

## The report

Per route: the skeletons found, the states measured (and the ones that could not be reproduced), CLS before → after
at 1440 / 768 / 390, the files changed. A route still over 0.05 says why (a third-party embed, an ad slot, an image
without dimensions — the last one is fixed with `width`/`height` or `aspect-ratio`, not with the skeleton).
