# Maps (web) — mapcn

The **how**, not just "use mapcn". Doc-grounded against [mapcn.dev/docs](https://mapcn.dev/docs) + the published registry item `https://mapcn.dev/r/map.json` (read directly — it is the source of truth for props) and GitHub `AnmolSaini16/mapcn` (MIT). mapcn is the ecosystem-first default when a **web** project needs a map: **MapLibre GL**-powered, Tailwind-styled, shadcn/ui-compatible components you copy into your repo. `stack.maps = "mapcn"`. `[VERIFY]` identifiers after each re-install — it's young and the registry file is the version you actually own.

## ⚠️ Read first — basemap licensing (don't skip)

mapcn's **default tiles are [CARTO Basemaps](https://docs.carto.com/faqs/carto-basemaps)** (OpenStreetMap data). Verified in the repo README and in the installed source (`defaultStyles` = `basemaps.cartocdn.com/gl/positron-gl-style/style.json` for light, `dark-matter-gl-style` for dark):
- **Commercial use requires a CARTO Enterprise license.**
- Non-commercial: free for CARTO grantees under their [basemap terms](https://carto.com/legal/bmap).
- **For any commercial product, switch the tile source** via the `styles` prop (see below). Decide the tile provider **before shipping** — it's a licensing decision, flag it to the user.

The docs site itself never mentions this; only the README does. Don't let "zero config, no API keys needed" on the landing page fool you.

## Install

Prerequisite: a project with **Tailwind CSS + shadcn/ui** already set up.

```bash
pnpm dlx shadcn@latest add @mapcn/map     # npm/yarn/bun equivalents also documented
```

One item installs **everything** — `@mapcn/map` is not per-component. It writes a single file to `components/ui/map.tsx`, adds deps `maplibre-gl` + `lucide-react` (+ `@types/geojson` as devDep), and injects a `@layer base` CSS block that restyles `.maplibregl-popup-content`, `.maplibregl-popup-tip` and `.maplibregl-ctrl-attrib` to shadcn tokens. There is **no** separate `add markers` / `add clusters` step.

`[VERIFY]` whether the `@mapcn` namespace resolves without a `registries` entry in your `components.json`. If the CLI rejects it, the direct URL works and returns the same item: `pnpm dlx shadcn@latest add https://mapcn.dev/r/map.json`.

Prebuilt **blocks** (full compositions, installed the same way): `@mapcn/store-locator`, `@mapcn/delivery-tracker`, `@mapcn/logistics-network`, `@mapcn/uptime-monitor`, `@mapcn/heatmap`, `@mapcn/choropleth`, `@mapcn/analytics-map`, `@mapcn/analytics-card`.

## The component set

Everything is exported from `@/components/ui/map`:

```
<Map>                              // root, owns the MapLibre instance
  <MapMarker longitude latitude>   // DOM marker
    <MarkerContent>                // the visual (defaults to a blue dot)
      <MarkerLabel />              // text above/below
    </MarkerContent>
    <MarkerPopup />                // opens on click
    <MarkerTooltip />              // opens on hover
  </MapMarker>
  <MapPopup longitude latitude />  // standalone popup, no marker
  <MapControls />                  // zoom / compass / locate / fullscreen
  <MapRoute coordinates={…} />     // polyline
  <MapArc data={…} />              // curved great-circle-ish arcs
  <MapGeoJSON data={…} />          // fill + outline layers
  <MapClusterLayer data={…} />     // native MapLibre clustering
</Map>
```

Plus the `useMap()` hook and the types `MapRef`, `MapViewport`, `MapStyleOption`, `MapArcDatum`, `MapArcEvent`, `MapGeoJSONData`, `MapGeoJSONEvent`, and a `*Props` type per component.

## `Map` — props

| Prop | Type | Default | Notes |
|---|---|---|---|
| `className` | `string` | — | merged onto a `relative h-full w-full` container |
| `theme` | `"light" \| "dark"` | auto | see theme-awareness below |
| `styles` | `{ light?: string \| StyleSpecification; dark?: string \| StyleSpecification }` | CARTO | **the licensing escape hatch** |
| `blank` | `boolean` | `false` | transparent, tile-less canvas — ignored when `styles` is given |
| `projection` | `ProjectionSpecification` | — | `{ type: "globe" }` for the 3D globe |
| `viewport` | `Partial<MapViewport>` | — | controlled mode (with `onViewportChange`) |
| `onViewportChange` | `(v: MapViewport) => void` | — | fires **continuously** during pan/zoom/rotate/pitch |
| `loading` | `boolean` | `false` | shows the built-in dot loader overlay |

`MapViewport = { center: [number, number]; zoom: number; bearing: number; pitch: number }`.

`MapProps` also spreads **`Omit<maplibregl.MapOptions, "container" | "style">`** — so `center`, `zoom`, `minZoom`, `maxZoom`, `bounds`, `maxBounds`, `interactive`, `bearing`, `pitch`, `fadeDuration`, `attributionControl` etc. are MapLibre's own options, documented at [maplibre.org](https://maplibre.org/maplibre-gl-js/docs/API/type-aliases/MapOptions/) — **not** mapcn props. `center` is `[lng, lat]`, always.

```tsx
import { Map } from "@/components/ui/map";

export function LocationMap() {
  return (
    <div className="h-[420px] w-full">        {/* the container MUST have a height */}
      <Map center={[-74.006, 40.7128]} zoom={12} />
    </div>
  );
}
```

## Changing the tile provider (the CARTO fix)

`styles` takes a MapLibre style URL **or** an inline `StyleSpecification`, per theme:

```tsx
// OpenFreeMap — free, no API key, no CARTO licence. URLs used by mapcn's own docs.
<Map
  center={[-0.1276, 51.5074]}
  zoom={13}
  styles={{ light: "https://tiles.openfreemap.org/styles/bright",
            dark:  "https://tiles.openfreemap.org/styles/liberty" }}
/>

// MapTiler — commercial tier, key in the URL. [VERIFY] the style slug you buy.
<Map styles={{ light: `https://api.maptiler.com/maps/streets-v2/style.json?key=${process.env.NEXT_PUBLIC_MAPTILER_KEY}`,
               dark:  `https://api.maptiler.com/maps/dataviz-dark/style.json?key=${process.env.NEXT_PUBLIC_MAPTILER_KEY}` }} />
