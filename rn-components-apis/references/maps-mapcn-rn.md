# Maps (mobile) — mapcn-rn

The **how**, not just "use mapcn-rn". Grounded in the live v2 docs (`mapcn-rn.dev/docs/{getting-started,core,data,location,styling,cli,reference}/`) and the published config schema, fetched **2026-08-26** against **`mapcn-rn@2.0.0`**. `stack.maps = "mapcn-rn"`.

Copy-paste map components for **Expo/React Native**, on **MapLibre** or **Mapbox**, styled with **Uniwind/NativeWind**, sitting alongside React Native Reusables. You own the source once it lands.

> **v1 → v2.** If a project still has a single `components/ui/map.tsx` and **no `mapcn.json`**, it is on v1 — v2 replaced that one-file bundle with a tracked component graph and a renderer-independent public API. Run `npx mapcn-rn migrate`: it moves the old file to `components/ui/map.v1.tsx.bak` (never deletes it), infers renderer + provider from the file's own imports, and installs the v2 equivalents. If `mapcn.json` already exists it refuses and points at `doctor`. Full walkthrough: <https://mapcn-rn.dev/docs/getting-started/upgrade-to-v2>.

> ⚠️ **Different project from the web `mapcn`.** Different author (`aikenahac` vs `AnmolSaini16`), different repo, deliberately similar API but **not** a port. v2 closed most of the gaps the v1 notes listed — clustering, GeoJSON, standalone popups and controlled viewports all exist now — but still check the components index before assuming a web component has a mobile twin.

## ⚠️ Read first — native modules ⇒ a dev build, not Expo Go

Both renderers carry native code. **Expo Go is not supported.** Use an Expo development build, run `prebuild` after changing the renderer or its Expo plugin, and rebuild the native client. Bare React Native "may work" — the CLI reports it as **unverified**.

## The two axes: renderer and provider

v2's central idea, and the thing that makes the config make sense: **the native SDK that draws the map and the source of the basemap style are separate decisions.**

**Axis 1 — renderer** (the native SDK; implements camera, sources, layers, markers, location puck):

| Renderer | Native package | Expo plugin |
|---|---|---|
| MapLibre | `@maplibre/maplibre-react-native@^11.3.6` | `@maplibre/maplibre-react-native` |
| Mapbox | `@rnmapbox/maps@^10.3.5` | `@rnmapbox/maps` |

⚠️ **The two renderer packages and plugins cannot coexist in one app.** Switch with `mapcn-rn provider <target>`, then prebuild and rebuild. `doctor` has a dedicated error-level check for "both present".

**Axis 2 — basemap provider** (named styles + credentials; constrained to a compatible renderer):

| Provider | Renderer | Key |
|---|---|---|
| **CARTO** | MapLibre | none |
| **MapTiler** | MapLibre | `EXPO_PUBLIC_MAPTILER_API_KEY` |
| **Custom** | MapLibre | none — your own style identifiers, no built-in styles |
| **Mapbox** | Mapbox | `EXPO_PUBLIC_MAPBOX_TOKEN`, **plus `MAPBOX_DOWNLOADS_TOKEN` at build time** |

The `provider` prop can override the configured provider **at runtime**, but it does **not** swap the native renderer — only pick providers compatible with what is installed.

⚠️ **Licensing is still the decision that outlives the code.** CARTO is the default and needs no key; MapTiler and Mapbox do. `[VERIFY]` the current free-tier terms with each provider before shipping commercially — this file deliberately restates no quota numbers, because pricing is the most perishable thing a reference can carry and it fails as a bill, not as an error.

## Install — one command

```bash
npx mapcn-rn init [--renderer maplibre|mapbox] [--provider maptiler|carto|custom|mapbox] [--all] [--components a,b] [--yes]
```

Run from the Expo project root. It is the entrypoint — configure **and** install in one pass. What it does, per the CLI docs:

