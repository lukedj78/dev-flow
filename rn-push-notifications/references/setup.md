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

Push notifications do NOT work in Expo Go (after SDK 53). You MUST use a development build:

```bash
eas build --profile development --platform ios
eas build --profile development --platform android
```

Install the resulting dev client on the device, then `npx expo start --dev-client`.

## 6. Verify

After running on a real device (simulators can't receive remote pushes):

```ts
import { getExpoPushTokenAsync } from "expo-notifications";

const token = await getExpoPushTokenAsync({ projectId: "your-expo-project-id" });
console.log(token); // → ExponentPushToken[...]
```

Send a test from https://expo.dev/notifications using that token — should arrive within seconds.
