> Sources: https://firebase.google.com/docs/auth, https://rnfirebase.io/
> Verified **2026-08-26** against `@react-native-firebase/{app,auth,firestore}@26.3.2` (npm `latest`).
> ⚠️ **None of the `@react-native-firebase/*` packages is in `expo@57`'s `bundledNativeModules.json`**,
> so `npx expo install` gives you npm `latest` for them, not an SDK-blessed pin — unlike
> `expo-secure-store` (`~57.0.1`). Pin them yourself and bump deliberately.
> `[VERIFY]` on a major: this library removed its whole namespaced API in v22.

# Firebase — alternative BaaS

Use Firebase when: existing Google Cloud / Firebase shop, need anonymous auth + phone auth out-of-the-box, NoSQL is fine (Firestore), or already invested in FCM / Analytics.

## 1. Install

For Expo, use `@react-native-firebase/*` packages (not the web `firebase` SDK — the web SDK works but loses native features like background notifications).

```bash
npx expo install @react-native-firebase/app \
  @react-native-firebase/auth \
  @react-native-firebase/firestore \
  expo-build-properties \
  expo-secure-store -- --legacy-peer-deps
```

## 2. Config plugin in `app.json`

```json
{
  "expo": {
    "plugins": [
      "expo-router",
      "@react-native-firebase/app",
      "@react-native-firebase/auth",
      [
        "expo-build-properties",
        { "ios": { "useFrameworks": "static" } }
      ]
    ],
    "ios": {
      "bundleIdentifier": "com.yourcompany.yourapp",
      "googleServicesFile": "./GoogleService-Info.plist"
    },
    "android": {
      "package": "com.yourcompany.yourapp",
      "googleServicesFile": "./google-services.json"
    }
  }
}
```

Add `GoogleService-Info.plist` (iOS) + `google-services.json` (Android) at project root. Get them from the Firebase console.

`@react-native-firebase` requires a development build — does NOT work in Expo Go.

## 3. `lib/firebase.ts`

```ts
import "@react-native-firebase/app"; // initialize on import
```

The native module reads `GoogleService-Info.plist` / `google-services.json` automatically — no JS config needed.

> The old namespaced API (`auth()`, `firestore()`) was deprecated and **removed in v22** (current v26) — use the modular API (`getAuth()`, `getFirestore()`), importing functions directly from each package as shown below.

## 4. `lib/auth.ts`

```ts
import { useMutation, useQueryClient, useQuery } from "@tanstack/react-query";
import { getAuth, signInWithEmailAndPassword, signOut } from "@react-native-firebase/auth";
import { useAuthStore } from "@/store/auth";

export function useSignIn() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ email, password }: { email: string; password: string }) => {
      const result = await signInWithEmailAndPassword(getAuth(), email, password);
      const user = result.user;
      useAuthStore.getState().setUser({ id: user.uid, email: user.email! });
      return user;
    },
    onSuccess: () => qc.invalidateQueries(),
  });
}

export function useSignOut() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      await signOut(getAuth());
      useAuthStore.getState().setUser(null);
      qc.clear();
    },
  });
}
```

Firebase tokens are stored automatically by the native SDK in Keychain/Keystore — no custom secure-store wrapper needed.

## 5. `app/_layout.tsx` — onAuthStateChanged subscription

```tsx
import { useEffect } from "react";
import { getAuth, onAuthStateChanged } from "@react-native-firebase/auth";
import { useAuthStore } from "@/store/auth";

// inside RootLayout
useEffect(() => {
  const unsubscribe = onAuthStateChanged(getAuth(), (user) => {
    if (user) {
      useAuthStore.getState().setUser({ id: user.uid, email: user.email! });
    } else {
      useAuthStore.getState().setUser(null);
    }
  });
  return unsubscribe;
}, []);
```

## 6. Firestore queries

```ts
// lib/queries/usePosts.ts
import { useQuery } from "@tanstack/react-query";
import { getFirestore, collection, query, orderBy, limit, getDocs } from "@react-native-firebase/firestore";

export function usePosts() {
  return useQuery({
    queryKey: ["posts", "list"],
    queryFn: async () => {
      const snapshot = await getDocs(
        query(
          collection(getFirestore(), "posts"),
          orderBy("createdAt", "desc"),
          limit(50),
        ),
      );
      return snapshot.docs.map((d) => ({ id: d.id, ...d.data() }));
    },
  });
}
```

## 7. Security rules

Firestore rules in `firestore.rules`:

```
rules_version = '2';
service cloud.firestore {
  match /databases/{db}/documents {
    match /posts/{postId} {
      allow read: if true;
      allow create: if request.auth != null;
      allow update, delete: if request.auth != null && request.auth.uid == resource.data.authorId;
    }
  }
}
```

Deploy via Firebase CLI: `firebase deploy --only firestore:rules`.

## 8. Realtime — `onSnapshot`

⚠️ **This snippet used to use the namespaced chain this very file says was removed in v22** —
`firestore().collection().orderBy().onSnapshot()`. Corrected to the modular form, verified against
`@react-native-firebase/firestore@26.3.2` (`lib/modular/snapshot.d.ts`, which declares eight
`onSnapshot` overloads — `(query, onNext, onError?, onCompletion?)` is the one below, and there are
`DocumentReference` and `SnapshotListenOptions` variants alongside it):

```ts
import { getFirestore, collection, query, orderBy, onSnapshot } from "@react-native-firebase/firestore";

useEffect(() => {
  const unsubscribe = onSnapshot(
    query(collection(getFirestore(), "posts"), orderBy("createdAt", "desc")),
    (snapshot) => {
      queryClient.setQueryData(
        ["posts", "list"],
        snapshot.docs.map((d) => ({ id: d.id, ...d.data() })),
      );
    },
  );
  return unsubscribe;               // onSnapshot returns Unsubscribe
}, []);
```

## Gotchas vs Supabase

- **Vendor lock-in**: Firestore data model + rules are Firebase-specific. Migrating away is significant work.
- **No SQL**: Firestore is NoSQL. Aggregations + joins are awkward.
- **Pricing**: read-heavy apps surprise on the bill (per-read charge). Cache aggressively.
- **Expo Go incompatible**: must use a development build from day one.
- **Sign in with Apple**: requires `@react-native-firebase/auth` + `expo-apple-authentication`. Two-step setup.
- **No Postgres**: if you need joins / RLS-style policies / SQL skills, Supabase is a better fit.
