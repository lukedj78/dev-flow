#!/usr/bin/env bash
# scaffold-mobile.sh — scaffold the Expo+RN mobile app inside apps/mobile/
#
# Wrapper around rn-bootstrap workflow: prepares the apps/mobile/ subdir,
# invokes rn-bootstrap, then patches the generated tailwind.config.js to import
# @<slug>/design's nativewind preset, and rewrites metro.config.js to handle
# the monorepo workspace correctly.
#
# Usage: scaffold-mobile.sh <project-root> <project-slug> [--patch]

set -euo pipefail

PROJECT_ROOT="${1:?project root required}"
SLUG="${2:?project slug required}"

cd "$PROJECT_ROOT"

if [[ ! -d apps/mobile ]]; then
  echo "[scaffold-mobile] apps/mobile/ does not exist — run init-monorepo.sh first"
  exit 1
fi

if [[ -f apps/mobile/package.json && -d apps/mobile/app ]]; then
  echo "[scaffold-mobile] apps/mobile/ already scaffolded — skipping (use --patch to update wiring only)"
  if [[ "${3:-}" != "--patch" ]]; then
    exit 0
  fi
fi

if [[ "${3:-}" != "--patch" ]]; then
  echo "[scaffold-mobile] Mobile side scaffold:"
  echo ""
  echo "  1. cd apps/mobile"
  echo "  2. Invoke rn-bootstrap skill (Claude agent reads:"
  echo "     $PROJECT_ROOT/.workflow/DESIGN.md and meta.json#stack.monorepo.mobile)"
  echo ""
  echo "  3. After rn-bootstrap completes, re-run this script with --patch."
  echo ""
  echo "[scaffold-mobile] Run me again with --patch after rn-bootstrap completes."
  exit 0
fi

# --patch phase
echo "[scaffold-mobile --patch] Patching apps/mobile/tailwind.config.js…"

TAILWIND_CFG="apps/mobile/tailwind.config.js"
if [[ ! -f "$TAILWIND_CFG" ]]; then
  echo "  ✗ No tailwind.config.js found in apps/mobile/. Has rn-bootstrap actually run?"
  exit 1
fi

if grep -q "@${SLUG}/design/nativewind" "$TAILWIND_CFG"; then
  echo "  ✓ @${SLUG}/design/nativewind preset already wired"
else
  node -e "
    const fs = require('fs');
    const path = '$TAILWIND_CFG';
    let text = fs.readFileSync(path, 'utf8');

    // We expect rn-bootstrap to have generated:
    //   presets: [require('nativewind/preset')],
    // We need to add @${SLUG}/design/nativewind alongside.

    if (text.includes('@${SLUG}/design/nativewind')) {
      console.log('  ✓ already wired');
    } else if (text.includes('nativewind/preset')) {
      text = text.replace(
        /presets:\\s*\\[require\\(['\\\"]nativewind\\/preset['\\\"]\\)\\]/,
        \"presets: [require('nativewind/preset'), require('@${SLUG}/design/nativewind').default]\"
      );
      fs.writeFileSync(path, text);
      console.log('  ✓ Patched ' + path + ' to import @${SLUG}/design/nativewind preset');
    } else {
      console.log('  ⚠ Could not find nativewind/preset in tailwind.config.js — manual fix needed');
    }
  "
fi

echo "[scaffold-mobile --patch] Patching apps/mobile/metro.config.js for monorepo…"

METRO_CFG="apps/mobile/metro.config.js"
if [[ -f "$METRO_CFG" ]]; then
  if grep -q "watchFolders" "$METRO_CFG" && grep -q "disableHierarchicalLookup" "$METRO_CFG"; then
    echo "  ✓ metro.config.js already monorepo-aware"
  else
    # Backup the existing one
    cp "$METRO_CFG" "${METRO_CFG}.bak"
    # Replace with the canonical monorepo-aware version
    cat > "$METRO_CFG" <<'EOF'
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

// CRITICAL: prevent two copies of React (one in apps/mobile/node_modules,
// one in the workspace root). Without this, hooks fail with "Invalid hook call."
config.resolver.disableHierarchicalLookup = true;

module.exports = withNativeWind(config, { input: './global.css' });
EOF
    echo "  ✓ Rewrote $METRO_CFG (backup saved as ${METRO_CFG}.bak)"
  fi
fi

echo "[scaffold-mobile --patch] Patching apps/mobile/package.json…"
node -e "
  const fs = require('fs');
  const path = 'apps/mobile/package.json';
  const pkg = JSON.parse(fs.readFileSync(path, 'utf8'));
  pkg.name = '@${SLUG}/mobile';
  pkg.dependencies = pkg.dependencies || {};
  pkg.dependencies['@${SLUG}/shared'] = 'workspace:*';
  pkg.dependencies['@${SLUG}/design'] = 'workspace:*';
  pkg.dependencies['@${SLUG}/api'] = 'workspace:*';
  pkg.devDependencies = pkg.devDependencies || {};
  pkg.devDependencies['@${SLUG}/typescript-config'] = 'workspace:*';
  fs.writeFileSync(path, JSON.stringify(pkg, null, 2) + '\\n');
  console.log('  ✓ apps/mobile/package.json: name + workspace deps updated');
"

# Patch tsconfig to extend the shared preset package (not a relative path to a
# root tsconfig.base.json — see scaffold-web.sh for why)
TS_CFG="apps/mobile/tsconfig.json"
if [[ -f "$TS_CFG" ]]; then
  node -e "
    const fs = require('fs');
    const path = '$TS_CFG';
    const cfg = JSON.parse(fs.readFileSync(path, 'utf8'));
    cfg.extends = '@${SLUG}/typescript-config/react-native.json';
    fs.writeFileSync(path, JSON.stringify(cfg, null, 2) + '\\n');
    console.log('  ✓ apps/mobile/tsconfig.json now extends @${SLUG}/typescript-config/react-native.json');
  "
fi

echo ""
echo "[scaffold-mobile --patch] Done. Now scaffold the packages/{design,shared,api}/ skeletons."
