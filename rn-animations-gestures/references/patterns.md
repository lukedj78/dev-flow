> Sources: docs.swmansion.com/react-native-reanimated, docs.swmansion.com/react-native-gesture-handler, internal opinion.

# Patterns — Reanimated 4 + Gesture Handler 2

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

## Layout animations (FadeIn / SlideIn / Layout)

```tsx
import Animated, { FadeIn, FadeOut, Layout } from "react-native-reanimated";

<Animated.View
  entering={FadeIn.duration(300)}
  exiting={FadeOut.duration(200)}
  layout={Layout.springify()}
>
  <Text>I fade in, fade out, and animate position on layout change.</Text>
</Animated.View>
```

Layout animations also work on FlashList / FlatList items via `itemLayoutAnimation={Layout.springify()}` on the list.

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

## DON'T

- ❌ `useEffect` to start an animation that should run on press — drive it from the press event directly.
- ❌ Read `useState` value inside `useAnimatedStyle` — it's a worklet; capture into a shared value first.
- ❌ Animate dimensions of components inside a list without `layout={Layout.springify()}` on the list — layout shifts will jump.
- ❌ Use multiple competing gestures without `Gesture.Race()` / `Gesture.Simultaneous()` / `Gesture.Exclusive()` — undefined behavior.
- ❌ Forget `scrollEventThrottle={16}` on `Animated.ScrollView` — animation will jitter.
