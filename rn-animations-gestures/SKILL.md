---
name: rn-animations-gestures
description: 'Use when adding animations or gestures to a React Native + Expo app: scale/opacity/translation transitions, layout animations (FadeIn/SlideIn/FadeOut), shared-value driven motion, swipe-to-delete, pan/pinch/long-press gestures, scroll-linked animations. Triggers on: "anima questo", "swipe to X", "fade in/out", "pinch zoom", "scroll-driven animation". Not for: styling (rn-styling), navigation transitions (Expo Router handles those — see rn-expo-router), CSS-only on web (Next.js stack).'
---

# rn-animations-gestures — guardrail for animations + gestures in RN/Expo

> For the current Expo API and per-version details, verify against the Expo docs / MCP `mcp.expo.dev` / `expo/skills` (see rn-fundamentals → Source of truth).

## The 5 rules (non-negotiable)

1. **Reanimated 4 is the default**. Never the legacy `Animated` API from `react-native` for new code. Reanimated 4 also ships a web-style CSS Animations/Transitions API (`transition: {...}`, `animationName` keyframes) as a backward-compatible ADDITION to worklets — good for state-driven style changes, not a replacement for `useSharedValue`/`useAnimatedStyle` on gesture-driven motion (see `references/patterns.md`).
2. **Gestures via Gesture Handler 3**. Never `PanResponder`. Use `Gesture.Pan()`, `Gesture.Pinch()`, `Gesture.Tap()`, `Gesture.LongPress()` with `<GestureDetector>`.
3. **Worklets run on the UI thread** — they CANNOT access React state directly. To call back to JS use `runOnJS(fn)(args)`. Inside worklets, only shared values, locals, and `runOnUI/runOnJS` are safe.
4. **Layout animations for enter/exit/move**. Use `entering={FadeIn}`, `exiting={FadeOut}`, `layout={LinearTransition.springify()}` from `react-native-reanimated` — they handle their own worklets correctly.
5. **`useDerivedValue` for computed shared values**. Never `useMemo` on a shared value — `useMemo` runs on JS thread.

## Quick decision tree

- "What's the right tool — worklets or the CSS Animations/Transitions API?" → `references/decision-tree.md`
- "How do I structure a worklet-driven animation?" → `references/patterns.md`
- "What native module setup do I need?" → both Reanimated 4 + RNGH 3 are already in `rn-bootstrap`'s `install-stack.sh`. No extra setup needed.

## Common anti-patterns (NEVER do)

- ❌ `import { Animated } from "react-native"` — use `react-native-reanimated`'s `Animated` instead.
- ❌ `setMyState(newValue)` from inside a worklet — wrap in `runOnJS(setMyState)(newValue)`.
- ❌ Reading `props.foo` directly inside `useAnimatedStyle` — capture into a shared value first.
- ❌ `PanResponder` — deprecated for new code. Gesture Handler 3.
- ❌ Animating `height: 'auto'` — impossible on the UI thread (no measure). Either measure with `onLayout` or use `LayoutAnimation` from Reanimated.
- ❌ Chaining `withTiming(...)` inside `useEffect` without `cancelAnimation` — leaks on unmount.

## Sources

- Course: codewithbeto.dev/rnCourse — "Animations & Gestures" module (paid, distilled).
- Official: https://docs.swmansion.com/react-native-reanimated/docs/
- Official: https://docs.swmansion.com/react-native-gesture-handler/docs/
