#!/usr/bin/env bash
# Removes the 8 dev-flow skills from your Claude Code skills directory.
# Restores `*.bak` backups created by install.sh, if present.
set -euo pipefail

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

echo "Uninstalling 8 dev-flow skills from $SKILLS_DIR"

for s in "${SKILLS[@]}"; do
  dest="$SKILLS_DIR/$s"
  bak="$SKILLS_DIR/$s.bak"

  if [ -d "$dest" ]; then
    rm -rf "$dest"
    echo "  ✓ $s removed"
  else
    echo "  · $s not found"
  fi

  if [ -d "$bak" ]; then
    mv "$bak" "$dest"
    echo "    ↩ restored backup $s.bak → $s"
  fi
done

echo
echo "Done."
