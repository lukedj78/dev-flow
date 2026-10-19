#!/usr/bin/env bash
# init-monorepo.sh — scaffold the turborepo monorepo root
#
# Writes: pnpm-workspace.yaml, turbo.json, root package.json, packages/typescript-config/,
# .gitignore, .npmrc, README.md, and empty apps/ + packages/ directories.
# No tsconfig.base.json at root — see packages/typescript-config/ below (Turborepo's own pattern).
# Idempotent: re-running detects existing files and skips them.
#
# Usage: init-monorepo.sh <project-root> <project-slug>

set -euo pipefail

PROJECT_ROOT="${1:?project root required}"
SLUG="${2:?project slug required (kebab-case, e.g. 'daysnap')}"

cd "$PROJECT_ROOT"

if [[ -f pnpm-workspace.yaml && -d apps && -d packages ]]; then
  echo "[init-monorepo] root already scaffolded (pnpm-workspace.yaml + apps + packages exist) — skipping"
  exit 0
fi

echo "[init-monorepo] scaffolding turborepo at $PROJECT_ROOT (slug: $SLUG)…"

# 1. pnpm-workspace.yaml
if [[ ! -f pnpm-workspace.yaml ]]; then
  cat > pnpm-workspace.yaml <<'EOF'
packages:
  - 'apps/*'
  - 'packages/*'
EOF
  echo "  ✓ pnpm-workspace.yaml"
fi

# 2. turbo.json
if [[ ! -f turbo.json ]]; then
  cat > turbo.json <<'EOF'
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
EOF
  echo "  ✓ turbo.json"
fi

# 3. Root package.json
if [[ ! -f package.json ]]; then
  cat > package.json <<EOF
{
  "name": "@${SLUG}/root",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "turbo dev",
    "dev:web": "pnpm --filter @${SLUG}/web dev",
    "dev:mobile": "pnpm --filter @${SLUG}/mobile start",
    "build": "turbo build",
    "lint": "turbo lint",
    "typecheck": "turbo typecheck",
    "test": "turbo test"
  },
  "devDependencies": {
    "turbo": "^2.0.0",
    "typescript": "^5.4.0"
  },
  "packageManager": "pnpm@9.0.0",
  "engines": {
    "node": ">=20"
  }
}
EOF
  echo "  ✓ package.json"
fi

# 4. packages/typescript-config/ (Turborepo official pattern — no tsconfig.base in root)
if [[ ! -d packages/typescript-config ]]; then
  mkdir -p packages/typescript-config
  cat > packages/typescript-config/package.json <<EOF
{
  "name": "@${SLUG}/typescript-config",
  "version": "0.0.0",
  "private": true,
  "files": ["base.json", "nextjs.json", "react-native.json"]
}
EOF
  cat > packages/typescript-config/base.json <<EOF
{
  "\$schema": "https://json.schemastore.org/tsconfig",
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "strict": true,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "baseUrl": ".",
    "paths": {
      "@${SLUG}/shared/*": ["packages/shared/src/*"],
      "@${SLUG}/design/*": ["packages/design/src/*"],
      "@${SLUG}/api/*": ["packages/api/src/*"]
    }
  }
}
EOF
  cat > packages/typescript-config/nextjs.json <<EOF
{
  "extends": "./base.json",
  "compilerOptions": {
    "plugins": [{ "name": "next" }],
    "moduleResolution": "Bundler",
    "jsx": "preserve",
    "incremental": true,
    "noEmit": true
  }
}
EOF
  cat > packages/typescript-config/react-native.json <<EOF
{
  "extends": "./base.json",
  "compilerOptions": {
    "jsx": "react-native",
    "moduleResolution": "Node",
    "lib": ["ESNext"],
    "noEmit": true
  }
}
EOF
  echo "  ✓ packages/typescript-config/ (base + nextjs + react-native presets)"
fi

# 5. packages/eslint-config/ (Turborepo official pattern)
if [[ ! -d packages/eslint-config ]]; then
  mkdir -p packages/eslint-config
  cat > packages/eslint-config/package.json <<EOF
{
  "name": "@${SLUG}/eslint-config",
  "version": "0.0.0",
  "private": true,
  "main": "base.js",
  "files": ["base.js", "nextjs.js", "react-native.js"]
}
EOF
  cat > packages/eslint-config/base.js <<'EOF'
// Shared ESLint config — extend in apps/<name>/eslint.config.mjs
module.exports = {
  extends: ["eslint:recommended"],
  rules: {
    "no-unused-vars": "warn",
    "no-console": ["warn", { allow: ["warn", "error"] }],
  },
};
EOF
  cat > packages/eslint-config/nextjs.js <<'EOF'
const base = require("./base");
module.exports = {
  ...base,
  extends: [...base.extends, "next/core-web-vitals", "next/typescript"],
};
EOF
  cat > packages/eslint-config/react-native.js <<'EOF'
const base = require("./base");
module.exports = {
  ...base,
  extends: [...base.extends, "@react-native/eslint-config"],
};
EOF
  echo "  ✓ packages/eslint-config/ (base + nextjs + react-native presets)"
fi

# 5. .gitignore
if [[ ! -f .gitignore ]]; then
  cat > .gitignore <<'EOF'
node_modules/
.next/
.expo/
.expo-shared/
dist/
build/
.turbo/
.env
.env.local
.env.*.local
*.log
.DS_Store
ios/
android/
EOF
  echo "  ✓ .gitignore"
fi

# 6. .npmrc — recommended for Expo SDK 54 era peer-dep issues
if [[ ! -f .npmrc ]]; then
  cat > .npmrc <<'EOF'
auto-install-peers=true
node-linker=isolated
shamefully-hoist=false
EOF
  echo "  ✓ .npmrc"
fi

# 7. README.md
if [[ ! -f README.md ]]; then
  cat > README.md <<EOF
# ${SLUG}

Monorepo scaffolded by dev-flow's \`monorepo-bootstrap\`.

## Layout

- \`apps/web/\` — Next.js web app
- \`apps/mobile/\` — Expo + RN mobile app
- \`packages/shared/\` — TS types, Zod schemas, business logic
- \`packages/design/\` — design tokens + Tailwind/NativeWind presets
- \`packages/api/\` — backend client + queries (Supabase / tRPC)

## Commands

\`\`\`bash
pnpm install                    # install all workspaces
pnpm dev                        # run web + mobile in parallel
pnpm dev:web                    # web only
pnpm dev:mobile                 # mobile only (Expo Metro)
pnpm build                      # build all (turbo cache)
pnpm typecheck                  # tsc --noEmit on all workspaces
pnpm test                       # all tests
\`\`\`

## Stack

See \`.workflow/meta.json#stack\` for the canonical record of choices.
EOF
  echo "  ✓ README.md"
fi

# 8. Create empty dirs for apps/ and packages/
mkdir -p apps/web apps/mobile packages/shared/src/types packages/shared/src/validators packages/shared/src/utils
mkdir -p packages/design/src packages/api/src
echo "  ✓ apps/ + packages/ directory structure"

echo ""
echo "[init-monorepo] root scaffold complete."
echo "  Next:"
echo "    - scaffold-web.sh   (invokes design-md-to-app in apps/web/)"
echo "    - scaffold-mobile.sh (invokes rn-bootstrap in apps/mobile/)"
echo "    - then: scaffold packages/{design,shared,api}/ skeletons"
