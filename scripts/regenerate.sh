#!/usr/bin/env bash
# regenerate.sh — rebuild everything CI derives from the skill sources, in dependency order.
#
#   skills.json  →  docs/ site  →  skill-map row meta  →  plugin manifests
#
# Run after editing any SKILL.md, references/ or scripts/ (the pre-commit hook in .githooks/
# does it for you). Idempotent: with nothing to change it writes nothing new.
#
# Usage:
#   ./scripts/regenerate.sh                # regenerate
#   REGEN_BUNDLES=1 ./scripts/regenerate.sh # also repackage dist/*.skill (slow, binary churn — opt in)

set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

python3 scripts/build_skills_registry.py
python3 scripts/build_site.py
python3 scripts/sync_skill_map.py
python3 scripts/build_plugin_manifest.py
python3 scripts/build_agent_plugin.py

if [ "${REGEN_BUNDLES:-0}" = "1" ]; then
  python3 scripts/build_skill_bundles.py
fi
