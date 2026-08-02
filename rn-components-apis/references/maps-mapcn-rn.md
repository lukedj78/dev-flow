# Maps (mobile) — mapcn-rn

The **how**, doc-grounded ([mapcn-rn.dev](https://mapcn-rn.dev/docs), MIT). mapcn-rn is the ecosystem-first default when an **Expo/React Native** project needs a map: ready-to-use map components built on **MapLibre React Native v11** *or* **Mapbox React Native**, styled with **NativeWind/Uniwind**. `stack.maps = "mapcn-rn"`. `[VERIFY]` commands/props against the site — it's young.

## ⚠️ Read first — native modules ⇒ a dev build, not Expo Go

mapcn-rn wraps native map SDKs (`@rnmapbox/maps` or MapLibre React Native), which are **native modules**. Therefore:
- It **cannot run in Expo Go**. You need a **development build** (`npx expo prebuild` + `eas build --profile development`, or a local `expo run:ios|android`), with the map SDK's **Expo config plugin** in `app.json`.
- **Free tiles, no API key** with the MapLibre default. If you pick **Mapbox**, you need a Mapbox access token (and accept Mapbox pricing).
- Decide **MapLibre vs Mapbox** up front — it changes the native dependency and the licensing/cost.

## Install / setup

```bash
npx mapcn-rn init            # one-time: config plugin, deps, styling wiring  [VERIFY]
npx mapcn-rn add <component> # add a specific map component
```

After `init`, rebuild the dev client (native deps changed): `npx expo prebuild && npx expo run:ios` (or `run:android`), or a new EAS dev build.

## Basic usage (shape — `[VERIFY]` exact imports/props against the docs)

```tsx
import { Map, Marker } from "@/components/ui/map"; // path per your NativeWind/components setup

export function LocationScreen() {
  return (
    <Map center={{ lng: -74.006, lat: 40.7128 }} zoom={12} className="flex-1">
      <Marker lng={-74.006} lat={40.7128} />
    </Map>
  );
}
```

## Components available

Map container + **Markers**, **Popups/Places**, **Routes** (turn-by-turn / delivery paths), **Layers** (analytics/heatmaps/data-viz), and **location controls** ("locate me", follow-user). The selling point is that you move from a static map to routes/nearby-places/live-location **without rebuilding the map foundation** — compose on one `<Map>`.

## dev-flow integration

- Owned on the mobile side: add a map via `rn-add-screen` (a screen with a map) using these components; this reference is the how-to.
- `meta.json#stack.maps = "mapcn-rn"`. Only set when the product shows a map.
- Because it needs a **dev build**, sequence it before an Expo-Go-only smoke test; it ships through the normal `rn-eas-deploy` flow. Web counterpart: `mapcn` (see `design-md-to-app/references/maps-mapcn.md`).