```

The docs also name **Stadia Maps** and **Thunderforest** as MapLibre-compatible; any style-spec-v8 URL works. If both `light` and `dark` should be the same style, pass the same URL twice (that's what the docs' style-picker demo does). Third option: `<Map blank>` — a tile-less transparent canvas for choropleths/arcs/dot maps where you draw every layer yourself, which sidesteps tile licensing entirely.

## Controlled vs uncontrolled viewport

Uncontrolled (default): pass `center`/`zoom` once; the user drives the map. Controlled: pass **both** `viewport` and `onViewportChange`.

```tsx
"use client";
import { useState } from "react";
import { Map, type MapViewport } from "@/components/ui/map";

export function ControlledMap() {
  const [viewport, setViewport] = useState<MapViewport>({
    center: [-74.006, 40.7128], zoom: 8, bearing: 0, pitch: 0,
  });
  return (
    <div className="relative h-[420px] w-full">
      <Map viewport={viewport} onViewportChange={setViewport} />
    </div>
  );
}
```

`onViewportChange` alone (no `viewport`) is the read-only observer form — use it to mirror zoom/bearing into a HUD without giving up uncontrolled behaviour.

## Markers, labels, tooltips, popups

```tsx
import { Map, MapMarker, MarkerContent, MarkerLabel, MarkerPopup, MarkerTooltip } from "@/components/ui/map";

