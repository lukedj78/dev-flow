"""The release-intelligence gate, shared by update_meta.py (blocks) and show_state.py (reports).

Crossing into `deployed` is the moment a change starts serving strangers. On a project that opted into
release-intelligence, that crossing must be covered by a Release Manifest, and a `high` or `critical`
release must carry a person's recorded yes — not the agent's own verdict that the analysis looked fine.
A successful risk assessment is not an authorisation.

**Applies only when the capability was opted into** (`meta.json#release.enabled` is true). A project
without the field — which is every project until someone runs `release.py enable` — is untouched: this
gate passes without looking further, exactly as `founder_gate` does on the direct path. Turning the
capability off (`release.py disable`) is a recorded decision and also lifts the gate; that is the
escape hatch, and it leaves a trace, which a silent bypass would not.

`release-intelligence/scripts/release.py` writes the block; this file only reads it.
"""

from __future__ import annotations

from pathlib import Path

#: The levels whose release needs a person. Below these the policy table may allow the agent through.
NEEDS_APPROVAL = ("high", "critical")


def applies(meta: dict) -> bool:
    block = meta.get("release")
    if block is None:  # never enabled: the overwhelming majority of projects
        return False
    if not isinstance(block, dict):
        return True  # a hand-edited block is checked, and refused, rather than ignored
    return block.get("enabled") is True


def _production_releases(block: dict) -> list[dict]:
    rels = [r for r in (block.get("releases") or []) if isinstance(r, dict)]
    return [r for r in rels if r.get("environment", "production") == "production"]


def verify(root: Path, meta: dict) -> tuple[bool, str]:
    """(passes, explanation). Never raises."""
    if not applies(meta):
        return True, "release gate not applicable: release-intelligence is not enabled on this project"
    block = meta["release"]
    if not isinstance(block, dict):
        return False, f"meta.json#release is {type(block).__name__}, not an object: it was edited by hand."
    if not isinstance(block.get("releases", []), list):
        return False, "meta.json#release.releases is not a list: it was edited by hand."

    rels = _production_releases(block)
    if not rels:
        return False, ("release-intelligence is enabled and no Release Manifest covers production: "
                       "nothing recorded what is about to ship, at what risk, or who agreed to it.")

    entry = rels[-1]
    rid = entry.get("id", "<no id>")
    level = entry.get("risk")
    approval = entry.get("approval") if isinstance(entry.get("approval"), dict) else {}

    if level not in ("low", "medium", "high", "critical"):
        return False, (f"{rid} has risk {level!r}, which is not a level this gate knows "
                       "(low, medium, high, critical): it was edited by hand.")

    if level in NEEDS_APPROVAL:
        if approval.get("granted_by_user") is not True:
            return False, (f"{rid} is a {level} release and nobody has approved it. "
                           "A high or critical release reaches production on a person's yes, "
                           "never on the agent's reading of its own analysis.")
        if not str(approval.get("quote") or "").strip():
            return False, (f"{rid} is marked approved with no quote: `approved_by_user` without the "
                           "user's own words is indistinguishable from the agent approving itself.")

    if entry.get("destructive_migration") is True:
        # Already implied by `critical`, but stated separately so the refusal names the real hazard
        # rather than a level — the two have different remedies.
        if not str(approval.get("quote") or "").strip():
            return False, (f"{rid} carries a migration a deployment rollback does not undo, and no "
                           "approval quote is recorded. Decide what the rollback leaves behind first.")

    detail = f"{rid}: {level} release"
    if approval.get("granted_by_user") is True:
        detail += f", approved — “{approval.get('quote')}”"
    exposure = (entry.get("rollout") or {}).get("current_percent")
    if isinstance(exposure, int):
        detail += f", exposure {exposure}%"
    return True, detail


def remedy(root: Path) -> str:
    script = Path(__file__).resolve().parents[2] / "release-intelligence" / "scripts" / "release.py"
    run = f"python3 {script}" if script.exists() else "python3 release-intelligence/scripts/release.py"
    return (f"  Fix:     {run} {root} plan --feature <US-N>  — the manifest, with the measured risk floor\n"
            f"  Then:    {run} {root} approve <REL-id> --user-said \"<their words>\"  (high/critical only)\n"
            f"  Opt out: {run} {root} disable  — release-intelligence off, recorded; dev-flow behaves as before")
