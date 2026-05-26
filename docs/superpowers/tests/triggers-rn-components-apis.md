# Trigger acceptance list — rn-components-apis

## Should trigger (3+)
1. "Come uso ScrollView vs FlatList?"
2. "Come gestisco il keyboard avoidance su iOS?"
3. "Quale primitive devo usare per un pulsante in RN?"

## Should NOT trigger (3+)
1. "Stila questo bottone con Tailwind" → expect rn-styling
2. "Naviga alla schermata profilo" → expect rn-expo-router
3. "Fai una chiamata API" → expect rn-data-fetching

## Anti-patterns the skill content MUST forbid
1. `TouchableOpacity` / `TouchableHighlight` in nuovo codice → usa `Pressable`.
2. `Image` da `react-native` per URL remote → usa `expo-image`.
3. `FlatList` per liste con > 20 item → usa `@shopify/flash-list`.
4. `Dimensions.get('window')` al top-level → usa `useWindowDimensions()` nel componente.
5. `KeyboardAvoidingView` senza `behavior` → causa layout broken su Android.
