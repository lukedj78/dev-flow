> Sources: synthesized from rn-eas-build-submit-update + rn-publishing-payments.

# Decision tree — deploy

## Q1: Is this the first deploy or a subsequent release?

```
Is the app already in App Store Connect / Play Console with at least one build?
├── NO  → first deploy
│        - eas init + eas build:configure (creates eas.json)
│        - eas credentials (one-time setup)
│        - manual: create app listing in ASC + Play Console
│        - full pre-submission checklist
│        - eas build preview → smoke test → eas build production → eas submit
│
└── YES → subsequent release
         - bump version in app.json
         - eas build production --platform all
         - eas submit --profile production --platform all
         - (or for JS-only fix: eas update --branch <name> --channel production)
```

## Q2: Native change or JS-only?

```
What changed since the last deploy?
├── Native (deps, config plugins, app.json bundle/scheme) → full build + submit
├── JS-only (components, hooks, queries, styles, assets) → eas update (OTA)
│                                                          on the production channel
└── Mixed (some native + some JS)                        → full build + submit
                                                            (the OTA is included in the bundle)
```

## Q3: Which platforms now?

```
Target?
├── iOS + Android together   → --platform all (parallel, ~same time as single platform)
├── Only iOS (Android pending) → --platform ios
└── Only Android              → --platform android
```

Recommendation: ALWAYS deploy iOS + Android together once both are ready. Avoids the "Android two weeks behind iOS" trap.

## Q4: Patch / Minor / Major version?

```
Semver, applied to app.json#expo.version:
├── Patch (1.2.3 → 1.2.4): bug fix, no UX change. Often shippable as OTA.
├── Minor (1.2.3 → 1.3.0): new feature, no breaking change.
├── Major (1.2.3 → 2.0.0): rebrand, paywall change, major redesign.
```

Match the `version` in store metadata if you change it significantly — users see the version in app details.

## Q5: First deploy — what's the typical timeline?

```
Day -7 to -3: pre-submission checklist + store listings created.
Day -3 to -1: preview builds + smoke test on devices.
Day 0:        production build + submit.
Day 0-2:      Apple review (now usually < 24h, sometimes hours).
Day 0-1:      Google review (Day 1 usually).
Day +1 to +3: monitor crash reports. Be ready with hotfix OTA.
```

## Q6: Apple rejected. Now what?

```
1. Read the rejection in Resolution Center.
2. Identify the guideline (e.g. 3.1.1, 4.8, 5.1.1).
3. Fix the code OR adjust metadata.
4. Reply in Resolution Center explaining the fix.
5. Submit a new build OR re-submit metadata (depending on what changed).

Don't argue. Don't escalate prematurely. Most rejections are real and the fastest path is to address them.
```

## Q7: Hotfix workflow

```
Production has a bug. Steps:

1. Identify if it's JS-only or native.
   ├── JS-only: 
   │   - Fix on a hotfix branch.
   │   - eas update --branch hotfix-<name> --channel preview --message "fix: X"
   │   - Smoke-test on a preview build.
   │   - eas update --branch hotfix-<name> --channel production --message "fix: X"
   │   - Reaches users within minutes (no Apple/Google review).
   │
   └── Native:
       - Fix on a hotfix branch.
       - Bump patch version.
       - Full build + submit pipeline.
       - Apple/Google review: hours to a day.
```

OTA hotfixes are the killer feature of EAS Update. Use them — but ALWAYS preview-channel first. A bad OTA reaches every user instantly.

## Q8: Reverting a bad OTA

```
eas update:rollback --branch <name> --channel production
```

Or republish the previous known-good update. Users on the next app cold-start (or after `expo-updates` checks for updates, which is automatic) receive the rollback within minutes.
