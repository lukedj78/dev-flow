> Sources: docs.expo.dev/push-notifications, internal opinion.

# Decision tree — push notifications

## Q1: Expo push service or direct APNs/FCM?

```
What's the scale + maturity?
├── Dev / small / single backend                  → Expo push service (api.expo.dev)
│                                                   - One token format works on iOS + Android
│                                                   - Server sends to https://exp.host/--/api/v2/push/send
│                                                   - Free, rate-limited but generous
├── Production at scale (>100k devices/day)       → Direct APNs (iOS) + FCM (Android)
│                                                   - More work server-side
│                                                   - More control over delivery, batching, scheduling
└── Already invested in FCM (cross-platform web)  → FCM end-to-end (still wraps via expo-notifications client)
```

**Default: Expo push service.** Switch to direct APNs/FCM only when you hit Expo's rate limits OR need delivery analytics.

## Q2: Local or remote notification?

```
What triggers the notification?
├── Server event (new message, payment received)  → remote (push)
├── User action with time delay (reminder)        → local (scheduleNotificationAsync)
├── Geo-fence / location enter                    → local + expo-location (out of scope, separate skill)
└── Time-of-day (daily summary)                   → local with weekly/daily trigger
```

Local notifications work offline and don't need a backend.

## Q3: When to ask for permission?

```
Stage of the user's journey?
├── First app launch                              → NEVER. User has zero context.
├── Right after signup                             → MAYBE — only if notifications are the core value.
├── First time using a feature that needs push    → YES. Show a pre-prompt explaining why.
├── Settings screen, explicit toggle               → YES. User chose to enable.
└── User declined → re-prompt strategy            → Linking.openSettings() (deep link to OS settings)
```

The pre-prompt pattern:
1. Show a custom modal: "Want a heads-up when a new message arrives?" with Yes/No buttons.
2. If user clicks Yes, THEN call `requestPermissionsAsync()`.
3. If user clicks No, store "asked, denied" — don't ask again for at least 30 days.

This avoids the OS-level permission dialog being denied permanently (which is irreversible without OS settings).

## Q4: Where in the code does push-handling live?

```
Concern             → File
-----------------------------------------------------------------
setNotificationHandler at module scope → app/_layout.tsx (top of file)
useEffect listeners                     → app/_layout.tsx (in RootLayout)
Permission request                      → triggered from settings/onboarding, lives in lib/push.ts
Token upload                            → lib/push.ts → uses lib/api.ts
Channel setup (Android)                 → lib/push.ts in registerForPushAsync
Payload-to-route mapping                → app/_layout.tsx handlePayload(), or extract to lib/push-routing.ts
```

## Q5: What does the payload look like?

```
Recommended payload schema (your server emits):

{
  "to": "ExponentPushToken[...]",
  "title": "Mario commented your post",
  "body": "Great write-up!",
  "data": {
    "type": "post",
    "postId": "abc123",
    "deepLink": "myapp://posts/abc123"
  },
  "badge": 3,
  "sound": "default",
  "priority": "high"
}
```

Always include a `type` in `data` — let the client switch on it. The `deepLink` field is redundant if your `type` + ids are enough; include only if you want server-side flexibility.

## Q6: Should I rely on push for critical state sync?

```
NEVER use push as the source of truth.

Notifications are unreliable: OS may suppress, delay, batch, or drop them.
Always re-fetch state from your backend when the app foregrounds (TanStack Query
refetchOnWindowFocus + AppState bridge — see rn-data-fetching).

Push = "hey, something changed, check the server".
NOT = "here's the new state, trust it".
```
