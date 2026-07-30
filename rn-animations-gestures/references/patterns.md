> Sources: docs.swmansion.com/react-native-reanimated, docs.swmansion.com/react-native-gesture-handler, internal opinion.

# Patterns — Reanimated 4 + Gesture Handler 3

## Press animation (scale + opacity)

```tsx
import Animated, { useSharedValue, useAnimatedStyle, withSpring, withTiming } from "react-native-reanimated";
import { Pressable, Text } from "react-native";

export function PressableButton({ label, onPress }: { label: string; onPress: () => void }) {
  const scale = useSharedValue(1);
  const opacity = useSharedValue(1);

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }],
    opacity: opacity.value,
  }));

  return (
    <Pressable
      onPressIn={() => {
        scale.value = withSpring(0.96);
        opacity.value = withTiming(0.7, { duration: 100 });
      }}
      onPressOut={() => {
        scale.value = withSpring(1);
        opacity.value = withTiming(1, { duration: 150 });
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
import Animated, { useSharedValue, useAnimatedStyle, withSpring, runOnJS } from "react-native-reanimated";
import { Gesture, GestureDetector } from "react-native-gesture-handler";
import { Dimensions } from "react-native";

const SCREEN = Dimensions.get("window").width;

export function SwipeableRow({ children, onDismiss }: { children: React.ReactNode; onDismiss: () => void }) {
  const translateX = useSharedValue(0);

  const pan = Gesture.Pan()
    .onUpdate((e) => {
      translateX.value = e.translationX;
    })
    .onEnd((e) => {
      const shouldDismiss = Math.abs(e.translationX) > SCREEN * 0.4;
      if (shouldDismiss) {
        translateX.value = withSpring(Math.sign(e.translationX) * SCREEN);
        runOnJS(onDismiss)();
      } else {
        translateX.value = withSpring(0);
      }
    });

  const style = useAnimatedStyle(() => ({
    transform: [{ translateX: translateX.value }],
  }));

  return (
    <GestureDetector gesture={pan}>
      <Animated.View style={style}>{children}</Animated.View>
    </GestureDetector>
  );
}
```

Note `runOnJS(onDismiss)()` — the callback is JS but we're inside a worklet.

## Scroll-linked animation (header collapse)

```tsx
import Animated, { useAnimatedScrollHandler, useSharedValue, useAnimatedStyle, interpolate, Extrapolation } from "react-native-reanimated";

const HEADER_MAX = 200;
const HEADER_MIN = 60;

export function CollapsingHeader() {
  const scrollY = useSharedValue(0);

  const onScroll = useAnimatedScrollHandler({
    onScroll: (e) => {
      scrollY.value = e.contentOffset.y;
    },
  });

  const headerStyle = useAnimatedStyle(() => ({
    height: interpolate(
      scrollY.value,
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
import { Gesture, GestureDetector } from "react-native-gesture-handler";
import Animated, { useSharedValue, useAnimatedStyle } from "react-native-reanimated";

export function ZoomableImage({ uri }: { uri: string }) {
  const scale = useSharedValue(1);
  const translateX = useSharedValue(0);
  const translateY = useSharedValue(0);
  const savedScale = useSharedValue(1);
  const savedTranslate = useSharedValue({ x: 0, y: 0 });

  const pinch = Gesture.Pinch()
    .onUpdate((e) => {
      scale.value = savedScale.value * e.scale;
    })
    .onEnd(() => {
      savedScale.value = scale.value;
    });

  const pan = Gesture.Pan()
    .onUpdate((e) => {
      translateX.value = savedTranslate.value.x + e.translationX;
      translateY.value = savedTranslate.value.y + e.translationY;
    })
    .onEnd(() => {
      savedTranslate.value = { x: translateX.value, y: translateY.value };
    });

  const composed = Gesture.Simultaneous(pinch, pan);

  const style = useAnimatedStyle(() => ({
    transform: [
      { scale: scale.value },
      { translateX: translateX.value },
      { translateY: translateY.value },
    ],
  }));

  return (
    <GestureDetector gesture={composed}>
      <Animated.Image source={{ uri }} style={[{ width: 300, height: 300 }, style]} />
    </GestureDetector>
  );
}
```

## CSS Animations / Transitions API (Reanimated 4, web-style)

Reanimated 4 added a CSS-style `animation` / `transition` API alongside the classic worklet API (`useSharedValue` + `useAnimatedStyle`). It's fully backward-compatible — existing worklet code keeps working unchanged; this is an additional, simpler way to express declarative animations, not a replacement.

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
          transition: { property: "height", duration: 250, easing: "easeInOut" },
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

- ✅ State-driven style changes (expand/collapse, toggle on/off, theme-driven color/size) where the trigger is a plain React state change, not a continuous gesture value — `transition: { property, duration, easing }` on plain style props is less code than `useSharedValue` + `useAnimatedStyle` + `withTiming`.
- ✅ Simple one-shot mount/unmount animations that don't need `entering`/`exiting` presets — `animationName` keyframes.
- ✅ Porting a design spec written in CSS terms (duration, easing curve, keyframes) — maps almost 1:1.

### Still use classic worklets (`useSharedValue`/`useAnimatedStyle`) for

- ❌ Per-frame gesture-driven values (drag, pinch, scroll-linked) — CSS transitions animate FROM one committed style TO another; they don't drive continuous per-frame updates from a gesture.
- ❌ Anything needing `runOnJS`, `interpolate`, or cross-shared-value coordination.
- ❌ Existing layout animations (`FadeIn`/`FadeOut`/`LinearTransition.springify()`) — those are a separate, already-declarative API; no need to migrate them to CSS transitions.

Both APIs run on the UI thread and can be mixed in the same app/component tree without conflict.

## DON'T

- ❌ `useEffect` to start an animation that should run on press — drive it from the press event directly.
- ❌ Read `useState` value inside `useAnimatedStyle` — it's a worklet; capture into a shared value first.
- ❌ Animate dimensions of components inside a list without `layout={LinearTransition.springify()}` on the list — layout shifts will jump.
- ❌ Use multiple competing gestures without `Gesture.Race()` / `Gesture.Simultaneous()` / `Gesture.Exclusive()` — undefined behavior.
- ❌ Forget `scrollEventThrottle={16}` on `Animated.ScrollView` — animation will jitter.
