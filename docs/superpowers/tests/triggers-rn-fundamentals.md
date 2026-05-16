# Trigger acceptance list — rn-fundamentals

This skill MUST be selected by the agent when the user asks something matching these patterns:

## Should trigger (3+)
1. "Sto iniziando un nuovo progetto React Native, da dove parto?"
2. "Cosa cambia tra Expo managed e bare workflow?"
3. "Mi spieghi la New Architecture di RN (Fabric, Hermes, JSI)?"

## Should NOT trigger (3+)
1. "Aggiungi una schermata di login" → expect rn-add-screen (Wave 2) or rn-expo-router
2. "Stila questa card con dark mode" → expect rn-styling
3. "Configura Stripe nel mio progetto Next.js" → expect module-add (Next.js stack)

## Anti-patterns the skill content MUST forbid
1. Using `react-native init` (CLI bare) when Expo managed works — Expo is default.
2. Using legacy "Old Architecture" without justification — New Architecture default ON.
3. Mixing Yarn + npm in the same project — pick one (npm by default).
