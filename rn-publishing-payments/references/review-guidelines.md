> Sources: https://developer.apple.com/app-store/review/guidelines/, https://support.google.com/googleplay/android-developer/topic/9858052

# Store review — what gets you rejected

The full Apple guidelines are 30+ pages. This file lists the points you'll most likely trip on.

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
