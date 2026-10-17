> Sources: Reanimated 4 docs, Gesture Handler docs, internal opinion. Versions come from the Expo SDK's `bundledNativeModules.json`, never from npm `latest` — see `rn-bootstrap/references/stack-defaults.md`.

# Decision tree — animations + gestures

## Q1: Reanimated worklets or the CSS Animations/Transitions API?

```
What does the animation do?
├── Per-frame value (drag, scroll-linked, gesture)         → Worklets, MANDATORY
│                                                            (useSharedValue + useAnimatedStyle)
├── Enter / exit / layout shift                             → Reanimated Layout animations
│                                                            (FadeIn / FadeOut / SlideIn / LinearTransition)
├── State-driven style change (expand/collapse, toggle,     → CSS Animations/Transitions API
│   theme swap) — trigger is plain React state, not a         (Reanimated 4+): `transitionProperty`…
│   continuous gesture value                                  on the style, or `animationName` keyframes
├── Simple opacity/scale on press                           → Either: worklets with withSpring/withTiming,
│                                                            or a CSS `transition` — pick worklets if the
│                                                            press also needs a gesture-linked value later.
└── Already-animated by another lib (Expo Router header)    → leave it alone
```

Reanimated 4 introduced a web-style `transitionProperty` / `transitionDuration` / `transitionTimingFunction` / `animationName` keyframes API (style props, CSS names — there is no `transition: {...}` object) — see `references/patterns.md` for examples. It runs on the UI thread like worklets and is fully backward-compatible, but it animates FROM one committed style TO another; it does not drive continuous per-frame gesture values, so drag/pinch/scroll-linked motion still needs classic worklets.

## Q2: `withTiming` or `withSpring`?

```
Is the motion responding to a user gesture or a "snap-to" action?
├── Gesture-end snap (swipe back, pull to refresh)  → withSpring (feels natural)
├── Toggle / fade / state change                    → withTiming (predictable duration)
├── Sequence of values                              → withSequence(a, b, c)
└── Loop                                             → withRepeat(withTiming(...), -1)
```

## Q3: Where should the animation logic live?

```
Animation scope?
├── Per-component, self-contained             → useSharedValue + useAnimatedStyle inside the component
├── Shared across components (theme transition) → context + shared value passed down
├── Triggered by route change                  → useFocusEffect (expo-router) + start the animation
└── Triggered by data change                   → useEffect with the data as dep + start the animation
```

## Q4: Crossing between the runtimes — `scheduleOnRN` / `scheduleOnUI`

```
Where am I, where do I want to be?
├── In a worklet, want to call a JS function (setState, navigate, haptic) → scheduleOnRN(fn, ...args)
├── In JS, want to set a shared value                                     → sv.set(x) (it's automatic)
├── In JS, want to RUN a worklet on the UI runtime                        → scheduleOnUI(workletFn, ...args)
└── In a worklet, want to set another shared value                        → sv.set(x) (already a worklet)
```

All from `react-native-worklets` (0.13.0 on SDK 58). `runOnJS(fn)(args)` / `runOnUI(fn)(args)` still
work but are `@deprecated` in Reanimated 4.7.1 — see SKILL.md rule 3.

## Q5: Gesture choice — Gesture Handler 3 hooks (SDK 58 bundles `~3.3.0`)

```
What's the interaction?
├── Single tap / double tap                  → useTapGesture({...}) / useTapGesture({ numberOfTaps: 2, ... })
├── Long press                                → useLongPressGesture({...})
├── Drag in 1D / 2D                           → usePanGesture({...})  (activeOffsetX: [-10, 10] for 1D)
├── Two-finger pinch                          → usePinchGesture({...})
├── Two-finger rotate                         → useRotationGesture({...})
├── Multiple gestures together                → useSimultaneousGestures(g1, g2)
├── Multiple gestures, one wins               → useCompetingGestures(g1, g2)
├── Multiple gestures, in priority order      → useExclusiveGestures(g1, g2)
├── Across detectors (nested, scroll + pan)   → config: simultaneousWith / requireToFail / block
├── Swipe-to-reveal row actions               → ReanimatedSwipeable ("react-native-gesture-handler/ReanimatedSwipeable")
└── Plain press feedback, no gesture logic    → Pressable, or RNGH's Touchable (activeScale / activeOpacity)
```

The v2 names (`Gesture.Tap()`, `Gesture.Race()`, …) still compile and are all `@deprecated` — the
mapping is in `patterns.md` → "Migrating from Gesture Handler 2".

## Q6: Performance — am I doing it right?

```
Symptom → fix
├── Animation janks                               → check it's a worklet (useAnimatedStyle, not inline style)
├── ScrollView lags                                → use Animated.ScrollView + scrollEventThrottle={16}
├── Layout animation jumps on list items           → add itemLayoutAnimation={LinearTransition.springify()} on the list
├── Worklet logs nothing                           → console.log inside worklets works in dev only
├── Gesture doesn't fire                           → wrap parent in GestureHandlerRootView (already in
│                                                    rn-bootstrap root layout? if not, add it)
└── Reanimated warning "useNativeDriver"           → silence in jest.setup.ts (already done — see rn-write-tests)
```

## Q7: GestureHandlerRootView setup

The root of the app must include `<GestureHandlerRootView style={{ flex: 1 }}>`. In Expo Router, this lives in `app/_layout.tsx`:

```tsx
import { GestureHandlerRootView } from "react-native-gesture-handler";
import { Stack } from "expo-router";
import "../global.css";

export default function RootLayout() {
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <Stack />
    </GestureHandlerRootView>
  );
}
```

If `rn-bootstrap` did NOT add this (early bootstrap versions before Wave 3), add it manually. Future Wave 3 update to `rn-bootstrap` will include it by default.
