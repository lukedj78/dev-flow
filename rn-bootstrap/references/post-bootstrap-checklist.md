# Post-bootstrap checklist

After `rn-bootstrap` finishes, verify each item before bumping `meta.json#phase` to `scaffolded`. The `scripts/verify.ts` automates most of this.

## File existence

- [ ] `package.json` with `expo`, `expo-router`, `nativewind`, `tailwindcss`, `zustand`, `@tanstack/react-query`, `react-native-reanimated`, `react-native-gesture-handler`, `react-native-safe-area-context`, `expo-image`, `@shopify/flash-list`.
- [ ] `app/_layout.tsx` imports `../global.css` and renders `<Stack />`.
- [ ] `app/index.tsx` exists with a "hello world" screen using NativeWind classes.
- [ ] `global.css` with `@tailwind base/components/utilities`.
- [ ] `tailwind.config.js` with `nativewind/preset` and tokens from DESIGN.md.
- [ ] `babel.config.js` with `nativewind/babel`.
- [ ] `metro.config.js` with `withNativeWind`.
- [ ] `nativewind-env.d.ts` with `/// <reference types="nativewind/types" />` (required for NativeWind v4 `className` to type-check).
- [ ] `app.json` with `expo.scheme`, `expo.experiments.typedRoutes: true`, `expo.newArchEnabled: true`.
- [ ] `tsconfig.json` with `extends: "expo/tsconfig.base"` and `paths` for `@/*`.
- [ ] `.env.example` listing `EXPO_PUBLIC_*` vars used by the app.
- [ ] `components/`, `lib/`, `store/`, `types/`, `assets/` directories (can be empty with `.gitkeep`).

## Tooling

- [ ] `npx tsc --noEmit` exits 0.
- [ ] `npx expo doctor` exits 0 or with only documented warnings (e.g. "no native modules").
- [ ] `npx expo start` starts Metro and shows the app in Expo Go / dev client.

## meta.json

- [ ] `meta.json#stack.framework == "expo-rn"`.
- [ ] `meta.json#stack` has the other keys populated (`ui: "nativewind"`, `auth: null`, `db: null`, `payments: null`, `deploy: null` — backend/payments come from `rn-module-add`, deploy from `rn-eas-deploy`).
- [ ] `meta.json#stack_config` populated (`expo_sdk`, `state_lib: "zustand"`, `data_lib: "tanstack-query"`).
- [ ] `meta.json#phase == "scaffolded"`.
- [ ] `meta.json#history` appended with this bootstrap event.

If any item fails: do NOT bump the phase. Report the failure and stop.
