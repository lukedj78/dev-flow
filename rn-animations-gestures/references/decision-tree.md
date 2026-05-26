> Sources: Reanimated 4 docs, Gesture Handler 2 docs, internal opinion.

# Decision tree — animations + gestures

## Q1: Reanimated or just CSS-like transitions?

```
What does the animation do?
├── Per-frame value (drag, scroll-linked, gesture)         → Reanimated, MANDATORY.
├── Enter / exit / layout shift                             → Reanimated Layout animations
│                                                            (FadeIn / FadeOut / SlideIn / Layout)
├── Simple opacity/scale on press                           → Reanimated with withSpring/withTiming
└── Already-animated by another lib (Expo Router header)    → leave it alone
```

There is no `transition: 0.3s` CSS-equivalent in RN. All animation is JS-driven via Reanimated.

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

## Q4: When to use `runOnJS` / `runOnUI`?

```
Where am I, where do I want to be?
├── In a worklet, want to call a JS function (setState, navigate, alert) → runOnJS(fn)(args)
├── In JS, want to set a shared value urgently from JS                    → just `sv.value = x` (it's automatic)
├── In JS, want to RUN a worklet on UI thread                             → runOnUI(workletFn)(args)
└── In a worklet, want to set another shared value                        → just `sv.value = x` (already worklet)
```

## Q5: Gesture choice

```
What's the interaction?
├── Single tap / double tap                  → Gesture.Tap() / Gesture.Tap().numberOfTaps(2)
├── Long press                                → Gesture.LongPress()
├── Drag in 1D / 2D                           → Gesture.Pan()
├── Two-finger pinch                          → Gesture.Pinch()
├── Two-finger rotate                         → Gesture.Rotation()
├── Multiple gestures together                → Gesture.Simultaneous(g1, g2)
├── Multiple gestures, one wins               → Gesture.Race(g1, g2)
└── Multiple gestures, in priority order      → Gesture.Exclusive(g1, g2)
```

## Q6: Performance — am I doing it right?

```
Symptom → fix
├── Animation janks                               → check it's a worklet (useAnimatedStyle, not inline style)
├── ScrollView lags                                → use Animated.ScrollView + scrollEventThrottle={16}
├── Layout animation jumps on list items           → add itemLayoutAnimation={Layout.springify()} on the list
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
