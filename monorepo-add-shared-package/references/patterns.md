> Sources: monorepo-bootstrap/references/patterns.md, internal opinion.

# Patterns — extracting / creating shared packages

## When to create a NEW shared package

You should create a new package, not just add to an existing one, when:

| Trigger | Suggested package name |
|---|---|
| Need types/Zod schemas that BOTH apps use | `@<slug>/shared` (exists by default) |
| Need design tokens / Tailwind presets | `@<slug>/design` (exists by default) |
| Need backend client + query helpers | `@<slug>/api` (exists by default, populated by module-add) |
| Cross-platform UI components (rare, Tamagui) | `@<slug>/ui` |

> **Naming collision to be aware of**: `monorepo-bootstrap` also uses the name `packages/ui` (`@workspace/ui`), but for a *different* meaning — its shadcn-monorepo layout for **web-centric** topologies (web-only or web+agent, no NativeWind side), where `packages/ui` holds the actual shadcn primitives + `src/styles/globals.css` tokens, not a cross-platform Tamagui package. If the project already went through `monorepo-bootstrap` with that topology, `packages/ui` is already shadcn's official layout — don't reinterpret or re-scaffold it as the rare Tamagui case described here. See `monorepo-bootstrap/references/decision-tree.md` → "The `packages/ui` rule" for which convention applies.
| Shared ESLint/Prettier configs | `@<slug>/config-eslint` |
| Shared TypeScript configs beyond base | `@<slug>/config-tsconfig` |
| Domain-specific business logic | `@<slug>/<domain>` (e.g. `@<slug>/billing`, `@<slug>/analytics`) |
| Test fixtures | `@<slug>/test-fixtures` |

Rule of thumb: **create a package when ≥2 apps consume it and ≥10 files live in it**. Below that, just keep it as a local module.

## When NOT to create a package

- The logic lives in one app and only one app would ever use it → keep it inside that app's `lib/` or `utils/`.
- You want "tooling" (eslint config, prettier config) but the project has only this one config → just put the config at the repo root.
- It's "would be nice to share someday" — wait. Premature abstraction is more expensive than late refactor.

## `package.json` shape

Every shared package follows this minimal shape:

```json
{
  "name": "@<slug>/<name>",
  "version": "0.1.0",
  "private": true,
  "main": "./src/index.ts",
  "types": "./src/index.ts",
  "exports": {
    ".": "./src/index.ts",
    "./*": "./src/*"
  },
  "scripts": {
    "typecheck": "tsc --noEmit"
  },
  "devDependencies": {
    "typescript": "^5.4.0"
  }
}
```

For packages with sub-paths (e.g. `@<slug>/design/tailwind`, `@<slug>/design/nativewind`):

```json
{
  "exports": {
    ".": "./src/index.ts",
    "./tokens": "./src/tokens.ts",
    "./tailwind": "./src/tailwind-preset.ts",
    "./nativewind": "./src/nativewind-preset.ts"
  }
}
```

`exports` map lets you import `@<slug>/design/tailwind` and have it resolve to `packages/design/src/tailwind-preset.ts`. This is cleaner than exposing the whole package via `./*`.

## `tsconfig.json` shape (per package)

```json
{
  "extends": "@<slug>/typescript-config/base.json",
  "compilerOptions": {
    "outDir": "./dist",
    "rootDir": "./src"
  },
  "include": ["src/**/*"],
  "exclude": ["dist", "node_modules"]
}
```

Same in all packages — extended **by package name**, not a relative path to a root
`tsconfig.base.json` (`monorepo-bootstrap` never creates one; Turborepo's own pattern is a
`packages/typescript-config` workspace package — see `monorepo-bootstrap/references/structure.md`).
The base does the heavy lifting (paths, strict, target); the new package also needs
`@<slug>/typescript-config` as a `devDependency` (`workspace:*`) or the `extends` can't resolve.

## Path alias convention

In `packages/typescript-config/base.json`:

```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@<slug>/shared/*": ["packages/shared/src/*"],
      "@<slug>/design/*": ["packages/design/src/*"],
      "@<slug>/api/*": ["packages/api/src/*"],
      "@<slug>/<your-new-pkg>/*": ["packages/<your-new-pkg>/src/*"]
    }
  }
}
```

The alias name MUST match the package's `name` field. Apps' tsconfigs extend the base — no duplication of paths.

## How extract-from-app works

Example: user has `apps/web/lib/format-price.ts` and wants to extract it.

**Before:**
```
apps/web/
├── lib/
│   └── format-price.ts          ← extract this
└── app/products/page.tsx        ← imports it
apps/mobile/
└── app/(app)/products.tsx       ← would also need it
```

**Steps the skill runs:**
1. `mkdir -p packages/shared/src/utils`
2. `mv apps/web/lib/format-price.ts packages/shared/src/utils/format-price.ts`
3. Add to `packages/shared/src/index.ts`:
   ```ts
   export { formatPrice } from './utils/format-price';
   ```
4. Find all imports of `format-price` in apps/, rewrite:
   - `from "@/lib/format-price"` → `from "@<slug>/shared/utils/format-price"`
   - `from "../../lib/format-price"` → same
5. Verify `apps/web/app/products/page.tsx` compiles (`pnpm typecheck`).

**After:**
```
apps/web/                            ← no longer has lib/format-price.ts
└── app/products/page.tsx            ← imports from @<slug>/shared
apps/mobile/
└── app/(app)/products.tsx           ← can now import from @<slug>/shared too
packages/shared/
└── src/utils/format-price.ts        ← single source
```

## Multiple file moves

If user wants to extract a whole folder (e.g. `apps/web/lib/auth/` → `packages/shared/auth/`), do it as a single batch operation: move the folder, update all imports, run typecheck once.

## Anti-patterns to refuse

- **Cyclic imports**: `@<slug>/foo` imports from `@<slug>/bar` AND `@<slug>/bar` imports from `@<slug>/foo`. Detect on TS compile, refuse with: "Cycle detected: foo ↔ bar. Pull the shared part into a third package."
- **God packages**: a `@<slug>/utils` that grows to 50+ unrelated files. Split into themed packages (`@<slug>/strings`, `@<slug>/dates`, `@<slug>/numbers`).
- **App imports across apps**: `apps/web` importing from `apps/mobile/lib/` — categorically wrong. Anything used by both apps lives in a package.
