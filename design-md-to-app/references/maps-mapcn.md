# Maps (web) — mapcn

The **how**, doc-grounded ([mapcn.dev](https://mapcn.dev/docs), GitHub `AnmolSaini16/mapcn`, MIT, Vercel OSS). mapcn is the ecosystem-first default when a **web** project needs a map: ready-to-use, **MapLibre GL**-powered, Tailwind-styled, shadcn/ui-compatible components. `stack.maps = "mapcn"`. `[VERIFY]` commands/props against the site — it's young.

## ⚠️ Read first — basemap licensing (don't skip)

mapcn's **default tiles are [CARTO Basemaps](https://docs.carto.com/faqs/carto-basemaps)** (OpenStreetMap-based). Per mapcn's own README:
- **Commercial use requires a CARTO Enterprise license.**
- Non-commercial: free under CARTO's basemap terms.
- **For any commercial product, switch the tile source** to OpenStreetMap, [MapTiler](https://www.maptiler.com/), [Stadia Maps](https://stadiamaps.com/), or OpenFreeMap via the `styles` prop (any MapLibre-compatible style URL). Decide the tile provider **before shipping** — this is a licensing decision, flag it to the user.

## Install (shadcn registry)

```bash
npx shadcn@latest add https://mapcn.dev/r/map.json     # [VERIFY] exact registry URL (mapcn.dev vs mapcn.vercel.app/r/…)
```

Installs the component into `@/components/ui/map` and adds the dependency **`maplibre-gl`**. Add more pieces (markers, popups, routes, clusters, controls) the same way from their registry items. Same `shadcn add` mechanism as `coss-ui` / `heroicons-animated`.

## Basic usage

```tsx
"use client"; // maplibre-gl is a browser/WebGL library — client-only, never SSR'd
import { Map } from "@/components/ui/map";

export function LocationMap() {
  return (
    <div className="h-[420px] w-full">
      <Map center={[-74.006, 40.7128]} zoom={12} />   {/* center = [lng, lat] */}
    </div>
  );
}
```

Key props (`[VERIFY]` against docs): `center` `[lng, lat]`, `zoom`, `styles` (custom MapLibre style URL — this is where you set a commercial tile provider), `viewport` + `onViewportChange` (controlled mode), `blank` (transparent canvas for fully custom layers). **Theme-aware** — adapts to light/dark automatically.

## Components available

`Map`, `MapGeoJSON` (render GeoJSON layers), `MapArc` (great-circle arcs), plus **Markers**, **Popups** (with tooltips/labels), **Routes**/paths, **Clusters**, and **Controls** (zoom, compass, locate, fullscreen). Compose declaratively as children of `<Map>` — same philosophy as shadcn primitives.

## Next.js integration notes

- **Client-only**: put map components behind `"use client"`; if a Server Component must host it, load via `next/dynamic` with `{ ssr: false }`. maplibre-gl touches `window`/WebGL.
- **CSS**: ensure `maplibre-gl/dist/maplibre-gl.css` is imported once (the registry component usually handles it — `[VERIFY]`).
- **Sizing**: the map needs an explicit height on its container (`h-[420px]` etc.) or it renders 0px.
- **Tokens**: mapcn follows shadcn/Tailwind conventions, so it inherits DESIGN.md tokens for controls/popovers.

## Record in the contract

`meta.json#stack.maps = "mapcn"`. Only set when the product actually shows a map. Mobile counterpart: `mapcn-rn` (see `rn-components-apis/references/maps-mapcn-rn.md`).
