# React Bits — borrowed motion, and the four things to fix on the way in

[React Bits](https://reactbits.dev) ([DavidHDev/react-bits](https://github.com/DavidHDev/react-bits), 47.5k★,
read 2026-09-18) is a catalogue of animated React components served as a **shadcn registry**, so it arrives
through `registry-intake` like any other third-party registry. It is a **source of motion**, not a component
library to adopt: the tier ladder in `SKILL.md` and golden rule 3 both still decide what may land.

## What it is, exactly

- **Registry:** `https://reactbits.dev/r/registry.json`, `$schema` = `ui.shadcn.com/schema/registry.json`,
  namespace `@react-bits`. Items at `https://reactbits.dev/r/{name}.json`.
- **808 items = 202 components × 4 variants**, suffixed `JS-CSS`, `JS-TW`, `TS-CSS`, `TS-TW`.
  **Always take `TS-TW`** — our projects are TypeScript + Tailwind; a `-CSS` variant brings its own stylesheet
  and a `JS-` one drops the types.
- **Licence: MIT + Commons Clause** (`LICENSE.md`): use, modify and distribute *"as part of an application,
  website, or product"*, including commercially, *"so long as you do not sell, sublicense, or redistribute the
  components themselves — whether alone, in a bundle, or as a ported version."* So: fine inside a product we
  build. **Not** fine in anything we publish as components — never vendor one into this repo, a public
  `packages/ui` template, or our own registry.
- **Runtimes it pulls** (from the registry's own `dependencies`, across all items): `ogl` (188 items),
  `motion` (152), `gsap` (142), `three` (92), `@hugeicons/*`, `@react-three/fiber`, `postprocessing`,
  `matter-js`. Licences checked: `ogl` Unlicense, `three` MIT, `matter-js` MIT, **`gsap` is a
  "Standard 'no charge' license"**, not an OSI licence — read it before a GSAP-based item enters a client project.

## The `/c/micro` category — 30 micro-interactions

Branched Menu · Folder Float · Refine Frame · Thought Line · Voice Pill · Slosh Gauge · Prompt Bar ·
Swipe Toast · Sling Button · Bell Toggle · Call Chip · Status Mark · Glide Select · Swipe Row · Jelly Radio ·
Comet Dial · Wake Slider · Code Slots · Dodge Field · Lattice Loader · Scrub Field · Fuse Button ·
Warm Tooltip · Slide Commit · Rubber Segment · Pulse Heart · Spring Check · Peek Rating · Hold Button ·
Squish Switch.

They are **Motion-based** (`motion@^12.23.12`) and, checked in the source of `SpringCheck`, `SquishSwitch`,
`BellToggle` and `SwipeToast`, they call **`useReducedMotion()`** from `motion/react` themselves — non-negotiable 2
is satisfied by the component, so **don't strip that hook** when you adapt it.

## Golden rule 3 comes first: most of these ARE primitives

More than half the micro set animates a pattern shadcn already ships. Installing it as a component would give
the project two checkboxes, two switches, two toasts — exactly what golden rule 3 forbids
(`references/contracts.md` §Golden rules).

| React Bits micro | The primitive that owns the pattern | What to do |
|---|---|---|
| Spring Check | `Checkbox` | port the motion into ours |
| Squish Switch | `Switch` | port the motion |
| Jelly Radio | `RadioGroup` | port the motion |
| Glide Select | `Select` | port the motion |
| Warm Tooltip | `Tooltip` | port the motion |
| Swipe Toast | `Sonner` (shadcn's toast) | port the swipe-dismiss behaviour; shadcn's Toast already has one — compare first |
| Hold / Sling / Fuse / Slide Commit buttons | `Button` (+ variants) | port the motion as a variant or a wrapper; never a second button |
| Wake Slider · Scrub Field · Slosh Gauge · Comet Dial | `Slider` | port the motion |
| Code Slots | `InputOTP` | port the motion |
| Status Mark | `Badge` | port |
| Rubber Segment | `Tabs` / `ToggleGroup` | port |
| Branched Menu · Bubble-style menus | `DropdownMenu` / `NavigationMenu` | port |
| Bell Toggle | an animated icon — `animated-icons` owns this | use that skill's registries instead |
| Peek Rating · Pulse Heart · Voice Pill · Call Chip · Thought Line · Folder Float · Dodge Field · Lattice Loader · Prompt Bar · Refine Frame · Swipe Row | no shadcn primitive | a domain component in `_components/`, composed from primitives where it can be |

**"Port the motion" means:** read the item (`shadcn add <url> --view`, or `registry_intake.py review`), take the
timings, easings and gesture logic, and express them through `lib/motion/tokens.ts` on **our** primitive. That is
this skill's Tier 3 work, and it leaves `components/ui/` intact. A component that genuinely has no primitive
behind it is a normal domain component — and if you truly need a *new primitive*, that is the recorded exception
golden rule 3 describes (`meta.json#stack_config.primitive_exceptions`), not a silent install.

## Installing one, when it is the last row of the table

Third-party registry ⇒ `registry-intake`, never a bare `shadcn add`:

```bash
S=<skills>/registry-intake/scripts/registry_intake.py
python3 $S allow   <root> @react-bits 'https://reactbits.dev/r/{name}.json' \
  --reason "micro-interaction source for <feature>" --by <name>
python3 $S review  <root> @react-bits/PeekRating-TS-TW
python3 $S approve <root> @react-bits/PeekRating-TS-TW --by <name>
python3 $S install <root> @react-bits/PeekRating-TS-TW
```

Two findings the review raises on this registry, both by design:

- **D7 — the Motion major.** Every micro item declares `motion@^12.23.12`; our projects are on **13.4.0**. Do not
  let the install add a second major: install the component, then run it against the project's Motion. Verified in
  `SpringCheck`: it uses `animate`, `useMotionValue`, `useMotionValueEvent` and `useReducedMotion` from
  `motion/react`, all of which exist in 13 — but `[VERIFY]` the imports of whichever item you take, and pin
  nothing to 12.
- **S6 — very wide lines.** `SwipeToast` carries a single 1070-character Tailwind class list of arbitrary values
  (`w-[min(var(--st-w),100%)]`, `text-[13px]`, `data-[inline=false]:bottom-[calc(...)]`…). The design lint counts
  each one, and these files land in `components/<Name>/`, **not** in the exempt `components/ui/` directory — so
  the cap jumps. `registry_intake.py check` refuses a raised cap, which is the point: convert the arbitrary values
  to tokens as part of adopting the component, or don't adopt it.

## Where its other categories sit on the ladder

- **Micro** (Motion) → **Tier 3**. Requires the Motion runtime (`module-add motion`).
- **Text animations, components** (Motion or GSAP) → Tier 3. A **GSAP** item adds a *second* animation engine to a
  project that already has Motion: take the idea, not the dependency, unless the effect is unreachable otherwise.
- **Backgrounds** (`ogl`, `three`, `postprocessing`, `@react-three/fiber`) → **Tier 4 territory**. Read
  `vgpu-shaders` §the three gating questions first; a WebGL canvas behind a screen someone keeps open all day is
  the case that skill exists to refuse. None of our stack ships `ogl` or `three` today — adding one is a stack
  decision, and it wants `stack.shaders` recorded.

## In one line

Take React Bits as a **motion cookbook**: read it freely, port timings and gestures onto our own primitives, and
let `registry-intake` handle the rare item that has no primitive behind it — `TS-TW`, Motion 13, tokens instead of
arbitrary values, and nothing of it ever republished.
