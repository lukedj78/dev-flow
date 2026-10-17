> Sources: docs.swmansion.com/react-native-reanimated, docs.swmansion.com/react-native-gesture-handler, internal opinion.
> Checked 2026-10-17 against the shipped `react-native-gesture-handler@3.3.0`, `react-native-reanimated@4.7.1`
> and `react-native-worklets@0.13.0` (Expo SDK 58); every block below type-checks in an SDK 58 app.

# Patterns — Reanimated 4 + the Gesture Handler 3 hook API

## Press animation (scale + opacity)

```tsx
import Animated, { useSharedValue, useAnimatedStyle, withSpring, withTiming } from "react-native-reanimated";
import { Pressable, Text } from "react-native";

export function PressableButton({ label, onPress }: { label: string; onPress: () => void }) {
  const scale = useSharedValue(1);
  const opacity = useSharedValue(1);

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ scale: scale.get() }],
    opacity: opacity.get(),
  }));

  return (
    <Pressable
      onPressIn={() => {
        scale.set(withSpring(0.96));
        opacity.set(withTiming(0.7, { duration: 100 }));
      }}
      onPressOut={() => {
        scale.set(withSpring(1));
        opacity.set(withTiming(1, { duration: 150 }));
      }}
      onPress={onPress}
    >
      <Animated.View style={animatedStyle} className="px-4 py-3 rounded-full bg-primary">
        <Text className="text-white font-semibold text-center">{label}</Text>
      </Animated.View>
    </Pressable>
  );
}
```

## Layout animations (FadeIn / SlideIn / LinearTransition)

```tsx
import Animated, { FadeIn, FadeOut, LinearTransition } from "react-native-reanimated";

<Animated.View
  entering={FadeIn.duration(300)}
  exiting={FadeOut.duration(200)}
  layout={LinearTransition.springify()}
>
  <Text>I fade in, fade out, and animate position on layout change.</Text>
</Animated.View>
```

Layout animations also work on FlashList / FlatList items via `itemLayoutAnimation={LinearTransition.springify()}` on the list.

## Pan gesture (swipe-to-dismiss)

```tsx
import Animated, { useSharedValue, useAnimatedStyle, withSpring } from "react-native-reanimated";
import { scheduleOnRN } from "react-native-worklets";
import { GestureDetector, usePanGesture } from "react-native-gesture-handler";
import { Dimensions } from "react-native";

const SCREEN = Dimensions.get("window").width;

export function SwipeToDismiss({ children, onDismiss }: { children: React.ReactNode; onDismiss: () => void }) {
  const translateX = useSharedValue(0);

  const pan = usePanGesture({
    activeOffsetX: [-10, 10], // horizontal only: a vertical scroll still wins
    onUpdate: (e) => {
      translateX.set(e.translationX);
    },
    onDeactivate: (e) => {
      if (e.canceled) {
        translateX.set(withSpring(0));
        return;
      }
      // Velocity OR distance — a flick is enough (mobile-standards.md).
      const shouldDismiss = Math.abs(e.translationX) > SCREEN * 0.4 || Math.abs(e.velocityX) > 800;
      if (shouldDismiss) {
        translateX.set(withSpring(Math.sign(e.translationX || e.velocityX) * SCREEN, { velocity: e.velocityX }));
        scheduleOnRN(onDismiss);
      } else {
        translateX.set(withSpring(0, { velocity: e.velocityX }));
      }
    },
  });

  const style = useAnimatedStyle(() => ({
    transform: [{ translateX: translateX.get() }],
  }));

  return (
    <GestureDetector gesture={pan}>
      <Animated.View style={style}>{children}</Animated.View>
    </GestureDetector>
  );
}
```

- **The config is one object**, passed to the hook; no chained builder. The callbacks are worklets
  without a `'worklet'` directive: the `react-native-worklets@0.13.0` Babel plugin knows every
  `use*Gesture` hook by name and workletizes its callbacks (it did the same for the v2 builder chain).
  A helper *they* call still needs `'worklet'` (SKILL.md rule 6).
