> Snapshot date: 2026-07-22. Re-check monthly with `npm view <pkg> version`.

# Stack defaults (opinionated)

When bootstrapping a new RN/Expo app via `rn-bootstrap`, install these exact major versions:

| Package | Version | Purpose | Notes |
|---|---|---|---|
| `expo` | `^57.0.8` | Expo SDK | Latest stable. New Architecture ON by default. |
| `react-native` | `0.86.0` | RN core | Bumped by Expo SDK — DO NOT override manually. |
| `react` | `19.2.8` | React | Bumped by Expo SDK — DO NOT override manually. |
| `typescript` | `^7.0.2` | TS | Template `blank-typescript` brings a compatible version. |
| `expo-router` | `^57.0.8` | File-based routing | Mandatory for all apps in this set. |
| `nativewind` | `^4.2.6` | Tailwind for RN | Major 4 only. |
| `tailwindcss` | `^3.4` | Required by NativeWind v4 | ⚠️ DO NOT install Tailwind 4.x yet — NativeWind v4 is not yet compatible. Pin to 3.4.x until NativeWind confirms support. |
| `zustand` | `^5.0.14` | Global state | Default for non-trivial global state. |
| `@tanstack/react-query` | `^5.101.4` | Data fetching | Major 5 only. |
| `react-native-reanimated` | `^4.5.3` | Animations | Required by Expo Router for native stack animations. |
| `react-native-gesture-handler` | `^3.1.0` | Gestures | Required by Expo Router. |
| `react-native-safe-area-context` | `^5.8.0` | Safe area | Required for all root screens. |
| `expo-image` | `^57.0.1` | Optimized `<Image>` | Replaces `Image` from `react-native`. |
| `@shopify/flash-list` | `^2.3.2` | Performant lists | Replaces `FlatList` for long lists. |

## Engine / runtime defaults

- JS engine: **Hermes** (default).
- Architecture: **New Architecture ON** (`newArchEnabled: true` in `app.json`).
- Min iOS: 15.1 (Expo SDK 55+ default).
- Min Android: 24 (API level for Android 7.0).
- Bundler: Metro (Expo default).
- Package manager: **npm**.

## How to refresh

Re-run `npm view <pkg> version` once a month for each row of the table above. If a major version bump appears (Expo, React Native, NativeWind, Reanimated), do not bump silently — open a discussion: the related skill content (`patterns.md`, `decision-tree.md`, `examples/`) may need updates.

## Known compatibility constraints

- **Tailwind 4.x ≠ NativeWind v4 today.** NativeWind v4 reads Tailwind 3.x preset format; Tailwind 4 changed config format substantially. NativeWind **v5 targets Tailwind v4**, but it is still on the `preview` dist-tag (`5.0.0-preview.4`) — `latest` remains **4.2.6**. Stay on Tailwind 3.4.x until v5 leaves preview.
- **React 19** is the default for Expo SDK 55+. Some third-party RN libraries lag — when one breaks, check its issues page before downgrading React.
- **Reanimated 4** uses the New Architecture under the hood; it requires `newArchEnabled: true` (already our default).
