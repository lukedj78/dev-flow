#!/usr/bin/env bash
# scaffold-web.sh — scaffold the Next.js web app inside apps/web/
#
# Wrapper around design-md-to-app workflow: prepares the apps/web/ subdir,
# invokes the existing design-md-to-app skill (manually or via Claude), then
# patches the generated tailwind.config.js to import @<slug>/design's preset.
#
# This script PRINTS the steps and assists the operator — for a fully automated
# flow, the agent reading monorepo-bootstrap/SKILL.md performs them.
#
# Usage: scaffold-web.sh <project-root> <project-slug> <ui-library>

set -euo pipefail

PROJECT_ROOT="${1:?project root required}"
SLUG="${2:?project slug required}"
UI_LIB="${3:?UI library required: shadcn | base-ui | mui}"

cd "$PROJECT_ROOT"

if [[ ! -d apps/web ]]; then
  echo "[scaffold-web] apps/web/ does not exist — run init-monorepo.sh first"
  exit 1
fi

# Check if web is already scaffolded
if [[ -f apps/web/package.json && -d apps/web/app ]]; then
  echo "[scaffold-web] apps/web/ already scaffolded — skipping"
  exit 0
fi

echo "[scaffold-web] Web side scaffold:"
echo ""
echo "  1. cd apps/web"
echo "  2. Invoke design-md-to-app skill (Claude agent reads:"
echo "     $PROJECT_ROOT/.workflow/DESIGN.md"
echo "     and chooses scaffold for stack.monorepo.web.ui = \"$UI_LIB\")"
echo ""
echo "  3. After scaffold, this script will patch apps/web/tailwind.config.js"
echo "     to import @${SLUG}/design/tailwind preset."
echo ""
echo "  This step is INTERACTIVE — the agent (or operator) runs design-md-to-app's"
echo "  workflow inside apps/web/. When complete, re-run this script with --patch"
echo "  to apply the design preset wiring."
echo ""

if [[ "${4:-}" != "--patch" ]]; then
  echo "[scaffold-web] Run me again with --patch after design-md-to-app completes."
  exit 0
fi

# --patch phase: assume apps/web/ has been scaffolded by design-md-to-app
echo "[scaffold-web --patch] Patching apps/web/tailwind.config.js…"

TAILWIND_CFG="apps/web/tailwind.config.js"
if [[ ! -f "$TAILWIND_CFG" ]]; then
  # Also try .ts
  TAILWIND_CFG="apps/web/tailwind.config.ts"
fi

if [[ ! -f "$TAILWIND_CFG" ]]; then
  echo "  ✗ No tailwind.config.{js,ts} found in apps/web/. Has design-md-to-app actually run?"
  exit 1
fi

# Check if preset is already wired
if grep -q "@${SLUG}/design/tailwind" "$TAILWIND_CFG"; then
  echo "  ✓ @${SLUG}/design/tailwind preset already wired in $TAILWIND_CFG"
else
  # Use Node to safely patch the config (more robust than sed)
  node -e "
    const fs = require('fs');
    const path = '$TAILWIND_CFG';
    let text = fs.readFileSync(path, 'utf8');

    // Try to inject 'presets' alongside 'theme'
    const presetLine = \"  presets: [require('@${SLUG}/design/tailwind').default],\";

    if (text.includes('presets:')) {
      // Already has presets — add our preset to the array if not present
      if (!text.includes('@${SLUG}/design/tailwind')) {
        text = text.replace(/presets:\\s*\\[/, \"presets: [require('@${SLUG}/design/tailwind').default, \");
      }
    } else {
      // Insert presets line before theme
      text = text.replace(/(\\s+)theme:/, '\\n' + presetLine + '\$1theme:');
    }
    fs.writeFileSync(path, text);
    console.log('  ✓ Patched ' + path + ' to import @${SLUG}/design/tailwind preset');
  "
fi

# Patch apps/web/package.json to add workspace deps
echo "[scaffold-web --patch] Adding @${SLUG}/{shared,design,api} as workspace dependencies…"
node -e "
  const fs = require('fs');
  const path = 'apps/web/package.json';
  const pkg = JSON.parse(fs.readFileSync(path, 'utf8'));
  pkg.name = '@${SLUG}/web';
  pkg.dependencies = pkg.dependencies || {};
  pkg.dependencies['@${SLUG}/shared'] = 'workspace:*';
  pkg.dependencies['@${SLUG}/design'] = 'workspace:*';
  pkg.dependencies['@${SLUG}/api'] = 'workspace:*';
  fs.writeFileSync(path, JSON.stringify(pkg, null, 2) + '\\n');
  console.log('  ✓ apps/web/package.json: name + workspace deps updated');
"

# Patch apps/web/tsconfig.json to extend base
TS_CFG="apps/web/tsconfig.json"
if [[ -f "$TS_CFG" ]]; then
  node -e "
    const fs = require('fs');
    const path = '$TS_CFG';
    const cfg = JSON.parse(fs.readFileSync(path, 'utf8'));
    cfg.extends = '../../tsconfig.base.json';
    fs.writeFileSync(path, JSON.stringify(cfg, null, 2) + '\\n');
    console.log('  ✓ apps/web/tsconfig.json now extends ../../tsconfig.base.json');
  "
fi

echo ""
echo "[scaffold-web --patch] Done. Run scaffold-mobile.sh next."
