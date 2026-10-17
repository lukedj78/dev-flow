> Snapshot date: 2026-10-17. Refresh with `python3 scripts/refresh_stack_defaults.py` (dry-run) — **not** by hand.
> This file is carried by `rn-fundamentals` and `rn-bootstrap`, byte-identical (`lint_skills.py` fails otherwise).

# Stack defaults (opinionated)

When bootstrapping a new RN/Expo app via `rn-bootstrap`, install these exact major versions:

⚠️ **For everything Expo manages, npm `latest` is the wrong answer.** Expo SDK ships
`bundledNativeModules.json` — the version `expo install` resolves for that SDK — and it lags npm on
purpose, because a native module has to match the SDK's compiled runtime. The table below is generated
from **the current SDK's manifest** (`expo@58.0.14` on the snapshot date), not from `npm view`, and the range operators are Expo's own (`~` is
narrower than `^`, and for a native module that difference is the point).

Checking this against npm instead had every Expo-managed row wrong, `react-native-gesture-handler`
included — pinned at `^3.1.0` while SDK 57 bundled `~2.32.0`, a whole major ahead of what that SDK
supported (SDK 58 moved to `~3.3.0`, and the table followed the SDK, not npm). Following npm there does not give you a newer app; it gives you one `expo install` disagrees
with. **Install with `npx expo install <pkg>`, never `npm install <pkg>`**: it reads the same manifest
and is the reason these numbers are what they are.

The non-Expo rows (`typescript`, `zustand`, `@tanstack/react-query`, `nativewind`, `tailwindcss`) still
track npm `latest`, since Expo does not manage them.

| Package | Version | Purpose | Notes |
|---|---|---|---|
| `expo` | `^58.0.14` | Expo SDK | Latest stable. New Architecture ON by default. |
| `react-native` | `0.88.0` | RN core | Bumped by Expo SDK — DO NOT override manually. Verified 2026-10-17 against `expo-template-blank-typescript@58.0.23`'s own `dependencies` (RN `0.88.0`, React `19.3.0`) (the SDK-bundled version, not npm `latest` — Expo pins a specific RN per SDK and `expo install` resolves to that, not to whatever npm calls latest). |
| `react` | `19.3.0` | React | Bumped by Expo SDK — DO NOT override manually. |
| `typescript` | `^7.0.2` | TS | Template `blank-typescript` brings a compatible version. |
| `expo-router` | `~58.0.23` | File-based routing | Mandatory for all apps in this set. |
| `nativewind` | `^4.2.7` | Tailwind for RN | Major 4 only. |
| `tailwindcss` | `^3.4` | Required by NativeWind v4 | ⚠️ DO NOT install Tailwind 4.x yet — NativeWind v4 is not yet compatible. Pin to 3.4.x until NativeWind confirms support. |
| `zustand` | `^5.0.15` | Global state | Default for non-trivial global state. |
| `@tanstack/react-query` | `^5.104.4` | Data fetching | Major 5 only. |
| `react-native-reanimated` | `4.7.1` | Animations | Required by Expo Router for native stack animations. **Reverted 2026-10-03 to the SDK pin.** It was bumped to `4.7.0` on 2026-09-22 on the strength of the peer range alone — the wrong test: for a native module in an Expo-managed project the authority is the SDK's `bundledNativeModules.json`, not npm `latest` and not the peer range. Expo 57.0.26 bundled `4.5.1`, so `4.7.0` made `npx expo install --check` complain in every project scaffolded from this table. SDK 58 (`expo@58.0.14`) bundles `4.7.1`, which is why it is here now. ⚠️ 4.7 makes the new layout-animations engine the default, and Jest needs `react-native-reanimated/jest/resolver` (see `rn-write-tests`). |
| `react-native-worklets` | `0.13.0` | Worklets runtime | **Separate package since Reanimated 4** — `expo install` takes both, and the SDK pins them as a pair (57.0.26: reanimated `4.5.1` + worklets `0.10.1`; 58.0.14: `4.7.1` + `0.13.0`). Missing it fails at runtime, not at build. Reverted with Reanimated on 2026-10-03, and now tracked by `refresh_stack_defaults.py`, which did not watch it before — which is how one half of the pair got bumped alone. |
| `react-native-gesture-handler` | `~3.3.0` | Gestures | Required by Expo Router. ⚠️ **Major 3 since SDK 58**: the hook API (`usePanGesture`, …) replaces the `Gesture.*` builders, which still work but are deprecated. See `rn-animations-gestures`. |
| `react-native-safe-area-context` | `~5.10.1` | Safe area | Required for all root screens. |
| `expo-image` | `~58.0.15` | Optimized `<Image>` | Replaces `Image` from `react-native`. |
| `@shopify/flash-list` | `^2.3.2` | Performant lists | Replaces `FlatList` for long lists. |

## Engine / runtime defaults

- JS engine: **Hermes** (default).
- Architecture: **New Architecture** — always on since SDK 55, not configurable. Do not set `newArchEnabled`; it is ignored.
- Min iOS: 15.1 (Expo SDK 55+ default).
- Min Android: 24 (API level for Android 7.0).
- Bundler: Metro (Expo default).
- Package manager: **npm**.

## How to refresh

Monthly, from the dev-flow repo: `python3 scripts/refresh_stack_defaults.py` prints the drift (dry-run),
and `--apply` rewrites the table in both copies of this file. It reads the Expo-managed rows from the
SDK's `bundledNativeModules.json` and the others from npm `latest`, the split explained at the top. When
`bundledNativeModules.json` is unreachable it falls back to npm for every row and says so; don't apply
that run. If a major version bump appears (Expo, React Native, NativeWind, Reanimated), do not bump
silently — open a discussion: the RN skills' patterns, decision trees and examples may need updates too.

## Known compatibility constraints

- **Tailwind 4.x ≠ NativeWind v4 today.** NativeWind v4 reads Tailwind 3.x preset format; Tailwind 4 changed config format substantially. NativeWind **v5 targets Tailwind v4**, and it is at release candidate: `5.0.0-rc.0` on the `preview` and `rc` dist-tags, while `latest` is **4.2.7** (npm registry, read 2026-10-17). Stay on Tailwind 3.4.x until v5 is `latest`.
- **React 19** is the default for Expo SDK 55+. Some third-party RN libraries lag — when one breaks, check its issues page before downgrading React.
- **Reanimated 4** uses the New Architecture under the hood — which on SDK 55+ is simply always there, nothing to switch on.
