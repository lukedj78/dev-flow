# Design — Monorepo skill set for dev-flow

**Data**: 2026-05-29
**Stato**: draft → da implementare (4 ondate, ~6 ore stimate)
**Risolve**: la lacuna documentata in `2026-05-16-rn-expo-skills-set-design.md` §10 ("Esclusioni esplicite — monorepo") e il path 3 esposto nella discussione "fammi una guida" (5/29).

## 1. Obiettivo

Aggiungere il terzo path `stack.framework="monorepo"` al sistema dev-flow, con 3 nuove skill che gestiscono:

1. **`monorepo-bootstrap`** (operativa): scaffolda un repo turborepo + pnpm workspaces con `apps/web/` + `apps/mobile/` + `packages/{shared,design,api}/`, invocando in sequenza `design-md-to-app` (in `apps/web/`) e `rn-bootstrap` (in `apps/mobile/`).
2. **`monorepo-add-shared-package`** (operativa): estrai logica (types, utilities, Zod schemas) in `packages/shared/`, aggiorna imports nelle app, gestisce TS path mapping.
3. **`monorepo-sync-types`** (operativa): genera tipi backend (Supabase / tRPC) UNA volta + li espone via `packages/shared/types/`.

E pacche minimaliste alle skill operative web/mobile esistenti per renderle monorepo-aware (leggere `meta.json#stack.framework="monorepo"` e operare nella sub-cartella giusta).

## 2. Decisioni chiave

1. **Provider monorepo**: **pnpm workspaces + turborepo**. Standard de-facto 2026, supportato bene da Expo (richiede `expo-monorepo-config-utils`) e Next.js (zero config).
2. **Una sola `.workflow/`** in root, condivisa. UN solo PRD, UN solo DESIGN.md.
3. **`meta.json#stack.framework="monorepo"`** + nuova chiave `stack.monorepo` che è un oggetto:
   ```json
   "stack": {
     "framework": "monorepo",
     "monorepo": {
       "web": { "framework": "next", "ui": "shadcn" },
       "mobile": { "framework": "expo-rn", "ui": "nativewind" }
     },
     "auth": "supabase",
     "db": "supabase",
     "storage": "supabase",
     "payments": "revenuecat",
     "deploy": "eas+vercel"
   }
   ```
4. **Backend condiviso**: scelto al livello root (auth/db/storage/payments) — entrambe le app lo consumano via `packages/api/` (Supabase client o tRPC).
5. **Design tokens condivisi**: il DESIGN.md root genera `packages/design/` che emette **2 output**: un Tailwind preset per `apps/web/tailwind.config.js` + un NativeWind config per `apps/mobile/tailwind.config.js`.
6. **Niente UI cross-platform** (es. Tamagui): scelto come `non goal` perché aumenta complessità e copre solo il 30% dei casi. Web usa shadcn/Base-UI/MUI, mobile usa NativeWind, **componenti specifici per piattaforma**.
7. **Patches minime alle skill esistenti**: `module-add` e `rn-module-add` leggono `meta.json#stack.framework`; se è `monorepo`, operano in `apps/web/` o `apps/mobile/` rispettivamente. Tutte le altre skill (`design-md-to-app`, `rn-bootstrap`, `rn-add-screen`, `screenshot-to-page`) leggono `stack.framework` e — se `monorepo` — operano nella sub-cartella di pertinenza. Patches sono additive, non riscritture.

## 3. Architettura output

