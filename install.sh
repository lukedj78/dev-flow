#!/usr/bin/env bash
# Installs the 8 dev-flow skills into your Claude Code skills directory.
#
# Usage:
#   ./install.sh                       # install to default location
#   CLAUDE_SKILLS_DIR=/custom/path ./install.sh
#
# Idempotent-ish: if a skill already exists at the target, it's backed up to
# `<skill>.bak` before overwriting (one level of backup; running twice in a row
# loses the second-most-recent version).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_DIR="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"

SKILLS=(
  dev-flow
  prd-from-idea
  prd-to-tasks
  figma-to-design-md
  image-to-design-md
  design-md-to-app
  screenshot-to-page
  module-add
)

echo "Installing 8 dev-flow skills →  $SKILLS_DIR"
mkdir -p "$SKILLS_DIR"

# Sanity check: dev-flow uses Python helper scripts (parse_design_md.py,
# build_registry.py, palette quantization, etc). Warn the user up-front if
# the host environment is missing pieces the skills will need at runtime.
echo
echo "Checking host dependencies…"

missing=0
need_warn() { echo "  ⚠ $1"; missing=1; }

if ! command -v python3 >/dev/null 2>&1; then
  need_warn "python3 not found — install via 'brew install python' or your distro's package manager"
else
  echo "  ✓ python3"

  # Check the two Python packages dev-flow scripts import most often.
  if ! python3 -c "import yaml" >/dev/null 2>&1; then
    need_warn "PyYAML missing — 'pip3 install pyyaml' (used by parse_design_md.py)"
  else
    echo "  ✓ PyYAML"
  fi

  if ! python3 -c "import PIL" >/dev/null 2>&1; then
    need_warn "Pillow missing — 'pip3 install pillow' (used by image-to-design-md palette extraction)"
  else
    echo "  ✓ Pillow"
  fi
fi

if ! command -v node >/dev/null 2>&1; then
  need_warn "node not found — install Node 20+ (https://nodejs.org or 'brew install node')"
else
  echo "  ✓ node ($(node --version))"
fi

if ! command -v pnpm >/dev/null 2>&1; then
  need_warn "pnpm not found — install via 'npm install -g pnpm' or 'brew install pnpm'"
else
  echo "  ✓ pnpm ($(pnpm --version))"
fi

if [ "$missing" -eq 1 ]; then
  echo
  echo "Some host dependencies are missing. The skills will install fine, but"
  echo "some scripts will fail when they run. Address the warnings above when"
  echo "convenient — installation continues."
fi
echo

for s in "${SKILLS[@]}"; do
  src="$SCRIPT_DIR/$s"
  dest="$SKILLS_DIR/$s"

  if [ ! -d "$src" ]; then
    echo "  ✗ $s — source folder missing at $src"
    continue
  fi

  if [ -d "$dest" ]; then
    rm -rf "$dest.bak"
    mv "$dest" "$dest.bak"
    echo "  ⚠ $s — backed up existing version to $s.bak"
  fi

  cp -R "$src" "$dest"
  echo "  ✓ $s"
done

echo
echo "Done. Restart Claude Code (or reload your client) to pick up the skills."
echo "Then say something like \"voglio costruire X\" — dev-flow will route."
