# Skeleton audit — size each skeleton to the UI it stands for

A skeleton is a promise about the shape of what is coming. When it is guessed — the scaffold's generic heading and
six cards, a single grey bar for a list of twelve rows — the page **jumps** when the data lands: everything below
the skeleton moves, the reader loses their place, a tap lands on the wrong row. The cure is not a better guess: it is
to **measure the loaded UI, then build the skeleton from those measures**, and prove the jump is gone.

Two measures prove it, and both are needed:

- **The boxes match**: each skeleton block against the loaded block it stands for, at the same width.
- **The page does not jump**: cumulative layout shift (CLS, web-vitals' worst session window) **≤ 0.05** per route and
  width — web-vitals calls ≤ 0.1 "good"; a skeleton built from measures should do better than good.

A CLS of 0 proves nothing unless the skeleton was **on screen**: on a hard load of a prerendered or cached route,
`loading.tsx` never renders, and a fast local server can deliver the data before the first paint.

## When

- After `design-md-to-app` scaffolds and a route gets real data — the template `loading.tsx` is a **placeholder
  shape** until this runs.
- When `data-fetching` adds a `<Suspense fallback>`, when `screenshot-to-page` builds a page with async data, when a
  route's layout changes (a new column, a filter bar).
- When the render probe reports `layout-shift` on a route.

## Where skeletons live

Every `loading.tsx` (route-level, shown while a route streams — mostly on client-side navigation) and every
`<Suspense fallback={…}>` inside a page:

```bash
find . -name loading.tsx -not -path "*/node_modules/*" -not -path "*/.next/*"
grep -rln "fallback=" --include=*.tsx . --exclude-dir=node_modules --exclude-dir=.next
```

## The procedure

1. **The states that change size.** For each route, the data states it really has: **empty**, **a few items**, **many
   items**, **long text** (a long name, a long title), **error**. Reach each one the way the verify manual says
   (`.claude/skills/verify-<app>/`: the seed, the test account, a query parameter) — never by editing the component.
   A state you cannot reproduce is listed in the report, not guessed.
2. **Measure both sides at 1440, 768 and 390 px, in en and it** (Italian runs longer and wraps more): the loaded UI's
   main blocks, and the skeleton held on screen. A throwaway Playwright script, not committed — the skeleton is held by
   **delaying the data, never the network** (throttling delays the first byte, and data arriving within that window
   comes with the page, so the skeleton never paints):

   ```ts
   // measure-skeleton.ts — run once with `pnpm dlx tsx measure-skeleton.ts /en/orders`, then delete
   import { chromium } from "playwright";
   const [route = "/en/orders"] = process.argv.slice(2);
   const BASE = "http://localhost:3000";
   const boxes = (sel: string) => (els: Element[]) =>
     els.map((e) => { const r = e.getBoundingClientRect(); return { sel, y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) }; });
   const browser = await chromium.launch();
   for (const width of [1440, 768, 390]) {
     const page = await browser.newPage({ viewport: { width, height: 900 } });
     await page.goto(BASE + route, { waitUntil: "networkidle" });                  // the loaded UI
     const loaded = await page.$$eval("main > * > *", boxes("loaded"));
     // Hold the route's RSC payload (Next sends it with the `rsc: 1` header on client navigation) for 3 s,
     // navigate to the route by a client-side link, and measure the fallback while it is up.
     await page.route("**/*", async (r) =>
       (r.request().headers()["rsc"] === "1" ? setTimeout(() => r.continue(), 3000) : r.continue()));
     await page.goto(BASE + "/", { waitUntil: "networkidle" });
     await page.evaluate((href) => { const a = Object.assign(document.createElement("a"), { href }); document.body.append(a); a.click(); }, route);
     await page.waitForSelector('[data-slot="skeleton"]');
     const skeleton = await page.$$eval('[data-slot="skeleton"]', boxes("skeleton"));
     console.log(JSON.stringify({ width, loaded, skeleton }));
     await page.close();
   }
   await browser.close();
   ```

   A `<Suspense>` fed by a client fetch is held the same way, with `page.route` on its data URL — or with the probe's
   `--delay` (step 3).
3. **Measure the jump as it is now**, on a hard load:

   ```bash
   node <skills>/app-verification/scripts/render_probe.mjs http://localhost:3000/en/orders \
       --widths 1440,768,390 --json [--delay /api/orders=1500]
   ```

   The report's `cls` is per width; a `layout-shift` finding names the elements that moved and **the block that pushed
   them** — that block is the one to size. `skeletons` lists every shadcn `<Skeleton>` painted during the load, with
   its first box. `--delay <url-substring>=<ms>` holds a client fetch so its skeleton is seen.
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
   - **Announce it**: the skeleton's container carries `role="status"` and `aria-busy="true"`, with a screen-reader-only
     label from messages (`<span className="sr-only">{t("loading")}</span>`, en + it) — shadscan flags a loading state
     a screen reader cannot hear.
   - **Reduced motion, once**: Tailwind's `animate-pulse` keeps pulsing under reduced motion. Stop it for every
     skeleton in `globals.css` — `@media (prefers-reduced-motion: reduce) { [data-slot="skeleton"] { animation: none; } }`
     — never class by class at each call site.
5. **Re-measure** both sides (steps 2 and 3). The route is done when every skeleton block is within a scale step of
   its loaded block, CLS ≤ 0.05 at every width in both locales, **and** the skeleton was seen (`skeletons` not empty,
   or the step-2 measurements).

## The report

Per route: the skeletons found, the states measured (and the ones that could not be reproduced), the skeleton boxes
against the loaded boxes, CLS before → after at 1440 / 768 / 390, the files changed. A route still over 0.05 says why
(a third-party embed, an ad slot, an image without dimensions — the last one is fixed with `width`/`height` or
`aspect-ratio`, not with the skeleton).
