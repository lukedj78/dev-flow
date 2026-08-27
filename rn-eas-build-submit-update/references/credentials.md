> Sources: https://docs.expo.dev/app-signing/app-credentials/ and https://docs.expo.dev/app-signing/managed-credentials/
> (the bare `/app-signing/` index **404s** — checked 2026-08-26).
> CLI surface verified against **`eas-cli@22.6.0`**. `[VERIFY]` on a CLI major: EAS renames commands
> without breaking them — `secret:*` below survived two renames while still printing results.

# EAS credentials

## TL;DR

EAS stores your signing credentials server-side. You authenticate once with Apple/Google; from then on EAS uses those credentials to sign every build. You never touch a `.p12` file again.

## iOS credentials

What's needed:
- **Distribution certificate** (.p12) — used to sign the build.
- **Provisioning profile** — defines which devices and entitlements the build is allowed.
- **APNs key** (.p8) — used by Expo push service to send notifications.

How to set up (one-time):

```bash
eas credentials
```

Interactive prompt:
1. Pick platform: iOS.
2. Pick profile: production (or preview).
3. Distribution certificate: "Let EAS handle the entire process" → log in with your Apple ID → EAS creates and stores the certificate.
4. Provisioning profile: same.
5. APNs key: same (for push notifications).

Result: credentials stored on the EAS server, encrypted. Every `eas build` uses them automatically. You can rotate via the same command.

## Android credentials

What's needed:
- **Upload keystore** (.jks) — used to sign uploads to the Play Console.
- (Optional) **Google Play service account** (JSON) — for `eas submit` to upload automatically.

How to set up:

```bash
eas credentials
```

1. Platform: Android.
2. Keystore: "Generate new" → EAS creates a keystore + stores it. (Or "Use existing" if you have one.)
3. **Important**: download a backup of the keystore via `eas credentials` → "Download credentials". Store offline. If lost, you cannot publish app updates — Google does not let you re-upload with a different keystore for an existing app.

## Play Console service account (for `eas submit`)

Manual one-time setup (Google does not automate this):

1. Google Cloud Console → IAM & Admin → Service Accounts → Create.
2. Grant "Service Account User" role.
3. Create a JSON key, download it.
4. Google Play Console → Setup → API access → Link the service account → grant "Release Manager".
5. Save the JSON at `<project-root>/google-play-service-account.json` (gitignored).
6. Reference it in `eas.json` under `submit.production.android.serviceAccountKeyPath`.

## Rotating credentials

```bash
eas credentials
```

Pick the credential, choose "Replace" → upload new or generate new. Old credential is invalidated server-side.

## What NEVER to commit

```
.gitignore additions (already in rn-bootstrap):
google-play-service-account.json
google-services.json     ← Firebase config; OK to commit for OSS apps but treat as semi-sensitive
GoogleService-Info.plist ← same
*.p12
*.p8
*.keystore
*.jks
ios/Pods/                ← only if you eject; managed Expo never touches this
```

Note: `google-services.json` / `GoogleService-Info.plist` are CLIENT config files; the keys inside are public-by-design (anon-like). They CAN be committed in OSS projects but, for non-OSS, it's still good hygiene to keep them out of git and inject via EAS Secrets at build time.

## Environment variables at build time — ⚠️ `eas secret:*` is two renames behind

Checked against **`eas-cli@22.6.0`** (2026-08-26), reading the commands' own descriptions. The surface
moved twice and this file never caught up:

| What we used to write | Status at 22.6.0 |
|---|---|
| `eas secret:create` | deprecated → *"Use `eas env:create` instead"* |
| `eas env:create` | **also deprecated** → *"use `eas env:set`"* |
| `eas secret:list` | deprecated → *"Use `eas env:list` instead"* |

So the current form is:

```bash
eas env:set  --scope project --name PROD_API_URL --value https://api.example.com
eas env:list
```

`env:set` is create-or-update in one command, which is why `env:create` and `env:update` were both
folded into it. The rest of the family at 22.6.0: `env:get`, `env:delete`, `env:exec` (run a command
with an environment's variables), and the pair worth knowing — **`env:pull`** (environment → `.env`
file) and **`env:push`** (`.env` file → environment). `eas secret:*` still runs, so nothing breaks
loudly; it just deprecation-warns, which is exactly how a command survives two renames in a doc.

In `eas.json`:

```json
"production": {
  "env": {
    "EXPO_PUBLIC_API_URL": "$PROD_API_URL"
  }
}
```

For runtime env vars (read in the app), use `EXPO_PUBLIC_*` only. Anything else is server-side build-time only and won't reach the bundle.
