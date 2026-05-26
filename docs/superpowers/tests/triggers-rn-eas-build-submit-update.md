# Trigger acceptance list — rn-eas-build-submit-update

## Should trigger (3+)
1. "Setup EAS Build per la mia app"
2. "Come faccio una OTA update con EAS?"
3. "Configura EAS Submit per App Store / Play Store"

## Should NOT trigger (3+)
1. "Pubblica sullo store" (metadata, screenshots) → expect rn-publishing-payments
2. "Bootstrap dell'app" → expect rn-bootstrap
3. "Connetti il backend" → expect rn-backend

## Anti-patterns the skill content MUST forbid
1. Build "production" senza profilo `preview` testato prima → rischio di rilascio rotto.
2. OTA update di codice nativo o config-plugin → SE la modifica tocca i nativi, serve un nuovo build (non OTA).
3. Credenziali APNs / keystore Android in repo → MAI. Usa EAS credentials server-side.
4. EAS Update senza branch / channel — tutti gli utenti ricevono ogni push, anche QA.
5. Build da `main` senza tag / version bump — versione store collide / non monotona.
