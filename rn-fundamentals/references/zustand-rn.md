# Zustand — client state in Expo + RN

The **how**, not just "use Zustand". Doc-grounded against `zustand.docs.pmnd.rs` (create, useShallow, slices pattern, persist / `createJSONStorage`) plus the Expo SecureStore reference. Verified `zustand` **5.0.14** (2026-08) — the repo pins `^5.0.14` in `references/stack-defaults.md`. `[VERIFY]` identifiers against the installed version; the v4 → v5 surface changed (e.g. `createWithEqualityFn` now lives in `zustand/traditional`).

## Decide first: does this belong in Zustand at all?

Zustand is for **client state that outlives a screen**. Most state does not.

| State | Where it goes | Why |
|---|---|---|
| Anything the server owns (lists, details, profiles) | **TanStack Query** (`rn-data-fetching`) | cache, dedup, retry, invalidation, offline — Zustand has none of it |
| Field values, dirty/valid, submit | **the form library** | duplicating fields into a store re-renders the tree on every keystroke |
| Open/closed, hovered, selected tab *inside one screen* | **`useState`** | ephemeral, unmounts with the screen |
| Theme, locale, auth session, cart, onboarding step, feature flags | **Zustand** | read from many unrelated screens, must survive navigation |

Rule of thumb: if exactly one screen reads it, it is not global state.

## Creating a store (TypeScript)

TS requires the **curried** form `create<T>()(...)` — the extra `()` — because the state generic is invariant and cannot be inferred.

```ts
// store/cart.ts
import { create } from "zustand";

type CartItem = { id: string; qty: number };

type CartState = {
  items: CartItem[];
  // actions live in the store (see below)
  add: (id: string) => void;
  remove: (id: string) => void;
  clear: () => void;
};

export const useCartStore = create<CartState>()((set, get) => ({
  items: [],
  add: (id) =>
    set((state) => ({
      items: state.items.some((i) => i.id === id)
        ? state.items.map((i) => (i.id === id ? { ...i, qty: i.qty + 1 } : i))
        : [...state.items, { id, qty: 1 }],
    })),
  remove: (id) => set((state) => ({ items: state.items.filter((i) => i.id !== id) })),
  clear: () => set({ items: [] }),
}));
```

**Actions-in-store convention**: every mutation is a named action on the store. `set` is never called from a component, and the store is never exported raw. Consumers get verbs, not a setter. `set` merges shallowly at the top level — nested objects must be spread by hand.

Outside React (event handlers, API layer, background tasks): `useCartStore.getState().clear()` and `useCartStore.setState(...)`.

## Selectors — the re-render contract

Subscribe to the **narrowest value you actually render**. Calling the hook with no selector subscribes to the whole store and re-renders on every unrelated change.

```tsx
const qty = useCartStore((s) => s.items.length);   // ✅ atomic
const add = useCartStore((s) => s.add);            // ✅ actions are stable identities
const everything = useCartStore();                 // ❌ re-renders on any change
```

A selector that **builds a new object or array** returns a new reference every time, so `Object.is` always says "changed". Wrap it in `useShallow`:

```tsx
import { useShallow } from "zustand/react/shallow";

const { items, clear } = useCartStore(useShallow((s) => ({ items: s.items, clear: s.clear })));
const names = useMealsStore(useShallow((s) => Object.keys(s)));
```

Without `useShallow` this is the documented cause of "Maximum update depth exceeded" when reading multiple values at once.

## Slices, once the store grows

Split by domain, type each slice with `StateCreator<FullState, [], [], Slice>`, and combine in **one** bound store.

```ts
// store/slices/cart.ts
import type { StateCreator } from "zustand";

export interface CartSlice { items: CartItem[]; add: (id: string) => void }
export interface SessionSlice { userId: string | null; signOut: () => void }

export const createCartSlice: StateCreator<CartSlice & SessionSlice, [], [], CartSlice> = (set) => ({
  items: [],
  add: (id) => set((s) => ({ items: [...s.items, { id, qty: 1 }] })),
});
```

```ts
// store/index.ts
export const useBoundStore = create<CartSlice & SessionSlice>()((...a) => ({
  ...createCartSlice(...a),
  ...createSessionSlice(...a),
}));
```

Slices can call each other through `get()` (`get().add(id)`). **Apply middleware only on the combined store** — wrapping individual slices leads to unexpected behavior. With middleware, the mutator tuple changes: `StateCreator<S, [["zustand/persist", unknown]], [], Slice>` `[VERIFY]`.

