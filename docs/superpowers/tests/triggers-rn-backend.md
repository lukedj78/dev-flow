# Trigger acceptance list — rn-backend

## Should trigger (3+)
1. "Configura il backend per la mia app"
2. "Setup auth con Supabase" / "Setup auth con Firebase" / "Connetti il mio backend Node"
3. "Come gestisco il refresh token sicuro?"

## Should NOT trigger (3+)
1. "Aggiungi una schermata di login" → expect rn-add-screen (UI only — questa skill copre il client-auth)
2. "Stila il form" → expect rn-styling
3. "Push notification setup" → expect rn-push-notifications

## Anti-patterns the skill content MUST forbid
1. **Token in AsyncStorage** — usa `expo-secure-store` (Keychain iOS / Keystore Android).
2. Header `Authorization` hardcoded nell'`api()` wrapper senza un middleware refresh-on-401.
3. Auth state in un solo Zustand store senza replica in TanStack Query (`["auth", "session"]`) — perdi refetch-on-focus + offline persistence.
4. Polling `getUser()` ogni N secondi per "sapere se è loggato" — usa onAuthStateChange/realtime subscription.
5. Salvare la password in plain dentro lo store — MAI. Solo il token.
