> Bootstrap snapshot — kept in sync manually with `rn-fundamentals/references/stack-defaults.md`.
> Update both files together when bumping a major version.
> Snapshot date: 2026-10-03.

# Stack defaults (opinionated)

When bootstrapping a new RN/Expo app via `rn-bootstrap`, install these exact major versions:

⚠️ **For everything Expo manages, npm `latest` is the wrong answer** — the table is generated from
`expo@57`'s `bundledNativeModules.json` (what `expo install` resolves), with Expo's own range
operators. **Install with `npx expo install <pkg>`, never `npm install <pkg>`.** Full rationale in
`rn-fundamentals/references/stack-defaults.md`.

| Package | Version | Purpose | Notes |
|---|---|---|---|
| `expo` | `^57.0.27` | Expo SDK | Latest stable. New Architecture ON by default. |
| `react-native` | `0.86.3` | RN core | Bumped by Expo SDK — DO NOT override manually. Verified 2026-09-22 against `expo-template-blank-typescript@57.0.26`'s own `dependencies` (the SDK-bundled version, not npm `latest` — Expo pins a specific RN per SDK and `expo install` resolves to that, not to whatever npm calls latest). |
| `react` | `19.2.3` | React | Bumped by Expo SDK — DO NOT override manually. |
| `typescript` | `^7.0.2` | TS | Template `blank-typescript` brings a compatible version. |
| `expo-router` | `~57.0.24` | File-based routing | Mandatory for all apps in this set. |
| `nativewind` | `^4.2.7` | Tailwind for RN | Major 4 only. |
| `tailwindcss` | `^3.4` | Required by NativeWind v4 | ⚠️ DO NOT install Tailwind 4.x yet — NativeWind v4 is not yet compatible. Pin to 3.4.x until NativeWind confirms support. |
| `zustand` | `^5.0.15` | Global state | Default for non-trivial global state. |
| `@tanstack/react-query` | `^5.104.1` | Data fetching | Major 5 only. |
| `react-native-reanimated` | `4.5.1` | Animations | Required by Expo Router for native stack animations. **Reverted 2026-10-03 to the SDK pin.** It was bumped to `4.7.0` on 2026-09-22 on the strength of the peer range alone — the wrong test: for a native module in an Expo-managed project the authority is the SDK's `bundledNativeModules.json`, not npm `latest` and not the peer range. Expo 57.0.26 bundles `4.5.1`, so `4.7.0` made `npx expo install --check` complain in every project scaffolded from this table. Latest on npm is `4.7.1` and stays there until an SDK bundles it. |
| `react-native-worklets` | `0.10.1` | Worklets runtime | **Separate package since Reanimated 4** — `expo install` takes both, and the SDK pins them as a pair (57.0.26: reanimated `4.5.1` + worklets `0.10.1`). Missing it fails at runtime, not at build. Reverted with Reanimated on 2026-10-03, and now tracked by `refresh_stack_defaults.py`, which did not watch it before — which is how one half of the pair got bumped alone. |
| `react-native-gesture-handler` | `~2.32.0` | Gestures | Required by Expo Router. |
| `react-native-safe-area-context` | `~5.7.0` | Safe area | Required for all root screens. |
| `expo-image` | `~57.0.5` | Optimized `<Image>` | Replaces `Image` from `react-native`. |
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
