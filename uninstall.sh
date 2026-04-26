#!/usr/bin/env bash
# Remove the 8 dev-flow skills from the chosen runtime's skills directory.
# Restores `*.bak` backups created by install.sh, if present.
#
# Usage:
#   ./uninstall.sh                              # defaults to claude
#   ./uninstall.sh --platform codex             # ~/.codex/dev-flow-skills/
#   ./uninstall.sh --platform copilot           # etc.
#
#   DEV_FLOW_SKILLS_DIR=/custom/path ./uninstall.sh --platform codex   # override
set -euo pipefail

PLATFORM="claude"
while [ $# -gt 0 ]; do
  case "$1" in
    --platform)        PLATFORM="${2:-}"; shift 2 ;;
    --platform=*)      PLATFORM="${1#*=}"; shift ;;
    -h|--help)         sed -n '2,15p' "$0"; exit 0 ;;
    *)                 echo "Unknown argument: $1"; exit 2 ;;
  esac
done

case "$PLATFORM" in
  claude)   SKILLS_DIR="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}" ;;
  codex)    SKILLS_DIR="${DEV_FLOW_SKILLS_DIR:-$HOME/.codex/dev-flow-skills}" ;;
  copilot)  SKILLS_DIR="${DEV_FLOW_SKILLS_DIR:-$HOME/.config/gh-copilot/skills}" ;;
  gemini)   SKILLS_DIR="${DEV_FLOW_SKILLS_DIR:-$HOME/.gemini/skills}" ;;
  cursor)   SKILLS_DIR="${DEV_FLOW_SKILLS_DIR:-$HOME/.dev-flow-skills}" ;;
  generic)  SKILLS_DIR="${DEV_FLOW_SKILLS_DIR:-$HOME/.dev-flow-skills}" ;;
  *)        echo "Unknown platform: $PLATFORM"; exit 2 ;;
esac

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

echo "Uninstalling 8 dev-flow skills from $SKILLS_DIR (platform: $PLATFORM)"

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

# Clean up bootstrap artifacts (tool-mappings.md and platform-specific bootstrap).
if [ -d "$SKILLS_DIR/bootstrap" ]; then
  rm -rf "$SKILLS_DIR/bootstrap"
  echo "  ✓ bootstrap/ removed"
fi
for f in AGENTS.md GEMINI.md .cursorrules system-prompt.md; do
  if [ -f "$SKILLS_DIR/$f" ]; then
    rm -f "$SKILLS_DIR/$f"
    echo "  ✓ $f removed"
  fi
done

echo
echo "Done."
