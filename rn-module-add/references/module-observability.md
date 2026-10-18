# rn-module-add → `observability` (crash and error reporting for Expo)

`rn-eas-deploy` used to tell you to watch crashes on "Sentry / Bugsnag dashboard (if configured)", but no skill
configured it. EAS Observe measures slowness, not crashes: Expo lists crash tracking as a planned addition. This
module wires the crash reporter, with the same rules as the web module (`module-add/references/module-observability.md`):
- the region follows `stack.data_residency`;
- nothing personal is sent;
- every event carries its release;
- there is a proof before any account exists.

Versions were checked on 2026-10-18: `@sentry/react-native` 8.31.0 (MIT, peer `expo >=49`).

## Before anything

- **Provider by region**, the same table as the web: with `eu`, the Sentry organization in Frankfurt
  (`*.ingest.de.sentry.io`); with `eu-sovereign`, GlitchTip; with `none`, either.
- **The account is created by the user.** The DSN goes in `EXPO_PUBLIC_SENTRY_DSN`; a DSN is not a secret, it only
  allows sending events. `SENTRY_AUTH_TOKEN` (for source maps) goes in EAS secrets, never in chat or in the repo.
- **Register the provider** with `dev-flow/scripts/data_residency.py add`. The store privacy labels must declare
  crash data (`rn-publishing-payments/references/review-guidelines.md`).

## Install

```bash
npx expo install @sentry/react-native
```

**`app.json` / `app.config.ts`:** add the config plugin, so that EAS builds upload the source maps and the debug
symbols:

```json
{ "expo": { "plugins": [["@sentry/react-native/expo", {
  "organization": "<org>", "project": "<project>", "url": "https://de.sentry.io/"
}]] } }
```

`url` is the EU organization's API host. Omit it for a US organization; for GlitchTip, use the GlitchTip host. Check
the option against the plugin's docs on the first real install.

**`metro.config.js`:** `const { getSentryExpoConfig } = require("@sentry/react-native/metro")`, so that bundles keep
debug ids for symbolication.

**`app/_layout.tsx`:**

```tsx
import * as Sentry from "@sentry/react-native"
import * as Updates from "expo-updates"

Sentry.init({
  dsn: process.env.EXPO_PUBLIC_SENTRY_DSN,
  release: Updates.updateId ?? Updates.runtimeVersion ?? undefined,   // an OTA update is its own release
  environment: Updates.channel ?? "development",
  sendDefaultPii: false,
  beforeSend: (event) => { if (event.user) event.user = { id: event.user.id }; return event },
})

export default Sentry.wrap(RootLayout)
```

- No `mobileReplayIntegration`: replay stays off (privacy).
- Expo 58's `ObserveErrorBoundary` stays for EAS Observe, which measures performance: the two do different jobs.

## The proof, without an account

Point `EXPO_PUBLIC_SENTRY_DSN` at the local fake ingest. A simulator reaches the Mac's localhost directly:

```bash
python3 <skills>/module-add/scripts/fake_ingest.py serve --port 9010 --out .verification/ingest &
EXPO_PUBLIC_SENTRY_DSN=http://public@127.0.0.1:9010/1 npx expo start
# throw from a button in a dev build, then:
python3 <skills>/module-add/scripts/fake_ingest.py summary .verification/ingest
```

Expected:
- one or more events, with the release;
- `"emails": false`.

A crash of native code needs a real build to be symbolicated: that part is proven with the user's account.

## Record

- `meta.json#stack.observability`: `["errors"]`.
- `stack.observability_provider`: `{ "errors": "sentry" | "glitchtip" }`.
- A history entry. Never `phase`.
