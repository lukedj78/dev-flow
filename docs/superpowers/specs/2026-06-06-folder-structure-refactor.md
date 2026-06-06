# Spec — Folder structure refactor + composition patterns

**Data**: 2026-06-06
**Stato**: approvato (10 decisioni confermate utente)
**Risolve**: lacuna documentata nella conversation 2026-06-06: struttura cartelle generata da `design-md-to-app` e `rn-bootstrap` non è "parlante", `components/site/` è generico, manca pattern colocation chiaro, manca gestione esplicita dei componenti shared.

## 1. Obiettivo

Riallineare le 27 skill di dev-flow alle convenzioni 2026 dello state-of-the-art React/Next.js + Expo Router + Turborepo. Centro: **colocation radicale via `_components/`**, **componenti shared per dominio in `components/shared/<dominio>/`**, **promotion via Rule of Three**, nuova skill `promote-component` per refactor automatico.

## 2. Le 10 decisioni canonical

| # | Argomento | Scelta |
|---|---|---|
| 1 | Modello shared intra-app | 3 livelli: L0 page-private, L1 route-group, L2 global |
| 2 | Naming L2 | `components/shared/<dominio>/` (per dominio business) |
| 3 | L0/L1 folder | `_components/` (Next.js underscore convention) |
| 4 | `src/` directory | NO (codice a root, allineato a Vercel commerce + Cal.com) |
| 5 | Design system | Mix: `app/globals.css` + `components/theme/` |
| 6 | Route groups | Default intelligente (deduzione PRD), NON sempre tutti i 3 |
| 7 | Promotion threshold | Rule of Three (al 3° uso, non 2°) |
| 8 | Detection | On-demand + `scan candidates` command |
| 9 | React Native | Identica al web + adattamenti RN (`store/`, `assets/`, `hooks/`, `(tabs)/`) |
| 10 | Compound components | Soglia ~250 righe (file singolo default, cartella oltre) |

## 3. Fonti ufficiali (validazione)

- **Next.js 16.2 (Dec 2025)**, `getting-started/project-structure`: endorses `_folderName` private folders ("Separating UI logic from routing logic"), route groups `(name)`, esplicita che `components/` e `lib/` sono placeholder.
- **Expo Router**, `basics/notation`: conferma route groups + `_layout.tsx`; `_components/` underscore prefix è coerente col pattern Next.js.
- **Turborepo official** (`crafting-your-repository/structuring-a-repository`): NO `tsconfig.base.json` in root → `@<scope>/typescript-config` package; namespace `@<scope>/name`.
- **Vercel commerce template**: `components/<feature>/` flat (cart/, product/, grid/, layout/), NO `features/`, NO `src/`.
- **Cal.com**: `modules/` per scala 50+ domini (eccezione enterprise — non applicabile a noi).

## 4. Struttura finale — Web (Next.js)

```
<root>/
├── app/
│   ├── (marketing)/                  ← opzionale (deduzione PRD)
│   │   ├── _components/              ← L1: shared nel gruppo marketing
│   │   ├── _lib/                     ← (opzionale) marketing helpers
│   │   ├── layout.tsx                ← marketing layout
│   │   ├── page.tsx                  ← /
│   │   └── pricing/
│   │       ├── _components/          ← L0: page-private
│   │       └── page.tsx
│   │
│   ├── (auth)/                       ← opzionale (deduzione PRD)
│   │   ├── _components/
│   │   ├── layout.tsx
│   │   ├── sign-in/page.tsx
│   │   └── sign-up/page.tsx
│   │
│   ├── (app)/                        ← gated routes
│   │   ├── _components/              ← L1: AppShell, AppSidebar, AppHeader
│   │   ├── _lib/                     ← (opzionale) app-wide helpers
│   │   ├── layout.tsx                ← redirect a (auth) se !session
│   │   ├── dashboard/
│   │   │   ├── _components/
│   │   │   └── page.tsx
│   │   ├── posts/
│   │   │   ├── _components/          ← PostCard, PostList, PostFilter
│   │   │   ├── _lib/                 ← (opzionale)
│   │   │   ├── [id]/
│   │   │   │   ├── _components/
│   │   │   │   └── page.tsx
│   │   │   └── page.tsx
│   │   └── settings/
│   │       ├── _components/
│   │       └── page.tsx
│   │
│   ├── api/                          ← route handlers
│   ├── layout.tsx                    ← root: HTML + ThemeProvider
│   └── globals.css                   ← CSS variables + Tailwind directives
│
├── components/
│   ├── ui/                           ← shadcn/Base UI/MUI primitives
│   ├── theme/                        ← ThemeProvider, ModeToggle
│   └── shared/                       ← L2: per dominio business
│       ├── post/
│       │   ├── PostCard.tsx          ← compound singolo <250 righe
│       │   ├── PostList.tsx
│       │   └── DataTable/            ← compound complesso (>250 righe) → cartella
│       │       ├── DataTable.tsx
│       │       ├── Header.tsx
│       │       ├── Row.tsx
│       │       └── index.ts          ← barrel: export { DataTable }
│       ├── user/
│       │   ├── UserAvatar.tsx
│       │   └── UserMenu.tsx
│       └── billing/
│           └── PricingTable.tsx
│
├── lib/                              ← infrastruttura, NO business
│   ├── db/                           ← Drizzle/Prisma client + schema
│   ├── env.ts                        ← zod-validated env
│   ├── http.ts                       ← fetch wrapper
│   └── utils.ts                      ← cn(), formatters
│
├── hooks/                            ← cross-feature (useDebounce, useMediaQuery)
├── types/                            ← shared TS types
├── public/
├── package.json
├── next.config.ts
├── tailwind.config.ts
└── tsconfig.json
```

