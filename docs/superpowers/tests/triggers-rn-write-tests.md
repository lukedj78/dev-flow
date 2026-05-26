# Trigger acceptance list — rn-write-tests

## Should trigger (3+)
1. "Scrivi i test per la schermata di login"
2. "Aggiungi test e2e per il flusso di onboarding"
3. "Mocka Expo Notifications in questo test"

## Should NOT trigger (3+)
1. "Bootstrap dell'app" → expect rn-bootstrap
2. "Stila il bottone" → expect rn-styling
3. "Aggiungi una nuova schermata" → expect rn-add-screen

## Anti-patterns the skill content MUST forbid
1. **Detox** — too heavy and Expo Go unfriendly. Use Maestro for e2e.
2. **Enzyme** — abandoned. Use React Native Testing Library.
3. Snapshot tests per ogni componente — solo per design system / componenti deliberatamente "shape-locked".
4. Mock di `expo-*` con `jest.fn()` puro senza tipi — usa il pattern `jest.mock("expo-...", () => ({ ... }))` documentato.
5. Test che dipendono dall'ordine — ogni test deve essere indipendente (e poter girare con `--shuffle`).
