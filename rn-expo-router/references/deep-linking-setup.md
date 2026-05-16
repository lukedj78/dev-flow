> Sources: docs.expo.dev/router/reference/redirects, docs.expo.dev/linking/

# Deep linking with Expo Router

Expo Router supports deep links out of the box: every file-route is reachable via a URL. You only need to declare the scheme(s) and verify the domain on iOS/Android.

## 1. Custom scheme (always set this)

`app.json`:
```json
{
  "expo": {
    "scheme": "myapp"
  }
}
```

Now `myapp://profile/abc` opens the app at `/profile/abc`.

## 2. Universal Links (iOS) / App Links (Android)

For HTTPS URLs (`https://myapp.com/profile/abc`):

`app.json`:
```json
{
  "expo": {
    "ios": {
      "associatedDomains": ["applinks:myapp.com"]
    },
    "android": {
      "intentFilters": [
        {
          "action": "VIEW",
          "data": [{ "scheme": "https", "host": "myapp.com" }],
          "category": ["BROWSABLE", "DEFAULT"],
          "autoVerify": true
        }
      ]
    }
  }
}
```

You also need to host:
- iOS: `https://myapp.com/.well-known/apple-app-site-association` (JSON, see Apple docs)
- Android: `https://myapp.com/.well-known/assetlinks.json` (JSON, see Google docs)

## 3. Test it

```bash
# iOS simulator
xcrun simctl openurl booted myapp://profile/abc

# Android emulator
adb shell am start -a android.intent.action.VIEW -d "myapp://profile/abc"
```

## 4. Read the incoming URL programmatically

```tsx
import { useURL } from "expo-linking";

export default function App() {
  const url = useURL(); // null until app opened from link
  // …parse and act, but normally Expo Router handles routing automatically
}
```

## 5. From a push notification

See `rn-push-notifications` (Wave 3) for how to map the notification payload to a deep link.
