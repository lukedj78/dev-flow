> Sources: docs.expo.dev/router, internal opinion.

# Decision tree — Expo Router

## Q1: Stack, Tabs, or Drawer?

```
Are the top-level destinations a fixed small set the user switches between?
├── YES, 2-5 destinations    → Tabs (bottom on phones, top on web)
├── YES, 6+ destinations     → Drawer
└── NO, it's a hierarchy / flow → Stack (push/pop)
```

You can NEST them: a Stack inside a Tab, a Tab inside a Drawer, etc. The most common modern app: `Stack` at root → `(tabs)` group with `Tabs` layout → each tab has its own Stack of screens.

## Q2: Should this screen be a route or a component?

```
Does the user reach it via URL / share / deep link / push?
├── YES → file in app/ (route)
└── NO  → component in components/
```

## Q3: Modal or full screen?

```
Is the action temporary, dismissible, and shouldn't lose context?
├── YES → modal: <Stack.Screen options={{ presentation: 'modal' }} />
└── NO  → normal stack push
```

Use modal for: filters, sort, share sheet, settings overlay, sign-in prompt.
Use push for: detail view, list-to-item, anything you'd back-button out of.

## Q4: Should this protected area be a group or just a layout?

```
Multiple screens share the same auth-gate?
├── YES → (app)/ group with _layout.tsx that Redirects if no user
└── NO  → check auth inline in the single screen
```

## Q5: Where do I put the bottom-tab icons?

```
In the parent _layout.tsx, on each <Tabs.Screen options={{ tabBarIcon: () => ... }} />.
NEVER in the screen file itself.
```
