# Maps (mobile) — mapcn-rn

The **how**, not just "use mapcn-rn". Doc-grounded against [mapcn-rn.dev/docs](https://mapcn-rn.dev/docs), the published registry items (`https://mapcn-rn.dev/maps/map.json` and siblings — read them, they contain the full component source) and the `mapcn-rn` CLI (npm, v0.1.1). mapcn-rn is the ecosystem-first default when an **Expo/React Native** project needs a map: copy-paste map components on **MapLibre React Native v11** *or* **Mapbox React Native**, styled with **NativeWind/Uniwind**, sitting alongside **React Native Reusables** (shadcn/ui for RN). `stack.maps = "mapcn-rn"`. `[VERIFY]` after each install — the file you own *is* the API.

> ⚠️ **Different project from the web `mapcn`.** Different author (`aikenahac` vs `AnmolSaini16`), different repo, deliberately similar API but **not** a port. Do not assume a web component exists on mobile — several don't (see "What's missing vs web").

## ⚠️ Read first — native modules ⇒ a dev build, not Expo Go

MapLibre React Native and `@rnmapbox/maps` are **native modules**. The docs are explicit: they *"will not work with Expo Go"*.

- You need a **development build**: `npx expo run:ios` / `npx expo run:android` (or an `eas build --profile development` dev client).
- **Rebuild whenever a native dep changes** — i.e. after the first `mapcn-rn add`, and again if you ever switch provider (MapLibre ⇄ Mapbox swaps the native SDK).
- Choose **MapLibre vs Mapbox up front**: it changes the native dependency, the Expo config plugin, and the licensing/cost.

## ⚠️ Read first — basemap licensing

Default tiles are **CARTO Basemaps** (`basemaps.cartocdn.com/gl/positron-gl-style` light / `dark-matter-gl-style` dark), verified in the installed source. The docs state they are **free for NON-COMMERCIAL use only**. For a commercial product pick a provider at install time:

| Provider | Flag | Native dep | Key | Free tier (per docs) |
|---|---|---|---|---|
| CARTO (default) | *(none)* | `@maplibre/maplibre-react-native@11.2.1` | none | non-commercial only |
| MapTiler | `--provider=maptiler` | `@maplibre/maplibre-react-native@11.2.1` | `EXPO_PUBLIC_MAPTILER_API_KEY` | 100,000 requests/month |
| Mapbox | `--provider=mapbox` | `@rnmapbox/maps@^10.2.10` | `EXPO_PUBLIC_MAPBOX_API_KEY=pk...` | 25,000 monthly active users |

All three also install `expo-location@^19.0.8`. The "no API keys required" line on the landing page is true **only** for the CARTO default — which is the one you can't ship commercially.

## Install

There is **no `mapcn-rn init`**. The whole CLI surface is:

```bash
npx mapcn-rn add                       # interactive provider picker (carto | maptiler | mapbox)
npx mapcn-rn add --provider=carto
npx mapcn-rn add --provider=maptiler
npx mapcn-rn add --provider=mapbox
npx mapcn-rn --help                    # or -h
```

It is a thin wrapper: it resolves a registry URL and shells out to
`npx @react-native-reusables/cli@latest add https://mapcn-rn.dev/maps/map{,-maptiler,-mapbox}.json`.
That writes **one file — `components/ui/map.tsx`** — and installs the deps above. Nothing else. (You can run the underlying RNR command directly if you prefer.)

⚠️ **Undocumented prerequisite, verified in the source**: the installed file imports `useTheme` from `@/lib/theme-context` (expects `{ colorScheme }`) and `cn` from `@/lib/utils`. If your project doesn't already have those (React Native Reusables / NativeWind conventions), the file won't compile until you provide them. `[VERIFY]` whether your RNR template ships `lib/theme-context`.

Then, for MapTiler/Mapbox, add the key to `.env`:

```bash
EXPO_PUBLIC_MAPTILER_API_KEY=your_maptiler_api_key_here   # cloud.maptiler.com/account/keys
EXPO_PUBLIC_MAPBOX_API_KEY=pk...                          # console.mapbox.com/account/access-tokens
```

The MapTiler build reads the key at render time and **silently falls back to the CARTO basemaps with a `console.warn`** if it's absent — so a missing key looks like "it works", and you ship the non-commercial tiles. The Mapbox build calls `Mapbox.setAccessToken()` at module load and warns if unset.

## Expo config (`app.json`)

```jsonc
{
  "expo": {
    "ios": {
      "infoPlist": {
        "ITSAppUsesNonExemptEncryption": false,
        "NSAppTransportSecurity": { "NSAllowsArbitraryLoads": true },
        "NSLocationWhenInUseUsageDescription": "This app needs access to your location to show you on the map.",
        "NSLocationAlwaysAndWhenInUseUsageDescription": "This app needs access to your location to show you on the map."
      }
    },
    "android": { "permissions": ["ACCESS_FINE_LOCATION", "ACCESS_COARSE_LOCATION"] },
    "plugins": [
      // shows a "no valid plugin" warning but the docs say it IS required
      "@maplibre/maplibre-react-native"
      // "@rnmapbox/maps" instead, if using the mapbox version
    ]
  }
}
```

⚠️ **Never list both `@maplibre/maplibre-react-native` and `@rnmapbox/maps` under `plugins`** — the docs state it throws. Bare RN instead of Expo: add `NSLocationWhenInUseUsageDescription` to `ios/YourApp/Info.plist` and the two `<uses-permission>` lines to `AndroidManifest.xml`.

## The dev-build workflow, concretely

```bash
npx mapcn-rn add --provider=maptiler   # 1. adds native deps
# 2. edit app.json (plugins + permissions) as above
npx expo prebuild                      # 3. only if you keep native dirs / bare workflow
npx expo run:ios                       # 4. compile + install the dev build   [or run:android]
# EAS alternative for step 4:
eas build --profile development --platform ios
```

Rebuild (steps 3–4) after: the first install, a provider switch, any `app.json` plugin/permission change. A pure JS edit to `components/ui/map.tsx` only needs a Metro reload.

## Components + props (verified against the installed source)

Exported from `@/components/ui/map`: `Map`, `MapControls`, `MapMarker`, `MarkerContent`, `MarkerLabel`, `MarkerPopup`, `MapRoute`, `MapUserLocation`, `useMap`, plus `useCurrentPosition` and `LocationManager` re-exported from MapLibre — **the Mapbox variant exports neither of those two.**

**`Map`** — `children`, `styles?: { light?, dark? }`, `center = [0, 0]` (`[lng, lat]`), `zoom = 10`, `className`, `showLoader = true`. Renders a `flex-1 relative` `<View>`; the internal `<Camera>` uses `easing="fly"`, `duration={1000}`. Theme comes from `useTheme().colorScheme` — light/dark tiles switch automatically. Note there is **no `viewport`/`onViewportChange`** here (that's web-only); move the camera via `useMap()`.

```tsx
import { Map } from "@/components/ui/map";
import { View } from "react-native";

export default function BasicMapExample() {
  return (
    <View className="h-[500px] rounded-xl overflow-hidden border border-border">
      <Map zoom={12} center={[-122.4194, 37.7749]} />
    </View>
  );
}
```

**`MapMarker`** — position as **either** `coordinate={[lng, lat]}` **or** `longitude` + `latitude` (a TS union: pass one form, not both). Plus `label?: string` (shorthand for a `MarkerLabel`), `anchor = { x: 0.5, y: 0.5 }`, `allowOverlap = false`, `onPress`. ⚠️ `allowOverlap` is destructured and **never used** in the installed source — treat it as a no-op. Docs cap `MapMarker` at "hundreds"; past ~1000 use GeoJSON layers.

**`MarkerContent`** (`children`, `className`; defaults to a blue dot) · **`MarkerLabel`** (`children`, `className`, `classNameText`, `position: "top" | "bottom"` = `"top"`) · **`MarkerPopup`** (`children`, `className`, `title` — renders a native MapLibre `Callout`, opens on press).

```tsx
import { Map, MapMarker, MarkerContent, MarkerLabel, MarkerPopup } from "@/components/ui/map";
import { Text, View } from "react-native";

<Map center={[-73.98, 40.76]} zoom={12} className="flex-1">
  <MapMarker coordinate={[-73.9857, 40.7484]} onPress={() => {}}>
    <MarkerContent className="rounded-full">
      <View className="size-4 rounded-full border-2 border-white bg-blue-500" />
      <MarkerLabel position="bottom" classNameText="text-foreground">Empire State</MarkerLabel>
    </MarkerContent>
    <MarkerPopup title="Empire State Building">
      <Text className="text-muted-foreground text-xs">350 5th Ave</Text>
    </MarkerPopup>
  </MapMarker>
</Map>
```

**`MapControls`** — `position = "bottom-right"` (`"top-left" | "top-right" | "bottom-left" | "bottom-right"`), `showZoom = true`, `showLocate = false`, `className`, `onLocate?: (coords: { longitude, latitude }) => void`. ⚠️ **No `showCompass` / `showFullscreen`** — those exist only on the web version. `showLocate` needs the permissions above.

**`MapRoute`** — `coordinates: Array<[number, number]>`, `color = "#4285F4"`, `width = 3`, `opacity = 0.8`, `dashArray?: [number, number]`. Drawn as a native MapLibre line layer.

**`MapUserLocation`** — `visible = true`, `showAccuracy = true`, `showHeading = false`, `animated = true`, `minDisplacement?`, `onPress?`, `autoRequestPermission = true` (handles the permission prompt for you).

```tsx
<Map center={[0, 0]} zoom={12}>
  <MapUserLocation visible showAccuracy autoRequestPermission />
  <MapControls showZoom showLocate />
</Map>
```

**`useMap()`** → `{ mapRef, cameraRef, isLoaded, theme }`. `cameraRef.current.easeTo({ center, zoom, duration })` / `.flyTo(...)` is how you drive the camera; `mapRef.current` is the raw MapLibre `MapView` for anything the wrapper doesn't expose.

```tsx
function FitToUser() {
  const { mapRef, cameraRef, isLoaded } = useMap();
  useEffect(() => {
    if (!mapRef.current || !isLoaded) return;
    mapRef.current.getCenter().then((center) => console.log("center", center));
  }, [mapRef, isLoaded]);
  return null;
}
```

## What's missing vs web (don't assume parity)

- **No standalone `MapPopup`** — every popup must hang off a `MapMarker` via `MarkerPopup`.
- **No `MapClusterLayer`, `MapGeoJSON`, `MapArc` wrappers.** For clustering / heatmaps / thousands of points, use MapLibre's own `GeoJSONSource` + `Layer` (`cluster`, `clusterRadius={50}`, `filter={["has","point_count"]}` vs `filter={["!",["has","point_count"]]}`, `getClusterExpansionZoom()`), `CircleLayer`, `SymbolLayer` — imported from `@maplibre/maplibre-react-native`, not from mapcn. The docs' Clusters page says this explicitly.
- **No controlled viewport props.** Camera control is imperative via `useMap()`.

## Styling

NativeWind/Uniwind is a hard requirement — every component takes `className` and the source uses `cn()`. The docs state the component code is identical for both styling libraries. Labels/popups use theme tokens (`text-foreground`, `border-border`), so DESIGN.md tokens flow through for free.

## ⚠️ Gotcha — map inside a `ScrollView` (Android)

The only gotcha the docs document: on Android a `Map` inside a `ScrollView` loses pan/zoom to the parent's vertical scroll and flickers. Fix: give the map container a **fixed height** and toggle the parent's `scrollEnabled` from the map wrapper's `onTouchStart` → `false`, `onTouchEnd` **and** `onTouchCancel` → `true` (miss `onTouchCancel` and the ScrollView stays locked). Wrap only the map container, not the screen. Unnecessary if the map is full-screen. Test on a physical Android device.

## dev-flow integration

- Owned on the mobile side: add a map screen via `rn-add-screen` using these components; this reference is the how-to.
- `meta.json#stack.maps = "mapcn-rn"`. Also record the provider (`carto` / `maptiler` / `mapbox`) — it's a licensing + native-dep decision, not a detail.
- Because it needs a **dev build**, sequence it *before* any Expo-Go-only smoke test; it ships through the normal `rn-eas-deploy` flow. Web counterpart: `mapcn` (see `design-md-to-app/references/maps-mapcn.md`).

## Sources

- Intro: <https://mapcn-rn.dev/docs> · Installation: <https://mapcn-rn.dev/docs/installation> · CLI: <https://mapcn-rn.dev/docs/cli> · Commercial use: <https://mapcn-rn.dev/docs/commercial-use>
- API reference: <https://mapcn-rn.dev/docs/api-reference> · Gotchas: <https://mapcn-rn.dev/docs/gotchas> · Advanced: <https://mapcn-rn.dev/docs/advanced-usage>
- Examples: <https://mapcn-rn.dev/docs/basic-map> · <https://mapcn-rn.dev/docs/controls> · <https://mapcn-rn.dev/docs/markers> · <https://mapcn-rn.dev/docs/popups> · <https://mapcn-rn.dev/docs/routes> · <https://mapcn-rn.dev/docs/clusters>
- Installed source of truth: <https://mapcn-rn.dev/maps/map.json> · <https://mapcn-rn.dev/maps/map-maptiler.json> · <https://mapcn-rn.dev/maps/map-mapbox.json> · CLI package: <https://www.npmjs.com/package/mapcn-rn>
