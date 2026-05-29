> Sources: monorepo-bootstrap/references/structure.md, rn-backend decision-tree, internal opinion.

# Decision tree — sync types

## Q1: Where is the source of truth for types?

```
What backend?
├── Supabase                       → supabase gen types typescript (automated)
├── tRPC                            → TS inference from server router (no gen needed)
├── Firebase Firestore              → manual (no automated gen; types from rules + Zod)
├── Custom REST + Zod on server     → derive types from Zod via z.infer (automated if Zod imported)
├── Custom REST + OpenAPI           → npx openapi-typescript (automated)
└── Custom REST + manual TS         → copy/paste, keep in sync manually
```

## Q2: Where do generated types LIVE in the monorepo?

```
ALWAYS in packages/shared/src/types/.

Reasons:
- packages/shared/ is consumed by BOTH apps (web + mobile) — types must be universal.
- packages/api/ has the runtime client (supabase, trpc), but types are not "runtime".
- packages/shared also holds Zod schemas which import types — keep them together.

NEVER put types in apps/web/types/ or apps/mobile/types/ — they'd be inaccessible to the
other app, leading to duplication.
```

## Q3: How often to re-sync?

```
After every backend schema change.

Specifically:
- new table created in Supabase  → re-sync
- column renamed                  → re-sync (breaks consumers — that's the point)
- new tRPC procedure added        → no gen needed, just re-import the AppRouter
- Firestore collection schema     → manual edit + commit
- Zod schema in server changed    → re-sync (if automated chain set up)
```

Set up a CI step that calls `monorepo-sync-types` on a cron OR a git pre-push hook that warns
if backend schema has drifted (compare hash of `database.ts` to last-known).

## Q4: What if sync breaks consumers?

```
That's WHY we generate.

The TS compiler will surface every place that needs an update:
- `pnpm tsc --noEmit` in apps/web → list errors
- `pnpm tsc --noEmit` in apps/mobile → list errors
- fix each in turn

A breaking schema change should NEVER reach production without TS catching it. If it does,
you probably have `// @ts-ignore` somewhere — find and remove.
```

## Q5: Special case — server lives outside the monorepo (separate repo)

```
Options:
- Best: server publishes a private @<scope>/types package on npm. apps' deps include it.
- Good: server commits a generated types file; this skill copies it via `curl` or `gh release download`.
- OK:   manually paste the relevant section into packages/shared/src/types/server.d.ts and
         add a comment with the source URL.
- Bad:  hand-write the types and hope they match. Will diverge silently.

The skill defaults to asking the user which path; doesn't enforce.
```

## Q6: tRPC types — workspace import or .d.ts shim?

```
Server in monorepo (apps/server/ or packages/server/):
├── Add server as a workspace dep of packages/api/
├── In packages/api/src/client.ts:
│       import type { AppRouter } from '@<slug>/server';
│       export const trpc = createTRPCReact<AppRouter>();
└── apps consume via @<slug>/api/client — types flow.

Server in a different repo:
├── Generate a router-type.d.ts on every server release
│       (server runs: tsc --emitDeclarationOnly to produce it)
├── Copy router-type.d.ts into packages/api/src/router-type.d.ts (manual or curl)
└── Re-export via packages/api/src/client.ts.
```

## Q7: Firebase — what to put in types?

```
Firestore is schemaless at the wire level. Two options:

(a) Generate from firestore.rules (limited):
    - Rules express "must have X field" — extract those to a type.
    - Output: packages/shared/src/types/firestore.ts with one type per collection.
    - Caveat: rules don't fully express nested shapes.

(b) Author types manually + Zod-validate on read:
    - User writes types/Post.ts by hand.
    - In packages/api/src/queries/posts.ts:
        const data = await firestore.collection('posts').doc(id).get();
        return PostSchema.parse(data.data());  // Zod runtime check
    - This is the right pattern even outside monorepo.

The skill prefers (b) — more robust, and shows the user how to type-safely consume Firestore.
```
