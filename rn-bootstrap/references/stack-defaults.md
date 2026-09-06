> Bootstrap snapshot — kept in sync manually with `rn-fundamentals/references/stack-defaults.md`.
> Update both files together when bumping a major version.
> Snapshot date: 2026-08-26.

# Stack defaults (opinionated)

When bootstrapping a new RN/Expo app via `rn-bootstrap`, install these exact major versions:

⚠️ **For everything Expo manages, npm `latest` is the wrong answer** — the table is generated from
`expo@57`'s `bundledNativeModules.json` (what `expo install` resolves), with Expo's own range
operators. **Install with `npx expo install <pkg>`, never `npm install <pkg>`.** Full rationale in
`rn-fundamentals/references/stack-defaults.md`.

| Package | Version | Purpose | Notes |
|---|---|---|---|
| `expo` | `^57.0.16` | Expo SDK | Latest stable. New Architecture ON by default. |
| `react-native` | `0.86.2` | RN core | Bumped by Expo SDK — DO NOT override manually. |
| `react` | `19.2.3` | React | Bumped by Expo SDK — DO NOT override manually. |
| `typescript` | `^7.0.2` | TS | Template `blank-typescript` brings a compatible version. |
| `expo-router` | `~57.0.16` | File-based routing | Mandatory for all apps in this set. |
| `nativewind` | `^4.2.6` | Tailwind for RN | Major 4 only. |
| `tailwindcss` | `^3.4` | Required by NativeWind v4 | ⚠️ DO NOT install Tailwind 4.x yet — NativeWind v4 is not yet compatible. Pin to 3.4.x until NativeWind confirms support. |
| `zustand` | `^5.0.15` | Global state | Default for non-trivial global state. |
| `@tanstack/react-query` | `^5.102.6` | Data fetching | Major 5 only. |
| `react-native-reanimated` | `4.5.1` | Animations | Required by Expo Router for native stack animations. |
| `react-native-worklets` | `0.10.1` | Worklets runtime | **Separate package since Reanimated 4** — `expo install` takes both. Missing it fails at runtime, not at build. |
| `react-native-gesture-handler` | `~2.32.0` | Gestures | Required by Expo Router. |
| `react-native-safe-area-context` | `~5.7.0` | Safe area | Required for all root screens. |
| `expo-image` | `~57.0.3` | Optimized `<Image>` | Replaces `Image` from `react-native`. |
| `@shopify/flash-list` | `^2.0.2` | Performant lists | Replaces `FlatList` for long lists. |

## Engine / runtime defaults

- JS engine: **Hermes** (default).
- Architecture: **New Architecture** — always on since SDK 55, not configurable. Do not set `newArchEnabled`; it is ignored.
- Min iOS: 15.1 (Expo SDK 55+ default).
- Min Android: 24 (API level for Android 7.0).
- Bundler: Metro (Expo default).
- Package manager: **npm**.

## Known compatibility constraints

- **Tailwind 4.x ≠ NativeWind v4 today.** NativeWind v4 reads Tailwind 3.x preset format; Tailwind 4 changed config format substantially. Stay on Tailwind 3.4.x until NativeWind ships a v5 (or v4.x patch) confirming Tailwind 4 support.
- **React 19** is the default for Expo SDK 55+. Some third-party RN libraries lag — when one breaks, check its issues page before downgrading React.
- **Reanimated 4** uses the New Architecture under the hood — which on SDK 55+ is simply always there, nothing to switch on.
