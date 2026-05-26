> Sources: synthesized from rn-data-fetching patterns + auth best practices.

# Patterns — provider-agnostic client-auth architecture

These four pieces compose into the full auth flow. Each is provider-independent — provider files (`supabase.md`, `firebase.md`, etc.) plug into the same skeleton.

## 1. Secure token store (`lib/token-store.ts`)

```ts
import * as SecureStore from "expo-secure-store";

const ACCESS_KEY = "auth.access_token";
const REFRESH_KEY = "auth.refresh_token";

export const tokenStore = {
  async save(access: string, refresh: string) {
    await SecureStore.setItemAsync(ACCESS_KEY, access);
    await SecureStore.setItemAsync(REFRESH_KEY, refresh);
  },
  async read(): Promise<{ access: string; refresh: string } | null> {
    const access = await SecureStore.getItemAsync(ACCESS_KEY);
    const refresh = await SecureStore.getItemAsync(REFRESH_KEY);
    if (!access || !refresh) return null;
    return { access, refresh };
  },
  async clear() {
    await SecureStore.deleteItemAsync(ACCESS_KEY);
    await SecureStore.deleteItemAsync(REFRESH_KEY);
  },
};
```

## 2. Zustand auth store (`store/auth.ts`)

```ts
import { create } from "zustand";
import { tokenStore } from "@/lib/token-store";

type User = { id: string; email: string; name?: string };

type AuthState = {
  accessToken: string | null;
  refreshToken: string | null;
  user: User | null;
  hydrated: boolean;
  setTokens: (access: string, refresh: string) => Promise<void>;
  setUser: (u: User | null) => void;
  hydrate: () => Promise<void>;
  signOut: () => Promise<void>;
};

export const useAuthStore = create<AuthState>((set, get) => ({
  accessToken: null,
  refreshToken: null,
  user: null,
  hydrated: false,

  setTokens: async (access, refresh) => {
    await tokenStore.save(access, refresh);
    set({ accessToken: access, refreshToken: refresh });
  },

  setUser: (user) => set({ user }),

  hydrate: async () => {
    const tokens = await tokenStore.read();
    if (tokens) set({ accessToken: tokens.access, refreshToken: tokens.refresh });
    set({ hydrated: true });
  },

  signOut: async () => {
    await tokenStore.clear();
    set({ accessToken: null, refreshToken: null, user: null });
  },
}));
```

Call `useAuthStore.getState().hydrate()` once at app start (in `app/_layout.tsx`).

## 3. `api()` wrapper with refresh-on-401 (`lib/api.ts`)

```ts
import { useAuthStore } from "@/store/auth";

const BASE_URL = process.env.EXPO_PUBLIC_API_URL!;

let refreshPromise: Promise<void> | null = null; // single-flight refresh

async function refreshTokens(): Promise<void> {
  if (refreshPromise) return refreshPromise;
  refreshPromise = (async () => {
    const refresh = useAuthStore.getState().refreshToken;
    if (!refresh) throw new Error("no refresh token");
    const r = await fetch(`${BASE_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refreshToken: refresh }),
    });
    if (!r.ok) throw new Error("refresh failed");
    const { accessToken, refreshToken } = await r.json();
    await useAuthStore.getState().setTokens(accessToken, refreshToken);
  })().finally(() => {
    refreshPromise = null;
  });
  return refreshPromise;
}

export async function api<T>(
  path: string,
  init: RequestInit & { signal?: AbortSignal; auth?: boolean } = {},
): Promise<T> {
  const { auth = true, signal, ...rest } = init;
  const doFetch = async (): Promise<Response> => {
    const headers = new Headers(rest.headers);
    headers.set("Content-Type", "application/json");
    if (auth) {
      const token = useAuthStore.getState().accessToken;
      if (token) headers.set("Authorization", `Bearer ${token}`);
    }
    return fetch(`${BASE_URL}${path}`, { ...rest, headers, signal });
  };

  let r = await doFetch();

  // Refresh-on-401 dance
  if (r.status === 401 && auth) {
    try {
      await refreshTokens();
      r = await doFetch(); // retry once
    } catch {
      await useAuthStore.getState().signOut();
      throw new ApiError(401, "session expired");
    }
  }

  if (!r.ok) {
    const body = await r.text();
    throw new ApiError(r.status, body);
  }
  return r.json() as Promise<T>;
}

export class ApiError extends Error {
  constructor(public status: number, public body: string) {
    super(`API ${status}: ${body}`);
  }
}
```

## 4. Root layout — hydrate + handle splash

```tsx
// app/_layout.tsx
import { Stack } from "expo-router";
import { useEffect, useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth";
import "../global.css";

export default function RootLayout() {
  const [client] = useState(() => new QueryClient({ /* defaults */ }));
  const hydrate = useAuthStore((s) => s.hydrate);
  const hydrated = useAuthStore((s) => s.hydrated);

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  if (!hydrated) return null; // splash screen

  return (
    <QueryClientProvider client={client}>
      <Stack>
        <Stack.Screen name="(auth)" options={{ headerShown: false }} />
        <Stack.Screen name="(app)" options={{ headerShown: false }} />
      </Stack>
    </QueryClientProvider>
  );
}
```

## 5. Auth gate

```tsx
// app/(app)/_layout.tsx
import { Redirect, Stack } from "expo-router";
import { useAuthStore } from "@/store/auth";

export default function ProtectedLayout() {
  const accessToken = useAuthStore((s) => s.accessToken);
  if (!accessToken) return <Redirect href="/(auth)/sign-in" />;
  return <Stack />;
}
```

## 6. Sign-in / sign-out hooks

```ts
// lib/auth.ts
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "./api";
import { useAuthStore } from "@/store/auth";

export function useSignIn() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ email, password }: { email: string; password: string }) => {
      const r = await api<{
        accessToken: string;
        refreshToken: string;
        user: { id: string; email: string; name?: string };
      }>("/auth/sign-in", {
        method: "POST",
        body: JSON.stringify({ email, password }),
        auth: false, // don't attach a token to sign-in itself
      });
      await useAuthStore.getState().setTokens(r.accessToken, r.refreshToken);
      useAuthStore.getState().setUser(r.user);
      return r.user;
    },
    onSuccess: () => qc.invalidateQueries(),
  });
}

export function useSignOut() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      // Optional: tell server to invalidate the refresh token
      try {
        await api("/auth/sign-out", { method: "POST" });
      } catch {
        // ignore — local sign-out should always succeed
      }
      await useAuthStore.getState().signOut();
      qc.clear(); // critical: prevent leak of previous-user data
    },
  });
}
```

## DON'T

- ❌ Refresh logic per-screen (let `api()` own it).
- ❌ Sign-out without `qc.clear()` (cache leak).
- ❌ Hydrate the store from `useEffect` in a child component (race with `(app)/_layout.tsx` redirect).
- ❌ Read tokens from `SecureStore` on every request (slow + does not refresh).
- ❌ Treat the access token as a database lookup key (it's a credential; the user id is in the JWT claims or `/me`).
