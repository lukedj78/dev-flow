#!/usr/bin/env bash
# Remove every dev-flow skill (core · web · agent · mobile · monorepo · refactor) from the chosen
# runtime's skills directory.
#
# Files outside the skill folders (bootstrap/tool-mappings.md, AGENTS.md, GEMINI.md, .cursorrules,
# system-prompt.md) are removed only while they are exactly what install.sh wrote — checked against the
# hashes it recorded in <skills-dir>/.dev-flow-installed. One you edited, or one that was never ours, is
# kept and named. `bootstrap/` goes only if it is left empty, so a skill of your own by that name stays.
#
# --restore puts back what the most recent install moved aside (<skills-dir>-backup-*/): your previous
# version of each skill, and a bootstrap file of yours it replaced. Legacy `*.bak` folders left inside
# the skills dir by installs before 2026-08-28 are restored either way.
#
# Usage:
#   ./uninstall.sh                              # defaults to claude
#   ./uninstall.sh --restore                    # and put the previous versions back
#   ./uninstall.sh --platform codex             # ~/.codex/dev-flow-skills/
#   ./uninstall.sh --platform copilot           # etc.
#
#   DEV_FLOW_SKILLS_DIR=/custom/path ./uninstall.sh --platform codex   # override
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLATFORM="claude"
RESTORE=0
while [ $# -gt 0 ]; do
  case "$1" in
    --platform)
      [ -n "${2:-}" ] || { echo "--platform needs a value"; exit 2; }
      PLATFORM="$2"; shift 2 ;;
    --platform=*)      PLATFORM="${1#*=}"; shift ;;
    --restore)         RESTORE=1; shift ;;
    -h|--help)         sed -n '2,23p' "$0"; exit 0 ;;
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
  # Core
  dev-flow
  founder-intelligence
  prd-from-idea
  prd-to-tasks
  wireframe-canvas
  project-infra-setup
  linear-scrum
  compliance-audit
  app-security
  app-verification
  spec-review
  product-to-agent-skill
  registry-intake

  # Web stack
  figma-to-design-md
  image-to-design-md
  design-md-to-app
  coss-ui
  screenshot-to-page
  module-add
  write-tests
  forms
  data-fetching
  state-discipline
  transitions
  animated-icons
  vercel-doctor
  shadscan
  launch-audit
  vercel-deploy
  vgpu-shaders
  iframe-canvas

  # Agent engine (eve)
  eve-agent
  eve-registry-porting

  # Mobile stack
  rn-fundamentals
  rn-styling
  rn-expo-router
  rn-bootstrap
  rn-components-apis
  rn-data-fetching
  rn-add-screen
  rn-write-tests
  rn-animations-gestures
  rn-push-notifications
  rn-backend
  rn-eas-build-submit-update
  rn-publishing-payments
  rn-module-add
  rn-eas-deploy
  rn-upgrade

  # Monorepo stack (web + mobile shared)
  monorepo-bootstrap
  monorepo-add-shared-package
  monorepo-sync-types
  monorepo-add-python-service

  # Refactor & composition skills
  promote-component
  composition-patterns-guide
)

echo "Uninstalling ${#SKILLS[@]} dev-flow skills from $SKILLS_DIR (platform: $PLATFORM)"

for s in "${SKILLS[@]}"; do
  dest="$SKILLS_DIR/$s"
  bak="$SKILLS_DIR/$s.bak"

  if [ -d "$dest" ]; then
    rm -rf "$dest"
    echo "  ✓ $s removed"
  else
    echo "  · $s not found"
  fi

  # Legacy: installs before 2026-08-28 left `<name>.bak` INSIDE the skills dir,
  # where the harness registered it as a second skill with the same `name:`.
  # Restore one if present, then it is gone for good — current installs back up
  # to <skills-dir>-backup-*/ instead.
  if [ -d "$bak" ]; then
    mv "$bak" "$dest"
    echo "    ↩ restored legacy backup $s.bak → $s"
  fi
done

# Bootstrap files: removed only while still exactly as installed. This used to be `rm -rf bootstrap/`
# and `rm -f AGENTS.md …` by name, which deleted a user's own `bootstrap` skill and an AGENTS.md they
# had edited (AUDIT.md §6.3). The paths are fixed here, never read from the manifest, so a manifest
# cannot point the removal anywhere else.
MANIFEST="$SKILLS_DIR/.dev-flow-installed"

sha256_of() {
  if command -v shasum >/dev/null 2>&1; then shasum -a 256 "$1" | cut -d' ' -f1
  else sha256sum "$1" | cut -d' ' -f1; fi
}

recorded_sha() {
  if [ -f "$MANIFEST" ]; then awk -v p="$1" '$2 == p { h = $1 } END { print h }' "$MANIFEST"; fi
}

remove_if_ours() {   # <path relative to SKILLS_DIR> <the template it was installed from>
  local rel="$1" template="$2" dest="$SKILLS_DIR/$1" want
  [ -f "$dest" ] || return 0
  want="$(recorded_sha "$rel")"
  # An install from before the manifest: recognise the file by the current template instead.
  if [ -z "$want" ] && [ -f "$template" ]; then want="$(sha256_of "$template")"; fi
  if [ -n "$want" ] && [ "$(sha256_of "$dest")" = "$want" ]; then
    rm -f "$dest"
    echo "  ✓ $rel removed"
  else
    echo "  · $rel kept — changed since dev-flow installed it, or not dev-flow's"
  fi
}

remove_if_ours "bootstrap/tool-mappings.md" "$SCRIPT_DIR/bootstrap/tool-mappings.md"
for f in AGENTS.md GEMINI.md .cursorrules system-prompt.md; do
  remove_if_ours "$f" "$SCRIPT_DIR/bootstrap/templates/$f"
done
if [ -d "$SKILLS_DIR/bootstrap" ] && rmdir "$SKILLS_DIR/bootstrap" 2>/dev/null; then
  echo "  ✓ bootstrap/ removed"
fi
rm -f "$MANIFEST"

# The most recent backup install.sh made. Timestamped names sort chronologically. The pattern is the exact
# timestamp: `-backup-*` also matched a user's own `skills-backup-manual`, which sorts after every date and
# so was picked as "the latest".
LATEST=""
for d in "${SKILLS_DIR%/}"-backup-[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9][0-9][0-9]; do
  [ -d "$d" ] && LATEST="$d"
done

if [ -n "$LATEST" ]; then
  if [ "$RESTORE" -eq 1 ]; then
    echo
    echo "Restoring from $LATEST"
    for s in "${SKILLS[@]}"; do
      if [ -d "$LATEST/$s" ] && [ ! -e "$SKILLS_DIR/$s" ]; then
        mv "$LATEST/$s" "$SKILLS_DIR/$s"
        echo "  ↩ $s restored"
      fi
    done
    for rel in bootstrap/tool-mappings.md AGENTS.md GEMINI.md .cursorrules system-prompt.md; do
      if [ -f "$LATEST/$rel" ] && [ ! -e "$SKILLS_DIR/$rel" ]; then
        mkdir -p "$(dirname "$SKILLS_DIR/$rel")"
        mv "$LATEST/$rel" "$SKILLS_DIR/$rel"
        echo "  ↩ $rel restored"
      fi
    done
  else
    echo
    echo "The previous versions install.sh moved aside are in $LATEST"
    echo "  Rerun with --restore to put them back."
  fi
fi

echo
echo "Done."