## 5. Struttura finale — React Native (Expo Router)

```
<root>/
├── app/
│   ├── (auth)/
│   │   ├── _components/
│   │   ├── _layout.tsx
│   │   └── sign-in.tsx
│   ├── (app)/
│   │   ├── _components/              ← TabBar, AppHeader, AuthGuard
│   │   ├── _layout.tsx               ← redirect a (auth) se !session
│   │   ├── (tabs)/                   ← bottom-tab nav (mobile-specific)
│   │   │   ├── _components/
│   │   │   ├── _layout.tsx           ← Tabs definition
│   │   │   ├── feed/
│   │   │   │   ├── _components/
│   │   │   │   └── index.tsx
│   │   │   └── profile/
│   │   │       ├── _components/
│   │   │       └── index.tsx
│   │   └── settings.tsx
│   └── _layout.tsx                   ← root: GestureHandlerRootView + providers
│
├── components/
│   ├── ui/                           ← NativeWind primitives
│   ├── theme/                        ← ThemeProvider, useThemeColor
│   └── shared/                       ← per dominio (stesso pattern web)
│       └── post/PostCard.tsx
│
├── lib/                              ← infrastruttura
│   ├── api.ts                        ← fetch wrapper
│   ├── supabase.ts                   ← client (se Supabase)
│   ├── secure-store.ts               ← token wrapper
│   └── utils.ts
│
├── store/                            ← Zustand cross-feature (mobile-specific)
│   ├── auth-store.ts
│   └── app-preferences-store.ts
│
├── hooks/                            ← RN-specific (useColorScheme, useKeyboard)
├── assets/
│   ├── images/
│   └── fonts/
├── tailwind.config.js
├── nativewind-env.d.ts
├── babel.config.js
├── metro.config.js
├── app.json
├── package.json
└── tsconfig.json
```

## 6. Struttura finale — Monorepo

```
<root>/
├── apps/web/                         ← struttura web sopra
├── apps/mobile/                      ← struttura mobile sopra
├── packages/
│   ├── design/                       ← DESIGN.md → Tailwind + NativeWind presets
│   ├── shared/                       ← types TS + Zod + utils (NO JSX)
│   ├── api/                          ← backend client
│   ├── typescript-config/            ← Turborepo official pattern
│   │   ├── base.json
│   │   ├── nextjs.json               ← extends base + Next opinions
│   │   ├── react-native.json         ← extends base + RN opinions
│   │   └── package.json (name: @<slug>/typescript-config)
│   └── eslint-config/
│       ├── base.js
│       ├── nextjs.js
│       ├── react-native.js
│       └── package.json (name: @<slug>/eslint-config)
├── pnpm-workspace.yaml
├── turbo.json
└── package.json (root)
```

**Cambio chiave vs monorepo precedente**: niente `tsconfig.base.json` in root. Le app extends da `@<slug>/typescript-config/<preset>.json`.

## 7. Le 3 regole di colocation

### Regola 1 — Default: tutto in `_components/` della page

Ogni nuovo componente nasce in `app/<route>/_components/<Componente>.tsx`. Niente eccezioni al primo uso.

### Regola 2 — Rule of Three per promotion

```
1° uso  → L0:  app/<route>/_components/PostCard.tsx
2° uso  → L0:  COPIA in app/<altra-route>/_components/PostCard.tsx (tolerated duplicate)
3° uso  → 🔔 PROMOZIONE:
            - se i 3 usi sono nello stesso route group → L1: app/(group)/_components/
            - se i 3 usi sono in route groups diversi → L2: components/shared/<dominio>/
```

