# Trigger acceptance list — rn-publishing-payments

## Should trigger (3+)
1. "Prepara metadata + screenshots per l'App Store"
2. "Integra abbonamento mensile con RevenueCat"
3. "Usa Stripe per un acquisto una tantum (servizio non-digitale)"

## Should NOT trigger (3+)
1. "Build production con EAS" → expect rn-eas-build-submit-update
2. "Push notification al checkout" → expect rn-push-notifications
3. "Configura il backend per gli ordini" → expect rn-backend

## Anti-patterns the skill content MUST forbid
1. Stripe in-app per CONTENUTI DIGITALI / abbonamenti dentro l'app — VIETATO da Apple App Store Review (4.3.1). Devi usare IAP.
2. Bypass IAP per abbonamenti — banishment dallo store.
3. Mostrare il prezzo IAP hardcoded — usa `product.priceString` dal provider (localizzato + tax-inclusive).
4. Mostrare login social senza Sign in with Apple (su iOS) se hai Google/Facebook/altri → 4.8 reject.
5. Screenshot non-realistic (deepfake, illustrazioni non in app) → 2.3 reject.
