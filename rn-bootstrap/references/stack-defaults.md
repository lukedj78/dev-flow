> Bootstrap snapshot — kept in sync manually with `rn-fundamentals/references/stack-defaults.md`.
> Update both files together when bumping a major version.
> Snapshot date: 2026-05-16.

# Stack defaults (opinionated)

When bootstrapping a new RN/Expo app via `rn-bootstrap`, install these exact major versions:

| Package | Version | Purpose | Notes |
|---|---|---|---|
| `expo` | `^55.0.24` | Expo SDK | Latest stable. New Architecture ON by default. |
| `react-native` | `0.85.3` | RN core | Bumped by Expo SDK — DO NOT override manually. |
| `react` | `19.2.6` | React | Bumped by Expo SDK — DO NOT override manually. |
| `typescript` | `^6.0.3` | TS | Template `blank-typescript` brings a compatible version. |
| `expo-router` | `^55.0.14` | File-based routing | Mandatory for all apps in this set. |
| `nativewind` | `^4.2.4` | Tailwind for RN | Major 4 only. |
| `tailwindcss` | `^3.4` | Required by NativeWind v4 | ⚠️ DO NOT install Tailwind 4.x yet — NativeWind v4 is not yet compatible. Pin to 3.4.x until NativeWind confirms support. |
| `zustand` | `^5.0.13` | Global state | Default for non-trivial global state. |
| `@tanstack/react-query` | `^5.100.10` | Data fetching | Major 5 only. |
| `react-native-reanimated` | `^4.3.1` | Animations | Required by Expo Router for native stack animations. |
| `react-native-gesture-handler` | `^2.31.2` | Gestures | Required by Expo Router. |
| `react-native-safe-area-context` | `^5.7.0` | Safe area | Required for all root screens. |
| `expo-image` | `^55.0.10` | Optimized `<Image>` | Replaces `Image` from `react-native`. |
| `@shopify/flash-list` | `^2.3.1` | Performant lists | Replaces `FlatList` for long lists. |

## Engine / runtime defaults

- JS engine: **Hermes** (default).
- Architecture: **New Architecture ON** (`newArchEnabled: true` in `app.json`).
- Min iOS: 15.1 (Expo SDK 55+ default).
- Min Android: 24 (API level for Android 7.0).
- Bundler: Metro (Expo default).
- Package manager: **npm**.

## Known compatibility constraints

- **Tailwind 4.x ≠ NativeWind v4 today.** NativeWind v4 reads Tailwind 3.x preset format; Tailwind 4 changed config format substantially. Stay on Tailwind 3.4.x until NativeWind ships a v5 (or v4.x patch) confirming Tailwind 4 support.
- **React 19** is the default for Expo SDK 55+. Some third-party RN libraries lag — when one breaks, check its issues page before downgrading React.
- **Reanimated 4** uses the New Architecture under the hood; it requires `newArchEnabled: true` (already our default).
