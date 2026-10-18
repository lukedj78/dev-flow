#!/usr/bin/env bash
# Install every dev-flow skill (core · web · agent · mobile · monorepo · refactor) + a
# runtime-appropriate bootstrap file.
#
# dev-flow's skills format is Claude Code-native, but the SKILL.md content is
# generic markdown that any agent can follow. This installer supports six
# runtimes — pick yours with --platform.
#
# Stacks: core (stack-agnostic flow), web (Next.js 16 + shadcn / Base UI / MUI / Coss), agent engine
# (eve), mobile (Expo + RN), monorepo, refactor & composition. The SKILLS array below is the list, and
# lint_skills.py checks it against the skill folders on disk. (This header used to repeat it with counts;
# they said "won't drift" and drifted: Core 5 against 10, Web 16 against 19.)
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
#   ./install.sh --projects ~/projects          # also refresh the project hooks (see below)
#
#   CLAUDE_SKILLS_DIR=/custom/path ./install.sh --platform claude   # override
#
# Idempotent: an existing skill folder at the target is moved to a timestamped
#   <skills-dir>-backup-YYYYmmdd-HHMMSS/ before it is overwritten — OUTSIDE the skills dir, so the
#   backup is never itself registered as a skill. The newest 3 are kept (DEV_FLOW_KEEP_BACKUPS=N, 0 = all); `./uninstall.sh --restore`
#   puts back the most recent. A bootstrap file (AGENTS.md, GEMINI.md, .cursorrules, system-prompt.md,
#   bootstrap/tool-mappings.md) that is not the one this installer wrote is saved there too, and every
#   file it writes outside a skill folder is recorded with its hash in <skills-dir>/.dev-flow-installed,
#   so uninstall.sh removes only what is still exactly as installed.
#
# --projects DIR (repeatable): after installing, re-run the setup of every project in DIR (DIR itself and
#   its direct subfolders) that already has a dev-flow hook — registry-intake (.claude/hooks/registry_intake.py)
#   or the primitives guard (scripts/guard/primitives-guard.mjs). Each project runs its hook from a committed
#   copy, and `check` refuses the next phase while that copy differs from the installed skill, so every skill
#   update used to need one setup per project by hand. A project without a hook is never touched, nothing is
#   committed, and a setup that fails is named without failing the install. Opt-in: without the flag, this
#   installer writes only under the skills dir.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLATFORM="claude"
LIST_ONLY=0
PROJECT_DIRS=()

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
    --projects)
      [ -n "${2:-}" ] || { echo "--projects needs a directory"; exit 2; }
      [ -d "$2" ] || { echo "--projects: not a directory: $2"; exit 2; }
      PROJECT_DIRS+=("$(cd "$2" && pwd)")
      shift 2
      ;;
    -h|--help)
      sed -n '2,40p' "$0"   # prints the usage block above
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
  founder-intelligence
  prd-from-idea
  prd-to-tasks
  wireframe-canvas
  project-infra-setup
  scrum
  compliance-audit
  app-security
  app-verification
  spec-review
  product-to-agent-skill
  registry-intake

  # Web stack (Next.js 16 App Router + shadcn / Base UI / MUI)
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

  # Agent engine (eve — Vercel filesystem-first agent framework)
  eve-agent
  eve-registry-porting

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

# Backups go OUTSIDE the skills directory — anything left inside it is scanned
# and registered as a skill. Timestamped so consecutive installs don't collide.
BACKUP_DIR="${SKILLS_DIR%/}-backup-$(date +%Y%m%d-%H%M%S)"

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
    # ⚠️ The backup must NOT live inside SKILLS_DIR. A `<name>.bak` folder there
    # still holds a valid SKILL.md declaring the SAME `name:` as the live skill,
    # so the harness registers BOTH — and the stale copy competes for triggering
    # against the one you just installed. Found the hard way: one install left 42
    # duplicate pairs loadable, every one of them the pre-update version.
    mkdir -p "$BACKUP_DIR"
    rm -rf "$BACKUP_DIR/$s"
    mv "$dest" "$BACKUP_DIR/$s"
    echo "  ⚠ $s — previous version moved to $BACKUP_DIR/$s"
  fi

  cp -R "$src" "$dest"
  echo "  ✓ $s"
done

