# Trigger acceptance list — rn-animations-gestures

## Should trigger (3+)
1. "Anima questo pulsante al press con scale e opacity"
2. "Aggiungi swipe-to-delete su questa riga della lista"
3. "Fai un'animazione di entrata fade-in sulla schermata"

## Should NOT trigger (3+)
1. "Stila il bottone con dark mode" → expect rn-styling
2. "Aggiungi una nuova route" → expect rn-expo-router
3. "Fetch dei posts" → expect rn-data-fetching

## Anti-patterns the skill content MUST forbid
1. Legacy `Animated` API per nuove animazioni — usa Reanimated 4.
2. `setState` dentro un worklet — i worklet girano su UI thread, lo state React no. Usa `runOnJS()`.
3. `useAnimatedStyle` che legge state React invece di shared values — non sarà reattivo nel worklet.
4. `PanResponder` per gestures — usa Gesture Handler 2.
5. Animazioni dipendenti dal layout senza `runOnUI` o senza `measure()` — race condition.
