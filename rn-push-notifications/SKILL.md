---
name: rn-push-notifications
description: 'Use when adding push or local notifications to an Expo + RN app: requesting permissions at the right moment, registering for push (Expo push service in dev, APNs/FCM direct in prod), handling foreground + tapped + cold-start notifications, deep linking from a notification payload to a specific route, scheduling local notifications, badge management. Triggers on: "add push notifications", "local notification", "deep link from notification", "iOS/Android push setup", "register for notifications". Not for: backend setup that sends the notifications (rn-backend), animations on a notification badge (rn-animations-gestures).'
---

# rn-push-notifications — guardrail for push + local notifications

> For the current Expo API and per-version details, verify against the Expo docs / MCP `mcp.expo.dev` / `expo/skills` (see rn-fundamentals → Source of truth).

## The 5 rules (non-negotiable)

1. **`expo-notifications` is the SDK**. Don't pull `@react-native-firebase/messaging` directly — Expo wraps APNs+FCM. Bare FCM is needed only for the rare case where you ship without Expo.
2. **Request permission AT THE RIGHT MOMENT**, not at app launch. Wait for a clear opt-in trigger (signup complete, settings screen, feature first use).
3. **Setup `setNotificationHandler` at module level** in `app/_layout.tsx`, ONCE. Not inside any component.
4. **Handle the 3 entry paths**: foreground (`addNotificationReceivedListener`), tapped while alive (`addNotificationResponseReceivedListener`), tapped on cold start (`getLastNotificationResponseAsync`).
5. **Token storage**: send the Expo push token to YOUR backend via authenticated HTTPS POST. Never store the raw token in AsyncStorage — use `expo-secure-store` or treat it as server-owned.

## Quick decision tree

- "Expo push service or direct APNs/FCM?" → `references/decision-tree.md`
- "How do I wire up the handlers + deep linking?" → `references/patterns.md`
- "What's the app.json / config plugin setup?" → `references/setup.md`

## Common anti-patterns (NEVER do)

- ❌ `Notifications.requestPermissionsAsync()` in `app/_layout.tsx` on first render — bad UX (denied permanently if user says no by mistake).
- ❌ `setNotificationHandler` inside a screen component — runs on every mount, last one wins.
- ❌ Sending the Expo push token over plain HTTP — token = ability to spam the user.
- ❌ Reading `notification.request.content.data` without type-narrowing — runtime error on malformed payload.
- ❌ Forgetting `getLastNotificationResponseAsync` on cold start — deep link from tapped notification gets lost.
- ❌ Storing badge count in client state only — server is source of truth; client subtracts on read.

## Sources

- Course: codewithbeto.dev/rnCourse — "Push Notifications" module (1 lesson free, rest paid).
- Official: https://docs.expo.dev/push-notifications/overview/
- Official: https://docs.expo.dev/versions/latest/sdk/notifications/