```
~/projects/myapp/                  ← user runs dev-flow here
├── .workflow/                     ← ONE workflow, shared
│   ├── PROJECT.md                 ← strategic brief (audience, problem, ...)
│   ├── PRD.md                     ← user stories (cover BOTH web + mobile)
│   ├── DESIGN.md                  ← tokens (palette, type, radii) — single source
│   └── meta.json                  ← phase, stack.monorepo, history, artifacts
├── apps/
│   ├── web/                       ← Next.js + shadcn (scaffolded by design-md-to-app)
│   │   ├── app/, components/, ...
│   │   ├── package.json
│   │   └── tailwind.config.js (consumes @myapp/design preset)
│   └── mobile/                    ← Expo + RN + NativeWind (scaffolded by rn-bootstrap)
│       ├── app/, components/, ...
│       ├── package.json
│       └── tailwind.config.js (consumes @myapp/design preset)
├── packages/
│   ├── shared/                    ← TS types, Zod schemas, utilities, business logic
│   │   ├── src/
│   │   │   ├── types/
│   │   │   ├── validators/
│   │   │   └── utils/
│   │   └── package.json (name: @myapp/shared)
│   ├── design/                    ← DESIGN.md → 2 outputs
│   │   ├── src/
│   │   │   ├── tokens.ts          ← generated from DESIGN.md
│   │   │   ├── tailwind-preset.ts ← consumed by apps/web/
│   │   │   └── nativewind-preset.ts ← consumed by apps/mobile/
│   │   └── package.json (name: @myapp/design)
│   └── api/                       ← Backend client (Supabase / tRPC)
│       ├── src/
│       │   ├── client.ts          ← supabase.from(...) or trpc.useQuery
│       │   ├── auth.ts
│       │   └── queries/
│       └── package.json (name: @myapp/api)
├── pnpm-workspace.yaml
├── turbo.json
├── package.json (root, with workspaces glob)
└── tsconfig.base.json (path aliases for @myapp/*)
```

**Cosa NON facciamo** (YAGNI):
- ❌ `packages/ui/` con componenti cross-platform. Le UI restano specifiche per app.
- ❌ Code splitting cross-platform a runtime. Ogni app è build separato.
- ❌ Supporto a Yarn / npm workspaces / nx / bazel. Solo pnpm + turborepo.
- ❌ Supporto a `framework="monorepo"` quando una delle 2 sub-app cambia stack a metà (es. da next a astro). Hard refactor manuale.

## 4. Inventario delle nuove skill

| Skill | Tipo | Trigger | Effort |
|---|---|---|---|
| **`monorepo-bootstrap`** | operativa con scripts | Phase `prd_drafted` + `stack.framework="monorepo"`. "scaffolda monorepo", "bootstrap turborepo with web + mobile" | 3h |
| **`monorepo-add-shared-package`** | operativa knowledge-driven | "estrai questa logica in shared", "spostala in packages/shared", "create a shared package" | 1h |
| **`monorepo-sync-types`** | operativa con script | "rigenera i tipi da Supabase", "sync backend types", "sync DB schema to packages/shared/types" | 1h |

## 5. Phase machine (monorepo path)

```
empty → idea_captured → prd_drafted
      → design_extracted (if user provides DESIGN.md/Figma)
      → monorepo_initialized (turborepo skeleton + pnpm-workspace.yaml)
      → scaffolded (apps/web + apps/mobile exist, both runnable)
      → page_generated (at least one route in either app)
      → module_added (auth/db/etc. wired in packages/api/ + consumed by both apps)
      → feature_complete
      → deployed (web on Vercel + mobile on EAS)
```

**Nuova phase**: `monorepo_initialized`. Solo per `stack.framework="monorepo"`. È il momento tra "abbiamo turborepo scaffold" e "abbiamo entrambe le app dentro pronte".

## 6. Anatomia di `monorepo-bootstrap`

```
monorepo-bootstrap/
├── SKILL.md                       (operativa, full workflow)
├── references/
│   ├── contracts.md               (vendored)
│   ├── structure.md               (layout completo, package.json roots)
│   ├── decision-tree.md           (pnpm vs npm? turborepo vs nx? Tamagui no?)
│   ├── patterns.md                (turbo.json pipelines, workspaces protocols)
│   └── post-bootstrap-checklist.md
└── scripts/
    ├── init-monorepo.sh           (pnpm-workspace.yaml + turbo.json + tsconfig.base.json)
    ├── scaffold-web.sh            (invokes design-md-to-app inside apps/web/)
    ├── scaffold-mobile.sh         (invokes rn-bootstrap inside apps/mobile/)
    └── verify.ts                  (post-bootstrap: pnpm install OK, turbo dev runs)
```

## 7. Patches alle skill esistenti

### `dev-flow/SKILL.md`
Aggiungere alla tabella di routing:
```
| monorepo | turborepo monorepo | monorepo-bootstrap | references/stack-monorepo.md |
```