Skill `promote-component` automatizza il movimento + l'aggiornamento degli import.

### Regola 3 — Cross-platform (monorepo): solo logica condivisa

```
✅ packages/shared/    ← types, Zod, hook puri (no JSX), utils
❌ packages/shared/    ← MAI componenti JSX

Componenti UI:
- apps/web/components/...    (DOM-specific)
- apps/mobile/components/... (Native-specific)
Importano la stessa logica da packages/shared/.
```

## 8. Sistema design tokens + theme

### CSS variables — `app/globals.css`

Convenzione Next.js default. Modificato da shadcn `init` automaticamente.

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --background: 0 0% 100%;
  --foreground: 240 10% 4%;
  --primary: 220 90% 56%;
  /* ... */
}

.dark {
  /* dark mode overrides */
}
```

### ThemeProvider — `components/theme/`

```
components/theme/
├── theme-provider.tsx   ← next-themes provider wrapper
├── mode-toggle.tsx      ← bottone light/dark
└── use-theme-color.ts   ← hook helper (RN: ritorna token color basato su colorScheme)
```

Importati in `app/layout.tsx`:

```tsx
import { ThemeProvider } from "@/components/theme/theme-provider";
import "./globals.css";

export default function RootLayout({ children }) {
  return (
    <html suppressHydrationWarning>
      <body>
        <ThemeProvider attribute="class" defaultTheme="system">
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
```

## 9. Default intelligente route groups

`prd-from-idea` Q6 raccoglie il target platform. Per `framework="next"` o `framework="monorepo"`, il sistema **deduce** dai Q1-Q5 quali route groups creare:

| Indicatori nel PRD | Route groups scaffoldati |
|---|---|
| SaaS con dashboard + login + landing pubblica | `(marketing)` + `(auth)` + `(app)` |
| Internal tool / B2B back-office | `(auth)` + `(app)` (no marketing) |
| Marketing site / blog | `(marketing)` solo |
| App consumer iOS+Android (mobile) | `(auth)` + `(app)` (mobile pattern: `(tabs)/` dentro `(app)`) |
| Documentation site | nessun group (struttura piatta) |

`design-md-to-app` (web) e `rn-bootstrap` (mobile) leggono i route groups da `meta.json#stack.route_groups` (nuovo campo, array) e generano solo quelli.

Override esplicito: in qualunque momento l'utente può dire "aggiungi `(marketing)`" e la skill crea il group.

## 10. Nuove skill da creare

### `promote-component` (operativa)

Scope: muovere un componente da L0 → L1 o L0 → L2, aggiornare tutti gli import nel codebase, verificare tsc.

**Trigger**:
- "promovi PostCard"
- "scan promotion candidates" → analisi globale + tabella suggerimenti

**Workflow `scan` command**:
1. Trova tutti i `*.tsx` in `app/**/_components/` e conta gli usi (grep `from .*<name>`).
2. Tabella: nome, numero usi, paths, suggerimento (L0/L1/L2).
3. L'utente sceglie quali promuovere.

**Workflow `promote <name>` command**:
1. Identifica il file sorgente.
2. Identifica il livello target dal numero di usi:
   - 2 usi → resta L0, segnala "Aspetta il 3°"
   - 3+ usi nello stesso group → L1
   - 3+ usi in group diversi → L2 (chiede il dominio se ambiguo)
3. `mv` del file al nuovo path.
4. `find-replace` su tutti gli import in app/.
5. `pnpm tsc --noEmit`.
6. Commit atomico: `refactor: promote <Name> from <old> to <new>`.

**Files**: `promote-component/SKILL.md`, `references/contracts.md` (vendored), `references/colocation-rules.md`, `scripts/scan_promotion.py`, `scripts/promote.py`.

### `composition-patterns-guide` (knowledge)

Scope: combinazione delle 7 regole Vercel `composition-patterns` + le nostre regole colocation (`promote-component`, Rule of Three, anti-pattern naming).

**Trigger**:
- "refactor questo componente"
- "troppi prop booleani"
- "compound components"
- "context provider per X"
- "design del componente"

**Files**: `composition-patterns-guide/SKILL.md`, `references/vercel-rules-distilled.md`, `references/our-colocation-rules.md`, `references/anti-patterns.md`.

## 11. Skill esistenti — modifiche puntuali

### `design-md-to-app/SKILL.md`

- **Removed**: la sezione "components/site/" — non esiste più.
- **Added**: Step "Detect route groups" — legge `meta.json#stack.route_groups` o deduce da PRD.
- **Added**: Step "Scaffold theme system" — genera `components/theme/{theme-provider.tsx, mode-toggle.tsx}`.
- **Modified**: il scaffold genera `app/(<group>)/_components/` invece di `components/site/`.

### `screenshot-to-page/SKILL.md`

- **Modified**: default destination per nuovi componenti = `app/<route>/_components/`.
- **Added**: detection del route group dalla path target.
- **Added**: promotion suggerita se il componente è simile a uno esistente (call out a `promote-component`).

### `module-add/SKILL.md`

- **Modified**: `auth` module → UI in `app/(auth)/_components/`, infra in `lib/auth/`.
- **Modified**: `db` module → `lib/db/`.
- **Modified**: `payments` module → UI in `app/(app)/_components/` o page-specific, server in `lib/payments/`.

### `rn-bootstrap/SKILL.md`

- **Modified**: scaffold genera `app/(auth)/`, `(app)/`, `(app)/(tabs)/` con `_components/` co-located.
- **Added**: scaffold di `store/`, `hooks/`, `assets/` top-level.
- **Removed**: `components/` flat → diventa `components/{ui,theme,shared}/`.

### `rn-add-screen/SKILL.md`

- **Modified**: default `app/<route>/_components/`. Mai più flat `components/`.
- **Added**: detection route group + promotion path.

### `rn-module-add/SKILL.md`

- Identico a `module-add` ma per RN. Auth client → `lib/`, UI → `app/(auth)/_components/`.

### `monorepo-bootstrap/SKILL.md`

- **Removed**: scaffold di `tsconfig.base.json` in root.
- **Added**: scaffold di `packages/typescript-config/` con `base.json`, `nextjs.json`, `react-native.json`.
- **Added**: scaffold di `packages/eslint-config/` con `base.js`, `nextjs.js`, `react-native.js`.
- **Modified**: web e mobile apps' tsconfig estende da `@<slug>/typescript-config/<preset>.json`.

### `prd-from-idea/SKILL.md`

- **Modified**: Q6 ora include logica per dedurre `route_groups` per `framework ∈ {next, monorepo}`. Scrive in `meta.json#stack.route_groups`.

### `dev-flow/references/contracts.md`

- **Added**: `stack.route_groups: Array<"(marketing)" | "(auth)" | "(app)" | "(tabs)">` (campo nuovo, opzionale).
- **Added**: sezione "Folder structure conventions" con riferimenti a questo spec.

## 12. Patches a `lint_skills.py` (anti-pattern detection)

- Check 1: nessun file in `components/shared/` ha nome `Card.tsx`, `Header.tsx`, `Button.tsx` (collisione con primitives) — must use domain prefix.
- Check 2: nessun import cross-route-group (`(app)/X` importa da `(marketing)/_components/`).
- Check 3: in monorepo, nessun import cross-app (`apps/web/` importa da `apps/mobile/`).
- Check 4: in monorepo, `packages/shared/` non contiene `*.tsx` (solo `.ts`).

## 13. Ordine di build — 4 ondate

| Ondata | Skill toccate | Effort |
|---|---|---|
| **A** | spec + plan + dev-flow contracts + prd-from-idea (route groups deduction) | 2h |
| **B** | design-md-to-app + screenshot-to-page + module-add + rn-bootstrap + rn-add-screen + rn-module-add + monorepo-bootstrap | 8h |
| **C** | promote-component (NEW) + composition-patterns-guide (NEW) | 5h |
| **D** | docs alignment (README, conventions.md, install.sh, uninstall.sh, dist/, skills.json) + lint_skills patches + CI verde | 2h |

**Totale**: ~17h. Procedo in autonomia, commit atomici, push per ondata.

## 14. Validazione

- Lint `lint_skills.py` passes con nuove check.
- `build_skills_registry.py` rigenera 29 skill (era 27, +2 nuove).
- Trigger acceptance lists per le 2 nuove skill.
- No smoke test E2E (richiederebbe scaffold reali) — il test definitivo è il primo progetto reale.

## 15. Esclusioni esplicite (YAGNI)

- ❌ `features/` folder (rifiutata esplicitamente).
- ❌ `modules/` folder (rifiutata).
- ❌ Detection automatica passiva (rifiutata — solo on-demand + scan).
- ❌ `src/` directory.
- ❌ Tamagui o UI cross-platform.
- ❌ Migrazione automatica progetti esistenti (vecchio → nuovo) — manuale.