<Map center={[-73.98, 40.76]} zoom={12}>
  {locations.map((l) => (
    <MapMarker key={l.id} longitude={l.lng} latitude={l.lat}>
      <MarkerContent>
        <div className="bg-primary size-4 rounded-full border-2 border-white shadow-lg" />
        <MarkerLabel position="bottom">{l.label}</MarkerLabel>
      </MarkerContent>
      <MarkerTooltip>{l.name}</MarkerTooltip>          {/* hover */}
      <MarkerPopup className="w-62 p-0">…</MarkerPopup> {/* click */}
    </MapMarker>
  ))}
</Map>
```

- `MapMarker` events: `onClick`, `onMouseEnter`, `onMouseLeave`, and `onDragStart` / `onDrag` / `onDragEnd` (each gets `{ lng, lat }`; requires `draggable` — a MapLibre `MarkerOptions` field, since `MapMarker` spreads `Omit<MarkerOptions, "element">`).
- `MarkerLabel` `position`: `"top"` (default) | `"bottom"`. Must live inside `MarkerContent`.
- `MarkerPopup` / `MarkerTooltip` spread MapLibre `PopupOptions` (`offset`, `anchor`, `maxWidth`, `closeOnClick`, `focusAfterOpen`…); `closeButton` defaults to `false`.
- ⚠️ **`MapMarker` is DOM-based** — the docs cap it at "a few hundred". Beyond that use `MapGeoJSON` / `MapClusterLayer` (WebGL canvas).

Standalone popup, controlled from React state:

```tsx
{showPopup && (
  <MapPopup longitude={-74.006} latitude={40.7128}
            onClose={() => setShowPopup(false)}
            closeButton closeOnClick={false} focusAfterOpen={false}>
    …
  </MapPopup>
)}
```

## Controls

```tsx
<Map center={[2.3522, 48.8566]} zoom={10}>
  <MapControls position="top-right" showZoom showCompass showLocate showFullscreen />
</Map>
```

`position` defaults to `"bottom-right"`. **Only `showZoom` defaults to `true`** — `showCompass`, `showLocate`, `showFullscreen` are all `false` and must be opted into. `onLocate?: (coords: { longitude, latitude }) => void` fires with the user's position.

## Data layers

```tsx
// Polyline. interactive defaults to FALSE — set it to get onClick/onMouseEnter.
<MapRoute coordinates={route} color="#3b82f6" width={4} opacity={0.8} dashArray={[2, 2]} />

// Arcs. interactive defaults to TRUE here. data: MapArcDatum[] = { id, from: [lng,lat], to: [lng,lat] }
<MapArc<Lane>
  data={lanes}
  curvature={0.2} samples={64}
  paint={{ "line-color": modeColorExpression, "line-width": 1.5 }}
  hoverPaint={{ "line-width": 3, "line-opacity": 1 }}
  onHover={(e) => setSelected(e ? e.arc : null)}   // e is null on leave
/>

// GeoJSON: FeatureCollection | Feature | Geometry | URL string. Pass false to drop a layer.
<MapGeoJSON data={area}
  fillPaint={{ "fill-color": "#3b82f6", "fill-opacity": 0.25 }}
  linePaint={{ "line-color": "#2563eb", "line-width": 2 }}
  promoteId="iso3"                                  // REQUIRED for fillHoverPaint
  fillHoverPaint={{ "fill-opacity": 0.5 }} />

// Clustering (native MapLibre). Omit onClusterClick and clicking a cluster just zooms in.
<MapClusterLayer<EarthquakeProperties>
  data="https://…/earthquakes.geojson"
  clusterRadius={50} clusterMaxZoom={14}
  clusterColors={["#3b82f6", "#1d4ed8", "#1e3a8a"]} clusterThresholds={[100, 750]}
  onPointClick={(feature, coordinates) => setSelected({ feature, coordinates })} />
