> Sources: https://docs.expo.dev/push-notifications/overview/, https://docs.expo.dev/versions/latest/sdk/notifications/

# Setup — expo-notifications

## 1. Install

```bash
npx expo install expo-notifications expo-device -- --legacy-peer-deps
```

## 2. `app.json` — config plugin + iOS/Android permissions

```json
{
  "expo": {
    "plugins": [
      "expo-router",
      [
        "expo-notifications",
        {
          "icon": "./assets/notification-icon.png",
          "color": "#0ea5e9",
          "defaultChannel": "default",
          "sounds": ["./assets/notification.wav"]
        }
      ]
    ],
    "ios": {
      "bundleIdentifier": "com.yourcompany.yourapp",
      "infoPlist": {
        "UIBackgroundModes": ["remote-notification"]
      }
    },
    "android": {
      "package": "com.yourcompany.yourapp",
      "googleServicesFile": "./google-services.json",
      "permissions": ["RECEIVE_BOOT_COMPLETED", "WAKE_LOCK", "VIBRATE"]
    }
  }
}
```

Icon notes:
- Android: a 96×96 transparent PNG (white silhouette on transparent).
- iOS: uses the app icon by default — no separate file needed.
- `color`: hex string for Android notification accent.

## 3. (Android only) FCM setup

Create a Firebase project, add an Android app with your `package` name, download `google-services.json`, place it at the project root. Expo prebuild picks it up automatically.

You do NOT need iOS Firebase setup — Expo's APNs integration is direct.

## 4. (iOS only) APNs credentials in EAS

```bash
eas credentials
```

Then: iOS → production → Push Notifications → Generate (lets EAS handle the APNs key). EAS stores it server-side; you never touch certificate files.

## 5. Development build required

What the Expo docs say, verbatim, **re-read 2026-11-05 — and the sentence has changed**:
*"`expo-notifications` supports both push and local notifications. **You must use a development build
to use push notifications since the capability is not built into Expo Go.** See in-app notifications
on how to create and display a local notification."*
(<https://docs.expo.dev/push-notifications/what-you-need-to-know/> — it moved: the quote is no longer
on `/push-notifications/overview/`, which is now a navigation page.)

✅ **The ambiguity this section warned about is gone, and it resolved the way the warning predicted.**
The 2026-08-26 wording was *"unavailable in Expo Go **on Android** from SDK 53"*, and this file
flagged that reading "so iOS remote push still works in Expo Go" out of that qualifier was **our
inference, not something the page stated**. Expo has since **dropped both the platform qualifier and
the SDK gate**: the statement is now flat and unconditional, for both platforms. So the old caution is
settled rather than merely still advisable — do not plan an iOS-only Expo Go testing path. The
operative advice never changed, and it *is* what the docs state:

```bash
eas build --profile development --platform ios
eas build --profile development --platform android
```

**Local notifications are the exception** — `scheduleNotificationAsync` and friends keep working in
Expo Go, so the reminder/badge half of a feature is testable before you ever cut a build.

Install the resulting dev client on the device, then `npx expo start --dev-client`.

## 6. Verify

After running on a real device (simulators can't receive remote pushes):

```ts
import { getExpoPushTokenAsync } from "expo-notifications";

const token = await getExpoPushTokenAsync({ projectId: "your-expo-project-id" });
console.log(token); // → ExponentPushToken[...]
```

Send a test from https://expo.dev/notifications using that token — should arrive within seconds.
