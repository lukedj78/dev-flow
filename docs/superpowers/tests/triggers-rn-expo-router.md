# Trigger acceptance list — rn-expo-router

## Should trigger (3+)
1. "Aggiungi una nuova route /profile/[id]"
2. "Configura tab navigation con 3 tab"
3. "Apri questa schermata come modale"

## Should NOT trigger (3+)
1. "Cambia il colore del button" → expect rn-styling
2. "Anima la transizione tra schermate" → expect rn-animations-gestures (Wave 3)
3. "Fai un fetch dei posts" → expect rn-data-fetching (Wave 2)

## Anti-patterns the skill content MUST forbid
1. Importing `react-navigation/native` directly — must go through `expo-router`.
2. Using non-typed routes (`href="/foo"` instead of typed routes).
3. Hardcoded routes scattered in components — must be centralized as constants OR use typed routes.
4. Putting layout logic in screen files instead of `_layout.tsx`.
