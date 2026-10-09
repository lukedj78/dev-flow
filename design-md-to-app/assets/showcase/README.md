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
showcase spec tracks. Copy them into the project (`tailwindCssFile` for the CSS, the component
directory for the two `.tsx`) and keep them as they are.

**Upstream is tracked, not forked.** `references/showcase-template.md` follows
`skills/shadcn/design-system-page.md`; when that file changes, diff it and follow. If one of these
three helpers needs a change for our stack, say so in the diff rather than editing it silently —
otherwise the next upstream read cannot tell our change from theirs.
