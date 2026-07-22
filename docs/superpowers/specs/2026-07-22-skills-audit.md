# Skills audit — 2026-07-22

Audit completo dei 36 skill del repo (6 agenti paralleli, un batch per famiglia). Verdetti: **13 NOTEVOLE · 20 MINORE · 3 NESSUNO**. Nessuna modifica applicata — questo è il documento di valutazione.

## Temi trasversali (fix efficienti = un intervento risolve più skill)

### T1 — `contracts.md` vendorizzato stale (7 skill)
Le copie vendorizzate di `references/contracts.md` sono ferme a giugno e non hanno `stack.agent`, il blocco `linear`/`scrum`, né i campi shadcn CLI v4 (`ui_base`/`shadcn_preset`/`base_color`/`ui_theme`/`icon_library`/`css_variables`/`rtl`). Skill colpite: **prd-from-idea, prd-to-tasks, screenshot-to-page, figma-to-design-md, image-to-design-md, monorepo-bootstrap, monorepo-add-shared-package**. Inoltre il contract **canonico** (`dev-flow/references/contracts.md`) non elenca esplicitamente `"coss"` nell'enum `stack.ui`. Fix: correggere il canonico (aggiungere `coss`), poi ri-vendorizzare a tutte.

### T2 — nuove opzioni UI (Base UI standalone + Coss) non propagate
Skill che diramano sulla UI ma conoscono solo shadcn/MUI: **screenshot-to-page** (Step 4 cita solo shadcn/MUI), **module-add** (`module-auth`/`module-payments` non gestiscono base-ui/coss), **design-md-to-app** (description dice "three UI libraries"), **prd-from-idea** (interview UI senza `coss`).

### T3 — drift di versione RN (fonte: rn-bootstrap)
`rn-bootstrap/references/stack-defaults.md` è 2 major Expo SDK indietro (pin **55** vs reale **57**), `react-native-gesture-handler` pinnato su 2.x (ora `legacy`; latest 3.x), TypeScript 6 vs 7. Si propaga a valle (rn-add-screen, rn-module-add, rn-styling lo referenziano).

### T4 — bug concreti che rompono se copiati alla lettera (priorità massima)
- **write-tests** → `test-server-action.md` usa `getCurrentUserId` senza importarlo → `ReferenceError`.
- **rn-write-tests** → chiave Jest inesistente `setupFilesAfterEach` (corretta: `setupFilesAfterEnv`) → setup ignorato in silenzio.
- **rn-styling** + **rn-add-screen** → FlashList `estimatedItemSize` deprecato in v2.
- **coss-ui** → sezione "MCP option" in `coss-registry.md` **probabilmente inventata** (nessun server MCP Coss documentato). *(Skill appena mergiata — self-correction.)*

### T5 — gap feature di punta Next 16
**data-fetching** non copre **Cache Components / `"use cache"`** né `updateTag()` / nuova firma `revalidateTag` (mostra la forma deprecata a 1 argomento).

## Verdetti per skill