# Skills that were renamed or folded into another. An installed copy would still declare its old name and
# compete with its successor for the same triggers, so it is moved to the backup like any replaced version.
RETIRED=(
  "linear-scrum:scrum"
)
for pair in "${RETIRED[@]}"; do
  old="${pair%%:*}"; new="${pair#*:}"
  if [ -d "$SKILLS_DIR/$old" ]; then
    mkdir -p "$BACKUP_DIR"
    rm -rf "$BACKUP_DIR/$old"
    mv "$SKILLS_DIR/$old" "$BACKUP_DIR/$old"
    echo "  · removed retired skill $old (now $new) — moved to $BACKUP_DIR/$old"
  fi
done

# Files written OUTSIDE a skill folder share the skills dir with whatever the user keeps there — a skill
# of their own called `bootstrap`, an AGENTS.md they edited. uninstall.sh used to delete all of them by
# name. Now each one is recorded with its hash, and one the installer did not write is saved first.
MANIFEST="$SKILLS_DIR/.dev-flow-installed"
NEW_MANIFEST="$(mktemp)"

sha256_of() {
  if command -v shasum >/dev/null 2>&1; then shasum -a 256 "$1" | cut -d' ' -f1
  else sha256sum "$1" | cut -d' ' -f1; fi
}

recorded_sha() {
  if [ -f "$MANIFEST" ]; then awk -v p="$1" '$2 == p { h = $1 } END { print h }' "$MANIFEST"; fi
}

install_file() {   # <source> <path relative to SKILLS_DIR>
  local src="$1" rel="$2" dest="$SKILLS_DIR/$2"
  if [ -f "$dest" ] && ! cmp -s "$src" "$dest" && [ "$(sha256_of "$dest")" != "$(recorded_sha "$rel")" ]; then
    mkdir -p "$(dirname "$BACKUP_DIR/$rel")"
    cp "$dest" "$BACKUP_DIR/$rel"
    echo "  ⚠ $rel — the existing file is not the one dev-flow installed; saved to $BACKUP_DIR/$rel"
  fi
  mkdir -p "$(dirname "$dest")"
  cp "$src" "$dest"
  echo "$(sha256_of "$dest")  $rel" >> "$NEW_MANIFEST"
  echo "  ✓ $rel"
}

# Copy the cross-platform tool mappings — useful regardless of platform.
install_file "$SCRIPT_DIR/bootstrap/tool-mappings.md" "bootstrap/tool-mappings.md"

# Copy the platform-specific bootstrap if there is one.
if [ -n "$BOOTSTRAP_TEMPLATE" ] && [ -f "$BOOTSTRAP_TEMPLATE" ]; then
  install_file "$BOOTSTRAP_TEMPLATE" "$(basename "$BOOTSTRAP_TARGET")"
  echo "    (bootstrap for $PLATFORM)"
fi

# Keep the records of files this run did not touch (cursor and generic share a folder), then add ours.
if [ -f "$MANIFEST" ]; then
  awk 'NR == FNR { mine[$2] = 1; next } !($2 in mine)' "$NEW_MANIFEST" "$MANIFEST" > "$NEW_MANIFEST.all"
  cat "$NEW_MANIFEST" >> "$NEW_MANIFEST.all"
  mv "$NEW_MANIFEST.all" "$MANIFEST"
  rm -f "$NEW_MANIFEST"
else
  mv "$NEW_MANIFEST" "$MANIFEST"
fi

# Keep the newest DEV_FLOW_KEEP_BACKUPS backups (default 3; 0 keeps them all). Each run used to add one,
# about 7 MB, forever. Only folders with this installer's exact timestamp are counted or removed: a
# `skills-backup-manual` of the user's own shares the prefix and must never match.
KEEP="${DEV_FLOW_KEEP_BACKUPS:-3}"
case "$KEEP" in ''|*[!0-9]*) KEEP=3 ;; esac
if [ "$KEEP" -gt 0 ]; then
  total=0
  for d in "${SKILLS_DIR%/}"-backup-[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9][0-9][0-9]; do
    if [ -d "$d" ]; then total=$((total + 1)); fi
  done
  drop=$((total - KEEP))
  for d in "${SKILLS_DIR%/}"-backup-[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9][0-9][0-9]; do   # the glob sorts oldest first
    if [ "$drop" -le 0 ]; then break; fi
    if [ -d "$d" ]; then
      rm -rf "$d"
      echo "  · removed an old backup: $d (keeping the newest $KEEP; DEV_FLOW_KEEP_BACKUPS=0 keeps all)"
      drop=$((drop - 1))
    fi
  done
