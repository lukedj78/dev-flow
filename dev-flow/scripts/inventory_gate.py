"""Gate: a project does not leave `idea_captured` without an inventory on record.

`update_meta.py set-phase` calls `verify` when the phase crosses into `prd_drafted`. The rule is the
one in references/before-you-build.md — look before you build — made checkable: `meta.json#inventory`
must carry a verdict and what was searched. A skipped inventory is allowed; an unexplained one is not.
"""

from __future__ import annotations

from pathlib import Path

VERDICTS = ("have-it", "adapts", "halfway", "build", "skipped")


def verify(_root: Path, meta: dict) -> tuple[bool, str]:
    inv = meta.get("inventory")
    if not isinstance(inv, dict) or not inv:
        return False, "meta.json#inventory is missing: nobody has looked at whether this already exists."
    verdict = inv.get("verdict")
    if verdict not in VERDICTS:
        return False, f"meta.json#inventory.verdict is {verdict!r}; it must be one of {', '.join(VERDICTS)}."
    if verdict == "skipped":
        if not str(inv.get("reason") or "").strip():
            return False, "the inventory is marked skipped without a reason."
        return True, ""
    if not inv.get("searched"):
        return False, "meta.json#inventory.searched is empty: name what was searched, including what gave nothing."
    return True, ""


def remedy(root: Path) -> str:
    return (
        "  Run the inventory, then record it:\n"
        "    python3 dev-flow/scripts/inventory.py scan <two or three words for the idea>\n"
        f"    python3 dev-flow/scripts/inventory.py record {root} --verdict <have-it|adapts|halfway|build> \\\n"
        "        --searched <what you looked at> [--not-covered <what you could not>] [--summary \"...\"]\n"
        "  To skip on purpose: --verdict skipped --reason \"...\" — the reason is kept in meta.json."
    )
