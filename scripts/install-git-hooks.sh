#!/usr/bin/env bash
# install-git-hooks.sh — point this clone at the versioned hooks in .githooks/.
#
# Git does not version .git/hooks, so a hook only exists where somebody installed it.
# core.hooksPath is per clone: run this once after cloning (or after pulling the commit
# that added .githooks/). Undo with:  git config --unset core.hooksPath

set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

chmod +x .githooks/*
git config core.hooksPath .githooks
echo "✓ core.hooksPath = .githooks ($(ls .githooks | tr '\n' ' '))"
echo "  pre-commit regenerates skills.json / docs site / skill map / manifests when a skill source is committed, then lints."