- **`onDeactivate` replaces `onEnd`**, and its event has `canceled` instead of v2's `success` arg —
  `if (!e.canceled)` is the old `if (success)`. Events no longer carry `state` / `oldState`.
- `scheduleOnRN(onDismiss)` — the callback lives on the React Native runtime and we are inside a
  worklet. **Not `runOnJS`**: `@deprecated` in Reanimated 4 (still so in `4.7.1`'s
  `workletFunctions.ts`). It still works, so a copied snippet compiles — which is exactly why the
  deprecated name keeps spreading.
- A row with action buttons behind it is not this pattern: use `ReanimatedSwipeable` (below).

## Swipe-to-reveal row actions — `ReanimatedSwipeable`

```tsx
import ReanimatedSwipeable from "react-native-gesture-handler/ReanimatedSwipeable";
import { Pressable } from "react-native-gesture-handler";
import { Text } from "react-native";

export function Row({ onDelete }: { onDelete: () => void }) {
  return (
    <ReanimatedSwipeable
      friction={2}
      rightThreshold={40}
      renderRightActions={() => (
        <Pressable onPress={onDelete} style={{ width: 80, justifyContent: "center" }}>
          <Text>Delete</Text>
        </Pressable>
      )}
    >
      <Text>Row</Text>
    </ReanimatedSwipeable>
  );
}
```

Rewritten in Gesture Handler 3; the old `Swipeable` is gone. ⚠️ **`dragOffsetFromRight` is now
non-positive** (default `-10`): a v2 value like `dragOffsetFromRight={20}` throws in dev — flip the sign.

## Scroll-linked animation (header collapse)

```tsx
import Animated, { useAnimatedScrollHandler, useSharedValue, useAnimatedStyle, interpolate, Extrapolation } from "react-native-reanimated";

const HEADER_MAX = 200;
const HEADER_MIN = 60;

export function CollapsingHeader() {
  const scrollY = useSharedValue(0);

  const onScroll = useAnimatedScrollHandler({
    onScroll: (e) => {
      scrollY.set(e.contentOffset.y);
    },
  });

  const headerStyle = useAnimatedStyle(() => ({
    height: interpolate(
      scrollY.get(),
      [0, HEADER_MAX - HEADER_MIN],
      [HEADER_MAX, HEADER_MIN],
      Extrapolation.CLAMP,
    ),
  }));

  return (
    <>
      <Animated.View style={headerStyle} className="bg-primary" />
      <Animated.ScrollView onScroll={onScroll} scrollEventThrottle={16}>
        {/* content */}
      </Animated.ScrollView>
    </>
  );
}
```

## Pinch + pan combined

```tsx
import { GestureDetector, usePanGesture, usePinchGesture, useSimultaneousGestures } from "react-native-gesture-handler";
import Animated, { useSharedValue, useAnimatedStyle } from "react-native-reanimated";

export function ZoomableImage({ uri }: { uri: string }) {
  const scale = useSharedValue(1);
  const savedScale = useSharedValue(1);
  const translateX = useSharedValue(0);
  const translateY = useSharedValue(0);
  const savedTranslate = useSharedValue({ x: 0, y: 0 });

  const pinch = usePinchGesture({
    onUpdate: (e) => {
      scale.set(savedScale.get() * e.scale);
    },
    onDeactivate: () => {
      savedScale.set(scale.get());
    },
  });

  const pan = usePanGesture({
    onUpdate: (e) => {
      translateX.set(savedTranslate.get().x + e.translationX);
      translateY.set(savedTranslate.get().y + e.translationY);
    },
    onDeactivate: () => {
      savedTranslate.set({ x: translateX.get(), y: translateY.get() });
    },
  });

  const composed = useSimultaneousGestures(pinch, pan);

  const style = useAnimatedStyle(() => ({
    transform: [{ scale: scale.get() }, { translateX: translateX.get() }, { translateY: translateY.get() }],
  }));

  return (
    <GestureDetector gesture={composed}>
      <Animated.Image source={{ uri }} style={[{ width: 300, height: 300 }, style]} />
    </GestureDetector>
  );
}
```

