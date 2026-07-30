> Sources: https://supabase.com/docs/reference/javascript/, internal opinion.

# Supabase — the default provider

Supabase is the default for this skill set. It matches the course (codewithbeto.dev), provides Postgres + Auth + Storage + Realtime + Edge Functions in one managed BaaS, and the JS SDK handles tokens for us (including secure-store integration on RN).

## 1. Install

```bash
npx expo install @supabase/supabase-js @react-native-async-storage/async-storage \
  expo-secure-store -- --legacy-peer-deps
```

(`@supabase/supabase-js` uses AsyncStorage for the session — see step 3.)

## 2. `.env.example` additions

```
EXPO_PUBLIC_SUPABASE_URL=
EXPO_PUBLIC_SUPABASE_ANON_KEY=
```

The anon key is NOT secret — it's published in the client. RLS policies are what protect data, not the key.

## 3. `lib/supabase.ts` — client with AsyncStorage

```ts
import "react-native-url-polyfill/auto"; // required for Supabase on RN
import { createClient } from "@supabase/supabase-js";
import AsyncStorage from "@react-native-async-storage/async-storage";

export const supabase = createClient(
  process.env.EXPO_PUBLIC_SUPABASE_URL!,
  process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY!,
  {
    auth: {
      storage: AsyncStorage,
      autoRefreshToken: true,
      persistSession: true,
      detectSessionInUrl: false, // not relevant on mobile
    },
  },
);
```

> Use AsyncStorage for the session: expo-secure-store has a documented 2048-byte per-value limit that can truncate a session (JWT + refresh token). Keep SecureStore only for small secrets, not the session.

Also install `react-native-url-polyfill`: `npx expo install react-native-url-polyfill -- --legacy-peer-deps`.

## 4. `lib/auth.ts` — replaces the generic version

```ts
import { useMutation, useQueryClient, useQuery } from "@tanstack/react-query";
import { supabase } from "./supabase";
import { useAuthStore } from "@/store/auth";

export function useSignIn() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ email, password }: { email: string; password: string }) => {
      const { data, error } = await supabase.auth.signInWithPassword({ email, password });
      if (error) throw error;
      useAuthStore.getState().setUser({
        id: data.user!.id,
        email: data.user!.email!,
      });
      return data;
    },
    onSuccess: () => qc.invalidateQueries(),
  });
}

export function useSignOut() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      await supabase.auth.signOut();
      useAuthStore.getState().setUser(null);
      qc.clear();
    },
  });
}

export function useSession() {
  return useQuery({
    queryKey: ["auth", "session"],
    queryFn: async () => {
      const { data } = await supabase.auth.getSession();
      return data.session;
    },
    staleTime: 5 * 60_000,
  });
}
```

The Supabase SDK handles token + refresh automatically — no custom `api()` refresh logic needed.

## 5. `app/_layout.tsx` — listen to auth state changes

```tsx
import { useEffect } from "react";
import { supabase } from "@/lib/supabase";
import { useAuthStore } from "@/store/auth";
import { useQueryClient } from "@tanstack/react-query";

// inside RootLayout
const qc = useQueryClient();
useEffect(() => {
  const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
    if (session?.user) {
      useAuthStore.getState().setUser({ id: session.user.id, email: session.user.email! });
    } else {
      useAuthStore.getState().setUser(null);
    }
    qc.invalidateQueries({ queryKey: ["auth"] });
  });
  return () => subscription.unsubscribe();
}, [qc]);
```

## 6. Database queries — RLS-protected

```ts
// lib/queries/usePosts.ts
import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/lib/supabase";

export function usePosts() {
  return useQuery({
    queryKey: ["posts", "list"],
    queryFn: async () => {
      const { data, error } = await supabase
        .from("posts")
        .select("id, title, body, created_at, author:profiles(id, name)")
        .order("created_at", { ascending: false });
      if (error) throw error;
      return data;
    },
  });
}
```

Server-side: an RLS policy on the `posts` table that allows authenticated users to read their own + public rows.

## 7. Tipi generati

```bash
# In CI or as a script in package.json
npx supabase gen types typescript --project-id <ref> > types/database.ts
```

Then:

```ts
import type { Database } from "@/types/database";
import { createClient } from "@supabase/supabase-js";

const supabase = createClient<Database>(...);

// Now `.from('posts').select(...)` is fully typed.
```

## 8. Storage

```ts
const { data, error } = await supabase.storage.from("avatars").upload(`${userId}/avatar.jpg`, fileBlob);
const { data: { publicUrl } } = supabase.storage.from("avatars").getPublicUrl(data!.path);
```

Bucket policies: configure per-user "read own + write own" via the dashboard.

## 9. Realtime

```ts
useEffect(() => {
  const channel = supabase
    .channel("posts")
    .on("postgres_changes", { event: "INSERT", schema: "public", table: "posts" }, (payload) => {
      queryClient.setQueryData(["posts", "list"], (old: any) => [payload.new, ...(old ?? [])]);
    })
    .subscribe();
  return () => { void supabase.removeChannel(channel); };
}, []);
```

## Gotchas

- **Email confirmation**: enabled by default. Disable in Supabase dashboard for dev, or handle the "check your email" flow.
- **JWT expiry**: default 1 hour, refresh token rotates. The SDK handles both — don't poll the session.
- **RLS off by default on new tables**: Supabase warns in the dashboard. Always enable + write policies before shipping.
- **Anon key in client**: NEVER use service_role key in client code. Service role bypasses RLS.