```

`paint` / `layout` / `fillPaint` / `linePaint` take raw MapLibre layer specs, **including expressions** (`["match", ["get","mode"], …]`), so styling is data-driven without extra API. `beforeId` controls layer ordering.

## Escape hatches — the raw MapLibre instance

```tsx
const mapRef = useRef<MapRef>(null);                  // MapRef = maplibregl.Map
mapRef.current?.flyTo({ center: [-74, 40.7], zoom: 12 });

// inside a child of <Map>:
const { map, isLoaded } = useMap();
useEffect(() => {
  if (!map || !isLoaded) return;
  map.on("click", handleClick);
  return () => map.off("click", handleClick);
}, [map, isLoaded]);
```

There is **no `onClick` / `onLoad` prop on `<Map>`** — map-level events go through `map.on(...)` via `useMap()` or the ref. (The installed context actually also exposes `isStyleLoaded` and `resolvedTheme`; the published API reference only documents `map` + `isLoaded` — `[VERIFY]` before relying on the extras.)

## Next.js App Router specifics

- **`"use client"` is already in the installed file.** You can import `<Map>` from a Server Component and it becomes a client boundary automatically. You still need `"use client"` in *your* wrapper when it holds state or passes callbacks (`onViewportChange`, `onPointClick`, …) — functions can't cross the server→client boundary.
- **`next/dynamic` is usually unnecessary.** MapLibre is instantiated in an effect against a ref'd `<div>`, so SSR just renders an empty container. Only reach for `dynamic(..., { ssr: false })` if you hit a hydration issue — and note `ssr: false` is rejected inside Server Components in Next 15+, so the dynamic import must live in a Client Component. `[VERIFY]` against Next 16.
- **CSS**: nothing to import. `maplibre-gl/dist/maplibre-gl.css` is imported *inside* `components/ui/map.tsx`, and the shadcn-token overrides ship as the registry item's `css` block into your global stylesheet.
- **Sizing**: the root renders `relative h-full w-full` — a parent with an explicit height (`h-[420px]`, a `flex-1` cell, a `<Card className="h-[320px] p-0 overflow-hidden">`) is mandatory or you get a 0px map.
- **Theme**: auto-detected, in this order — `documentElement.classList` `dark`/`light`, then `documentElement.dataset.theme`, then `matchMedia("(prefers-color-scheme: dark)")`. That covers `next-themes` with both `attribute="class"` (default) and `attribute="data-theme"` with no wiring. Pass `theme="dark"` only to force it.
- **Tokens**: controls/popups are plain Tailwind + shadcn CSS variables, so DESIGN.md tokens apply for free.

## Record in the contract

`meta.json#stack.maps = "mapcn"`. Only set when the product actually shows a map. Mobile counterpart: `mapcn-rn` (see `rn-components-apis/references/maps-mapcn-rn.md`) — the two are **different projects by different authors** with a deliberately similar API, not one library.

## Sources

- Intro: <https://mapcn.dev/docs> · Installation: <https://mapcn.dev/docs/installation> · API reference: <https://mapcn.dev/docs/api-reference>
- Map: <https://mapcn.dev/docs/basic-map> · Controls: <https://mapcn.dev/docs/controls> · Markers: <https://mapcn.dev/docs/markers> · Popups: <https://mapcn.dev/docs/popups>
- Routes: <https://mapcn.dev/docs/routes> · Arcs: <https://mapcn.dev/docs/arcs> · GeoJSON: <https://mapcn.dev/docs/geojson> · Clusters: <https://mapcn.dev/docs/clusters> · Advanced: <https://mapcn.dev/docs/advanced-usage>
- Blocks: <https://mapcn.dev/blocks> · LLM digest: <https://mapcn.dev/llms.txt> · Installed source of truth: <https://mapcn.dev/r/map.json> · README/licensing: <https://github.com/AnmolSaini16/mapcn>
