# Mobile motion standards — the gate, the thread, and the senses the web doesn't have

The web counterpart is `transitions/references/animation-standards.md`, and the curves, durations and
the frequency gate are **the same bar**. This file is what mobile changes.

Distilled 2026-10-04 from [emilkowalski/skills](https://github.com/emilkowalski/skills) (MIT), with
the Reanimated API verified against `react-native-reanimated@4.5.1` and `react-native-worklets@0.10.1`
— the versions Expo SDK 57 bundles. `dev-flow/references/resources.md` has the row.

## Three things mobile changes, and everything else follows

1. **There is no hover.** Every affordance the web puts in hover has to live in press, in position,
   or nowhere. It is not a port, it is a redesign.
2. **There are two runtimes.** The React Native runtime, where React renders and app logic runs, and
   the UI runtime, where worklets run every frame. **An animation that touches the RN runtime stutters
   the moment the app does anything else.** The whole craft is keeping motion on the UI runtime.
3. **The user's finger is on the element.** Interruptibility and velocity handoff are not polish, they
   are the baseline.

## The gate, with mobile's own frequency table

| How often | Decision |
|---|---|
| **100+/day** — tab switches, keyboard open/close, scrolling, settings toggles | **No animation.** Platform default or nothing. |
| **Tens/day** — press feedback, list navigation, row selection | Under 150 ms, or nothing |
| **Occasional** — sheets, modals, toasts, onboarding steps | Standard animation |
| **Rare / first-time** — success, empty states, celebration | The delight budget |

**Tab switches never slide.** Tabs are peers, not a hierarchy — a slide implies depth that is not
there, and the user pays for it dozens of times a session. `animation: 'none'`.

**Screen transitions are the platform's, not yours.** Match the platform for navigation (iOS push is
350 ms) and beat it everywhere else. A screen transition rebuilt in JS is always worse than the native
stack's.

## Reach for the platform before reaching for a worklet

The cheapest tool is usually one that already exists. Walk down and stop at the first that fits:

| Need | Tool |
|---|---|
| A state-driven change — press, toggle, colour, a value flipping | Reanimated **CSS transition** (`transitionProperty` in the style) |
| A loop, multi-stage, or plays on mount | Reanimated **CSS animation** (`animationName` keyframes) |
| Mounting / unmounting, or a list reflowing | **Layout animations** (`entering` / `exiting` / `itemLayoutAnimation`) |
| Anything a finger touches, or derived from scroll | `useSharedValue` + `Gesture` + `useAnimatedStyle` |
| Screen to screen | **native stack options in Expo Router** — never hand-rolled |
| A bottom sheet that is its own screen | **`presentation: 'formSheet'`** — a real `UISheetPresentationController`, free and correct |
| Tab bar | **`NativeTabs`** (`expo-router/unstable-native-tabs`) — the platform's tab bar with its own behaviours |
| Context menu, press-and-hold preview | **`Link.Menu` / `Link.Preview`** (Expo Router, iOS) |
| A header collapsing into a large title | **`headerLargeTitleEnabled`** on the native stack (iOS; `headerLargeTitle` is deprecated) — not a scroll worklet |
| Pull to refresh | **`RefreshControl`**, unless it is a signature interaction |
| UI that tracks the keyboard | **`react-native-keyboard-controller`** — the keyboard's real position, frame by frame, on the UI thread |
| Vector illustration, celebration | **Lottie** — illustration only, never UI state |
| A huge animated scene, freeform drawing | **`@shopify/react-native-skia`** |

A press scale is a CSS transition; a drag is a shared value. **Using a worklet for a two-state toggle
is the mobile equivalent of installing a motion library for a fade.** `[VERIFY]` the Expo Router
entries against the installed SDK — `NativeTabs` is still on an `unstable-` subpath.

## Properties: what is free and the one exception

`transform` and `opacity` are free. **Everything else is a layout pass**: `width`, `height`, `margin`,
`padding`, `flex`, `top`, `left`, `gap` re-run Yoga every frame for that node *and its siblings*.

- **The exception, and it is a real one: an absolutely positioned element with no children** — a tab
  pill, a progress-bar fill. It is out of flow so nothing else re-lays-out, and animating `width`
  keeps the corner radius that `scaleX` would smear.
- **`transform` is an array and order matters.** `[{ translateY }, { scale }]` scales after moving;
  reversed, the translate gets scaled too.
- **Never animate Android `elevation`** — it re-renders the shadow every frame. Crossfade the opacity
  of a pre-shadowed layer.
- **Never animate `BlurView` intensity** — on Android it re-renders the blur each frame. Crossfade a
  static `BlurView`.
- **Never animate to a hardcoded height.** `allowFontScaling` is on by default, so a height measured
  at default type size is wrong at 200%. Measure with `onLayout`, or animate a transform.

## Springs: Reanimated takes Apple's two parameters directly

Use this form, not mass/stiffness/damping:

| Interaction | Config |
|---|---|
| Default settle, no overshoot | `{ duration: 400, dampingRatio: 1 }` |
| Reposition / snap back after a drag | `{ duration: 400, dampingRatio: 0.8, velocity }` |
| Sheet, drawer | `{ duration: 300, dampingRatio: 0.8, velocity }` |
| Must not pass a hard edge | add `overshootClamping: true` |

**If a finger was involved, use a spring** — it carries velocity through an interruption. Everything
else uses timing, and the curves are the web's: `Easing.bezier(0.23, 1, 0.32, 1)` for UI,
`Easing.bezier(0.77, 0, 0.175, 1)` for on-screen movement, `Easing.bezier(0.32, 0.72, 0, 1)` for an
iOS sheet. Reanimated's built-ins are as weak as CSS's, and **`Easing.in(...)` on UI is wrong** for
the same reason `ease-in` is.

