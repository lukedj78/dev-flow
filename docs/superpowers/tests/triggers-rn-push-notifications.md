# Trigger acceptance list — rn-push-notifications

## Should trigger (3+)
1. "Aggiungi le push notification all'app"
2. "Mostra una local notification quando arriva un nuovo messaggio"
3. "Naviga alla schermata X quando l'utente tocca la notifica"

## Should NOT trigger (3+)
1. "Configura il backend" → expect rn-backend (Wave 3)
2. "Stila la card" → expect rn-styling
3. "Animazione del badge" → expect rn-animations-gestures

## Anti-patterns the skill content MUST forbid
1. Push token ricevuto e poi inviato in chiaro via fetch → MAI senza HTTPS + auth header.
2. `setNotificationHandler` chiamato dentro un componente — deve essere a livello modulo (esegue una volta).
3. Request permissions all'avvio dell'app — pessima UX. Chiedi al momento giusto (signup, opt-in).
4. Salvare il push token in AsyncStorage in chiaro → usa expo-secure-store o lascia che il server lo gestisca.
5. Deep link da notifica gestito con `useEffect` + `Linking.addEventListener` invece di `Notifications.addNotificationResponseReceivedListener` → race condition al cold start.
