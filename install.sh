#!/usr/bin/env bash
# Install all 27 dev-flow skills (9 web + 15 mobile + 3 monorepo) + a
# runtime-appropriate bootstrap file.
#
# dev-flow's skills format is Claude Code-native, but the SKILL.md content is
# generic markdown that any agent can follow. This installer supports five
# runtimes — pick yours with --platform.
#
# Stacks:
#   * Web (Next.js + shadcn):    dev-flow, prd-from-idea, prd-to-tasks,
#                                figma-to-design-md, image-to-design-md,
#                                design-md-to-app, screenshot-to-page,
#                                module-add, write-tests
#   * Mobile (Expo + RN):         rn-fundamentals, rn-styling, rn-expo-router,
#                                rn-bootstrap, rn-components-apis,
#                                rn-data-fetching, rn-add-screen,
#                                rn-write-tests, rn-animations-gestures,
#                                rn-push-notifications, rn-backend,
#                                rn-eas-build-submit-update,
#                                rn-publishing-payments, rn-module-add,
#                                rn-eas-deploy
#
# Usage:
#   ./install.sh                                # defaults to claude
#   ./install.sh --platform claude              # ~/.claude/skills/
#   ./install.sh --platform codex               # ~/.codex/dev-flow-skills/ + AGENTS.md
#   ./install.sh --platform copilot             # ~/.config/gh-copilot/skills/
#   ./install.sh --platform gemini              # ~/.gemini/skills/ + GEMINI.md
#   ./install.sh --platform cursor              # ~/.dev-flow-skills/ + .cursorrules
#   ./install.sh --platform generic             # ~/.dev-flow-skills/ (path you wire yourself)
#   ./install.sh --list-platforms               # show the table without installing
#
#   CLAUDE_SKILLS_DIR=/custom/path ./install.sh --platform claude   # override
#
# Idempotent-ish: existing installs at the target are backed up to .bak before
# overwrite (one level only — running twice loses the second-most-recent).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLATFORM="claude"
LIST_ONLY=0

# Argument parsing.
while [ $# -gt 0 ]; do
  case "$1" in
    --platform)
      PLATFORM="${2:-}"
      shift 2 || { echo "--platform needs a value"; exit 2; }
      ;;
    --platform=*)
      PLATFORM="${1#*=}"
      shift
      ;;
    --list-platforms)
      LIST_ONLY=1
      shift
      ;;
    -h|--help)
      sed -n '2,30p' "$0"   # prints the usage block above
      exit 0
      ;;
    *)
      echo "Unknown argument: $1"
      echo "Run with --help for usage."
      exit 2
      ;;
  esac
done

print_platforms() {
  cat <<'EOF'
Supported platforms:

  claude    ~/.claude/skills/                — Claude Code (native skills)
  codex     ~/.codex/dev-flow-skills/        — Codex CLI (loads via AGENTS.md)
  copilot   ~/.config/gh-copilot/skills/     — GitHub Copilot CLI
  gemini    ~/.gemini/skills/                — Gemini CLI (loads via GEMINI.md)
  cursor    ~/.dev-flow-skills/              — Cursor (loads via .cursorrules)
  generic   ~/.dev-flow-skills/              — any agent (use with system-prompt.md)

Tested status:
  claude    fully tested
  codex/copilot/gemini/cursor/generic   bootstrap files scaffolded, end-to-end
                                        not yet validated. Help wanted — file an
                                        issue if your runtime needs adjustments.
EOF
}

if [ "$LIST_ONLY" -eq 1 ]; then
  print_platforms
  exit 0
fi

# Resolve install destination + bootstrap details by platform.
case "$PLATFORM" in
  claude)
    SKILLS_DIR="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
    BOOTSTRAP_TEMPLATE=""    # no bootstrap needed — Claude auto-discovers
    BOOTSTRAP_TARGET=""
    ;;
  codex)
    SKILLS_DIR="${DEV_FLOW_SKILLS_DIR:-$HOME/.codex/dev-flow-skills}"
    BOOTSTRAP_TEMPLATE="$SCRIPT_DIR/bootstrap/templates/AGENTS.md"
    # User project root is unknown at install time — we install the template
    # to the skills dir and tell the user to copy it into projects.
    BOOTSTRAP_TARGET="$SKILLS_DIR/AGENTS.md"
    ;;
  copilot)
    SKILLS_DIR="${DEV_FLOW_SKILLS_DIR:-$HOME/.config/gh-copilot/skills}"
    BOOTSTRAP_TEMPLATE=""    # Copilot CLI auto-discovers from skills folder
    BOOTSTRAP_TARGET=""
    ;;
  gemini)
    SKILLS_DIR="${DEV_FLOW_SKILLS_DIR:-$HOME/.gemini/skills}"
    BOOTSTRAP_TEMPLATE="$SCRIPT_DIR/bootstrap/templates/GEMINI.md"
    BOOTSTRAP_TARGET="$SKILLS_DIR/GEMINI.md"
    ;;
  cursor)
    SKILLS_DIR="${DEV_FLOW_SKILLS_DIR:-$HOME/.dev-flow-skills}"
    BOOTSTRAP_TEMPLATE="$SCRIPT_DIR/bootstrap/templates/.cursorrules"
    BOOTSTRAP_TARGET="$SKILLS_DIR/.cursorrules"
    ;;
  generic)
    SKILLS_DIR="${DEV_FLOW_SKILLS_DIR:-$HOME/.dev-flow-skills}"
    BOOTSTRAP_TEMPLATE="$SCRIPT_DIR/bootstrap/templates/system-prompt.md"
    BOOTSTRAP_TARGET="$SKILLS_DIR/system-prompt.md"
    ;;
  *)
    echo "Unknown platform: $PLATFORM"
    echo
    print_platforms
    exit 2
    ;;
