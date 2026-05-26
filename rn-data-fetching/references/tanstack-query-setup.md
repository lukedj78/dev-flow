> Sources: https://tanstack.com/query/v5/docs/framework/react/react-native

# TanStack Query v5 setup for Expo + RN

`rn-bootstrap` already installs `@tanstack/react-query`. This document covers how to wire the provider at the root layout and tune for mobile.

## 1. Provider at the root layout

```tsx
// app/_layout.tsx
import "../global.css";
import { Stack } from "expo-router";
import { QueryClient, QueryClientProvider, focusManager } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { AppState, type AppStateStatus, Platform } from "react-native";
import NetInfo from "@react-native-community/netinfo"; // optional, see "Online manager"
import { onlineManager } from "@tanstack/react-query";

function onAppStateChange(status: AppStateStatus) {
  // Only mobile: web focus events are handled natively.
  if (Platform.OS !== "web") {
    focusManager.setFocused(status === "active");
  }
}

export default function RootLayout() {
  const [client] = useState(() =>
    new QueryClient({
      defaultOptions: {
        queries: {
          retry: 2,
          staleTime: 60_000, // 1 min default
          refetchOnWindowFocus: true,
          refetchOnReconnect: true,
        },
        mutations: {
          retry: 0,
        },
      },
    }),
  );

  useEffect(() => {
    const sub = AppState.addEventListener("change", onAppStateChange);
    return () => sub.remove();
  }, []);

  return (
    <QueryClientProvider client={client}>
      <Stack />
    </QueryClientProvider>
  );
}
```

**Why `useState(() => new QueryClient(...))`**: ensures a single client per app lifecycle, even in Fast Refresh.

## 2. (Optional) Online manager — react to network changes

Install `@react-native-community/netinfo` if you want TanStack Query to know about connectivity. Without it, queries still work but won't pause when offline.

```bash
npx expo install @react-native-community/netinfo -- --legacy-peer-deps
```

Then in the root layout:

```tsx
import NetInfo from "@react-native-community/netinfo";
import { onlineManager } from "@tanstack/react-query";

onlineManager.setEventListener((setOnline) => {
  return NetInfo.addEventListener((state) => {
    setOnline(!!state.isConnected);
  });
});
```

## 3. (Optional) Persistence — cache survives app restart

```bash
npx expo install @tanstack/react-query-persist-client @tanstack/query-async-storage-persister @react-native-async-storage/async-storage -- --legacy-peer-deps
```

Then wrap with `PersistQueryClientProvider` instead of `QueryClientProvider`:

```tsx
import AsyncStorage from "@react-native-async-storage/async-storage";
import { PersistQueryClientProvider } from "@tanstack/react-query-persist-client";
import { createAsyncStoragePersister } from "@tanstack/query-async-storage-persister";

const persister = createAsyncStoragePersister({ storage: AsyncStorage });

<PersistQueryClientProvider client={client} persistOptions={{ persister, maxAge: 1000 * 60 * 60 * 24 }}>
  <Stack />
</PersistQueryClientProvider>
```

`maxAge: 24h` — drop persisted cache older than a day on app start. Tune per app.

## 4. Devtools (Wave 2 — not bundled by default)

Optional but useful in dev. Install `react-query-devtools` and gate behind `__DEV__`. Wave 3 adds an EAS update strategy to ship devtools only to internal builds.

## 5. Verify

In any child component:

```tsx
import { useQuery } from "@tanstack/react-query";

function Test() {
  const { data, isLoading } = useQuery({
    queryKey: ["ping"],
    queryFn: async ({ signal }) => {
      const r = await fetch("https://httpbin.org/get", { signal });
      return r.json();
    },
  });
  return isLoading ? <Text>loading…</Text> : <Text>OK</Text>;
}
```

Open dev tools / React DevTools — the cache should populate.

## Common pitfalls

- **Multiple QueryClient instances** because of Fast Refresh: always wrap in `useState(() => new QueryClient(...))`.
- **Forgot `signal` in queryFn** → cancel on unmount is broken.
- **`refetchOnWindowFocus: true`** without the `AppState` bridge → never refetches on mobile foreground.
- **Persisting sensitive data** (auth tokens) in AsyncStorage → use `expo-secure-store` instead, and store ONLY the token there; let TanStack persist non-sensitive caches.