### `dev-flow/references/stack-monorepo.md` (NUOVO)
Documenta:
- Identifier: `stack.framework="monorepo"`
- Routing per phase: `prd_drafted → monorepo-bootstrap`, `monorepo_initialized → monorepo-bootstrap (continues with scaffold-web + scaffold-mobile)`, `scaffolded → screenshot-to-page (in apps/web/) o rn-add-screen (in apps/mobile/) o module-add o rn-module-add`, ecc.
- Skill che NON girano direttamente in `apps/web/` o `apps/mobile/` ma operano sui packages: `monorepo-add-shared-package`, `monorepo-sync-types`.

### `prd-from-idea/SKILL.md`
Q6 mappa "both / monorepo" → `stack.framework="monorepo"`. Q7 per la web side resta (shadcn/Base UI/MUI). Mobile side è fissato a `nativewind`.

### `module-add/SKILL.md`
Verificare `stack.framework`. Se `monorepo`:
- Modules che sono backend client (auth/db/storage/realtime) → installati in `packages/api/`, esposti a entrambe le app.
- Modules che sono web-specific (motion, email — server actions) → installati in `apps/web/`.
- `payments`: web side va in `apps/web/` (Stripe checkout), mobile side va in `apps/mobile/` (RevenueCat) — devono fare cose distinte, segnala chiaramente.

### `rn-module-add/SKILL.md`
Identico ma da prospettiva mobile. Se `monorepo`:
- Reading `meta.json#stack.framework`, opera in `apps/mobile/`.
- Per shared backend (auth/db) consuma da `packages/api/` invece di reinstallare.

## 8. Ordine di build (4 ondate)

### Ondata A — Spec + scaffold + dev-flow extension (~1h)
- Questo spec doc
- Scaffold dirs delle 3 nuove skill
- `dev-flow/references/stack-monorepo.md`
- Patches a `dev-flow/SKILL.md` + `prd-from-idea/SKILL.md`

### Ondata B — `monorepo-bootstrap` skill (~3h)
- SKILL.md
- references (5 file)
- scripts (4 file)
- Trigger list

### Ondata C — Shared packages skills + module-add patches (~2h)
- `monorepo-add-shared-package` (SKILL.md + 2 refs)
- `monorepo-sync-types` (SKILL.md + 1 script + 2 refs)
- Patches a `module-add/SKILL.md` (monorepo branch in workflow)
- Patches a `rn-module-add/SKILL.md` (monorepo branch in workflow)

### Ondata D — Docs alignment (~30min)
- `install.sh` + `uninstall.sh`: aggiungere le 3 nuove skill
- `README.md`: aggiungere sezione "Monorepo (web + mobile)" sotto le 24 (ora diventano 27)
- `dist/`: generare 3 nuovi bundle `.skill`
- `skills.json`: rigenerato
- Lint passes, CI verde

## 9. Validazione

- Lint `lint_skills.py` passes (frontmatter, cross-refs, snake_case phase, ecc.)
- `build_skills_registry.py` rigenera 27 skill (3 core + 6 web + 15 mobile + 3 monorepo)
- Trigger acceptance lists per le 3 nuove skill
- No smoke test E2E in questa fase (richiederebbe scaffold turborepo + Expo + Next.js — 10+ min e ~500MB di download). Smoke test rimandato al primo progetto reale che useremo per validare.

## 10. Esclusioni esplicite (YAGNI)

- ❌ Supporto a yarn / npm workspaces. Solo pnpm.
- ❌ Supporto a nx. Solo turborepo.
- ❌ Componenti UI cross-platform (Tamagui, Restyle).
- ❌ Migrazione automatica "app esistente Next.js" → "monorepo con web+mobile". Manuale.
- ❌ Multi-app web (es. apps/web-admin + apps/web-marketing). Una sola web app per ora.
- ❌ Workspace mobile multi-target (Expo native + Expo Web). NativeWind sì, ma Expo Web come "ulteriore app" no.

## 11. Decisioni rimaste aperte (da chiudere in implementazione)

- Versione esatta di turborepo / pnpm al momento del bootstrap.
- Se aggiungere `nx` come alternativa in `decision-tree.md` o lasciare YAGNI.
- Se patchare `screenshot-to-page` e `rn-add-screen` esplicitamente per monorepo-awareness o lasciare che leggano `cwd` come fanno già.
