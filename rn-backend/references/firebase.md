> Sources: https://firebase.google.com/docs/auth, https://rnfirebase.io/

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
import "@react-native-firebase/app";        // initialize on import
import auth from "@react-native-firebase/auth";
import firestore from "@react-native-firebase/firestore";

export { auth, firestore };
```

The native module reads `GoogleService-Info.plist` / `google-services.json` automatically — no JS config needed.

## 4. `lib/auth.ts`

```ts
import { useMutation, useQueryClient, useQuery } from "@tanstack/react-query";
import { auth } from "./firebase";
import { useAuthStore } from "@/store/auth";

export function useSignIn() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ email, password }: { email: string; password: string }) => {
      const result = await auth().signInWithEmailAndPassword(email, password);
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
      await auth().signOut();
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
import { auth } from "@/lib/firebase";
import { useAuthStore } from "@/store/auth";

// inside RootLayout
useEffect(() => {
  const unsubscribe = auth().onAuthStateChanged((user) => {
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
import { firestore } from "@/lib/firebase";

export function usePosts() {
  return useQuery({
    queryKey: ["posts", "list"],
    queryFn: async () => {
      const snapshot = await firestore()
        .collection("posts")
        .orderBy("createdAt", "desc")
        .limit(50)
        .get();
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

```ts
useEffect(() => {
  const unsubscribe = firestore()
    .collection("posts")
    .orderBy("createdAt", "desc")
    .onSnapshot((snapshot) => {
      queryClient.setQueryData(
        ["posts", "list"],
        snapshot.docs.map((d) => ({ id: d.id, ...d.data() })),
      );
    });
  return unsubscribe;
}, []);
```

## Gotchas vs Supabase

- **Vendor lock-in**: Firestore data model + rules are Firebase-specific. Migrating away is significant work.
- **No SQL**: Firestore is NoSQL. Aggregations + joins are awkward.
- **Pricing**: read-heavy apps surprise on the bill (per-read charge). Cache aggressively.
- **Expo Go incompatible**: must use a development build from day one.
- **Sign in with Apple**: requires `@react-native-firebase/auth` + `expo-apple-authentication`. Two-step setup.
- **No Postgres**: if you need joins / RLS-style policies / SQL skills, Supabase is a better fit.
