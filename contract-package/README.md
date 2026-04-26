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

The runtime (`dev-flow/scripts/*.py`) is a thin wrapper around these primitives. Skills that don't run inside Claude Code can use the package directly.

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
