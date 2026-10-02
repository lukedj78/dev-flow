# Audio UI (web) — audiocn

The **how**, not just "use audiocn". Read against the published registry — `https://www.audiocn.dev/r/registry.json`
and the items themselves, which are the source of truth for props — and `github.com/audiocn/ui`.
Verified **2026-10-02**.

`audiocn` is a shadcn-format registry of **audio** components: mixers, faders, knobs, level meters,
waveforms, spectrum analysers, sound pads, an audio player. It is what a project reaches for when the
product has sound in it — a soundboard, a recorder, a mixing view, a player with a real waveform —
and the alternative is hand-rolling Web Audio plumbing next to a `<canvas>`.

## Read first

**Licence: MIT** (`license.md`, Copyright 2026 OrcDev). Note the trap: the file is lowercase, so
GitHub's own licence detector reports `NOASSERTION` and the repo page reads *"Other"*. Anyone
checking the badge instead of the file will conclude the wrong thing.

**It is two days old.** Created 2026-09-30, 27 stars. That is not a reason to avoid it — the code is
better behaved than most of what we have reviewed — but it is a reason to treat the copy you install
as the version you own: nothing will upgrade it, and `[VERIFY]` the identifiers after every install.

**It is blocked by `registry-intake` on C1, and that is the correct outcome to *accept*, not to
refuse.** `@audiocn/core` adds twelve semantic tokens through `cssVars.theme` plus light and dark
values:

```
meter-ok · meter-warn · meter-clip · channel-mute · channel-solo · channel-monitor
+ a -foreground for each
```

C1 exists because DESIGN.md owns the token layer, and that rule holds. But this is not Arc UI
redefining 97 tokens on `:root` — it is a **domain vocabulary DESIGN.md does not have**: a level
meter needs an ok / warn / clip scale, and no brand palette provides one. So the flow is:

1. `review` it and show the report, including C1;
2. decide the twelve values **from DESIGN.md** — the warning and clip colours should be the project's
   own warning and destructive hues, not audiocn's oklch defaults;
3. `approve … --accept C1="twelve audio-domain semantic tokens, values re-derived from DESIGN.md"`;
4. after `install`, replace the installed values with the derived ones and keep that edit — the
   snapshot is ours from then on.

Record the decision where the next person will see it, because an accepted C1 is a precedent.

## Install

```bash
# components.json
{ "registries": { "@audiocn": "https://www.audiocn.dev/r/{name}.json" } }

pnpm dlx shadcn@latest add @audiocn/mixer      # through registry-intake, never directly
```

The apex domain 308-redirects: use `www.audiocn.dev` in the registry URL, or the shadcn CLI follows a
redirect on every item fetch.

**Where it writes — into our own folders, not a second namespace:**

| Target | What |
|---|---|
| `components/ui/<name>.tsx` | the components, beside our primitives |
| `lib/audio/*.ts` | `@audiocn/core`: 11 files — `decibels`, `ballistics`, `taper`, `bands`, `zones`, `bar-levels`, `wave-line`, `time`, `frame-loop`, `frame-source`, `types` |
| `hooks/use-*.tsx` | 18 hooks over the Web Audio API |

That is the opposite of unlumen UI and Watermelon, which install under their own directory. It is
better — there is no second component namespace and golden rule 3 is not at stake — and it means the
files are **ours to lint and own from the first minute**, with no "theirs vs ours" boundary to hide
behind.

## The set, as the registry declares it

49 items: **23 `registry:ui`**, **18 `registry:hook`**, 2 `registry:lib`, 6 `registry:block`.

- **Meters and visualisers** — `level-meter`, `db-readout`, `db-scale`, `clip-indicator`,
  `bar-visualizer`, `spectrum`, `waveform`, `smooth-waveform`, `live-waveform`, `electric-waveform`
- **Controls** — `fader`, `knob`, `pan-control`, `parameter-slider`, `volume-control`,
  `channel-toggle`, `channel-strip`, `mixer`, `sound-pad`
- **Devices and system** — `audio-device-select`, `mic-setup`, `system-audio-mixer`,
  `system-audio-settings`, `quick-audio-popover`
- **Blocks** — `audio-player`, `music-player`, `soundboard`, `track-list`, `electric`
- **Hooks** — the layer worth reading even if no component is installed:
  `use-audio-analyser`, `use-web-audio-mixer`, `use-gain-node`, `use-level`, `use-microphone`,
  `use-waveform-data`, `use-frame-source`, `use-clip-hold`, `use-demo-signal`, `use-visibility`,
  `use-reduced-motion`, `use-sound`, `use-audio-context`, `use-audio-devices`, `use-audio-player`,
  `use-mixer`, `use-system-audio`, `use-audio-config`

## What it does right, verified in the source

**It uses our tokens.** `channel-strip` (453 lines) is `cva` + `cn`, and its classes are
`bg-muted`, `text-muted-foreground`, `bg-card`, `text-foreground` plus the audio tokens above.
**No raw Tailwind palette colours, no arbitrary hex values.** That is why the design lint has
nothing to say about it, and it is rarer than it should be — compare Watermelon UI, where the
untwinned items ship `#3E3E43` and `text-[15px]`.

**One frame loop, shared.** `waveform` and `spectrum` draw on `<canvas>`, but the
`requestAnimationFrame` loop lives once in `@audiocn/core` (`frame-loop.ts`, `frame-source.ts`)
behind `use-frame-source`, rather than being duplicated per component. A mixer with eight meters
costs one loop.

**`use-reduced-motion` is a first-class item**, written with `useSyncExternalStore`, SSR-safe, and
subscribed to `matchMedia` changes rather than read once on mount. `spectrum` and `level-meter` use
it; **`waveform` and `knob` do not** — check that before shipping a visualiser, and reach for the
hook plus `use-visibility` (pause while the tab is hidden) around any loop you keep.

**Dependencies are per component, not global**, which decides compatibility with the project's UI
library:

| Item | npm dependencies |
|---|---|
| `fader`, `audio-player` | `@base-ui/react@1.8.0` (MIT) |
| `level-meter`, `knob`, `fader` | `class-variance-authority@0.7.1` (Apache-2.0) |
| `waveform`, `spectrum` | none |

So a project on shadcn/Radix can take the visualisers with no new primitive library, and should know
that the faders bring Base UI with them. On a Base UI project (`stack.ui = "base-ui"`) the whole set
fits with nothing extra.

## Routing, and the question to ask before installing

A canvas loop painting 60 times a second is a battery and a cost question, not a visual one, so a
visualiser is subject to the same gating `vgpu-shaders` applies to a shader: what it costs on a
phone, what it does to battery, and the reduced-motion and `prefers-reduced-transparency` fallback
that must exist **before** the effect does. A static waveform image for a paused track is often the
right answer, and `smooth-waveform` on a 40-minute recording is not.

And the product question first: a `<audio controls>` element already plays sound. audiocn earns its
place when the *interface* is the audio — levels to read, gain to set, a waveform to scrub — not when
a file needs a play button.
