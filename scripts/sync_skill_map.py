#!/usr/bin/env python3
"""sync_skill_map.py — rewrite the per-skill meta in docs/dev-flow-skill-map.html from skills.json.

The skill map is hand-authored, but each row carries a bare `1122·9r·2s` (SKILL.md lines ·
references · scripts) that lint check 13 compares against skills.json. Nothing used to write
those numbers, so every SKILL.md edit left the map wrong until someone noticed in CI. This is
the writer: run it after `build_skills_registry.py` (it reads skills.json, not the skill dirs,
so the two can never disagree).

Usage:
    python3 scripts/sync_skill_map.py            # rewrite the rows that drifted
    python3 scripts/sync_skill_map.py --check    # exit 1 if any row is stale (CI)

Only the per-row meta is touched. The metric cards at the top of the map (check 16) change
only when a skill is added or removed, and stay a deliberate hand edit.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "skills.json"
SKILL_MAP = ROOT / "docs" / "dev-flow-skill-map.html"

# Same shape lint_skills.py's MAP_META_RE matches, with the pieces captured so the row can be rewritten.
ROW_RE = re.compile(
    r'(<span class="sk[^"]*">)([a-z0-9-]+)(</span><span class="m">)(\d+)·(\d+)r·(\d+)s(</span>)'
)


def main() -> int:
    check = "--check" in sys.argv[1:]
    if not SKILL_MAP.exists():
        print(f"[sync-skill-map] no {SKILL_MAP.relative_to(ROOT)} — nothing to do")
        return 0
    registry = json.loads(REGISTRY.read_text())
    entries = {e["name"]: e for e in registry.get("skills", [])}

    drifted: list[tuple[str, tuple[int, int, int], tuple[int, int, int]]] = []
    unknown: list[str] = []

    def rewrite(m: re.Match[str]) -> str:
        name = m.group(2)
        entry = entries.get(name)
        if entry is None:
            unknown.append(name)
            return m.group(0)
        real = (entry["skill_md_lines"], len(entry.get("references", [])), len(entry.get("scripts", [])))
        current = (int(m.group(4)), int(m.group(5)), int(m.group(6)))
        if current != real:
            drifted.append((name, current, real))
        return f"{m.group(1)}{name}{m.group(3)}{real[0]}·{real[1]}r·{real[2]}s{m.group(7)}"

    html = SKILL_MAP.read_text(errors="ignore")
    new_html = ROW_RE.sub(rewrite, html)

    for name in unknown:
        print(f"[sync-skill-map] ! `{name}` is on the map but not in skills.json — left as is")
    for name, cur, real in drifted:
        print(f"[sync-skill-map] {name}: {cur[0]}·{cur[1]}r·{cur[2]}s → {real[0]}·{real[1]}r·{real[2]}s")

    if not drifted:
        print("[sync-skill-map] ✓ every row matches skills.json")
        return 0
    if check:
        print(f"[sync-skill-map] ✗ {len(drifted)} stale row(s). Run: python3 scripts/sync_skill_map.py")
        return 1
    SKILL_MAP.write_text(new_html)
    print(f"[sync-skill-map] ✓ rewrote {len(drifted)} row(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
