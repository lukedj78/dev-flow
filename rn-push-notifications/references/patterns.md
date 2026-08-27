> Sources: https://docs.expo.dev/push-notifications/receiving-notifications/, internal opinion.
> API surface verified against **`expo-notifications@57.0.15`** (the version `expo@57.0.16` pins is
> `~57.0.14`) on 2026-08-26: all thirteen `Notifications.*` calls this skill uses exist, and the
> handler shape below is the current one. `[VERIFY]` on an SDK major — this package changes shapes,
> not just names: `shouldShowAlert` is now `@deprecated` in favour of the
> `shouldShowBanner`/`shouldShowList` pair, and a handler written before that split still typechecks
> while showing nothing.

# Patterns — receiving + handling push notifications

## Module-level setup (in `app/_layout.tsx`)

```tsx
// app/_layout.tsx
import * as Notifications from "expo-notifications";
import { Stack } from "expo-router";
import "../global.css";

// MUST be at module scope, runs ONCE.
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowBanner: true,
    shouldShowList: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
  }),
});

export default function RootLayout() {
  return <Stack />;
}
```

## Register for push — only when the user opts in

```tsx
// lib/push.ts
import * as Notifications from "expo-notifications";
import * as Device from "expo-device";
import { Platform } from "react-native";

const EXPO_PROJECT_ID = process.env.EXPO_PUBLIC_EXPO_PROJECT_ID!;

export async function registerForPushAsync(): Promise<string | null> {
  if (!Device.isDevice) {
    console.warn("[push] simulator/emulator cannot receive push notifications");
    return null;
  }

  // Android requires a channel before notifications can show
  if (Platform.OS === "android") {
    await Notifications.setNotificationChannelAsync("default", {
      name: "Default",
      importance: Notifications.AndroidImportance.DEFAULT,
      vibrationPattern: [0, 250, 250, 250],
      lightColor: "#0ea5e9",
    });
  }

  const settings = await Notifications.getPermissionsAsync();
  let status = settings.status;
  if (status !== "granted") {
    const req = await Notifications.requestPermissionsAsync();
    status = req.status;
  }
  if (status !== "granted") return null;

  const token = await Notifications.getExpoPushTokenAsync({ projectId: EXPO_PROJECT_ID });
  return token.data; // e.g. "ExponentPushToken[xxxxxxxx]"
}
```

Call `registerForPushAsync()` from a clear opt-in trigger: a "Turn on notifications" button in settings, after first signup, or when a feature that needs them is enabled.

## Send the token to your backend (authenticated)

```ts
import { api } from "@/lib/api"; // see rn-data-fetching patterns

export async function uploadPushToken(token: string) {
  await api("/users/me/push-token", {
    method: "POST",
    body: JSON.stringify({ token, platform: Platform.OS }),
  });
}
```

Backend stores `{ userId, token, platform }`. Replace the token if it changes (Expo rotates).

## Handle the 3 entry paths

```tsx
// app/_layout.tsx (inside RootLayout)
import { useEffect } from "react";
import * as Notifications from "expo-notifications";
import { useRouter } from "expo-router";

type NotificationPayload =
  | { type: "post"; postId: string }
  | { type: "chat"; conversationId: string }
  | { type: "generic" };

function handlePayload(payload: unknown, router: ReturnType<typeof useRouter>) {
  const p = payload as NotificationPayload;
  if (!p || !p.type) return;
  switch (p.type) {
    case "post":
      router.push({ pathname: "/posts/[id]", params: { id: p.postId } });
      break;
    case "chat":
      router.push({ pathname: "/chats/[id]", params: { id: p.conversationId } });
      break;
  }
}

export default function RootLayout() {
  const router = useRouter();

  useEffect(() => {
    // Cold start: notification tapped while app was killed
    Notifications.getLastNotificationResponseAsync().then((response) => {
      if (response) handlePayload(response.notification.request.content.data, router);
    });

    // Tapped while app is alive (foreground or background)
    const tapSub = Notifications.addNotificationResponseReceivedListener((response) => {
      handlePayload(response.notification.request.content.data, router);
    });

    // Foreground: notification arrived while user is in the app
    const fgSub = Notifications.addNotificationReceivedListener((_notification) => {
      // Optional: invalidate a TanStack Query, show an in-app banner, etc.
    });

    return () => {
      tapSub.remove();
      fgSub.remove();
    };
  }, [router]);

  return <Stack />;
}
```

## Local notification (no server needed)

```ts
import * as Notifications from "expo-notifications";

await Notifications.scheduleNotificationAsync({
  content: {
    title: "Promemoria",
    body: "Hai un'attività da completare",
    data: { type: "reminder", taskId: "123" },
  },
  trigger: { type: Notifications.SchedulableTriggerInputTypes.DATE, date: new Date(Date.now() + 60_000) },
});
```

## Badge management

```ts
import * as Notifications from "expo-notifications";

await Notifications.setBadgeCountAsync(3);  // set
const count = await Notifications.getBadgeCountAsync();
await Notifications.setBadgeCountAsync(0);  // clear (e.g. on app open)
```

Pattern: set badge from server in the push payload (`badge` field). On app foreground, clear or refresh from server-truth.

## DON'T

- ❌ Hardcode the Expo project ID — use `process.env.EXPO_PUBLIC_EXPO_PROJECT_ID`.
- ❌ Use `console.log(token)` and never delete the line — accidental leak in dev tools.
- ❌ Re-register the token on every app launch — only if it's missing on the server or rotated. Compare client cache to server state.
- ❌ Skip `Device.isDevice` check — token request on iOS Sim throws an opaque error.

## FCM topics — broadcast without storing tokens (Android only)

`expo-notifications` also exposes `subscribeToTopicAsync(topic)` / `unsubscribeFromTopicAsync(topic)`,
which let a device receive a broadcast without your backend keeping its token at all — the fan-out
happens at FCM.

⚠️ **Both are `@platform android`.** On iOS they are not available, so a "subscribe everyone to
`news`" design silently covers half your users. Use them as an *optimisation* on Android for genuinely
broadcast content, never as the primary delivery path — and keep the token-per-device path as the one
that actually defines who gets what.
