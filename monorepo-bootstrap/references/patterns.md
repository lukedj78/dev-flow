> Sources: turborepo.dev/docs, pnpm.io/workspaces, internal opinion.

# Patterns and anti-patterns — monorepo bootstrap

## Workspace protocol

Always use `workspace:*` for cross-workspace dependencies:

```json
// apps/web/package.json
{
  "dependencies": {
    "@<slug>/shared": "workspace:*",
    "@<slug>/design": "workspace:*",
    "@<slug>/api": "workspace:*"
  }
}
```

`workspace:*` resolves to the local copy at install time. When you publish (rare for monorepo repos), pnpm rewrites this to the actual version. For private monorepos, this is purely a development concern.

**DO NOT** use `file:../packages/shared` — that's the npm style, doesn't deduplicate correctly.

## Turborepo pipeline rules

```json
{
  "tasks": {
    "build": {
      "dependsOn": ["^build"],  // ← ^ means "all dependencies' build first"
      "outputs": [".next/**", "dist/**", "build/**"]
    },
    "dev": {
      "cache": false,            // ← never cache dev (it's interactive)
      "persistent": true         // ← long-running process
    },
    "test": {
      "dependsOn": ["^build"]    // ← need built packages to test
    },
    "typecheck": {
      "dependsOn": ["^build"]
    },
    "lint": {}                   // ← no dependencies, parallelizable
  }
}
```

**DO NOT** add `"build:web"`, `"build:mobile"` etc. as separate tasks. Use turborepo's `--filter`:

```bash
pnpm turbo build --filter=@<slug>/web
pnpm turbo build --filter=@<slug>/mobile
```

## Naming conventions

| Item | Convention | Example |
|---|---|---|
| Root package name | `@<slug>/root` | `@daysnap/root` |
| App packages | `@<slug>/web`, `@<slug>/mobile` | `@daysnap/web` |
| Shared packages | `@<slug>/<noun>` | `@daysnap/shared`, `@daysnap/design`, `@daysnap/api` |
| Path aliases | match package names | `@daysnap/shared/*` → `packages/shared/src/*` |

The slug comes from `meta.json#project_slug`. The skill enforces this — don't override.

## Importing across workspaces

In any TypeScript file, you can:

```ts
// apps/web/app/posts/page.tsx
import { Post } from "@<slug>/shared/types";
import { createPostSchema } from "@<slug>/shared/validators";
import { tokens } from "@<slug>/design/tokens";
import { supabase } from "@<slug>/api/client";
import { listPosts } from "@<slug>/api/queries/posts";
```

```ts
// apps/mobile/app/(app)/feed.tsx
import { Post } from "@<slug>/shared/types";
import { tokens } from "@<slug>/design/tokens";
import { supabase } from "@<slug>/api/client";
import { listPosts } from "@<slug>/api/queries/posts";
```

Same import paths in both apps. Same `Post` type. Same `listPosts()` function. **Single source.**

## Tailwind + NativeWind presets — wiring the design tokens

**Web app** (`apps/web/tailwind.config.js`):
```js
const designPreset = require('@<slug>/design/tailwind').default;
module.exports = {
  presets: [designPreset],
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'],
};
```

**Mobile app** (`apps/mobile/tailwind.config.js`):
```js
const designPreset = require('@<slug>/design/nativewind').default;
module.exports = {
  presets: [require('nativewind/preset'), designPreset],
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'],
};
```

Then in both apps, the same Tailwind class names work: `bg-primary`, `text-foreground`, `rounded-card`, etc.

## Metro config for the mobile side

Expo's Metro must explicitly know about the workspace root:

```js
// apps/mobile/metro.config.js
const { getDefaultConfig } = require('expo/metro-config');
const { withNativeWind } = require('nativewind/metro');
const path = require('path');

const projectRoot = __dirname;
const workspaceRoot = path.resolve(projectRoot, '../..');

const config = getDefaultConfig(projectRoot);
config.watchFolders = [workspaceRoot];
config.resolver.nodeModulesPaths = [
  path.resolve(projectRoot, 'node_modules'),
  path.resolve(workspaceRoot, 'node_modules'),
];
config.resolver.disableHierarchicalLookup = true;

module.exports = withNativeWind(config, { input: './global.css' });
```

**Without `disableHierarchicalLookup: true`**, Metro will find React both in `apps/mobile/node_modules` and in the root `node_modules`, leading to "Invalid hook call" crashes. This is the #1 monorepo + Expo bug.

## TypeScript path aliases

`tsconfig.base.json` at root has the aliases:

```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@<slug>/shared/*": ["packages/shared/src/*"],
      "@<slug>/design/*": ["packages/design/src/*"],
      "@<slug>/api/*": ["packages/api/src/*"]
    }
  }
}
```

Each `apps/*/tsconfig.json` and `packages/*/tsconfig.json` extends this. **DO NOT duplicate the paths in each tsconfig** — extends is enough.

## Common pitfalls

- ❌ Two copies of React → "Invalid hook call". Fix: `disableHierarchicalLookup: true` in Metro config.
- ❌ Two copies of Reanimated → opaque crash on launch. Fix: same — Metro config.
- ❌ Importing from `../../packages/shared/src/types` instead of `@<slug>/shared/types` → works in TS but breaks at runtime for the mobile app. Fix: always use the path alias.
- ❌ Adding a workspace dependency without updating `pnpm-workspace.yaml` — pnpm won't see it.
- ❌ `pnpm install` from inside `apps/mobile/` instead of root — installs at app level only, breaks hoisting. Always install from root.
- ❌ Forgetting to add `@<slug>/design` to BOTH `apps/web/package.json` AND `apps/mobile/package.json` — preset import breaks.

## DO

- ✅ Run `pnpm install --recursive` from root after any package change.
- ✅ Use `pnpm turbo dev` to run web + mobile in parallel (they don't conflict — different ports).
- ✅ Use `pnpm --filter @<slug>/<pkg> <command>` for single-workspace operations.
- ✅ Keep `tsconfig.base.json` as the single source of paths.
- ✅ When adding a new shared package, immediately add it to BOTH apps' package.json with `workspace:*`.

## DON'T

- ❌ Mix package managers — pnpm-lock.yaml is the only lockfile that exists.
- ❌ Commit `node_modules/` — they're hoisted to root, can be huge.
- ❌ Run two terminals' worth of `pnpm install` simultaneously — race conditions on the lockfile.
- ❌ Use `@<slug>/shared` without `workspace:*` in package.json — npm thinks you want to fetch from registry, fails.
- ❌ Put shared types in `apps/web/types/` and import them from mobile — circular dependency between apps. Always go through `packages/`.
