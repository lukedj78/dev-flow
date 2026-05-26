> Sources: Apple App Store Review Guidelines, Google Play Policy, internal opinion.

# Decision tree — payments

## Q1: Is the product digital or physical?

```
What is the user paying for?
├── Digital good consumed in the app:
│   - Premium tier / Pro features
│   - Subscription to a service
│   - In-app currency, gems, coins
│   - Unlock a one-shot feature (no shipping)
│   - Course / e-book viewed in the app
│   → IAP via RevenueCat. MANDATORY on iOS. Required on Android too (with rare exceptions).
│
├── Physical good (shipped to user):
│   - Marketplace item, retail, hardware
│   → Stripe / PayPal / other. The transaction is OK outside IAP.
│
└── Service performed outside the app:
   - Ride (Uber)
   - Food delivery
   - Real-world class / appointment
   - Consultant invoice (B2B)
   → Stripe / direct billing. NOT IAP.
```

## Q2: I have a digital product but I want to avoid the 30% fee. Options?

```
└── There is NO clean workaround. Apple enforces this aggressively.

Limited options:
- "Reader app" exemption: if your app is purely a consumer of content the user
  paid for elsewhere (Netflix, Spotify, Kindle), you can omit purchase UI in
  the app and let users sign in to access. NO purchase prompts.
- External link entitlement (iOS 17.4+, EU-only or US recent ruling): some apps
  can link to a web purchase. Strict rules; consult Apple's docs.
- Web app + thin native shell: if your native app is "incidental" you have more
  flexibility. But Apple may reject if the native app exists primarily for IAP avoidance.

Spend energy on a great IAP UX, not on dodging the fee. The 70% is usually fine.
```

## Q3: RevenueCat or raw `react-native-iap`?

```
RevenueCat is the answer 95% of the time:
- Receipt validation (server-side, no rolling your own)
- Cross-platform subscriptions (one entitlement, iOS+Android)
- Restore purchases (Apple-required, easy to get wrong)
- Sandbox testing
- Free up to 10k MTR (more than enough for indie + early startup)

Use raw react-native-iap only if:
- You have an existing backend with receipt validation logic and don't want to
  migrate.
- You're at scale and the RevenueCat % bites (rare; the price is fair).
```

## Q4: Subscription pricing strategy

```
Pricing tiers I should offer:
- Monthly + Annual (with discount on annual, e.g. monthly × 12 × 0.7)
- Optional: lifetime one-time (high price, removes 30% recurring fee psychology)
- Optional: family plan (shared via Apple Family Sharing)

What NOT to do:
- 7-day free trial without setting expectations is fine. 30-day is unusual on mobile.
- "Pay nothing today" must clearly show when the user will be charged + how much.
- Apple rejects unclear trial CTAs.

Use RevenueCat's "introductory offer" + "trial period" — these are first-class IAP concepts on iOS.
```

## Q5: External payment for a B2B / non-digital service

```
Stripe via WebView OR Stripe RN SDK:

- WebView is simpler: open a Stripe Checkout session URL inside an in-app browser.
  Use `WebBrowser.openAuthSessionAsync` from `expo-web-browser` for a clean dismiss.
- Native SDK gives more control (Apple Pay, custom flow) — heavier integration.

Either way: confirm with Apple's "external payment" rules. Even for non-digital,
Apple sometimes objects.
```

## Q6: First store submission — what do I prep?

```
Required materials:
1. App icon (1024×1024 PNG, no transparency for iOS).
2. Screenshots (3 sizes iOS, multiple sizes Android — see store-assets.md).
3. App preview video (optional but recommended).
4. App name + subtitle.
5. Short description (170 chars Android, 30 chars iOS subtitle).
6. Long description (4000 chars).
7. Keywords (iOS only, 100 chars).
8. Category (primary + secondary).
9. Age rating questionnaire.
10. Privacy policy URL (mandatory).
11. Privacy nutrition label (iOS) / Data safety form (Android).
12. (If paid) Pricing tier.
13. (If you have IAP) Subscription/IAP listings, each with name + description + screenshot.

Use a tool like Fastlane or Expo's submit configs to keep these in source control.
```
