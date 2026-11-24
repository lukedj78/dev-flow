#!/usr/bin/env bash
# init-monorepo.sh — scaffold the turborepo monorepo root
#
# Writes: pnpm-workspace.yaml, turbo.json, root package.json, packages/typescript-config/,
# .gitignore, .npmrc, README.md, and empty apps/ + packages/ directories.
# No tsconfig.base.json at root — see packages/typescript-config/ below (Turborepo's own pattern).
# Idempotent: re-running detects existing files and skips them.
#
# Usage: init-monorepo.sh <project-root> <project-slug> [topology]
#   topology: web-mobile (default) | web-agent | web-only | web-agent-inapp
#   web-agent-inapp: the agent lives in apps/web/agent; Biome instead of ESLint for code; ONE shared
#   packages/config instead of typescript-config + eslint-config; capabilities/* in the workspace; the
#   packages themselves come from boundaries.json (scaffold_packages.py), not from this script; no tool
#   versions written here — SKILL.md Step 2 adds them with --save-exact.

set -euo pipefail

PROJECT_ROOT="${1:?project root required}"
SLUG="${2:?project slug required (kebab-case, e.g. 'daysnap')}"
TOPOLOGY="${3:-web-mobile}"
case "$TOPOLOGY" in web-mobile|web-agent|web-only|web-agent-inapp) ;; *) echo "unknown topology: $TOPOLOGY" >&2; exit 2;; esac
INAPP=0; [[ "$TOPOLOGY" == "web-agent-inapp" ]] && INAPP=1
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$PROJECT_ROOT"

if [[ -f pnpm-workspace.yaml && -d apps && -d packages ]]; then
  echo "[init-monorepo] root already scaffolded (pnpm-workspace.yaml + apps + packages exist) — skipping"
  exit 0
fi

echo "[init-monorepo] scaffolding turborepo at $PROJECT_ROOT (slug: $SLUG)…"

# 1. pnpm-workspace.yaml
if [[ ! -f pnpm-workspace.yaml && $INAPP == 1 ]]; then
  cat > pnpm-workspace.yaml <<'EOF'
packages:
  - 'apps/*'
  - 'packages/*'
  - 'capabilities/*'
EOF
  echo "  ✓ pnpm-workspace.yaml (apps, packages, capabilities)"
fi
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
if [[ ! -f package.json && $INAPP == 1 ]]; then
  cat > package.json <<EOF
{
  "name": "@${SLUG}/root",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "turbo dev",
    "build": "turbo build",
    "lint": "biome check . && python3 scripts/check_boundaries.py . && turbo lint",
    "format": "biome format --write .",
    "boundaries": "python3 scripts/check_boundaries.py .",
    "typecheck": "turbo typecheck",
    "test": "turbo test"
  },
  "engines": {
    "node": ">=24"
  }
}
EOF
  echo "  ✓ package.json (Biome + boundaries in lint; tool versions added in Step 2)"
fi
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
#    web-agent-inapp: skipped — packages/config holds tsconfig, Biome and env (scaffold_packages.py).
if [[ $INAPP == 1 && ! -f scripts/check_boundaries.py ]]; then
  mkdir -p scripts
  cp "$SCRIPT_DIR/check_boundaries.py" scripts/check_boundaries.py
  echo "  ✓ scripts/check_boundaries.py (the project runs its own copy, in lint and CI)"
fi
if [[ ! -d packages/typescript-config && $INAPP == 0 ]]; then
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

# 5. packages/eslint-config/ (Turborepo official pattern) — not for web-agent-inapp (Biome)
if [[ ! -d packages/eslint-config && $INAPP == 0 ]]; then
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
if [[ ! -f README.md && $INAPP == 1 ]]; then
  cat > README.md <<EOF
# ${SLUG}

Monorepo scaffolded by dev-flow's \`monorepo-bootstrap\` (topology \`web-agent-inapp\`).

## Layout

- \`apps/web/\` — the Next.js app, with the eve agent in \`apps/web/agent/\`
- \`capabilities/\` — one capability per package (eve extensions)
- \`packages/\` — the packages declared in \`boundaries.json\`, which also says who may depend on whom

## Commands

\`\`\`bash
pnpm install       # install all workspaces
pnpm dev           # run the app (and the agent beside it)
pnpm lint          # Biome + package boundaries + per-package lint
pnpm typecheck     # tsc on every package
pnpm test          # Vitest on every package
\`\`\`

Adding a package or a dependency between packages starts in \`boundaries.json\`: \`pnpm lint\` fails until the code agrees.
EOF
  echo "  ✓ README.md"
fi
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

# 8. Create the directories this topology uses — and only those (v1 created apps/mobile and
#    packages/design for every topology, contradicting Step 3).
case "$TOPOLOGY" in
  web-mobile)
    mkdir -p apps/web apps/mobile packages/shared/src/types packages/shared/src/validators packages/shared/src/utils
    mkdir -p packages/design/src packages/api/src ;;
  web-agent|web-only)
    mkdir -p apps/web packages/shared/src/types packages/shared/src/validators packages/shared/src/utils
    mkdir -p packages/api/src packages/ui ;;
  web-agent-inapp)
    mkdir -p apps/web capabilities packages ;;
esac
echo "  ✓ directory structure for topology $TOPOLOGY"

echo ""
echo "[init-monorepo] root scaffold complete."
if [[ $INAPP == 1 ]]; then
  echo "  Next (SKILL.md Step 2, references/boundaries.md):"
  echo "    - write boundaries.json, then scaffold_packages.py <root>"
  echo "    - pnpm add -D -w --save-exact turbo typescript @biomejs/biome vitest @types/node"
  echo "    - design-md-to-app in apps/web, then eve-agent (layout A in apps/web)"
  exit 0
fi
echo "  Next:"
echo "    - scaffold-web.sh   (invokes design-md-to-app in apps/web/)"
echo "    - scaffold-mobile.sh (invokes rn-bootstrap in apps/mobile/)"
echo "    - then: scaffold packages/{design,shared,api}/ skeletons"
