> Sources: docs.expo.dev/router, codewithbeto.dev lesson 11 (free).

# Concepts — Expo Router

## File-based routing

The `app/` directory IS the routing config. Every file is a route.

```
app/
├── _layout.tsx              # root layout (wraps everything)
├── index.tsx                # /
├── about.tsx                # /about
├── profile/
│   ├── _layout.tsx          # layout for /profile/*
│   ├── index.tsx            # /profile
│   └── [id].tsx             # /profile/:id (dynamic segment)
└── (tabs)/                  # GROUP — parens are syntax, not URL
    ├── _layout.tsx          # tab navigator
    ├── feed.tsx             # /feed
    └── settings.tsx         # /settings
```

- `_layout.tsx` defines the layout (Stack / Tabs / Drawer / Slot) for its directory.
- `[id].tsx` is a dynamic segment. Access via `useLocalSearchParams<{ id: string }>()`.
- `(name)/` is a route GROUP: parens are stripped from the URL, used for shared layouts and code organization.
- `+not-found.tsx` is the 404 handler.

## Typed routes

With `"typedRoutes": true` in `app.json`, Expo Router generates TypeScript types for every route at build time. Then:

```tsx
import { Href, Link, useRouter } from "expo-router";

const href: Href = { pathname: "/profile/[id]", params: { id: "abc" } };

<Link href={href}>Go</Link>

const router = useRouter();
router.push(href);
```

Wrong route string → compile error. Wrong params → compile error.

## Layouts vs screens

- **Layouts** own the navigator (`<Stack />`, `<Tabs />`, `<Drawer />`) and the chrome (header, tab bar). Defined in `_layout.tsx`.
- **Screens** own only the content. Reference them in the parent layout via `<Stack.Screen name="…" options={…} />`.

```tsx
// app/(tabs)/_layout.tsx
import { Tabs } from "expo-router";

export default function TabsLayout() {
  return (
    <Tabs>
      <Tabs.Screen name="feed" options={{ title: "Feed" }} />
      <Tabs.Screen name="settings" options={{ title: "Settings" }} />
    </Tabs>
  );
}
```

## Groups for auth

```
app/
├── _layout.tsx                  # checks auth, redirects
├── (auth)/                      # public routes
│   ├── _layout.tsx
│   ├── sign-in.tsx
│   └── sign-up.tsx
└── (app)/                       # protected routes
    ├── _layout.tsx              # redirects to /(auth)/sign-in if no user
    ├── index.tsx
    └── profile/[id].tsx
```

## Sources

- https://docs.expo.dev/router/introduction/
- https://docs.expo.dev/router/reference/typed-routes/
- https://docs.expo.dev/router/advanced/router-settings/
