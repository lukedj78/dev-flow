# Trigger acceptance list — rn-eas-deploy

## Should trigger (3+)
1. "Deploy the app to production"
2. "Pubblica l'app sull'App Store / Play Store"
3. orchestrator routes here from `dev-flow` when `meta.json#phase == "feature_complete"` and `stack.framework == "expo-rn"`

## Should NOT trigger (3+)
1. "Aggiungi auth" → expect rn-module-add
2. "OTA update di un bug fix" → expect rn-eas-build-submit-update direttamente (più granulare)
3. "Bootstrap app" → expect rn-bootstrap

## Idempotency contract
1. Re-running on a project already configured for EAS MUST detect `eas.json` + linked project and skip init.
2. Re-running after a successful deploy MUST report current store state, not blindly re-build.
3. Credenziali MAI generate al volo se non già fatto via `eas credentials` — refuse con messaggio chiaro.
4. NESSUN bump di version automatico — l'utente bumpa esplicitamente in `app.json` o approva un bump suggerito.

## End-state after success
1. `eas.json` con i 3 profili in repo.
2. `meta.json#stack.deploy = "eas"`.
3. `meta.json#phase = "deployed"`.
4. Production build su entrambi gli store + EAS Update sul canale production.
5. Pre-submission checklist (da rn-publishing-payments) confermata.
