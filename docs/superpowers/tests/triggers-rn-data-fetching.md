# Trigger acceptance list — rn-data-fetching

## Should trigger (3+)
1. "Carica i posts da questa API e mostrali"
2. "Aggiungi infinite scroll alla lista feed"
3. "Mutazione optimistica per il like di un post"

## Should NOT trigger (3+)
1. "Stila la lista" → expect rn-styling
2. "Configura Supabase" / "Configura Firebase" / "Connetti il backend" → expect rn-backend (Wave 3, provider-agnostic)
3. "Naviga al dettaglio" → expect rn-expo-router

## Anti-patterns the skill content MUST forbid
1. `fetch + useEffect` per data produttiva (no cache, no retry, no dedup) → usa TanStack Query.
2. `useState + useEffect` per stato server (loading/error/data manuali) → usa TanStack Query.
3. Chiamate API senza cancel-on-unmount → race condition.
4. Mutazioni senza `invalidateQueries` → cache stale.
5. Refetch su ogni focus senza `staleTime` → richieste sprecate.
