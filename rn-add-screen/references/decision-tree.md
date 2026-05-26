> Sources: synthesized from rn-expo-router decision-tree + rn-data-fetching decision-tree.

# Decision tree — adding a screen

## Q1: Where does the file go in `app/`?

```
Public unauthenticated screen?
├── YES → app/(auth)/<name>.tsx       (sign-in, sign-up, forgot, marketing)
└── NO  → app/(app)/<name>.tsx        (everything post-login)

Reached by URL share / deep link / push?
├── YES → must be a file in app/
└── NO  → component in components/, not a route

Tab in the bottom bar?
├── YES → app/(tabs)/<name>.tsx + register in app/(tabs)/_layout.tsx
└── NO  → app/<name>.tsx  (or under a group)
```

## Q2: Which template (from screen-patterns.md)?

```
What does the screen DO primarily?
├── Show a list of items                → List template (FlashList + useQuery)
├── Show one item                       → Detail template (useLocalSearchParams + useQuery)
├── Collect user input → submit         → Form template (KeyboardAvoidingView + useMutation)
├── Temporary action (filter / share)   → Modal template (presentation: "modal")
└── Show static content (about, terms)  → Detail template minus the query
```

## Q3: Does it need data?

```
Where does the data come from?
├── Network → useQuery (or useInfiniteQuery for paginated)
├── Local store (Zustand) → useStore selector
├── URL params → useLocalSearchParams<T>()
├── Static → in-file constant
```

Combine freely: a profile screen typically reads `id` from URL params AND fetches profile data with that id.

## Q4: Should I wrap in SafeAreaView?

```
Type of screen?
├── Root in a Stack    → YES, wrap in SafeAreaView edges={['top', 'bottom']}.
├── Inside a Tab       → YES, but bottom edge already handled by tab bar:
│                        edges={['top']}.
├── Modal              → NO (modal presentation handles it).
├── Fullscreen video   → NO (you want edge-to-edge).
```

## Q5: Form layout — single column or two-column?

```
Tablet supported?
├── NO (phone-only)  → single column, full width inputs
└── YES              → useWindowDimensions; on width ≥ 600, two-column
                       grid for inputs (see rn-styling/responsive-card example)
```

## Q6: Should I add a header back button?

```
Expo Router default header is enabled?
├── YES → back button is automatic, do nothing
└── NO  (headerShown: false in layout) → add a custom Pressable with router.back()
```

## Q7: What if the user gives a screenshot?

```
1. Identify the template (Q2 above).
2. Match colors/spacing to existing tailwind.config.js tokens (no new magic values).
3. Confirm interpretation with the user BEFORE generating (one round-trip).
4. Generate, run tsc, commit, report.
```

If the screenshot uses tokens NOT in the config, ask the user whether to add them to DESIGN.md (which `wire-nativewind.ts` regenerates) or use arbitrary values sparingly.
