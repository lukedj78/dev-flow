> Sources: https://developer.apple.com/help/app-store-connect/reference/screenshot-specifications/, https://developer.apple.com/app-store/product-page/, https://support.google.com/googleplay/android-developer/answer/9866151

# Store assets — what to produce, what size

## iOS — App Store Connect

### App icon
- 1024×1024 px, PNG, no alpha channel (no transparency).
- File: `./assets/icon.png` (Expo handles resizing for in-device icons automatically).

### Screenshots (REQUIRED — 1 to 10 per size)

Apple auto-scales down for smaller devices, so you upload **one iPhone size** (plus iPad only if you ship iPad). The 2026 set:

| Display | Accepted portrait sizes | Requirement |
|---|---|---|
| 6.9" iPhone | **1320×2868**, 1290×2796, or 1260×2736 | REQUIRED if the app runs on iPhone — **6.9" OR 6.5", not both** |
| 6.5" iPhone | 1284×2778 or 1242×2688 | Only required if you do NOT provide 6.9". Providing 6.9" is preferred (no upscaling) |
| 13" iPad | **2064×2752** or 2048×2732 | REQUIRED if the app runs on iPad |
| 12.9" iPad | 2048×2732 | Legacy/optional — 13" screenshots are scaled down if omitted |

Apple accepts several resolutions per display class; pick the largest (bold above) — it's the native size of the newest device and scales down cleanly to the rest. Landscape is the same numbers transposed.

Best practice:
- Capture from a real device or `xcrun simctl io booted screenshot`.
- 3-5 screenshots per size, showing key value proposition (Apple's own limit is 1–10).
- `.png` / `.jpg` / `.jpeg`, **no alpha channel or transparency**.
- Optional: overlay text + device frames (must use Apple's provided frames or none — third-party renders rejected).

### App preview video (optional)
- 15-30 seconds, MP4 / MOV, captured from device.
- Powerful for conversion.

## Android — Google Play Console

### App icon
- 512×512 px, PNG with alpha OK.
- File: same `./assets/icon.png` — Expo regenerates correctly.

### Screenshots (REQUIRED, minimum 2)
- Phone: 320–3840 px each side, 16:9 or 9:16 ratio.
- 7-inch tablet (optional): 320–3840 px.
- 10-inch tablet (optional): 320–3840 px.

### Feature graphic (REQUIRED)
- 1024×500 px JPG/PNG, no transparency.
- Shown on the Play Store listing header.

### Promo video (optional)
- YouTube URL.

## Both stores — copy

| Field | iOS | Android |
|---|---|---|
| App name | 30 chars | 30 chars |
| Subtitle / short desc | 30 chars (iOS subtitle) | 80 chars (Android short desc) |
| Long description | 4000 chars | 4000 chars |
| Keywords | 100 chars (iOS only) | n/a (Play uses long-desc for indexing) |

## Privacy policy URL (REQUIRED both stores)

A publicly hosted privacy policy. Use a generator (Termly, iubenda) or write your own.
Must cover:
- What data you collect (auth, analytics, push token, etc.).
- How long you retain it.
- Third-party processors.
- User rights (deletion, export — GDPR, CCPA).

## Privacy nutrition label (iOS) / Data safety form (Android)

Both stores ask you to declare WHAT YOU COLLECT and WHY. You fill a form during submission. Categories:

- Contact info (email, name, phone)
- Identifiers (user ID, device ID)
- Usage data (analytics)
- Diagnostics (crash data)
- Location
- Health
- Financial

For EACH category collected:
- Is it linked to the user's identity?
- Is it used for tracking (cross-app/cross-site)?
- What's the purpose (analytics, personalization, ad targeting, app functionality)?

**You MUST declare everything your SDKs collect**, not just your own code. Audit:
- `expo-notifications` — push token (identifier).
- `@supabase/supabase-js` — auth identifiers.
- `@sentry/react-native` (if used) — diagnostic + identifier.
- Firebase Analytics — usage + identifier.
- Any analytics SDK — usage + identifier.

If you're unsure, the SDK's docs almost always have a "Privacy" section.

## Asset folder structure (recommendation)

```
project-root/
├── assets/
│   ├── icon.png                       # 1024×1024 (App Store) — Expo handles the rest
│   ├── adaptive-icon.png              # 1024×1024 (Android adaptive)
│   ├── splash.png                     # 1284×2778 (modern iPhone Pro)
│   └── notification-icon.png          # 96×96 transparent (Android)
└── store-assets/                       # NOT bundled — used at submission time
    ├── ios/
    │   ├── screenshots/
    │   │   ├── 6.9/                    # 1320×2868 — the one iPhone size you need
    │   │   └── ipad-13/                # 2064×2752 — only if you ship iPad
    │   └── preview.mp4
    ├── android/
    │   ├── screenshots/phone/
    │   └── feature-graphic.png
    └── descriptions/
        ├── en-US.md
        └── it-IT.md
```

The `store-assets/` folder lives in git but is NOT in the app bundle. Use a tool like Fastlane to upload, or upload manually via ASC / Play Console.

## Localization

- iOS: list app metadata in each locale in App Store Connect.
- Android: list each in Play Console.

Translate at minimum: app name, subtitle, description, keywords (iOS). Screenshots: ideally localized but optional.
