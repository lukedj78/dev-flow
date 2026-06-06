# Trigger acceptance list — promote-component

## Should trigger (3+)
1. "Scansiona candidati di promozione" / "scan promotion candidates"
2. "Promovi PostCard a L2 nel dominio post"
3. "Questo componente UserAvatar è ovunque, mettilo nei shared"

## Should NOT trigger (3+)
1. "Crea un nuovo componente PostCard" → expect rn-add-screen / screenshot-to-page
2. "Refactor questo componente con compound" → expect composition-patterns-guide
3. "Scaffolda il progetto" → expect design-md-to-app / rn-bootstrap

## End-state after scan
1. Tabella con candidati: nome, usi, livello attuale, suggerimento.
2. Per `framework="monorepo"`: 2 tabelle separate, una per `apps/web/` e una per `apps/mobile/`.
3. Per ogni componente con 3+ usi suggerisce livello target.

## End-state after promote
1. File spostato al nuovo path (L1 o L2).
2. Duplicati eventuali rimossi.
3. Tutti gli import in `app/` e `components/` aggiornati al nuovo path.
4. `npx tsc --noEmit` passa.
5. Commit atomico `refactor: promote <Name> to <Level>`.
6. `meta.json#history` appended.
