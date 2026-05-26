> Sources: vendor docs, internal opinion.

# Decision tree — which backend?

## Q1: Do you already have a backend?

```
├── YES, I want to keep my Node/Rails/Django/etc. + Postgres/MySQL/MongoDB
│   → custom REST/JSON → references/custom-rest.md
│   → if you want end-to-end typed and it's Node → tRPC → references/trpc.md
│
└── NO, I need everything (auth + db + storage)
    → BaaS — see Q2
```

## Q2: BaaS choice — Supabase or Firebase?

```
What matters most?
├── Postgres + SQL skills already on the team        → Supabase
├── Open-source / self-host option preserved          → Supabase
├── RLS-style fine-grained policies                  → Supabase
├── Realtime over Postgres LISTEN/NOTIFY              → Supabase
├── Excellent web admin to query data                 → Supabase
│
├── Existing Google Cloud / Firebase shop             → Firebase
├── Battle-tested at enormous scale                   → Firebase
├── Already using FCM, GCP Storage, Analytics         → Firebase
├── NoSQL is fine                                     → Firebase (Firestore)
└── Anonymous auth + phone auth + many providers OOTB → Firebase
```

**Our default: Supabase** (matches the course, simpler SQL story, more portable). Pick Firebase if you have a strong existing reason.

## Q3: How do you write to the database?

```
Provider's RLS pattern (Supabase, Firestore rules)?
├── YES → client writes directly. Server only enforces policies.
│        Tradeoff: less server code, complex policies.
└── NO  → write via your API endpoints. Server validates + persists.
         Tradeoff: more code, easier to test + audit.
```

Hybrid is also fine — write via API for mutations, read directly via RLS for fast queries.

## Q4: Auth providers — which to enable?

```
Always:
- Email + password
- "Sign in with Apple" (REQUIRED by App Store guideline 4.8 if you offer any other 3rd party auth)

Common to enable:
- Magic link (passwordless email)
- Google
- Apple
- (Optionally) GitHub / Twitter / etc.

Skip until you actually need:
- Phone OTP (paid SMS in most providers)
- Enterprise SSO (SAML / OIDC)
```

Apple's rule: if you offer Google/Facebook/etc., you MUST also offer Sign in with Apple. iOS-only rule, but you must respect it to ship to the App Store.

## Q5: Where does provider-specific code live?

```
Goal: keep the rest of the app provider-agnostic.

lib/
├── api.ts          ← provider-aware wrapper. ONE place that knows about Supabase / Firebase / etc.
├── auth.ts         ← signIn / signOut hooks. Calls lib/api.ts. Returns generic User type.
├── token-store.ts  ← secure-store wrapper. Provider-agnostic.
└── queries/        ← TanStack Query hooks. Use api.ts; don't import supabase/firebase directly.

store/
└── auth.ts         ← Zustand store. Provider-agnostic.
```

Swapping providers = rewriting `lib/api.ts` + `lib/auth.ts`. Nothing else.

## Q6: Token strategy

```
Provider's SDK handles token storage automatically (Supabase, Firebase)?
├── YES → you can SKIP custom token-store.ts. Use the SDK's session helpers
│        (supabase.auth.getSession() / firebase.auth().currentUser).
│        BUT: configure the SDK to use expo-secure-store as backend, not its
│        default AsyncStorage. See provider sub-references.
└── NO (custom REST) → implement token-store.ts yourself + refresh-on-401 in api().
```

## Q7: Realtime — do I need it Wave 3, or later?

```
Use case for realtime?
├── Chat / live cursors / multi-player          → YES, set up early
├── Notification badge counter sync             → MAYBE — push notifications often enough
├── Form collaboration                          → YES
├── Read-only dashboards                        → NO, polling or refetch-on-focus is fine
└── Anything where one user's action changes
   another user's UI within < 5 seconds         → YES
```

Realtime adds significant complexity (subscription lifecycle, presence, edge cases). Skip until you have a concrete use case.