| Skill | Verdetto | Motivo sintetico |
|---|---|---|
| prd-from-idea | NOTEVOLE | contracts stale (T1); interview UI senza coss + niente domanda agent |
| prd-to-tasks | NOTEVOLE | contracts stale (T1); "Linear CSV" fuorviante → puntare a linear-scrum; formato riga task load-bearing per `task_key()` non documentato |
| coss-ui | NOTEVOLE | sezione MCP inventata (T4); `[VERIFY]` URL+licenza ora CONFERMATI (da irrigidire); enum `stack.ui` senza coss |
| screenshot-to-page | NOTEVOLE | solo shadcn/MUI (T2); contracts stale (T1); `npm` invece di `pnpm` |
| forms | NOTEVOLE | contraddizione col write-layer di data-fetching (chiama service dal client vs Server Action); `zod/v4` obsoleto; `stack.ui=mui` non gestito |
| data-fetching | NOTEVOLE | manca Cache Components/`use cache` (T5); `revalidateTag` forma deprecata; ambiguità SWR vs TanStack |
| monorepo-sync-types | NOTEVOLE | manca il branch `neon-drizzle` (DB di default reale) |
| monorepo-bootstrap | NOTEVOLE | variante "solo-web / web+agent" documentata ma non implementata; contracts stale (T1); niente `engines.node` |
| rn-bootstrap | NOTEVOLE | drift versioni (T3): Expo 55→57, gesture-handler legacy, TS 6→7 |
| rn-write-tests | NOTEVOLE | bug `setupFilesAfterEach` (T4) |
| rn-styling | NOTEVOLE | FlashList `estimatedItemSize` deprecato (T4) |
| rn-add-screen | NOTEVOLE | FlashList deprecato (T4); contraddizione interna folder (screen-patterns flat vs SKILL vieta) |
| rn-publishing-payments | NOTEVOLE | regole Apple pagamenti esterni cambiate (impatto economico) |
| dev-flow | MINORE | fresco; solo: sezione agent non cita dove si sceglie il service-tier |
| linear-scrum | MINORE | `[VERIFY]` ora troppo ampio; accoppiamento `task_key`↔prd-to-tasks non dichiarato |
| design-md-to-app | MINORE | description "three libraries"→quattro; eval non coprono Coss; handoff Coss OK |
| figma-to-design-md | MINORE | contracts stale (T1) |
| image-to-design-md | MINORE | contracts stale (T1) |
| module-add | MINORE | contracts senza `agent`; voice/realtime fuori da tabella cross-module + folder rules; auth UI ignora base-ui/coss (T2) |
| state-discipline | MINORE | mancano `useActionState`, `useEffectEvent`, `<Activity>` (React 19.2) |
| write-tests | MINORE | bug import nel template (T4); mancano pattern test TanStack Query/Form |
| promote-component | MINORE | regola cross-platform/`packages/` "morta", nessun link a monorepo-add-shared-package |
| composition-patterns-guide | MINORE | `colocation-rules.md` dichiara "kept in sync" ma è driftato; manca confine RSC |
| eve-agent | MINORE | service tier coerente ✓; assume `packages/types` ma nessuna skill lo crea |
| eve-registry-porting | MINORE | manca link alla sintassi approval di eve-conventions |
| monorepo-add-shared-package | MINORE | collisione semantica `packages/ui` con monorepo-bootstrap; contracts stale (T1) |
| rn-module-add | MINORE | cita "Expo SDK 54" |
| rn-eas-build-submit-update | MINORE | esempio `eas-cli ">= 5.0.0"` vs reale 21.x |
| rn-eas-deploy | MINORE | eredita esempio eas-cli |
| rn-fundamentals | MINORE | pin SDK 2 major indietro |
| rn-animations-gestures | MINORE | manca sezione Reanimated 4 CSS Animations |
| rn-expo-router | MINORE | ok, solo cenno RSC/API routes mancante |
| rn-data-fetching | MINORE | solo drift di patch TanStack Query |
| rn-backend | NESSUNO | principi stabili, verificati correnti |
| rn-push-notifications | NESSUNO | verificato allineato (no Expo Go post-SDK53) |
| rn-components-apis | NESSUNO | Pressable/expo-image/FlashList v2 tutti correnti |

## Piano di aggiornamento proposto (per priorità)

- **P0 — bug che rompono (T4)**: coss-ui MCP, write-tests import, rn-write-tests Jest key, FlashList v2 (rn-styling + rn-add-screen). Piccoli, alto impatto.
- **P1 — contract sync (T1)**: fix canonico (+`coss`) → ri-vendor a 7 skill. Meccanico, un colpo.
- **P2 — RN version bump (T3)**: aggiornare `rn-bootstrap/stack-defaults.md` a Expo 57 + gesture-handler 3 + TS 7 (verificare), refresh dei riferimenti SDK a valle.
- **P3 — propagazione UI (T2)**: coss/base-ui in screenshot-to-page, module-add, design-md-to-app description, prd-from-idea interview.
- **P4 — gap contenuto**: data-fetching (Cache Components), forms (write-layer + zod), monorepo-sync-types (neon-drizzle), monorepo-bootstrap (variante web/agent), rn-publishing-payments (Apple), state-discipline (React 19.2).
- **P5 — rifiniture MINORE varie**: i restanti.
