> Sources: turborepo.dev/docs, pnpm.io/workspaces, docs.expo.dev/guides/monorepos, internal opinion.

# Monorepo layout — the canonical structure

Every monorepo scaffolded by `monorepo-bootstrap` follows this exact layout. Deviation breaks the assumptions of the patched skills (module-add, rn-module-add, screenshot-to-page, rn-add-screen).

```
<project-root>/
├── .workflow/                     ← SHARED across the whole monorepo
│   ├── PROJECT.md
│   ├── PRD.md
│   ├── DESIGN.md
│   ├── screenshots/               ← if Figma/image-to-design-md ran
│   └── meta.json                  ← phase, stack.monorepo, history, artifacts
│
├── apps/
│   ├── web/                       ← Next.js + shadcn/Base UI/MUI
│   │   ├── app/                   ← App Router routes
│   │   ├── components/
│   │   ├── lib/
│   │   ├── public/
│   │   ├── tailwind.config.js     ← presets: [require("@<slug>/design/tailwind")]
│   │   ├── tsconfig.json          ← extends "@<slug>/typescript-config/nextjs.json"
│   │   ├── package.json           ← name: @<slug>/web
│   │   └── next.config.ts
│   │
│   └── mobile/                    ← Expo + RN + NativeWind
│       ├── app/                   ← Expo Router file-based routes
│       ├── components/
│       ├── lib/
│       ├── store/
│       ├── types/
│       ├── assets/
│       ├── tailwind.config.js     ← presets: [require("@<slug>/design/nativewind")]
│       ├── global.css
│       ├── nativewind-env.d.ts
│       ├── babel.config.js
│       ├── metro.config.js        ← see Metro monorepo config below
│       ├── app.json
│       ├── tsconfig.json          ← extends "@<slug>/typescript-config/react-native.json"
│       └── package.json           ← name: @<slug>/mobile
│
├── packages/
│   ├── shared/                    ← TS types, Zod validators, business logic
│   │   ├── src/
│   │   │   ├── index.ts           ← barrel export
│   │   │   ├── types/             ← User, Post, etc.
│   │   │   ├── validators/        ← Zod schemas
│   │   │   └── utils/             ← pure functions
│   │   ├── tsconfig.json
│   │   └── package.json           ← name: @<slug>/shared
│   │
│   ├── design/                    ← DESIGN.md → 2 output presets
│   │   ├── src/
│   │   │   ├── tokens.ts          ← typed JS object generated from DESIGN.md
│   │   │   ├── tailwind-preset.ts ← consumed by apps/web
│   │   │   └── nativewind-preset.ts ← consumed by apps/mobile
│   │   ├── tsconfig.json
│   │   └── package.json           ← name: @<slug>/design
│   │                                exports: ./tokens, ./tailwind, ./nativewind
│   │
│   ├── api/                       ← Backend client + queries (filled by module-add)
│   │   ├── src/
│   │   │   ├── index.ts
│   │   │   ├── client.ts          ← Supabase / tRPC instance
│   │   │   ├── auth.ts            ← signIn/signOut/useSession
│   │   │   └── queries/
│   │   │       └── (one file per domain — posts, users, etc.)
│   │   ├── tsconfig.json
│   │   └── package.json           ← name: @<slug>/api
│   │
│   ├── typescript-config/         ← shared tsconfig presets — NOT a root tsconfig.base.json
│   │   ├── base.json              ← strict mode, path aliases, extended by everything below
│   │   ├── nextjs.json            ← extends ./base.json, Next.js plugin + bundler resolution
│   │   ├── react-native.json      ← extends ./base.json, RN/Metro-flavored options
│   │   └── package.json           ← name: @<slug>/typescript-config
│   │
│   └── eslint-config/             ← shared ESLint flat config, same extends pattern
│
├── pnpm-workspace.yaml
├── turbo.json
├── package.json                   ← name: @<slug>/root, scripts proxy turbo
├── .gitignore
├── .npmrc                         ← if needed (legacy-peer-deps for SDK 54 era)
└── README.md
```

## Root configuration files

### `pnpm-workspace.yaml`
```yaml
packages:
  - 'apps/*'
  - 'packages/*'
```

### `turbo.json`
```json
{
  "$schema": "https://turborepo.dev/schema.json",
  "globalDependencies": [".env"],
  "tasks": {
    "build": {
      "dependsOn": ["^build"],
      "outputs": [".next/**", "dist/**", "build/**"],
      "env": ["NODE_ENV"]
    },
    "dev": {
      "cache": false,
      "persistent": true
    },
    "lint": {},
    "typecheck": {
      "dependsOn": ["^build"]
    },
    "test": {
      "dependsOn": ["^build"]
    }
  }
}
```

### Root `package.json` (proxies)
```json
{
  "name": "@<slug>/root",
  "private": true,
  "engines": {
    "node": ">=24"
  },
  "scripts": {
    "dev": "turbo dev",
    "dev:web": "pnpm --filter @<slug>/web dev",
    "dev:mobile": "pnpm --filter @<slug>/mobile start",
    "build": "turbo build",
    "lint": "turbo lint",
    "typecheck": "turbo typecheck",
    "test": "turbo test"
  },
  "devDependencies": {
    "turbo": "^2.0.0",
    "typescript": "^5.4.0"
  },
  "packageManager": "pnpm@9.0.0"
}
```

`engines.node >= 24` is required because eve (the agent engine wired via the `eve-agent` skill, used in the `"web-agent"` topology and optionally added later to any topology) requires Node ≥ 24. Setting it at the monorepo root keeps the constraint visible even for topologies that don't have an agent yet.