**Bounce only when the gesture carried momentum.** Overshoot on a menu that faded in feels wrong;
overshoot on a card you flicked feels right.

The two worklets worth keeping in the project, because they are what make a flick feel thrown:

```js
// Where the finger would come to rest if it kept decelerating.
// Apple's exponential-decay form — not the v²/2a from physics class.
function project(velocity, decelerationRate = 0.998) {
  'worklet';
  return ((velocity / 1000) * decelerationRate) / (1 - decelerationRate);
}

// The further past the edge, the less the element follows.
function rubberband(overshoot, dimension, constant = 0.55) {
  'worklet';
  return (overshoot * dimension * constant) / (dimension + constant * Math.abs(overshoot));
}
```

Dismiss on **velocity or distance**, never distance alone — a flick should be enough.

## Press, because there is no hover

- **Feedback on press-in, commit on press-out.** Waiting for the tap to complete before showing
  anything feels dead; this is the latency a user actually perceives.
- **`scale: 0.97` in 100–150 ms** on any pressable. `scale` takes the label and icons with it, which
  is what makes it physical.
- **44×44 pt minimum touch target** (48 dp Android). If the visual is smaller, add **`hitSlop`** —
  never grow the visual.
- **`pressRetentionOffset`** so a finger drifting a few pixels does not cancel a press the user meant.
- **Android ripple only in a Material-styled app.** In a custom-designed app the same scale on both
  platforms is more coherent than a ripple on one.

## Haptics — the sense the web does not have

Used sparingly it is the thing that makes an app feel expensive. Used everywhere, users turn it off.

| Moment | Call |
|---|---|
| A value ticks past a step — picker, slider detent, segmented control | `Haptics.selectionAsync()` |
| Something snaps home, a sheet detent catches, a drag commits | `Haptics.impactAsync(ImpactFeedbackStyle.Light)` |
| A heavy object lands, a destructive action fires | `Haptics.impactAsync(ImpactFeedbackStyle.Medium)` |
| Succeeded or failed | `Haptics.notificationAsync(NotificationFeedbackType.Success / Error)` |

Three rules, and they are absolute:

- **Same frame as the visual.** A haptic that lags its animation reads as a glitch, not feedback. Fire
  it at the causal moment — the detent catching — not when the animation finishes.
- **One per user action.** Never on scroll, never per frame, never on an entrance the user did not cause.
- **Never the only feedback.** Haptics are off system-wide for many users and silent on most Android
  hardware. The visual has to stand alone.

From a worklet: `scheduleOnRN(Haptics.selectionAsync)`.

## Reduced motion

```jsx
const reduced = useReducedMotion();
withSpring(0, { duration: 300, dampingRatio: 0.8, reduceMotion: ReduceMotion.System });
```

Fewer and gentler, not zero: keep opacity and colour changes that explain a state change, drop
translation, scale, parallax and overshoot. Screen transitions become `animation: 'fade'`.

## Setup that silently breaks motion — check these first when "it just doesn't run"

- **`npx expo install`, never `npm install`** — it resolves the version matching the SDK.
  `babel-preset-expo` configures the worklets Babel plugin automatically; only a bare RN project adds
  it by hand, and there it must be **last**. A missing plugin no longer falls back silently — it
  throws `Failed to create a worklet` at runtime.
- **`GestureHandlerRootView` must wrap the app**, or gestures do nothing, with no error.
- **Reanimated 4 requires the New Architecture.**
- **120 fps needs a flag.** On ProMotion iPhones third-party animations are capped at 60 unless
  `CADisableMinimumFrameDurationOnPhone` is set in `infoPlist`. Recent Expo SDKs set it by default —
  confirm it rather than assume. With it, the frame budget is 8 ms, not 16, which is why keeping motion
  off the RN runtime matters more here than on web.

## ⚠️ Feel is judged on a release build, on the slowest device you support

**Expo Go is not a performance environment**, and neither is a dev build: its JS thread is slow enough
to *hide* exactly the problems you are looking for, and fast enough on your own flagship to hide the
rest. The simulator cannot judge a gesture at all. Nothing else counts as verified — and that is the
same rule as `before-you-build.md`'s: say which of your claims you verified and which need the device.

## Never ship

| Never | Instead |
|---|---|
| `PanResponder` | `Gesture.Pan()` |
| `setState` in a gesture or scroll handler | shared value + `useAnimatedStyle` |
| `runOnJS` / `runOnUI` (deprecated in Reanimated 4) | `scheduleOnRN` / `scheduleOnUI` from `react-native-worklets` |
| `scheduleOnRN` per frame | `onEnd`, or `useAnimatedReaction` at a threshold |
| Reading or writing a shared value during render | `.get()` / `.set()` in worklets, handlers, effects |
| Core `Animated` for anything a finger touches | Reanimated |
| Animating `height` / `width` / `margin` / `flex` / `top` | `transform` + `opacity` (absolute childless elements exempt) |
| Animating `BlurView` intensity or Android `elevation` | crossfade a static layer |
| `entering` on a virtualized list row | animate the container, or `itemLayoutAnimation` |
| A screen transition rebuilt in JS | native stack `animation` |
| Sliding between tabs | `animation: 'none'` |
| `Easing.in(...)` on a UI element | `Easing.bezier(0.23, 1, 0.32, 1)` |
| `scale(0)` entrance | `scale(0.95)` + `opacity: 0` |
| Distance-only dismissal threshold | velocity **or** distance |
| A hard stop at a boundary | `rubberband()` resistance |
| A haptic per frame, or as the only feedback | one per commit, always with a visual |
| Judging feel in Expo Go or the simulator | release build, slowest supported device |