## Persisting with AsyncStorage

`persist`'s default storage is `localStorage`, which does not exist in RN. Pass AsyncStorage through `createJSONStorage`:

```bash
npx expo install @react-native-async-storage/async-storage -- --legacy-peer-deps
```

```ts
// store/session.ts
import AsyncStorage from "@react-native-async-storage/async-storage";
import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

type SessionState = {
  userId: string | null;
  locale: "en" | "it";
  hasOnboarded: boolean;
  _hasHydrated: boolean;
  setHasHydrated: (v: boolean) => void;
  signOut: () => void;
};

export const useSessionStore = create<SessionState>()(
  persist(
    (set) => ({
      userId: null,
      locale: "en",
      hasOnboarded: false,
      _hasHydrated: false,
      setHasHydrated: (v) => set({ _hasHydrated: v }),
      signOut: () => set({ userId: null }),
    }),
    {
      name: "session",                                  // storage key — required
      storage: createJSONStorage(() => AsyncStorage),
      partialize: (s) => ({ locale: s.locale, hasOnboarded: s.hasOnboarded }),
      version: 1,
      migrate: (persisted, from) => (from === 0 ? { ...(persisted as object), locale: "en" } : persisted),
      onRehydrateStorage: () => (state, error) => {
        if (error) console.warn("rehydrate failed", error);
        state?.setHasHydrated(true);
      },
    },
  ),
);
```

Other options: `merge` (custom merge, defaults to shallow), `skipHydration: true` + `useSessionStore.persist.rehydrate()` for manual control. Runtime helpers: `.hasHydrated()`, `.onHydrate()`, `.onFinishHydration()`, `.clearStorage()`, `.setOptions()`.

### `partialize` — secrets never reach AsyncStorage

`partialize` is an **allowlist**, and the only thing standing between your store and plaintext-on-disk. AsyncStorage is unencrypted; `createJSONStorage` does `JSON.stringify` with no validation on the way back in.

- ✅ persist: locale, theme, onboarding flags, non-identifying preferences.
- ❌ never persist: access/refresh tokens, API keys, passwords, PII, payment data.

Secrets go to **`expo-secure-store`** (Keychain / Android Keystore), read at startup and held in memory only:

```ts
import * as SecureStore from "expo-secure-store";

await SecureStore.setItemAsync("session_token", token);
const token = await SecureStore.getItemAsync("session_token");
await SecureStore.deleteItemAsync("session_token");   // on sign-out
```

SecureStore is iOS/Android/tvOS only (no web) and rejects large payloads — historically ~2048 bytes on iOS. Store the token, not the profile.

## ⚠️ AsyncStorage is async — the first render sees defaults, not persisted state

The store is created **synchronously** with its initial values; rehydration lands one or more ticks later. So on the very first frame `hasOnboarded` is `false` and `locale` is `"en"` **even for a returning user**. Any redirect, gate, or `<Redirect>` in `app/_layout.tsx` that reads persisted state will fire on the wrong values — users get bounced back to onboarding, then flicker to the real screen.

Gate on hydration before you branch:

```tsx
// app/_layout.tsx
const hasHydrated = useSessionStore((s) => s._hasHydrated);
const hasOnboarded = useSessionStore((s) => s.hasOnboarded);

if (!hasHydrated) return <SplashScreenPlaceholder />;   // keep the splash up, don't guess
return hasOnboarded ? <Stack /> : <Redirect href="/onboarding" />;
```

The `_hasHydrated` + `onRehydrateStorage` pair above is the documented approach; the alternative is a `useHydration()` hook built on `.onFinishHydration()` / `.hasHydrated()`. Either way: **never branch on persisted state before hydration completes.**

## Integration in dev-flow

- Installed at scaffold by `rn-bootstrap`; stores live in `store/` (see `references/patterns.md` project layout).
- `rn-add-screen` reaches for `useState` first, Zustand only when a second unrelated screen needs the same value.
- Server data stays in TanStack Query (`rn-data-fetching`) — a Zustand store that mirrors an API response is a bug, not a cache.
- `rn-module-add auth` owns the token: `expo-secure-store` for the credential, Zustand for the derived `userId` / role, and both cleared on sign-out alongside `queryClient.clear()`.
- `rn-write-tests`: reset stores between tests (`useCartStore.setState(initialState, true)`) — module-level stores leak across test files.