fi

# Opt-in: refresh the vendored hooks of the projects that already have them (see --projects above).
if [ "${#PROJECT_DIRS[@]}" -gt 0 ]; then
  echo
  echo "Refreshing project hooks:"
  touched=0
  for base in "${PROJECT_DIRS[@]}"; do
    for proj in "$base" "$base"/*/; do
      proj="${proj%/}"
      [ -d "$proj" ] || continue
      jobs=()
      if [ -f "$proj/.claude/hooks/registry_intake.py" ]; then
        jobs+=("registry-intake|$SKILLS_DIR/registry-intake/scripts/registry_intake.py|setup")
      fi
      if [ -f "$proj/scripts/guard/primitives-guard.mjs" ]; then
        jobs+=("primitives-guard|$SKILLS_DIR/design-md-to-app/scripts/setup_primitives_guard.py|")
      fi
      [ "${#jobs[@]}" -gt 0 ] || continue
      # The scan reaches every subfolder, cloned third-party repos included, and setup writes the hook copies,
      # settings.json, AGENTS.md, meta.json, the lock, the formatter's ignore file and more. A symlink on the
      # way to any of them would make setup overwrite the file it points to, outside the project. The rule is
      # general, not a list of paths that ages with every file setup learns to write: skip a project that is
      # itself a symlink, or that has a symlink anywhere in its real tree resolving outside it. The walk has
      # no depth limit, so a chain of in-project links always lands on folders it has checked. The folders it
      # skips for cost (node_modules, .git, .next) are the exception, so a link into one of them counts too.
      linked="$(python3 - "$proj" <<'PY'
import os, sys
SKIP = ("node_modules", ".git", ".next")
top = sys.argv[1].rstrip("/")
root = os.path.realpath(top)
if os.path.islink(top):
    print("the project folder itself"); sys.exit()
def inside(path):
    return os.path.commonpath([root, path]) == root
def unscanned(path):
    return any(part in SKIP for part in os.path.relpath(path, root).split(os.sep))
for folder, dirs, files in os.walk(top):          # os.walk does not descend into symlinked folders
    dirs[:] = [d for d in dirs if d not in SKIP]
    for name in dirs + files:
        path = os.path.join(folder, name)
        if os.path.islink(path):
            target = os.path.realpath(path)
            if not inside(target) or unscanned(target):
                print(os.path.relpath(path, top)); sys.exit()
PY
)"
      if [ -n "$linked" ]; then
        echo "  ✗ $(basename "$proj"): skipped — $linked is a symlink out of the project; setup would write through it"
        continue
      fi
      touched=$((touched + 1))
      line="  ↻ $(basename "$proj"):"
      fails=""
      for job in "${jobs[@]}"; do
        IFS='|' read -r name script sub <<< "$job"
        if [ ! -f "$script" ]; then
          line="$line $name ✗ (skill not installed)"
          continue
        fi
        if out="$(python3 "$script" ${sub:+"$sub"} "$proj" 2>&1)"; then
          skipped="$(printf '%s\n' "$out" | grep -m1 ' skipped — ' | sed 's/.* skipped — //' || true)"
          if [ -n "$skipped" ]; then
            line="$line $name skipped ($skipped)"
          else
            line="$line $name ✓"
          fi
        else
          line="$line $name ✗"
          fails="$fails$(printf '%s\n' "$out" | grep -E '✗|!|rror' | sed 's/^/      /')"$'\n'
        fi
      done
      echo "$line"
      if [ -n "$fails" ]; then printf '%s' "$fails"; fi
    done
  done
  if [ "$touched" -eq 0 ]; then
    echo "  no project with a dev-flow hook found under: ${PROJECT_DIRS[*]}"
  else
    echo "  Nothing was committed: review each project's changes with git diff."
  fi
fi

echo
echo "Done. Next steps for platform: $PLATFORM"
case "$PLATFORM" in
  claude)
    echo "  Restart Claude Code (or reload your client) to pick up the skills."
    echo "  Then say something like \"voglio costruire X\" — dev-flow will route."
    ;;
  codex)
    echo "  1. Merge $BOOTSTRAP_TARGET into each project root AGENTS.md (append — do NOT overwrite)."
    echo "     Next.js 16.3+ maintains its own block between <!-- BEGIN:nextjs-agent-rules --> markers"
    echo "     in AGENTS.md/CLAUDE.md; overwriting the file wipes it. Never edit inside the markers."
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
