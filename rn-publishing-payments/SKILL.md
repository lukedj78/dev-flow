---
name: rn-publishing-payments
description: 'Use when preparing an Expo + RN app for store submission (metadata, screenshots, localized listings, privacy nutrition label, age rating) and integrating monetization (In-App Purchases via RevenueCat for digital goods/subscriptions; Stripe via WebView ONLY for non-digital services). Triggers on: "submit to App Store", "Play Store listing", "screenshot sizes", "RevenueCat setup", "Stripe payment in app", "subscription", "IAP", "privacy nutrition label", "App Store review reject". Not for: building / submitting (rn-eas-build-submit-update), backend setup (rn-backend).'
---

# rn-publishing-payments — guardrail for store publishing + payments

> For the current Expo API and per-version details, verify against the Expo docs / MCP `mcp.expo.dev` / `expo/skills` (see rn-fundamentals → Source of truth).

## The 5 rules (non-negotiable)

1. **Apple's 30% rule**: ANY digital good/service consumed inside the app MUST go through IAP (subscriptions, premium tiers, in-app currency, unlock-feature one-shots) — **unless** an allowed external-purchase path applies (notably the US external-link rule since May 2025; see `references/decision-tree.md` Q2). Bypassing IAP *without* an allowed path = rejection under guideline 3.1.1.
2. **Stripe / external payment only for NON-digital**: physical goods (shipped), services rendered outside the app (ride, food delivery, classroom), B2B (consultant invoice). Even then, Apple's "anti-steering" rules apply — careful what you link.
3. **Use RevenueCat for IAP**, not raw `react-native-iap`. RevenueCat handles receipt validation, cross-platform subscriptions, restore-purchases, sandbox testing, and analytics in one SDK with a generous free tier. Raw IAP works but you'll write 10x the code.
4. **Screenshots must be REAL** screenshots of the running app, not marketing illustrations (guideline 2.3.10). iOS needs **one iPhone size — 6.9" (preferred) or 6.5"** — plus 13" iPad only if you ship iPad; Apple scales the rest down (see `references/store-assets.md`).
5. **Privacy nutrition label (iOS) + Data safety (Android) MUST match reality**. Lying about data collection = ban. Audit the SDKs you use (analytics, push, crash reporting) — each declares what it collects.

## Quick decision tree

- "IAP, Stripe, or external link?" → `references/decision-tree.md`
- "What assets do I need for the store?" → `references/store-assets.md`
- "How do I get them *up there* without the web UI?" → the optional `asc` CLI
  (`metadata init | apply | keywords`, `screenshots plan | matrix | upload`); the
  permission table and the credential rules live in `rn-eas-deploy/references/asc-cli.md`.
  Uploading metadata and screenshots rewrites a listing the public reads — **ask before
  applying**, and never let an agent run the submit-to-review step on its own.
- "How do I integrate RevenueCat?" → `references/revenuecat.md`
- "What about App Store review?" → `references/review-guidelines.md`

## Common anti-patterns (NEVER do)

- ❌ "Buy premium" button that opens Stripe Checkout in a WebView for an in-app subscription → rejection.
- ❌ "Already paid on the web? Sign in to unlock" → tolerated under specific conditions (reader app exemption, multi-platform service), but read the rules first.
- ❌ Hardcoded `"€4.99/month"` in the UI — use `product.priceString` from RevenueCat / StoreKit (localized currency, tax-included for EU).
- ❌ Skipping Sign in with Apple when offering Google sign-in (iOS) → 4.8 reject.
- ❌ Marketing screenshots with fake content or device frames not provided by Apple → 2.3 reject.
- ❌ Privacy nutrition label that says "no data collected" while you ship Firebase Analytics → ban risk.
- ❌ Asking for IDFA (ATT prompt) before showing app value → bad practice + low opt-in rate.

## Sources

- Course: codewithbeto.dev/rnCourse — "Publishing, Payments, Native Modules" module (paid).
- Official Apple: https://developer.apple.com/app-store/review/guidelines/
- Official Google: https://support.google.com/googleplay/android-developer/topic/9858052
- Official RevenueCat: https://www.revenuecat.com/docs/getting-started
- Official Stripe RN: https://stripe.com/docs/payments/accept-a-payment?platform=react-native