## Double tap vs single tap — `useExclusiveGestures`

```tsx
import { GestureDetector, useExclusiveGestures, useTapGesture } from "react-native-gesture-handler";
import { scheduleOnRN } from "react-native-worklets";
import { View } from "react-native";

export function LikeOnDoubleTap({ onLike, onOpen }: { onLike: () => void; onOpen: () => void }) {
  const doubleTap = useTapGesture({
    numberOfTaps: 2,
    onDeactivate: (e) => {
      if (!e.canceled) scheduleOnRN(onLike);
    },
  });
  const singleTap = useTapGesture({
    onDeactivate: (e) => {
      if (!e.canceled) scheduleOnRN(onOpen);
    },
  });
  // Exclusive: the double tap gets first claim; the single tap fires only once it fails.
  const taps = useExclusiveGestures(doubleTap, singleTap);

  return (
    <GestureDetector gesture={taps}>
      <View style={{ width: 200, height: 200 }} />
    </GestureDetector>
  );
}
```

Relations between gestures on **different** detectors go in the config, not a composition hook:
`usePanGesture({ requireToFail: outer, ... })`, `simultaneousWith: other`, `block: other` — each takes
a gesture or an array.

## Migrating from Gesture Handler 2

SDK 58 is where an app crosses from `~2.32.0` to `~3.3.0`. Nothing breaks at compile time — the v2
builders still type-check — so the migration is a sweep, not a fix. Source: the
[upgrade guide](https://docs.swmansion.com/react-native-gesture-handler/docs/guides/upgrading-to-3),
names confirmed in the 3.3.0 package.

```tsx
// Before — v2 (deprecated in 3.x)
const pan = Gesture.Pan()
  .activeOffsetX([-10, 10])
  .onStart(() => { /* ... */ })
  .onChange((e) => { x.value += e.changeX; })
  .onEnd((e, success) => { if (success) scheduleOnRN(done); });
const both = Gesture.Simultaneous(pan, pinch);

// After — v3 hooks
const pan = usePanGesture({
  activeOffsetX: [-10, 10],
  onActivate: () => { /* ... */ },
  onUpdate: (e) => { x.set((v) => v + e.changeX); },
  onDeactivate: (e) => { if (!e.canceled) scheduleOnRN(done); },
});
const both = useSimultaneousGestures(pan, pinch);
```

| v2 | v3 |
|---|---|
| `Gesture.Pan()` / `.Tap()` / `.Pinch()` / `.LongPress()` / `.Rotation()` / `.Fling()` / `.Manual()` | `usePanGesture({...})` / `useTapGesture` / `usePinchGesture` / `useLongPressGesture` / `useRotationGesture` / `useFlingGesture` / `useManualGesture` |
| `.onStart` / `.onEnd` / `.onTouchesCancelled` | `onActivate` / `onDeactivate` / `onTouchesCancel` (`onBegin`, `onUpdate`, `onFinalize` keep their names) |
| `.onChange(e => e.changeX)` | removed — `changeX` / `changeY` are on the `onUpdate` event |
| `(e, success) => if (success)` | `(e) => if (!e.canceled)` |
| `e.state`, `e.oldState` | removed from events |
| `Gesture.Simultaneous` / `.Race` / `.Exclusive` | `useSimultaneousGestures` / `useCompetingGestures` / `useExclusiveGestures` |
| `.simultaneousWithExternalGesture` / `.requireExternalGestureToFail` / `.blocksExternalGesture` | config `simultaneousWith` / `requireToFail` / `block` |
| `manager.activate()` in a manual gesture | `GestureStateManager.activate(e.handlerTag)` |
| `ScrollView`, `FlatList`, `Pressable`, `RectButton`, … | same names, rewritten; the v2 versions survive as `LegacyScrollView`, `LegacyPressable`, … |
| `TouchableOpacity` and the other Touchables | `@deprecated` — `Pressable`, or `Touchable` |
| `Swipeable` | `ReanimatedSwipeable` (subpath import); `dragOffsetFromRight` sign flipped |

⚠️ **A hook gesture and a v2 gesture cannot be related** — no `simultaneousWith` across the two APIs.
Migrate every gesture on a screen (and the RNGH components it nests in, whose `simultaneousHandlers` /
`waitFor` / `blocksHandlers` props are the component-side version of the same relations) in one pass.
Gesture Handler 3 also runs on the **New Architecture only** (per the upgrade guide) — already true of every SDK 58 app, since
Reanimated 4 requires it.

## CSS Animations / Transitions API (Reanimated 4, web-style)

Reanimated 4 added a CSS-style `animation*` / `transition*` style-prop API alongside the classic worklet API (`useSharedValue` + `useAnimatedStyle`). It's fully backward-compatible — existing worklet code keeps working unchanged; this is an additional, simpler way to express declarative animations, not a replacement.

⚠️ The props are the CSS longhands, one per style key. A `transition: { property, duration, easing }`
object — the shape this file showed until 2026-10-17 — fails to type-check: `transition` is the CSS
*shorthand* and takes a string (`transition: "height 250ms ease-in-out"`).

```tsx
import Animated from "react-native-reanimated";
import { useState } from "react";
import { Pressable, Text } from "react-native";

export function ExpandableCard({ title, children }: { title: string; children: React.ReactNode }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <Pressable onPress={() => setExpanded((v) => !v)}>
      <Text className="font-semibold">{title}</Text>
      <Animated.View
        style={{
          transitionProperty: "height",
          transitionDuration: 250,
          transitionTimingFunction: "ease-in-out",
          height: expanded ? 200 : 0,
          overflow: "hidden",
        }}
      >
        {children}
      </Animated.View>
    </Pressable>
  );
}
```

```tsx
// Keyframe-style animation (mounts once, no shared value needed)
import Animated from "react-native-reanimated";

<Animated.View
  style={{
    animationName: {
      from: { opacity: 0, transform: [{ translateY: 20 }] },
      to: { opacity: 1, transform: [{ translateY: 0 }] },
    },
    animationDuration: "300ms",
    animationTimingFunction: "ease-out",
  }}
>
  <Text>Fades and slides in on mount, no useSharedValue/useAnimatedStyle needed.</Text>
</Animated.View>
```

### When to prefer CSS Animations/Transitions over worklets

- ✅ State-driven style changes (expand/collapse, toggle on/off, theme-driven color/size) where the trigger is a plain React state change, not a continuous gesture value — `transitionProperty` / `transitionDuration` / `transitionTimingFunction` on plain style props is less code than `useSharedValue` + `useAnimatedStyle` + `withTiming`.
- ✅ Simple one-shot mount/unmount animations that don't need `entering`/`exiting` presets — `animationName` keyframes.
- ✅ Porting a design spec written in CSS terms (duration, easing curve, keyframes) — maps almost 1:1.

### Still use classic worklets (`useSharedValue`/`useAnimatedStyle`) for

- ❌ Per-frame gesture-driven values (drag, pinch, scroll-linked) — CSS transitions animate FROM one committed style TO another; they don't drive continuous per-frame updates from a gesture.
- ❌ Anything needing `scheduleOnRN`, `interpolate`, or cross-shared-value coordination.
- ❌ Existing layout animations (`FadeIn`/`FadeOut`/`LinearTransition.springify()`) — those are a separate, already-declarative API; no need to migrate them to CSS transitions.

Both APIs run on the UI thread and can be mixed in the same app/component tree without conflict.

## DON'T

- ❌ `useEffect` to start an animation that should run on press — drive it from the press event directly.
- ❌ Read `useState` value inside `useAnimatedStyle` — it's a worklet; capture into a shared value first.
- ❌ Animate dimensions of components inside a list without `layout={LinearTransition.springify()}` on the list — layout shifts will jump.
- ❌ Use multiple competing gestures on one detector without `useCompetingGestures` / `useSimultaneousGestures` / `useExclusiveGestures` — undefined behavior.
- ❌ Forget `scrollEventThrottle={16}` on `Animated.ScrollView` — animation will jitter.
