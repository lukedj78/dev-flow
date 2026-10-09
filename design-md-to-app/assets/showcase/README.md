# Showcase helpers — vendored from shadcn-ui/ui

Three files copied verbatim from
[`skills/shadcn/assets/showcase/`](https://github.com/shadcn-ui/ui/tree/main/skills/shadcn/assets/showcase)
on **2026-10-09**, MIT (shadcn-ui/ui), at the commit that added the DESIGN.md design-system workflow
(PR #12252).

| File | What it does |
|---|---|
| `preview-states.css` | Redefines the `hover`, `focus-visible` and `active` Tailwind variants so each also matches a `data-preview` attribute. This is what makes a **state matrix possible on a static page**: a row of `<Button data-preview="hover">` renders the hover state at rest. The `hover` variant keeps its `@media (hover: hover)` guard, so the matrix does not reintroduce a sticky hover on touch. |
| `state-matrix.tsx` | `StateMatrix` + `previewState(state)` — the grid that renders variant × state for a primitive. |
| `color-pair.tsx` | Renders a foreground/background pair **with its measured contrast ratio**, which is what turns the Foundations section from swatches into a check. |

**Vendored rather than reimplemented**, deliberately: together they are about 5.5 KB, and a
hand-written `StateMatrix` would be 5.5 KB of divergence from the upstream that the rest of the
showcase spec tracks. Keep them as they are.

## Where they go, and how they are called

Put the CSS in `tailwindCssFile`, and the two `.tsx` **under the showcase route**
(`app/<locale>/showcase/_components/`), *not* in the project's shared component directory. The
design-system lint's exception for literal values is scoped by path to the showcase folder, so a
helper that lives in `components/shared/` is linted as product code and `color-pair.tsx` fails
`shadcn/no-inline-styles` — which it cannot avoid, since painting a pair is its whole job.

`ColorPair` takes **bare token names**, not CSS expressions: it builds `var(--<token>)` itself.

```tsx
<ColorPair name="primary / primary-foreground" background="primary" foreground="primary-foreground" />
```

Pass `background="var(--primary)"` and it renders `var(--var(--primary))` — no colour, and the
label underneath reads `--var(--primary)`, which is how you spot it.

## ⚠️ One adaptation every Next project needs

These were written for a **Vite** app, where there is no server/client split. In the App Router,
**`color-pair.tsx` needs `"use client"` as its first line**: it resolves a colour by painting a pixel
and reading it back, so it uses `useRef`, `useState` and `useEffect`, and the showcase page itself is
a server component (`async` + `getTranslations`). Without the directive the page fails to build.

`state-matrix.tsx` needs nothing — it only renders, and a server component may pass it a `render`
function. `preview-states.css` goes into the app's global stylesheet **after the `@custom-variant
dark` line**.

Add the directive when you copy the file, and leave the rest byte-identical, so the next upstream
read still diffs cleanly. Found on 2026-10-09 installing these into `fit-room`.

**Upstream is tracked, not forked.** `references/showcase-template.md` follows
`skills/shadcn/design-system-page.md`; when that file changes, diff it and follow. If one of these
three helpers needs a change for our stack, say so in the diff rather than editing it silently —
otherwise the next upstream read cannot tell our change from theirs.
