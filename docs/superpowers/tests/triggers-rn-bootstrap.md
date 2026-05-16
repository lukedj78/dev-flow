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
