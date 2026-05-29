> Sources: synthesized from provider-specific decision trees in rn-backend, rn-push-notifications, rn-publishing-payments.

# Decision tree — module-add

## Q1: Which module first?

```
A new app's typical order:
1. auth      ← first. Most of the app gates behind this.
2. db        ← second (often same provider, automatic if Supabase/Firebase).
3. storage   ← when user uploads (avatar, photo, file).
4. push      ← when first notification feature.
5. realtime  ← when first "live" feature.
6. payments  ← later, after retention is proven.
```

You can skip any of these. Adding later is fine — `rn-module-add` is idempotent and incremental.

## Q2: Provider choice — same across modules?

```
For BaaS (Supabase, Firebase): YES — one provider covers auth + db + storage + realtime.
For Custom REST / tRPC: PARTIAL — auth + db + storage all hit your own server. Push and payments are separate (Expo/RevenueCat).
```

Mixing is allowed but adds friction. Example mix that works: custom REST for everything + RevenueCat for payments + expo-notifications + your own server for push send.

## Q3: I picked Firebase. Do I need to do anything special?

```
YES:
- Firebase requires a development build (not Expo Go) from Day 1.
- The first rn-module-add for any Firebase module will print a reminder: rebuild required.
- Set up GoogleService-Info.plist (iOS) and google-services.json (Android) BEFORE running rn-module-add — the skill can't generate these.
```

## Q4: Auth provider already wired. Now I want to add `db` from the SAME provider — what happens?

```
rn-module-add detects:
  meta.json#stack.auth = "supabase"
  (you asked for db with default provider)

Behavior:
- The `lib/supabase.ts` client is already there (from auth).
- The skill ONLY adds `lib/queries/` templates and sets `stack.db = "supabase"`.
- No duplicate install, no duplicate file.
- Phase remains "module_added".
```

## Q5: What if I want to SWAP a provider mid-project?

```
rn-module-add will REFUSE by default to prevent accidental destruction.

To intentionally swap (e.g. auth from Supabase to Firebase):
1. Read the migration cost. Files affected: lib/supabase.ts, lib/auth.ts, every place that imports them.
2. Make a backup branch.
3. Manually remove the old wiring (delete files, uninstall deps).
4. Set meta.json#stack.auth = null.
5. Run rn-module-add for the new provider.

This is a multi-day operation. The skill doesn't automate it — the migration is too risky to script blindly.
```

## Q6: payments — RevenueCat or Stripe?

```
Digital good in the app?
└── RevenueCat. (Apple requires IAP — RevenueCat wraps StoreKit/Play Billing.)

Non-digital good (shipped item, real-world service)?
└── Stripe via WebView, or external link if regional rules allow.

See rn-publishing-payments/references/decision-tree.md for the full reasoning.
```

## Q7: I want push notifications but my backend isn't ready yet. What now?

```
rn-module-add push installs the client-side (permissions + token retrieval).
Run it now; you can test local notifications immediately.

The server-side (sending push from your backend) is a separate concern:
- For dev/test: use https://expo.dev/notifications to send manually with a token.
- For production: implement a /users/me/push-token POST endpoint on your backend, then have the backend POST to https://exp.host/--/api/v2/push/send when needed.

Defer the server-side implementation. The client-side stays the same.
```

## Q8: How do I know which modules are wired in this project?

```
Read meta.json#stack:

{
  "framework": "expo-rn",
  "ui": "nativewind",
  "auth": "supabase",       ← wired
  "db": "supabase",         ← wired
  "storage": null,           ← not wired
  "realtime": null,
  "push": "expo-notifications",
  "payments": null,
  "deploy": null
}
```

Anything that's `null` is not wired. `rn-module-add` reads this to decide idempotency.
