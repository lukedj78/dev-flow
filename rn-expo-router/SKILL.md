---
name: rn-expo-router
description: 'Use when working with navigation in an Expo + React Native app: adding routes, building tab/stack/drawer layouts, modal routes, dynamic segments (e.g. /profile/[id]), typed routes, deep linking, search params. Triggers on: "add a route", "wire up tabs", "open as modal", "set up deep linking", "configure navigation", or whenever an agent is about to touch a file under app/. Not for: styling navigation chrome (rn-styling), animating transitions (rn-animations-gestures, Wave 3), or non-RN web routing.'
---

# rn-expo-router — guardrail for navigation in Expo + RN

## The 4 rules (non-negotiable)

1. **Expo Router only**. Never `import` from `@react-navigation/*` directly — Expo Router wraps and owns it.
2. **File-based**: routes live in `app/`. The filename IS the URL. `_layout.tsx` files define the layout for their directory.
3. **Typed routes ON**. In `app.json`: `"expo": { "experiments": { "typedRoutes": true } }`. Use `Href` type for navigation, never raw strings.
4. **Layouts contain navigators**. Screen files contain only the screen UI. Tab bar / stack header config goes in `_layout.tsx`.

## Quick decision tree

- "Tabs / Stack / Drawer — which?" → `references/decision-tree.md`
- "How do I structure routes for an auth-gated section?" → `references/patterns.md` (Auth groups)
- "Deep linking from notification or URL?" → `references/deep-linking-setup.md`
- "Show me a real layout" → `references/examples/`

## Common anti-patterns (NEVER do)

- ❌ `import { useNavigation } from '@react-navigation/native'` → use `useRouter()` from `expo-router`.
- ❌ `router.push('/profile/123')` as raw string → typed routes: `router.push({ pathname: '/profile/[id]', params: { id: '123' } })`.
- ❌ Defining a `<Tabs.Screen>` in a screen file — it goes in the parent `_layout.tsx`.
- ❌ Hardcoded route strings scattered everywhere → use typed routes (`expo-router/typed-routes` provides static checking).

## Sources

- Course: codewithbeto.dev/rnCourse — lesson 11 "Navigation Basics" (free) + 1 free Expo Router lesson.
- Official: https://docs.expo.dev/router/introduction/
- Official: https://docs.expo.dev/router/reference/typed-routes/
