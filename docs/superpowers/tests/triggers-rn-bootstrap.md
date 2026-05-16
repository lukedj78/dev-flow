# Trigger acceptance list — rn-bootstrap

## Should trigger (3+)
1. orchestrator routes here from `dev-flow` when `meta.json#stack.framework == "expo-rn"` and `phase == "prd_drafted"`
2. user says: "scaffolda l'app Expo da questo PRD"
3. user says: "create RN app from PRD and DESIGN.md"

## Should NOT trigger (3+)
1. "Aggiungi una schermata di login" → expect rn-add-screen (Wave 2)
2. "Setup deploy on EAS" → expect rn-eas-deploy (Wave 3)
3. "Scaffolda l'app Next.js" → expect design-md-to-app (Next.js stack, untouched)

## Idempotency contract
1. Running the skill twice on the same project root MUST NOT duplicate package.json entries.
2. Running on a directory that already has package.json + app/ MUST report "already bootstrapped" and exit successfully.
3. Modifications to tailwind.config.js MUST be regenerated from DESIGN.md, not appended.

## Smoke test (post-bootstrap)
1. `package.json` exists with `expo`, `expo-router`, `nativewind`, `zustand`, `@tanstack/react-query`.
2. `app/_layout.tsx` exists and imports `../global.css`.
3. `tailwind.config.js` exists and contains colors derived from DESIGN.md.
4. `npx tsc --noEmit` exits 0.
5. `npx expo doctor` exits 0 (or with only warnings).

## Smoke test run log

- Date: 2026-05-16
- Expo SDK installed: 54.0.34 (expo@~54.0.33 from create-expo-app@latest)
- React Native installed: 0.81.5
- expo-router installed: 5.1.11 (manually pinned to sdk-53; see Bug #1 below)
- NativeWind installed: 4.2.4 (nativewind@^4)
- Tailwind installed: 3.4.19 (tailwindcss@^3.4 — correctly NOT 4.x)
- react-native-reanimated: 4.1.7
- react-native-gesture-handler: 2.28.0
- All verify.ts checks passed: YES — all 20/20 after manual workarounds (see concerns below)
- Idempotency: confirmed (init-expo-app.sh correctly detected package.json + app/ and skipped)
- tsc --noEmit: PASS (after manually creating nativewind-env.d.ts; see Bug #2 below)
- Total elapsed time: ~12 minutes
- Notes / bugs found requiring script fixes:

  **Bug #1 — init-expo-app.sh: pre-existing files in project root**
  `create-expo-app` aborts if any files exist in the target directory. In real use
  the project root already has PROJECT.md, PRD.md, DESIGN.md, and .workflow/ before
  init-expo-app.sh is called. The script must stash those files, run create-expo-app,
  then restore them. Fix: wrap the npx create-expo-app call with stash/restore logic.

  **Bug #2 — init-expo-app.sh: wrong expo-router version (SDK mismatch)**
  `npm install expo-router` (unversioned) installs expo-router@55.x (latest), which
  requires react-native-screens@4.25+ (needs RN >= 0.82). But create-expo-app@latest
  installs Expo SDK 54 (RN 0.81.5). There is no sdk-54 dist-tag for expo-router.
  Fix: use `npx expo install expo-router` (not plain `npm install`) so the Expo CLI
  picks the SDK-compatible version. Alternatively pin to the sdk-53 tag (~5.1.x) and
  note SDK 54 compatibility.

  **Bug #3 — install-stack.sh: peer dep conflict on animations stack**
  `npx expo install react-native-reanimated react-native-gesture-handler` fails
  due to react-native-screens@4.25 resolving into the dep graph via the latest
  @react-navigation/bottom-tabs. Fix: pass `-- --legacy-peer-deps` to the expo
  install command for the animations step, or add --legacy-peer-deps to .npmrc.

  **Bug #4 — wire-nativewind.ts: missing nativewind-env.d.ts**
  NativeWind v4 requires a nativewind-env.d.ts file (/// <reference types="nativewind/types" />)
  for className to type-check. The script generates 4 files but not this 5th one.
  tsc --noEmit fails on app/index.tsx and app/_layout.tsx until this file exists.
  Fix: add writeNativewindEnvDts() to wire-nativewind.ts that writes this file.
