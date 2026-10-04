---
name: rn-animations-gestures
description: 'Use when adding animations or gestures to a React Native + Expo app: scale/opacity/translation transitions, layout animations (FadeIn/SlideIn/FadeOut), shared-value driven motion, swipe-to-delete, pan/pinch/long-press gestures, scroll-linked animations. Triggers on: "anima questo", "swipe to X", "fade in/out", "pinch zoom", "scroll-driven animation". Not for: styling (rn-styling), navigation transitions (Expo Router handles those — see rn-expo-router), CSS-only on web (Next.js stack).'
---

# rn-animations-gestures — guardrail for animations + gestures in RN/Expo

> For the current Expo API and per-version details, verify against the Expo docs / MCP `mcp.expo.dev` / `expo/skills` (see rn-fundamentals → Source of truth).

## The 5 rules (non-negotiable)

1. **Reanimated 4 is the default**. Never the legacy `Animated` API from `react-native` for new code. Reanimated 4 also ships a web-style CSS Animations/Transitions API (`transition: {...}`, `animationName` keyframes) as a backward-compatible ADDITION to worklets — good for state-driven style changes, not a replacement for `useSharedValue`/`useAnimatedStyle` on gesture-driven motion (see `references/patterns.md`).
2. **Gestures via the Gesture Handler `Gesture` API**. Never `PanResponder`. Do not go looking for a major number: npm's `latest` is 3.x, and **Expo SDK 57 bundles `~2.32.0`** — `expo install` will not give you 3, and the `Gesture` API below is the same in both. Installing what npm says here is the exact mistake `rn-bootstrap/references/stack-defaults.md` documents. Use `Gesture.Pan()`, `Gesture.Pinch()`, `Gesture.Tap()`, `Gesture.LongPress()` with `<GestureDetector>`.
3. **Worklets run on the UI thread** — they CANNOT access React state directly. To call back to the React Native runtime use **`scheduleOnRN(fn, ...args)` from `react-native-worklets`**. ⚠️ **`runOnJS` is `@deprecated` in Reanimated 4** — verified in `react-native-reanimated@4.5.1`'s own `workletFunctions.d.ts`, which names the replacement; `runOnUI` → `scheduleOnUI`, `executeOnUIRuntimeSync` → `runOnUISync`, `makeShareableClone` → `createSerializable`. All of them live in `react-native-worklets` (0.10.1 on SDK 57), the package `expo install` already brings alongside Reanimated. The old names still work and will keep compiling, which is why they survive in copied snippets.
4. **Read and write shared values with `.get()` / `.set()`, not `.value`.** Same semantics, but `.value` is the form the React Compiler cannot see through, and `set` takes a functional update: `sv.set(v => v + 1)`. **Never read or write a shared value during render** — a read is a snapshot that never updates and silently desyncs, a write fires mid-reconciliation and is replayed by any re-render you did not cause. Worklets, handlers and effects only.
5. **Never `scheduleOnRN` per frame.** In `onUpdate` or a scroll handler that is 60–120 calls a second across the runtime boundary — the single biggest cause of jank in an RN app, along with `setState` in the same place. It belongs in `onEnd`, or in a `useAnimatedReaction` that fires when a value crosses a threshold.
6. **A function called from a worklet needs `'worklet'` as its first line**, or it throws at runtime on device while working fine in the debugger.
7. **Layout animations for enter/exit/move**. Use `entering={FadeIn}`, `exiting={FadeOut}`, `layout={LinearTransition.springify()}` from `react-native-reanimated` — they handle their own worklets correctly.
8. **`useDerivedValue` for computed shared values**. Never `useMemo` on a shared value — `useMemo` runs on JS thread.

## The standards — read before writing motion, and before approving it

**`references/mobile-standards.md`** holds the gate (mobile's own frequency table, where tab switches
never slide), the platform-first tool ladder (`formSheet`, `NativeTabs`, `Link.Preview`,
`headerLargeTitleEnabled` — reach for these before a worklet), the spring configs in Reanimated's
`dampingRatio` form, the `project()` / `rubberband()` worklets, press targets and `hitSlop`, the three
absolute haptics rules, the setup that silently breaks motion, and the **release-build-on-the-slowest-
device** rule. The curves and durations are the same bar as the web's
(`transitions/references/animation-standards.md`); that file is what mobile *changes*.

## Quick decision tree

- "What's the right tool — worklets or the CSS Animations/Transitions API?" → `references/decision-tree.md`
- "How do I structure a worklet-driven animation?" → `references/patterns.md`
- "What native module setup do I need?" → Reanimated 4, `react-native-worklets` and Gesture Handler are all in `rn-bootstrap`'s `install-stack.sh`. No babel config to write: `babel-preset-expo` wires the worklets plugin when the library is installed.

## Common anti-patterns (NEVER do)

- ❌ `import { Animated } from "react-native"` — use `react-native-reanimated`'s `Animated` instead.
- ❌ `setMyState(newValue)` from inside a worklet — `scheduleOnRN(setMyState, newValue)`. And if it is a gesture or scroll handler, prefer a shared value + `useAnimatedStyle` so React never re-renders at all.
- ❌ `runOnJS` / `runOnUI` in new code — deprecated in Reanimated 4 (see rule 3).
- ❌ Reading `props.foo` directly inside `useAnimatedStyle` — capture into a shared value first.
- ❌ `PanResponder` — deprecated for new code. Use `<GestureDetector>`.
- ❌ Installing `react-native-reanimated` alone. **Reanimated 4 moved worklets into `react-native-worklets`**, a separate required package — Expo's own line is `npx expo install react-native-reanimated react-native-worklets`. It builds without it and fails at runtime.
- ❌ Animating `height: 'auto'` — impossible on the UI thread (no measure). Either measure with `onLayout` or use `LayoutAnimation` from Reanimated.
- ❌ Chaining `withTiming(...)` inside `useEffect` without `cancelAnimation` — leaks on unmount.

## Sources

- Course: codewithbeto.dev/rnCourse — "Animations & Gestures" module (paid, distilled).
- Official: https://docs.swmansion.com/react-native-reanimated/docs/
- Official: https://docs.swmansion.com/react-native-gesture-handler/docs/
