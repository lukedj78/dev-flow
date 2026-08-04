> Sources: https://developer.apple.com/app-store/review/guidelines/, https://developer.apple.com/news/upcoming-requirements/, https://support.google.com/googleplay/android-developer/topic/9858052, https://developer.android.com/developer-verification

# Store review — what gets you rejected

The full Apple guidelines are 30+ pages. This file lists the points you'll most likely trip on.

## Hard gates — these block the upload, not the review

Guideline violations get you a rejection you can argue with. These three reject the binary or pull the listing outright, and no amount of Resolution Center prose helps.

### Xcode 26 / iOS 26 SDK floor (Apple, since 2026-04-28)

Apps uploaded to App Store Connect **must be built with Xcode 26 or later, using the iOS 26 SDK** (or iPadOS/tvOS/visionOS/watchOS 26). An older toolchain is refused at upload.

On EAS this is free if you leave the build image alone: `image: auto` resolves to `macos-tahoe-26.5-xcode-26.6` for SDK 57. The trap is a project that **pinned an older `image` in `eas.json`** (e.g. `macos-sequoia-15.5-xcode-16.4` from an SDK 53 era) — those builds still succeed and then fail at submit. Grep `eas.json` for `"image"` before a release; if it's pinned to an Xcode < 26 image, drop the pin or move it forward. See `rn-eas-build-submit-update/references/eas-json.md`.

### Google Play developer verification + content ratings (announced 2026-07-15)

Two things, both now mandatory:
- **Developer verification** — all your apps must be registered in Play Console under a verified developer identity (legal name, address, contactable email/phone; D-U-N-S + website for organizations). ~99% of Play apps are auto-registered, but check Play Console for stragglers, and register anything you also distribute outside Play.
- **Content ratings** — Google no longer allows unrated apps. Fill the rating questionnaire; an unanswered one is now a removal reason, not a nag.

Enforcement starts **2026-09-30** for users in **Brazil, Indonesia, Singapore and Thailand**, expanding **globally in 2027**. Unverified apps can't be installed or updated on certified Android devices in the enforcing regions.

### EU DSA trader status (Apple, in force since 2025-02-17)

Apps **without verified trader status are removed from the App Store in the EU** until it's provided and verified — and trader status has been required to submit updates for EU-distributed apps since 2024-10-16. This is a Digital Services Act obligation, not an App Review guideline: it hits the listing directly.

Relevant to every EU-based project we ship. Fill it in App Store Connect → Business → Trader Status; verification takes days, so do it well before the release you care about.

## Apple App Store — most common rejections

### 2.1 — App completeness
- Bug / crash on first launch → reject.
- Placeholder text / lorem ipsum → reject.
- Broken links / 404 in About / Privacy → reject.

### 2.3.7 — Marketing
- Mentioning competitors by name in your description → reject.
- "Award-winning" without specifying the award → reject.

### 2.3.10 — Accurate metadata
- Screenshots showing features that don't exist in the app → reject.
- Screenshots with text overlays that misrepresent the app → reject.
- Different content per locale that materially changes the app's purpose → reject.

### 3.1.1 — In-App Purchase
- Selling digital goods or subscriptions WITHOUT IAP → reject + ban risk — EXCEPT on the US storefront, where since May 1, 2025 (Epic v. Apple injunction) apps may link/button out to external web checkout for digital goods with no entitlement and no Apple-mandated friction screen (see `decision-tree.md` Q2). This is a real, supported path on US builds, not a loophole to hide.
- No "Restore Purchases" button on paywall → reject (still applies when you offer IAP at all; if you route entirely through the US external-link path for a given SKU, restore semantics move to your own backend).
- Misleading subscription terms (unclear price, unclear trial end) → reject.

### 4.0 — Design
- "Looks like a website wrapped in a WebView" with no native value → reject.

### 4.3.1 — Spam
- Similar to many existing apps without a unique value → reject.

### 4.8 — Sign in with Apple
- If you offer Google / Facebook / X / Microsoft sign-in, you MUST also offer Sign in with Apple. iOS only.
- Email-based sign-in alone does NOT trigger this rule.

### 5.1.1 — Privacy
- Collecting data without disclosing in the Privacy Policy → reject.
- Privacy nutrition label that lies → reject + ban risk.
- ATT (App Tracking Transparency) prompt missing if you do cross-app tracking → reject.

### 5.1.5 — Location
- Asking for "Always" location when "While Using" suffices → reject.
- Sending location to third parties without disclosure → reject.

## Google Play — common rejections

### Policy: Permissions
- Requesting permissions not used by the app → reject (Android 13+).
- High-risk permissions (background location, SMS, call log) require a special declaration → reject without it.

### Policy: Data safety
- Data safety form doesn't match what your SDKs collect → reject + warning.

### Policy: Target API level
- Google Play requires targeting a recent Android API level (rolling requirement, roughly the current major − 1 each year — e.g. API 35 in 2025, API 36 by August 31, 2026 for new/updated apps). Check the current deadline at Play Console's target API level policy page before submitting. The Expo SDK you're on handles the underlying `targetSdkVersion` — verify after each SDK bump.
- **The API 36 deadline can be extended to November 1, 2026** on request: Play Console → Policy status → the warning's details page has an extension form. It buys two months, not a pass — and you have to ask before August 31.

### Policy: User data
- Sending personal data over HTTP (not HTTPS) → reject.

### Policy: Subscriptions
- Auto-renewing subscriptions must clearly disclose the renewal price, period, and cancellation steps in the Play listing AND in the paywall.

## Pre-submission checklist

- [ ] App icon present, 1024×1024 (iOS) and 512×512 (Android), no alpha for iOS.
- [ ] Screenshots: 3-5 per required size, all from the real app.
- [ ] Privacy policy URL hosted and reachable.
- [ ] Privacy nutrition label / Data safety form filled and matches reality.
- [ ] Sign in with Apple present (if any other 3rd party auth on iOS).
- [ ] Restore Purchases button on paywall (if IAP).
- [ ] All IAP / subscription products created and APPROVED in ASC / Play Console.
- [ ] App version bumped, build number bumped (or `autoIncrement: true` in eas.json).
- [ ] `npx expo doctor` passes.
- [ ] `npx tsc --noEmit` passes.
- [ ] Smoke-tested on at least one real device per platform via the `preview` EAS profile.
- [ ] Crash reporting (Sentry / similar) enabled in production build — first-week churn comes from crashes you didn't catch.
- [ ] Age rating questionnaire answered honestly.

## When review rejects you

Apple's response usually includes:
- The guideline cited (e.g. "3.1.1").
- A screenshot of the issue.
- Suggested resolution.

Reply via App Store Connect → Resolution Center. Be polite and concrete. Apple's review team is responsive but volume-bound.

For "appeal" cases (think they're wrong), Apple has an appeals board — but use sparingly. Most rejections have a real basis and the fastest path is to address it.

## "Soft" review heuristics (not in the rulebook but common)

- Apple reviewers test on iPhone SE (small screen). If your UI breaks on 4.7" → reject.
- Apple reviewers test with a fresh sandbox account. If onboarding requires a specific server state → reject.
- Apple reviewers test offline at least once. If the app crashes with no network → reject.
- Apple reviewers test in non-English locales. If strings overflow → reject.
- Google reviewers test on a low-end Android (Android Go-class). If perf is awful → reject.

Address these in QA BEFORE submitting.