esac

SKILLS=(
  # Core orchestrator + stack-agnostic flow
  dev-flow
  prd-from-idea
  prd-to-tasks

  # Web stack (Next.js + shadcn)
  figma-to-design-md
  image-to-design-md
  design-md-to-app
  screenshot-to-page
  module-add
  write-tests

  # Mobile stack (Expo + React Native)
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

  # Monorepo stack (web + mobile shared)
  monorepo-bootstrap
  monorepo-add-shared-package
  monorepo-sync-types
)

echo "Installing ${#SKILLS[@]} dev-flow skills →  $SKILLS_DIR  (platform: $PLATFORM)"
mkdir -p "$SKILLS_DIR"

# Sanity check the host environment. The skills install fine without these
# but several scripts will fail at runtime — warn the user up-front.
echo
echo "Checking host dependencies…"
missing=0
need_warn() { echo "  ⚠ $1"; missing=1; }

if ! command -v python3 >/dev/null 2>&1; then
  need_warn "python3 not found — install via 'brew install python' or your distro's package manager"
else
  echo "  ✓ python3"
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
  echo "Some host dependencies are missing. Skills will install fine, but"
  echo "some scripts will fail when they run. Address the warnings above when"
  echo "convenient — installation continues."
fi
echo

# Copy each skill folder.
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

# Copy the cross-platform tool mappings — useful regardless of platform.
mkdir -p "$SKILLS_DIR/bootstrap"
cp "$SCRIPT_DIR/bootstrap/tool-mappings.md" "$SKILLS_DIR/bootstrap/tool-mappings.md"
echo "  ✓ bootstrap/tool-mappings.md"

# Copy the platform-specific bootstrap if there is one.
if [ -n "$BOOTSTRAP_TEMPLATE" ] && [ -f "$BOOTSTRAP_TEMPLATE" ]; then
  cp "$BOOTSTRAP_TEMPLATE" "$BOOTSTRAP_TARGET"
  echo "  ✓ $(basename "$BOOTSTRAP_TARGET")  (bootstrap for $PLATFORM)"
fi

echo
echo "Done. Next steps for platform: $PLATFORM"
case "$PLATFORM" in
  claude)
    echo "  Restart Claude Code (or reload your client) to pick up the skills."
    echo "  Then say something like \"voglio costruire X\" — dev-flow will route."
    ;;
  codex)
    echo "  1. Copy $BOOTSTRAP_TARGET into each project root as AGENTS.md."
    echo "  2. Open the project with Codex CLI — it'll read AGENTS.md automatically."
    echo "  3. Try: 'I want to build a CRM for veterinarians.'"
    echo
    echo "  Alternative: keep AGENTS.md only at $SKILLS_DIR and reference it"
    echo "  from project AGENTS.md with a single 'load $SKILLS_DIR/AGENTS.md' line."
    ;;
  copilot)
    echo "  Copilot CLI auto-discovers skills from the directory above."
    echo "  Verify with 'gh copilot skills list' and try invoking dev-flow."
    ;;
  gemini)
    echo "  1. Copy $BOOTSTRAP_TARGET into each project root as GEMINI.md."
    echo "  2. Run 'gemini' in the project — it reads GEMINI.md at session start."
    ;;
  cursor)
    echo "  1. Copy $BOOTSTRAP_TARGET into each project root as .cursorrules."
    echo "  2. Cursor will load it automatically when you open the project."
    ;;
  generic)
    echo "  Prepend $BOOTSTRAP_TARGET to your agent's system prompt."
    echo "  Make sure the agent has filesystem + shell access to $SKILLS_DIR."
    ;;
esac
