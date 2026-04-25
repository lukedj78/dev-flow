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
