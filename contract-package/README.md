# @dev-flow/contract

The portable filesystem contract that backs the dev-flow skills, extracted as a standalone Python package.

## Why a separate package

The dev-flow skills are tied to Claude Code's `Skill` system. When the skills API evolves (new triggering rules, plugin format changes, future runtime swaps), the skills will need rework. **The contract — `meta.json` schema, phase enum, artifact tracking — is what's actually load-bearing.** Putting it behind a versioned package isolates it from the runtime churn.

Anyone can build a new tool that reads/writes `.workflow/` — a CLI, a VSCode extension, a different LLM agent — by depending on this package. The contract becomes the API.

## What's inside

```python
from dev_flow_contract import (
    init_workflow,           # create .workflow/ with seed meta.json
    load_meta, save_meta,    # read/write meta.json
    record_artifact,         # SHA-256 a file + register under meta#artifacts
    set_phase,               # forward-only phase bump
    append_history,          # structured run record
    check_drift,             # diagnostic — returns drift report
    Phase,                   # enum
    Meta, Artifact, Stack,   # dataclasses with full schema
)
```

**Status: a reference implementation, not what the skills run.** The dev-flow skills call `dev-flow/scripts/*.py` (`update_meta.py`, `show_state.py`, `check_drift.py`), which are a separate implementation; the normative text is [`dev-flow/references/contracts.md`](../dev-flow/references/contracts.md). This README used to call the scripts "a thin wrapper" around the package — nothing imported it. Tests hold both to the contract: the phase enum here and the aliases are checked against the contract's table and against `dev-flow/scripts/phases.py`.

What that means in practice:

- **It does not run dev-flow's phase gates.** `set_phase()` enforces monotonicity only. `update_meta.py set-phase` also refuses a move until the inventory, the wireframe canvas, the data-residency decision, the design lint, registry intake and the primitives guard are on record, and, on the founder path, until the founder has approved the Playbook (`meta.json#founder`, kept like any field this package does not model). A tool that moves phase through this package walks past all seven — move phase with `update_meta.py`.
- **It keeps what it does not model.** Keys the dataclasses don't know (`inventory`, `wireframes`, `linear`, `stack.agent`, `stack.data_residency`, a history entry's `action`…) are written back untouched, and an entry no call changed is written back exactly as read.
- **Writes are atomic**, like the scripts': a reader never sees a half-written `meta.json`. There is no lock, so two writers at once can still lose one's change; the scripts take one (`dev-flow/scripts/meta_io.py`).

## Installation

```bash
# From the dev-flow repo, while it's not on PyPI yet:
pip install -e ./contract-package

# Once published:
pip install dev-flow-contract
```

## Usage

```python
from pathlib import Path
from dev_flow_contract import init_workflow, record_artifact, check_drift

root = Path("./my-project")
init_workflow(root, name="My Project")

# After writing some file:
(root / ".workflow" / "DESIGN.md").write_text("# Design")
record_artifact(root, ".workflow/DESIGN.md", produced_by="my-skill")

# Later, check what's stale:
report = check_drift(root)
if report.has_drift:
    for row in report.rows:
        if row.status != "fresh":
            print(f"{row.path}: {row.status}")
```

## Stability guarantees

- The contract schema (`meta.json` shape) follows semver. Breaking changes bump the major.
- Field additions (new optional keys, new phase values appended to the enum) bump minor.
- Bug fixes / clarifications bump patch.
- The current version (`0.1.0`) is **pre-stable** — expect the surface to evolve until the dev-flow skills cut a 1.0 alongside.

## Compatibility

- Python ≥ 3.9 (the dev-flow scripts target the same).
- No third-party runtime dependencies. Stdlib only — `hashlib`, `json`, `pathlib`, `dataclasses`, `enum`.
- Test deps: `pytest`.

## License

MIT — same as the parent dev-flow repo.
