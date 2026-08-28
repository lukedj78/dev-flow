#!/usr/bin/env bash
# skill-doctor.sh — run skill-doctor's collector against THIS repo, and refuse to
# hand back an empty report that looks valid.
#
# Two traps this exists to remove, both found the hard way:
#
#   1. Without --skills-dir the collector probes only the conventional roots
#      (~/.claude/skills and friends). This repo is flat folders at its root, so
#      it prints "skills found: 0" — a perfectly formed, completely empty report
#      from which you would conclude that no skill is ever used.
#
#   2. With --include-global-skills the global roots are prepended and the
#      collector skips names it has already seen (`if name in skills: continue`),
#      so it reads the INSTALLED copy of every skill and attributes almost
#      nothing to this repo. Any edit it drafts is then written against that copy.
#      We leave the flag off: --skills-dir wins, and all skills resolve here.
#
# Usage:  scripts/skill-doctor.sh [path-to-common-skills-checkout] [-- extra args]
#         SKILL_DOCTOR_DIR=~/src/common-skills scripts/skill-doctor.sh
#
# skill-doctor is not vendored here — it is warpdotdev/common-skills (MIT), and
# it stays theirs. Point this at your own checkout.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DAYS="${SKILL_DOCTOR_DAYS:-90}"
OUT="${SKILL_DOCTOR_OUT:-$REPO_ROOT/.skill-doctor-report}"

SRC="${1:-${SKILL_DOCTOR_DIR:-}}"
if [ -z "$SRC" ]; then
  echo "usage: scripts/skill-doctor.sh <path-to-common-skills-checkout>" >&2
  echo "   or: SKILL_DOCTOR_DIR=<path> scripts/skill-doctor.sh" >&2
  echo "   get it from https://github.com/warpdotdev/common-skills (MIT)" >&2
  exit 2
fi

COLLECTOR="$(find "$SRC" -name collect_sessions.py -not -path '*/node_modules/*' 2>/dev/null | head -1)"
if [ -z "$COLLECTOR" ]; then
  echo "✗ no collect_sessions.py under $SRC" >&2
  exit 2
fi

echo "→ collector: $COLLECTOR"
echo "→ skills:    $REPO_ROOT (global roots deliberately excluded)"

LOG="$(mktemp)"
trap 'rm -f "$LOG"' EXIT
python3 "$COLLECTOR" \
  --harness claude --all-conversations \
  --skills-dir "$REPO_ROOT" \
  --days "$DAYS" --out "$OUT" "${@:2}" | tee "$LOG"

# The whole point: a zero here is silent by default. Make it loud.
FOUND="$(sed -n 's/^skills found: *\([0-9][0-9]*\).*/\1/p' "$LOG" | head -1)"
if [ -z "$FOUND" ]; then
  echo "✗ could not read 'skills found' from the collector output" >&2
  exit 1
fi
if [ "$FOUND" -eq 0 ]; then
  echo "✗ skills found: 0 — the report is empty and would read as 'nothing is used'." >&2
  echo "  The collector globs <root>/*/SKILL.md; check that $REPO_ROOT still holds" >&2
  echo "  one folder per skill at its top level." >&2
  exit 1
fi
# Third trap, found by counting: the collector keys sampled sessions by the
# sessionId inside the .jsonl, but writes each transcript to <harness>-<id>.md.
# A resumed conversation keeps its sessionId across two files, so both records
# are marked sampled and the second write CLOBBERS the first. Sessions are
# ordered newest-first, so the survivor is the older, usually smaller fragment
# — the richer transcript is the one that disappears. Observed: 13 sessions
# marked sampled, 12 files on disk, a 674-call session overwritten by a 13-call
# one. Report it; the count in the summary will not.
MARKED="$(python3 -c '
import json,sys
inv=json.load(open(sys.argv[1]))
print(sum(1 for s in inv.get("sessions",[]) if s.get("sampled")))' "$OUT/inventory.json" 2>/dev/null || echo "")"
ONDISK="$(ls -1 "$OUT/transcripts"/*.md 2>/dev/null | wc -l | tr -d ' ')"
if [ -n "$MARKED" ] && [ "$MARKED" -gt "$ONDISK" ]; then
  echo "⚠ $MARKED sessions marked sampled but only $ONDISK transcripts written —" >&2
  echo "  $((MARKED - ONDISK)) collided on filename (same sessionId across files) and were overwritten." >&2
fi

echo "✓ skills found: $FOUND — report in $OUT"
