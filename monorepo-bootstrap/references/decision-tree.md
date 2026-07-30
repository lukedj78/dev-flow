> Sources: turborepo.dev/docs, pnpm.io/workspaces, docs.expo.dev/guides/monorepos, internal opinion.

# Decision tree — monorepo

## Q1: Do I really need a monorepo?

```
Will the same product ship to BOTH a web admin/dashboard AND a consumer mobile app
that share business logic, backend, and design tokens?
├── YES                              → monorepo, topology="web-mobile". The skill set fits this
│                                      as its primary case (apps/web + apps/mobile).
├── NO — but there's an eve agent    → monorepo, topology="web-agent" (apps/web + apps/agent,
│   engine behind the web app          no mobile). Still worth the turborepo/shared-package
│                                      scaffolding — see "The packages/ui rule" below.
├── NO — only web, no mobile/agent   → usually framework="next" (or astro/vite-react), no
│                                      monorepo. BUT you can still opt into
│                                      monorepo/topology="web-only" if you specifically want
│                                      the turborepo tooling + a shared-package layout (e.g.
│                                      anticipating a second web app or an agent later).
│                                      Don't do this "just in case" — see the wrong reasons below.
├── NO — only mobile                 → framework="expo-rn". Same — no monorepo.
└── KIND OF — web admin + landing    → could be a monorepo (apps/admin + apps/marketing)
                                       BUT v1 of this skill set only supports 1 web app (plus,
                                       depending on topology, 1 mobile app or 1 agent — never both
                                       admin+marketing as two separate web apps).
                                       If you genuinely need 2 web apps, fork the skill or wait for v2.
```

`monorepo-bootstrap` Step 1 detects or asks which of these three topologies (`web-mobile` / `web-agent` / `web-only`) applies and records it in `meta.json#stack.monorepo.topology` — every later step (packages/design vs packages/ui, whether `rn-bootstrap` runs) branches on it.

The wrong reasons to pick monorepo:
- "I want to share types between frontend and backend" — that's possible without monorepo (npm publish private packages, or git submodules) but a monorepo is the cleanest.
- "I want to use turborepo for caching" — turborepo works with non-monorepo too (single app). Don't reach for `topology="web-only"` just for this; it's meant for projects that genuinely anticipate a second app (mobile or agent) or a multi-web-app future.

## Q2: pnpm or yarn or npm?

```
Only pnpm. No discussion in v1.

Reasons:
- workspace:* protocol Just Works
- hard links save disk
- Expo officially recommends pnpm for monorepos
- turborepo has zero pnpm-specific bugs in 2026
```

If you have a strict reason to use yarn or npm, this skill set is not for you yet.

## Q3: turborepo or nx?

```
Only turborepo. No discussion in v1.

Reasons:
- minimal config (a single turbo.json)
- no opinions on file structure (unlike nx, which expects you to use generators)
- excellent caching
- Vercel + Expo + the broader ecosystem all assume turborepo first
```

nx is also good, but its opinions clash with the dev-flow contract. Future v2 could add a path.

## Q4: Which packages do I actually need?

```
Mandatory (created by monorepo-bootstrap):
- packages/shared/ — TS types, Zod schemas, business logic
- packages/design/ — design tokens + Tailwind/NativeWind presets
- packages/api/   — backend client + queries (filled later by module-add)

Optional, add later via monorepo-add-shared-package:
- packages/ui/ — see the UI-package rule below
- packages/config-eslint/ — IF you want shared lint configs
- packages/config-tsconfig/ — IF tsconfig.base.json isn't enough

Don't create packages "just in case". Make one when there's a real need.
```

### The `packages/ui` rule (shadcn shared components)

Whether `packages/ui` exists depends on whether the monorepo has a **NativeWind (mobile) side**:

- **Web + mobile** (`stack.monorepo.mobile` present): keep the default — shadcn components live in `apps/web/components/ui/`, only *tokens* are shared via `packages/design/`. Components can't cross the React-DOM / React-Native boundary, so a shared component package only helps with cross-platform UI (Tamagui) — rare/YAGNI.
- **Web-centric, no NativeWind consumer** (web-only, **web + agent**, or multiple web apps): use shadcn's **official monorepo layout** — `packages/ui` IS the shared component package (`@workspace/ui`), holding the primitives + `src/styles/globals.css` (DESIGN.md tokens), consumed by `apps/web`. This is canonical shadcn (<https://ui.shadcn.com/docs/monorepo>); `design-md-to-app` scaffolds it via `shadcn init --monorepo` (see `design-md-to-app/references/shadcn-mapping.md` → "Monorepo (shared `packages/ui`)"). Here `packages/design` is redundant — tokens live in `packages/ui/src/styles/globals.css`.

## Q5: What if I change the UI library for the web side after bootstrap?

```
Hard refactor. The skill set helps:
1. Read packages/design/src/tokens.ts — that part is library-agnostic.
2. Delete apps/web/components/ui/ (shadcn) and re-run design-md-to-app inside apps/web/ with the new library.
3. The Tailwind preset stays the same.

For "mid-project swap" be aware: tailwind.config.js in apps/web/ may need MUI overrides removed,
or shadcn's components.json removed, depending on direction.
```

## Q6: Can I have multiple mobile apps (e.g. iOS-only + Android-only)?

```
No. v1 = one apps/mobile/ that ships to both stores via EAS.

If you really need two mobile apps (e.g. a consumer app + a delivery driver app),
either:
- 2 separate monorepos
- modify the workspace yourself (eject from this skill set conventions)
```

## Q7: How do I deploy a monorepo?

```
Two pipelines, run in parallel:

Web (apps/web/):
- Vercel: connect the GitHub repo, set "root directory" = apps/web. Vercel auto-detects Next.js.
- Build command: cd ../.. && pnpm install --frozen-lockfile && pnpm turbo build --filter=@<slug>/web
- Output: apps/web/.next

Mobile (apps/mobile/):
- EAS: cd apps/mobile && eas build --profile production --platform all
- EAS Submit: eas submit --profile production --platform all
- For OTA: eas update --channel production --branch <branch>

Future: a CI workflow in .github/workflows/deploy.yml could run both in parallel on tag pushes.
```

## Q8: When should NOT use this skill?

```
- You're modifying an existing project (not greenfield). monorepo-bootstrap requires phase ≤ design_extracted.
- You only want web OR only mobile. Use design-md-to-app or rn-bootstrap directly.
- You want a different monorepo tool (yarn workspaces / nx / lerna / bazel). v1 only does pnpm + turborepo.
- You want >1 web app or >1 mobile app. v1 limit.
- You don't want shared design tokens. Then you don't need this skill — separate repos are simpler.
```

## Q9: Cosa fa il bootstrap quando manca DESIGN.md?

```
Si potrebbe ancora procedere, ma con i token di default:
- packages/design/src/tokens.ts viene generato con palette/typography/radii "neutri"
  (zinc-based, system fonts, 0.625rem radius — defaults shadcn)
- Il warning viene stampato chiaramente:
  "DESIGN.md absent. Using default tokens. You can re-run wire-design-tokens later
   to regenerate from a real DESIGN.md."

L'utente può sempre runnare design-md-to-app o image-to-design-md DOPO per generare il vero
DESIGN.md, poi rigenerare packages/design/ via monorepo-bootstrap --refresh-design (TODO future flag).
```
