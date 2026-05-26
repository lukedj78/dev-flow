# Trigger acceptance list — rn-styling

## Should trigger (3+)
1. "Stila questa schermata con dark mode"
2. "Configura NativeWind dal mio DESIGN.md"
3. "Ho un componente che ignora la safe area su iPhone, fixalo"

## Should NOT trigger (3+)
1. "Aggiungi una nuova route a /settings" → expect rn-expo-router
2. "Anima il pulsante al press" → expect rn-animations-gestures (Wave 3)
3. "Fetch dei posts da API" → expect rn-data-fetching (Wave 2)

## Anti-patterns the skill content MUST forbid
1. Magic numbers in inline `style={{ padding: 16 }}` — must use tokens.
2. Root screen without `SafeAreaView` from `react-native-safe-area-context`.
3. Importing `tailwindcss` directly (must go through NativeWind v4).
4. Using `Appearance.getColorScheme()` at module top-level instead of `useColorScheme()` (doesn't update reactively).
5. Using `Image` from `react-native` for remote images (must use `expo-image`).
