#!/usr/bin/env bash
# refresh-stack-defaults.sh — wrapper around scripts/refresh_stack_defaults.py
#
# Usage:
#   ./scripts/refresh-stack-defaults.sh           # dry-run, print diff
#   ./scripts/refresh-stack-defaults.sh --apply   # rewrite the stack-defaults.md files

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$SCRIPT_DIR/refresh_stack_defaults.py" "$@"