### `packages/typescript-config/` (shared presets, NOT a root `tsconfig.base.json`)

**No `tsconfig.base.json` at repo root.** Turborepo's own official pattern (verified against
`vercel/turborepo`'s `examples/basic`) is a small **package** that ships the shared config and is
consumed by **package name**, the same way any other workspace dependency is — a root file that
every app reaches via a relative `../../` path doesn't compose once a package nests deeper, and
isn't itself a workspace member `pnpm` can version or swap.

`packages/typescript-config/package.json`:
```json
{
  "name": "@<slug>/typescript-config",
  "version": "0.0.0",
  "private": true
}
```

`packages/typescript-config/base.json` — path aliases live here, extended by everything else:
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "strict": true,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "baseUrl": ".",
    "paths": {
      "@<slug>/shared/*": ["packages/shared/src/*"],
      "@<slug>/design/*": ["packages/design/src/*"],
      "@<slug>/api/*": ["packages/api/src/*"]
    }
  }
}
```

`packages/typescript-config/nextjs.json` and `react-native.json` each `extend "./base.json"` and
add the platform-specific bits (`jsx: "preserve"` + the Next.js plugin for the former, Metro/RN
options for the latter) — that split is why there are two presets instead of one.

Every `apps/*/tsconfig.json` and `packages/*/tsconfig.json` extends the **package**, not a relative
path to the root:
```json
{
  "extends": "@<slug>/typescript-config/nextjs.json",
  "compilerOptions": {
    "outDir": "./dist",
    "rootDir": "./src"
  },
  "include": ["src/**/*"]
}
```
(`packages/shared`, `packages/design`, `packages/api` extend `base.json` directly — no JSX/bundler
concerns there — while `apps/web` extends `nextjs.json` and `apps/mobile` extends
`react-native.json`.)

## Metro config for the mobile workspace (`apps/mobile/metro.config.js`)

Expo needs special config to resolve sibling workspaces:

```js
const { getDefaultConfig } = require('expo/metro-config');
const { withNativeWind } = require('nativewind/metro');
const path = require('path');

const projectRoot = __dirname;
const workspaceRoot = path.resolve(projectRoot, '../..');

const config = getDefaultConfig(projectRoot);

// Watch all files within the monorepo
config.watchFolders = [workspaceRoot];
// Resolve modules from this app first, then from the workspace root
config.resolver.nodeModulesPaths = [
  path.resolve(projectRoot, 'node_modules'),
  path.resolve(workspaceRoot, 'node_modules'),
];
// Prevent duplicate React copies
config.resolver.disableHierarchicalLookup = true;

module.exports = withNativeWind(config, { input: './global.css' });
```

This is the official Expo recommendation for monorepos (https://docs.expo.dev/guides/monorepos/).

## Shared package — Tailwind preset shape

`packages/design/src/tailwind-preset.ts`:

```ts
import type { Config } from "tailwindcss";
import { tokens } from "./tokens";

export const tailwindPreset = {
  theme: {
    extend: {
      colors: tokens.colors,
      spacing: tokens.spacing,
      borderRadius: tokens.borderRadius,
      fontFamily: tokens.fontFamily,
      fontSize: tokens.fontSize,
    },
  },
} satisfies Partial<Config>;

export default tailwindPreset;
```

`packages/design/src/nativewind-preset.ts`:

```ts
import { tokens } from "./tokens";

export const nativewindPreset = {
  theme: {
    extend: {
      colors: tokens.colors,
      borderRadius: tokens.borderRadius,
      fontFamily: tokens.fontFamily,
    },
  },
};

export default nativewindPreset;
```

The web app then does in its `tailwind.config.js`:
```js
const designPreset = require('@<slug>/design/tailwind').default;
module.exports = {
  presets: [designPreset],
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'],
};
```

The mobile app does in its `tailwind.config.js`:
```js
const designPreset = require('@<slug>/design/nativewind').default;
module.exports = {
  presets: [require('nativewind/preset'), designPreset],
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'],
};
```

Tokens flow from `DESIGN.md` → `packages/design/src/tokens.ts` → both Tailwind presets → both apps' `tailwind.config.js`. Single source.

## Why these specific choices

- **pnpm**: only package manager with `workspace:*` protocol + hard-link semantics + working with both Next.js + Expo without surprises.
- **turborepo**: minimal config, no opinions on monorepo "right way" (unlike nx), good caching.
- **Metro `watchFolders` trick**: required for Expo + Metro to "see" sibling packages.
- **`disableHierarchicalLookup`**: prevents Metro from finding two copies of React (one in apps/mobile/node_modules, one in root/node_modules) which causes "Invalid hook call" crashes.
- **`@<slug>/*` namespacing**: avoids collisions with public npm packages.
- **TS path aliases + workspace protocol**: works at both compile time (TS) and runtime (Node module resolution).

## What's NOT in the layout

- No `apps/admin/`, `apps/marketing/`, `apps/docs/`. v1 = exactly 1 web + 1 mobile.
- No `packages/ui/` **for web + mobile monorepos** — cross-platform UI is YAGNI (Tamagui adds complexity; few projects benefit), so shadcn components stay in `apps/web/components/ui/` and only tokens are shared via `packages/design/`. **Exception — web-centric monorepos** (web-only, web + agent, multiple web apps with no NativeWind side): use shadcn's official `packages/ui` (`@workspace/ui`) shared-component layout instead; see `decision-tree.md` → "The `packages/ui` rule".
- No `tooling/` package. ESLint/Prettier configs live in each app for simplicity.
