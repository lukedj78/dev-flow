# Motion catalogues — where to look, and what looking is allowed to turn into

> Read 2026-09-27. Prices and counts move; re-read the source before quoting either.

Sites that publish animated components. They are useful as a **reference of what to build** — the
vocabulary of a loader, a menu, a reveal — and dangerous as a shortcut, because every one of them
hands you a second component namespace.

**Two rules decide what happens after you look:**

1. **Golden rule 3** (`dev-flow/references/contracts.md`). UI is composed from the primitives the
   project declared. A catalogue component that re-does a primitive the project already has — a
   switch, a toast, a card — is **ported**, not installed: take its timings, easings and gestures onto
   our primitive through `lib/motion/tokens.ts`. Only a component with no primitive behind it is a
   candidate for installing, and then it is a recorded exception.
2. **`registry-intake`** for anything that arrives as `shadcn add @ns/…` or a registry URL: allowlist
   with a reason, review the whole dependency closure, install the hashed snapshot. The hook refuses
   the shortcut. A catalogue is a **code mine, not a dependency**.

## React Bits — `@react-bits`

The one written up in full: `references/react-bits.md` (licence MIT + Commons Clause, the `TS-TW`
variant rule, the micro→primitive map, the `motion@^12` range trap). Start there; the map is the
worked example of rule 1.

## Loading — <https://loading.daniasyrofi.com>

**What it is.** A single page of ~24 named loaders — Orbit Status, Sonar Sweep, Newton Cradle,
Hourglass Flip, Kettle Whistle… — each a live specimen, with a playground for size (64 / 32 / 20 px)
and speed. React and HTML variants; the page says the component is "copied into `components/ui`".
**MIT**, © 2026 Dani Asyrofi — read off the header of `indicator.js`, which the site serves directly
for the HTML variant.

**Why it is worth knowing:** it is a vocabulary. Most projects reach for one spinner and stop; this
names two dozen shapes of waiting, which is exactly the decision a loading state needs.

**The discipline that comes first, though:** a loader is **not** the default for content that is
loading. `evals/generated-page/check.py` flags *a spinner where a skeleton belongs*, and shadcn ships
`Skeleton` for that. Reach for one of these only where a skeleton cannot express the wait:

- an **indeterminate** background job (export, import, a long agent turn);
- an **action in flight** inside a control that already exists (a `Button` with `disabled` + a small
  indicator), never a new button;
- a **full-page boot** where nothing is known yet.

Then keep it on our tokens: the duration and easing come from `lib/motion/tokens.ts`, and
`prefers-reduced-motion` is honoured — the site itself freezes its previews under that setting, which
is the right instinct and the one non-negotiable we do not delegate.

⚠️ **Not verified:** the exact install command. The page renders it with JavaScript and the block
stayed empty in a headless read, so read it in a real browser before running anything. There is no
`/r/registry.json`, so this is a copy-paste source, not a shadcn registry — which also means
`registry-intake` will not see it: **you** are the review.

## unlumen UI — `@unlumen-ui`, <https://ui.unlumen.com/components>

**What it is.** A shadcn registry: `npx shadcn@latest add @unlumen-ui/<name>`, items at
`https://ui.unlumen.com/r/{name}.json` (verified: `tilt-card` is `registry:ui`, depends on `motion`,
with `registryDependencies` inside its own namespace). The catalogue advertises 80 components and
monthly drops, split **Free / Pro**: Animations 28, Navigation 10, Backgrounds & Shaders 7, Icons 4,
Marketing 6, Image Effects 2.

**The price, before anyone gets close to a signup page** (2026-09-27): **Pro $119 one-time**
(listed against $149), lifetime access and unlimited projects; **Annual $69/year**; **Studio $430**
for 5 seats; 20 % student discount. The Free items are usable without any of that.

**Where it lands, and why that matters.** Its components install under `components/unlumen-ui/` and
are imported from there — a **second component namespace beside `components/ui/`**. That is precisely
what golden rule 3 exists to prevent, so the default action is to port the motion onto our primitive
rather than to compose the app from two libraries. Installing one is an exception with a reason
recorded in `meta.json#stack_config.primitive_exceptions`.

**Routing, when something there is genuinely new:**

- **Backgrounds & Shaders** (WebGL/canvas) → `vgpu-shaders` owns the gating questions: cost on a
  phone, battery, the reduced-motion fallback that must exist before the shader does.
- **Icons** (animated SVG, path morphing) → `animated-icons` already covers two registries with the
  reduced-motion guard and our timing tokens; compare before adding a third.
- **Navigation / Animations** → in almost every case a `Tabs`, `Sidebar`, `Accordion` or
  `NavigationMenu` primitive already exists: port the motion.

**What to take for free, without installing anything:** their component pages are a good model of
documentation — a props table, then a "Notes" section that states the awkward truths (fixed image
width, the anchor is a plain `<a>` and not a Next `<Link>`, the responsive heights). That is the
shape our own references aim for.
