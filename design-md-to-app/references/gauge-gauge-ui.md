# Gauges (web) — gauge-ui

The **how**, not just "use gauge-ui". Read against the published item
`https://www.gauge-ui.dev/r/gauge.json` — the source of truth for props — and
`github.com/thordursk/gauge-ui` (**MIT**). Verified **2026-10-03**.

`gauge-ui` is composable **SVG gauges** for React, distributed as a shadcn registry. One item,
`gauge`, fourteen files into `components/gauge/`, and **no npm dependencies at all**.

## What the review says, and why that is remarkable

```
https://www.gauge-ui.dev/r/gauge.json · tier low · clean
```

**Zero findings** — the first registry item we have reviewed with none. There is nothing to accept
and nothing to port, because there is nothing to object to: no `cssVars`, no config or tooling
target, no npm dependency to licence-check, and one `registryDependencies` entry — `utils`, a bare
name, which is shadcn's own and therefore not governed. Approve it, snapshot it, install it.

**It has no colour of its own.** No Tailwind palette class, no hex value anywhere in the fourteen
files, and `currentColor` eight times: the gauge inherits its colour from CSS context, so DESIGN.md's
tokens apply without the component knowing they exist. That is the cleanest answer to golden rule 3
we have seen — compare Watermelon UI shipping `#3E3E43`, Arc UI shipping 97 tokens on `:root`, and
audiocn needing twelve new ones. Here the number is zero.

It imports `cn` from `@/lib/utils`, which works unchanged in our projects where that file is
`export { cn } from "cn"`.

## Install

```bash
pnpm dlx shadcn@latest add https://www.gauge-ui.dev/r/gauge.json   # through registry-intake
```

The apex domain 308-redirects, so use `www.gauge-ui.dev`: `gauge-ui.dev/r/gauge.json` makes the CLI
follow a redirect on every fetch, and a `registry.json` fetched without `www` fails outright.

One item installs the whole set into `components/gauge/`:

| | |
|---|---|
| composition | `index.ts`, `gauge.tsx` (the `<svg>` and its viewBox), `context.tsx`, `inset.tsx` |
| marks | `arcs.tsx`, `ticks.tsx`, `needle.tsx`, `dot.tsx`, `text.tsx` |
| interaction | `control.tsx` — a gauge the user **drags** |
| maths and motion | `math.ts`, `utils.ts`, `transition.ts`, `use-animated-value.ts` |

Ten of the fourteen files are `"use client"`.

## Motion

One `requestAnimationFrame` loop, cancelled on teardown, in `use-animated-value.ts`. It honours
`prefers-reduced-motion` **by snapping** — the comment says so in as many words — and reads the query
per transition rather than once on mount, which is the right granularity for a value that changes.
Note it is a direct `window.matchMedia(…).matches` read, not a subscription: a reader who flips the
OS setting mid-session sees it apply from the next value change, not immediately. That is fine here
and worth knowing if you copy the pattern.

## Accessibility — the one real gap

**The interactive gauge is correct.** `control.tsx` carries `role="slider"` with `aria-label`,
`aria-valuemin`, `aria-valuemax`, `aria-valuenow`, `aria-valuetext` and `aria-disabled`. That is the
right ARIA for a dial someone drags, and it is more than most registries ship.

**The read-only gauge carries none.** The root `<svg>` in `gauge.tsx` has no `role="img"` and no
`aria-label`. A screen reader does read the number, because `text.tsx` renders a real SVG `<text>`
node — but nothing says *what* that number measures. So when the gauge is presentational, do one of
two things yourself, and `shadscan` will ask for it either way:

- put `role="img"` and an `aria-label` that names the measure and its unit on the gauge, or
- mark the gauge `aria-hidden` and keep the value and its label in ordinary text beside it.

## When a gauge is the right component, and when it is decoration

A gauge is a **data-viz decision**, so the form question comes first: a single number is usually
better as a number with a sparkline, and a gauge that fills a card to show "73" has spent a lot of
pixels on one digit.

A gauge earns its place when the value has **a bounded range whose zones mean something** and the
reader has to judge position at a glance: a disk filling up, a rate limit approaching, a temperature
inside or outside a comfort band, a speed against a limit. Then the arc *is* the information.

And `control.tsx` is the real differentiator: a gauge the user **turns** — a thermostat dial, a
trim control — is otherwise a custom build every time, and this one arrives with its slider
semantics already right.

## The alternative, and why it lost

`antoniolago/react-gauge-component` is the one thing a GitHub search surfaces for this need — 201
stars, MIT, pushed 2026-08-16, alive. It is a competent library and the wrong shape for us, on three
counts measured on 2026-10-03:

| | gauge-ui | react-gauge-component |
|---|---|---|
| What lands in the repo | 14 files of source you own | an npm dependency, **776 KB unpacked** |
| Underneath it | nothing | **d3 ^7.9.0**, to draw an arc and a needle |
| Colour | `currentColor`: inherits the page, so DESIGN.md applies untouched | its own props, configured per instance |
| A dial the user turns | `Control`, with slider ARIA | none |

The d3 line is the one that decides it. A charting grammar is the right dependency for a chart
library; for one gauge it is a large surface, a second animation model beside Motion, and a package
whose major we would then have to track. The rest follows: a configured component themes through its
API, which means the gauge's colours live somewhere other than the design system.

## Standing

Six days old at the time of reading (created 2026-09-27), three stars, one author, pushed once since.
The code is small, dependency-free and better behaved than catalogues ten times its size, which is
exactly why the ordinary rule applies with no drama: the snapshot you install is the version you own,
nothing will upgrade it, and `[VERIFY]` the props after any re-install.