- Detects the project (Expo vs bare RN, `src` layout) and warns if `expo` isn't a dependency.
- Prompts for renderer, then a compatible provider (**skipped for Mapbox**, which has no separate provider prompt).
- Detects the package manager (lockfile), the styling system (**Uniwind / NativeWind / none**) and path aliases (`components.json` if present, else mapcn's defaults).
- Asks which components: **Minimal** (`map`, `marker`, `popup`, `controls`), **Everything**, or a grouped checklist.
- Writes **`mapcn.json` (schema version 2)**, installs the renderer package, adds its Expo config plugin to `app.json` if readable, scaffolds the provider's public env key into `.env.example`.
- Installs the chosen components and their transitive dependencies, their native permissions, and the generated `components/ui/mapcn/index.ts` barrel.

## `mapcn.json` — the CLI's source of truth

```jsonc
{
  "$schema": "https://mapcn-rn.dev/schema/mapcn.json",
  "schemaVersion": 2,
  "renderer": "maplibre",                                     // "maplibre" | "mapbox"
  "provider": { "id": "maptiler", "envKey": "EXPO_PUBLIC_MAPTILER_API_KEY" },
  "styling": "uniwind",                                       // "uniwind" | "nativewind" | "none"
  "aliases": { "ui": "@/components/ui", "lib": "@/lib", "hooks": "@/hooks", "components": "@/components" },
  "components": { "core": { "version": "…", "files": [{ "path": "lib/mapcn/types.ts", "hash": "…" }] } }
}
```

Two things follow from the `hash` field: **the CLI knows whether you edited an installed file**, and **you must not hand-edit those hashes**. The current CLI supports schema version 2 and **rejects configs written by a newer schema** — so a teammate on a newer CLI can lock you out until you upgrade, which is a feature, not a bug.

## Adding components later

```bash
npx mapcn-rn add <component…> [--overwrite] [--yes] [--renderer maplibre|mapbox]
npx mapcn-rn add --all
npx mapcn-rn list        # the registry set, against your project's installed state
```

`add` reads `mapcn.json` (and runs `init` first if there is none), resolves `registryDependencies` transitively and topologically, and prints the resolved set before writing anything.

⚠️ **This is the part that makes "you own the file" safe.** Per file:

| State | What happens |
|---|---|
| New | written directly |
| Unmodified since install | upgraded silently if the registry version differs |
| **Locally modified** (or an untracked file already at that path) | **never overwritten** — the new version goes to a `<name>.new.tsx` sidecar and the CLI prints a diff command |
| …with `--overwrite` | original snapshotted to `.mapcn-backup/<timestamp>/` first, then replaced |

So an upgrade cannot silently eat your edits, which was the standing hazard of the v1 copy-once model.

## `doctor` — run it before debugging anything

```bash
npx mapcn-rn doctor [--json] [--verbose]
```

Non-mutating, **14 independent checks** (a failure never skips the rest), levelled `ok`/`warn`/`error`/`info`, **exit 1 if anything is error-level** — so it is CI-usable, and `--json` makes it scriptable. It covers exactly the things that go wrong here: renderer package installed and matching the config, **both renderer packages present**, Expo plugin present and matching, `MAPBOX_DOWNLOADS_TOKEN` (Mapbox only), the provider's required env key (skipped for CARTO), iOS/Android location permissions (only when `location`/`location-puck` is installed), and a legacy-v1 detection.

## The component set

17 components, from the reference index. **`map`, `marker` and `location-puck` are per-renderer** (two implementations behind one shared prop-type file); everything else is a single shared source.

| Category | Components |
|---|---|
| **core** | `core` · `map` · `marker` · `popup` · `controls` |
| **data** | `route` · `geojson` · `circle` · `polygon` · `cluster` · `heatmap` · `choropleth` · `legend` |
| **location** | `location` · `location-puck` |
| **styling** | `style-switcher` |

Import everything from the generated barrel:

```tsx
import { Map, useMap } from "@/components/ui/mapcn";
```

### `<Map>` — the container

Its props are **identical on both renderers** (one shared `map-types.ts`), so there is no drift to design around. The ones that matter:

- **Camera**: `viewport` (controlled) vs `defaultViewport` (uncontrolled, `{ center: [0,0], zoom: 2, bearing: 0, pitch: 0 }`), `bounds` + `padding`, `minZoom`/`maxZoom`, `maxBounds`.
- **Events**: `onViewportChange(viewport, { userInteraction })` fires continuously while moving, throttled by `viewportChangeThrottle` (default **100 ms**); `onViewportChangeEnd` fires once it settles. Also `onPress`/`onLongPress` (`MapFeaturePressEvent` — coordinate, screen point, features under it), `onLoad`, `onError`.
- **Style**: `style` takes a named provider style id, an explicit URL/spec, **or a `{ light, dark }` pair**; `colorScheme` overrides what `useColorScheme()` resolved.
- **Gestures**: `interactive` as a master toggle, `gestures={{ pan, zoom, rotate, pitch }}` individually.
- **Chrome**: `compass` / `logo` / `attribution` / `scaleBar`, each `boolean | { position }`.
- **Styling**: `className` (Uniwind/NativeWind) merged with `containerStyle`; `loader` renders until `onLoad`, `false` hides it.
- **Escape hatches**: `maplibre` / `mapbox` props, `Record<string, unknown>`, loosely typed on purpose.

`useMap()` returns the same `MapInstance` on both renderers and **throws outside a `<Map>` subtree**: `renderer`, `isLoaded`, `getViewport()`, `setViewport()`, `flyTo()`, `moveTo()`, `zoomTo()`, `zoomBy()`, `fitBounds()`, `fitFeatures()`, `resetNorth()`.

## Renderer capability gaps — documented, not silent

The compatibility matrix is built from the `CAPABILITIES` constants each renderer adapter actually exports, not from intentions. The gaps worth knowing:

| Capability | MapLibre 11 | Mapbox 10 | Handling |
|---|---|---|---|
| `clusterMinPoints` | ✓ | ✗ | accepted on both prop types, **ignored on Mapbox** — a documented gap, not a silent drop |
| Location puck: pulsing / scale / custom images | ✗ | ✓ | Mapbox-only props; **`__DEV__` warning** if passed on MapLibre |
| Location puck: `onPress`, custom children | ✓ | ✗ | MapLibre-only; same warning the other way |
| Cluster ref methods, GeoJSON + native clustering | ✓ | ✓ | full parity |
| Unified layer style keys & expressions | ✓ | ✓ | shared verbatim, no translation layer |
| Native feature state, `querySourceFeatures` | ✗ | ✓ | unused by mapcn — selection everywhere uses filter expressions, which both support |

**Choose the renderer on this table, not on brand preference** — and note the two location-puck rows point in opposite directions.

## Styling

Uniwind/NativeWind is the expected integration (`styling` in `mapcn.json` records which, and `"none"` is a valid value). Components take `className`.

## dev-flow integration

- Owned on the mobile side: add a map screen via `rn-add-screen` using these components; this reference is the how-to.
- `meta.json#stack.maps = "mapcn-rn"`. **Also record the renderer and the provider** — they are a licensing + native-dependency decision, and they cannot both change cheaply.
- Because it needs a **dev build**, sequence it *before* any Expo-Go-only smoke test; it ships through the normal `rn-eas-deploy` flow. Web counterpart: `mapcn` (see `design-md-to-app/references/maps-mapcn.md`).

## Sources

- Getting started: <https://mapcn-rn.dev/docs> · <https://mapcn-rn.dev/docs/getting-started/installation> · <https://mapcn-rn.dev/docs/getting-started/renderers-and-providers> · <https://mapcn-rn.dev/docs/getting-started/configuration> · <https://mapcn-rn.dev/docs/getting-started/theming> · <https://mapcn-rn.dev/docs/getting-started/upgrade-to-v2>
- CLI: <https://mapcn-rn.dev/docs/cli/init> · <https://mapcn-rn.dev/docs/cli/add> · <https://mapcn-rn.dev/docs/cli/doctor> · <https://mapcn-rn.dev/docs/cli/migrate>
- Components: <https://mapcn-rn.dev/docs/core/map> · <https://mapcn-rn.dev/docs/core/markers> · <https://mapcn-rn.dev/docs/core/popups> · <https://mapcn-rn.dev/docs/core/controls> · <https://mapcn-rn.dev/docs/data/routes> · <https://mapcn-rn.dev/docs/data/clustering> · <https://mapcn-rn.dev/docs/data/geojson> · <https://mapcn-rn.dev/docs/location/location-puck> · <https://mapcn-rn.dev/docs/styling/style-switcher>
- Reference: <https://mapcn-rn.dev/docs/reference/components-index> · <https://mapcn-rn.dev/docs/reference/renderer-compatibility-matrix>
- npm: <https://www.npmjs.com/package/mapcn-rn>

`[VERIFY]` on the next minor — this project shipped a full API redesign between v1 and v2, and **the file you own is the API**: once `add` has written it, your repo is the source of truth, and `mapcn.json`'s hashes are what tell the CLI whether it may touch it again.
