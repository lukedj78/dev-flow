# Trigger acceptance list — rn-add-screen

## Should trigger (3+)
1. "Aggiungi una schermata di login con form email + password"
2. orchestrator routes here from `dev-flow` when `meta.json#stack.framework == "expo-rn"` and `phase == "scaffolded"` and the user asks to add UI
3. "Crea la schermata profilo da questo screenshot"

## Should NOT trigger (3+)
1. "Bootstrap dell'app" → expect rn-bootstrap (phase prd_drafted)
2. "Configura Supabase" → expect rn-module-add (Wave 3)
3. "Stila il bottone" → expect rn-styling

## Idempotency contract
1. Adding the same screen twice MUST NOT duplicate the file — the skill detects the route and reports "already exists".
2. Modifying an existing screen MUST be additive: don't rewrite from scratch unless the user says "rewrite".
3. The skill MUST NOT touch unrelated routes.

## Outputs (per screen)
1. A new file under `app/...` (route in Expo Router convention).
2. (Optional) a new component under `components/` if the screen pulls out shared UI.
3. (Optional) a new hook under `lib/queries/` if the screen needs data fetching.
4. NO modifications to global config (`tailwind.config.js`, `app.json`, `babel.config.js`).
