"""Tests for dev_flow_contract core API."""
from __future__ import annotations

import json
import pathlib
import re
from pathlib import Path

import pytest

from dev_flow_contract import (
    Phase,
    append_history,
    check_drift,
    init_workflow,
    load_meta,
    record_artifact,
    set_phase,
)


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    """Fresh project with .workflow/ initialized."""
    init_workflow(tmp_path, name="Test Project")
    return tmp_path


# ---------------------------------------------------------------------------
# init_workflow
# ---------------------------------------------------------------------------


def test_init_workflow_creates_meta_json(tmp_path: Path) -> None:
    meta = init_workflow(tmp_path, name="My App")
    assert (tmp_path / ".workflow" / "meta.json").exists()
    assert meta.project_name == "My App"
    assert meta.project_slug == "my-app"
    assert meta.phase == Phase.EMPTY.value


def test_init_workflow_is_idempotent(tmp_path: Path) -> None:
    first = init_workflow(tmp_path, name="App")
    # Mutate something so we'd notice an overwrite.
    set_phase(tmp_path, Phase.PRD_DRAFTED)
    second = init_workflow(tmp_path, name="Different Name")
    assert second.phase == Phase.PRD_DRAFTED.value
    assert second.project_name == first.project_name  # NOT overwritten


def test_init_workflow_fails_on_missing_root(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        init_workflow(tmp_path / "nonexistent")


# ---------------------------------------------------------------------------
# record_artifact
# ---------------------------------------------------------------------------


def test_record_artifact_hashes_and_stores(project_root: Path) -> None:
    target = project_root / ".workflow" / "DESIGN.md"
    target.write_text("# DESIGN")

    artifact = record_artifact(project_root, ".workflow/DESIGN.md", produced_by="test-skill")
    assert len(artifact.sha256) == 64
    assert artifact.produced_by == "test-skill"

    meta = load_meta(project_root)
    assert ".workflow/DESIGN.md" in meta.artifacts
    assert meta.artifacts[".workflow/DESIGN.md"].sha256 == artifact.sha256


def test_record_artifact_with_derived_from(project_root: Path) -> None:
    design = project_root / ".workflow" / "DESIGN.md"
    design.write_text("# DESIGN")
    record_artifact(project_root, ".workflow/DESIGN.md", produced_by="image-to-design-md")

    registry = project_root / "registry.json"
    registry.write_text("{}")
    artifact = record_artifact(
        project_root,
        "registry.json",
        produced_by="design-md-to-app",
        derived_from=[".workflow/DESIGN.md"],
    )
    assert len(artifact.derived_from) == 1
    assert artifact.derived_from[0].path == ".workflow/DESIGN.md"


def test_record_artifact_fails_on_missing_file(project_root: Path) -> None:
    with pytest.raises(FileNotFoundError):
        record_artifact(project_root, "nonexistent.md", produced_by="x")


# ---------------------------------------------------------------------------
# set_phase
# ---------------------------------------------------------------------------


def test_set_phase_forward_succeeds(project_root: Path) -> None:
    set_phase(project_root, Phase.PRD_DRAFTED)
    assert load_meta(project_root).phase == Phase.PRD_DRAFTED.value


def test_set_phase_regression_refused(project_root: Path) -> None:
    set_phase(project_root, Phase.SCAFFOLDED)
    with pytest.raises(ValueError, match="regression refused"):
        set_phase(project_root, Phase.PRD_DRAFTED)


def test_set_phase_regression_allowed_with_flag(project_root: Path) -> None:
    set_phase(project_root, Phase.SCAFFOLDED)
    set_phase(project_root, Phase.PRD_DRAFTED, allow_regress=True)
    assert load_meta(project_root).phase == Phase.PRD_DRAFTED.value


def test_set_phase_invalid_value_raises(project_root: Path) -> None:
    with pytest.raises(ValueError, match="Unknown phase"):
        set_phase(project_root, "garbage")


# ---------------------------------------------------------------------------
# append_history
# ---------------------------------------------------------------------------


def test_append_history_records_run(project_root: Path) -> None:
    append_history(
        project_root,
        skill="prd-from-idea",
        inputs={"idea": "..."},
        outputs=["PRD.md"],
        phase_after=Phase.PRD_DRAFTED,
    )
    meta = load_meta(project_root)
    assert len(meta.history) == 1
    assert meta.history[0].skill == "prd-from-idea"
    assert meta.history[0].outputs == ["PRD.md"]
    assert meta.phase == Phase.PRD_DRAFTED.value


# ---------------------------------------------------------------------------
# check_drift — single hop + transitive
# ---------------------------------------------------------------------------


def _make_chain(project_root: Path) -> None:
    """A → B → C: design → registry → showcase."""
    design = project_root / ".workflow" / "DESIGN.md"
    design.write_text("# DESIGN v1")
    record_artifact(project_root, ".workflow/DESIGN.md", produced_by="image-to-design-md")

    registry = project_root / "registry.json"
    registry.write_text('{"v": 1}')
    record_artifact(project_root, "registry.json", produced_by="design-md-to-app",
                    derived_from=[".workflow/DESIGN.md"])

    (project_root / "app").mkdir()
    showcase = project_root / "app" / "showcase.tsx"
    showcase.write_text("export default function() {}")
    record_artifact(project_root, "app/showcase.tsx", produced_by="design-md-to-app",
                    derived_from=["registry.json"])


def test_check_drift_all_fresh(project_root: Path) -> None:
    _make_chain(project_root)
    report = check_drift(project_root)
    assert not report.has_drift
    assert report.fresh_count == 3


def test_check_drift_self_drift(project_root: Path) -> None:
    _make_chain(project_root)
    (project_root / ".workflow" / "DESIGN.md").write_text("# DESIGN v2")
    report = check_drift(project_root)

    statuses = {r.path: r.status for r in report.rows}
    assert statuses[".workflow/DESIGN.md"] == "self-drift"
    assert statuses["registry.json"] == "upstream-stale"
    # Transitive: showcase derives from registry, which is stale because
    # DESIGN drifted. Showcase MUST be flagged stale too.
    assert statuses["app/showcase.tsx"] == "upstream-stale"


def test_check_drift_missing_file(project_root: Path) -> None:
    _make_chain(project_root)
    (project_root / "registry.json").unlink()
    report = check_drift(project_root)
    statuses = {r.path: r.status for r in report.rows}
    assert statuses["registry.json"] == "missing"
    assert statuses["app/showcase.tsx"] == "upstream-stale"


def test_check_drift_no_artifacts(project_root: Path) -> None:
    report = check_drift(project_root)
    assert not report.has_drift
    assert report.fresh_count == 0


# ---------------------------------------------------------------------------
# Round-trip: meta.json wire format stays parseable
# ---------------------------------------------------------------------------


def test_meta_json_roundtrip(project_root: Path) -> None:
    """Make sure the dataclass → JSON → dataclass round-trip preserves shape.
    This is what protects against schema drift across versions."""
    target = project_root / ".workflow" / "DESIGN.md"
    target.write_text("# X")
    record_artifact(project_root, ".workflow/DESIGN.md", produced_by="t")
    set_phase(project_root, Phase.DESIGN_EXTRACTED)
    append_history(project_root, skill="t", outputs=["DESIGN.md"], phase_after=Phase.DESIGN_EXTRACTED)

    raw = json.loads((project_root / ".workflow" / "meta.json").read_text())
    # Must contain all top-level fields.
    for key in {"project_slug", "project_name", "created_at", "updated_at",
                "phase", "stack", "artifacts", "history"}:
        assert key in raw, f"missing key {key}"

    # Reload via our parser.
    meta = load_meta(project_root)
    assert meta.phase == Phase.DESIGN_EXTRACTED.value
    assert ".workflow/DESIGN.md" in meta.artifacts
    assert len(meta.history) == 1


# ---------------------------------------------------------------------------
# The enum above is a COPY of something that lives elsewhere. This is the test
# that notices when the original moves.
#
# `Phase` says "Must match contracts.md" in a comment, and for four phases it
# did not: monorepo_initialized, feature_complete and deployed were never added,
# and module_added still carried its historical hyphen. Nothing caught it,
# because this package's workflow only watched contract-package/** — so a change
# to the canonical contract never re-ran these tests.
# ---------------------------------------------------------------------------

CANONICAL_CONTRACT = (
    pathlib.Path(__file__).resolve().parents[2] / "dev-flow" / "references" / "contracts.md"
)


def _canonical_phases() -> list[str]:
    """The phase enum, read out of the canonical contract's own table."""
    text = CANONICAL_CONTRACT.read_text()
    section = re.search(
        r"### `phase` enum \(canonical\)(.+?)(?=\n### )", text, re.S
    )
    assert section, "contracts.md has no '### `phase` enum (canonical)' section"
    # One phase per table row, in order, first backticked cell of each row.
    rows = re.findall(r"^\| *`([a-z_]+)`", section.group(1), re.M)
    return [r for r in rows if r != "phase"]


@pytest.mark.skipif(
    not CANONICAL_CONTRACT.exists(),
    reason="canonical contract not present (package installed standalone)",
)
def test_phase_enum_matches_canonical_contract() -> None:
    canonical = _canonical_phases()
    ours = [p.value for p in Phase.order()]
    assert ours == canonical, (
        "Phase.order() has drifted from dev-flow/references/contracts.md.\n"
        f"  contract: {canonical}\n"
        f"  package : {ours}\n"
        "Update the enum (and its order — phase is monotonic), not the contract."
    )


def test_legacy_hyphen_still_parses() -> None:
    """Projects written before the rename must keep loading."""
    assert Phase("module-added") is Phase.MODULE_ADDED
    assert Phase.MODULE_ADDED.value == "module_added"
