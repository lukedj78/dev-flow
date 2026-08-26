"""Core types + functions for the dev-flow filesystem contract.

This is the load-bearing module. The CLI scripts in `dev-flow/scripts/`
delegate to these primitives so there's a single source of truth for the
contract semantics.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Phase enum — canonical, monotonic. Must match contracts.md.
# ---------------------------------------------------------------------------


class Phase(str, Enum):
    """The dev-flow phase enum.

    `phase` is monotonic: a skill should never set it to an earlier value.
    Re-running a skill on a project that's already further along appends to
    `history` but keeps the phase ≥ current.
    """

    EMPTY = "empty"
    IDEA_CAPTURED = "idea_captured"
    PRD_DRAFTED = "prd_drafted"
    TASKS_SPLIT = "tasks_split"
    DESIGN_EXTRACTED = "design_extracted"
    MONOREPO_INITIALIZED = "monorepo_initialized"
    SCAFFOLDED = "scaffolded"
    PAGE_GENERATED = "page_generated"
    MODULE_ADDED = "module_added"
    FEATURE_COMPLETE = "feature_complete"
    DEPLOYED = "deployed"

    @classmethod
    def _missing_(cls, value: object) -> "Phase | None":
        """Accept the legacy hyphenated spelling of `module_added`.

        Projects scaffolded before the enum was normalised carry
        `"module-added"` in their meta.json. `update_meta.py` rewrites it on
        the next write; until then it must still parse, or a working project
        stops loading because of a dash.
        """
        if value == "module-added":
            return cls.MODULE_ADDED
        return None

    @classmethod
    def order(cls) -> list["Phase"]:
        return [
            cls.EMPTY,
            cls.IDEA_CAPTURED,
            cls.PRD_DRAFTED,
            cls.TASKS_SPLIT,
            cls.DESIGN_EXTRACTED,
            cls.MONOREPO_INITIALIZED,
            cls.SCAFFOLDED,
            cls.PAGE_GENERATED,
            cls.MODULE_ADDED,
            cls.FEATURE_COMPLETE,
            cls.DEPLOYED,
        ]

    def index(self) -> int:
        return self.order().index(self)


# ---------------------------------------------------------------------------
# Dataclasses for the meta.json shape
# ---------------------------------------------------------------------------


@dataclass
class Stack:
    """Stack choices recorded by skills as the user picks them.

    Use `None` for undecided keys (not the string "none"). Skills downstream
    check `if stack.framework is None: ask user`.
    """
    framework: str | None = None
    ui: str | None = None
    auth: str | None = None
    db: str | None = None
    payments: str | None = None
    email: str | None = None
    test: str | None = None
    ci: str | None = None
    storage: str | None = None
    deploy: str | None = None


@dataclass
class DerivedFrom:
    """One upstream input snapshotted at the time the artifact was produced."""
    path: str
    sha256: str


@dataclass
class Artifact:
    """A file produced by a skill, content-addressed for drift detection."""
    sha256: str
    produced_by: str
    produced_at: str
    derived_from: list[DerivedFrom] = field(default_factory=list)


@dataclass
class HistoryEntry:
    """One skill run."""
    skill: str
    ran_at: str
    inputs: dict[str, Any] = field(default_factory=dict)
    outputs: list[str] = field(default_factory=list)
    phase_before: str | None = None
    phase_after: str | None = None


@dataclass
class Meta:
    """The complete meta.json document."""
    project_slug: str
    project_name: str
    created_at: str
    updated_at: str
    phase: str = Phase.EMPTY.value
    stack: Stack = field(default_factory=Stack)
    artifacts: dict[str, Artifact] = field(default_factory=dict)
    history: list[HistoryEntry] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Drift report types
# ---------------------------------------------------------------------------


@dataclass
class DriftRow:
    """Status for a single artifact."""
    path: str
    produced_by: str
    status: str  # "fresh" | "self-drift" | "upstream-stale" | "missing"
    detail: str = ""


@dataclass
class DriftReport:
    """Full drift report for a workflow."""
    rows: list[DriftRow]

    @property
    def has_drift(self) -> bool:
        return any(r.status != "fresh" for r in self.rows)

    @property
    def fresh_count(self) -> int:
        return sum(1 for r in self.rows if r.status == "fresh")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _slugify(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", name).strip("-").lower()
    return s or "project"


def sha256_file(path: Path) -> str:
    """Stream-hash a file (works for any size)."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _meta_path(root: Path) -> Path:
    return root / ".workflow" / "meta.json"


def _to_dict(meta: Meta) -> dict[str, Any]:
    """Serialize Meta → dict for JSON output (preserving the shape)."""
    d = asdict(meta)
    # asdict turns Stack into a dict and keeps None values — the spec wants
    # null on undecided keys, so leave them.
    # artifacts: dict[str, Artifact] → asdict turns the values into dicts,
    # but the keys (paths) are preserved.
    return d


def _from_dict(d: dict[str, Any]) -> Meta:
    """Parse a dict (from JSON) into Meta. Tolerant of older shapes."""
    stack_d = d.get("stack") or {}
    stack = Stack(
        framework=stack_d.get("framework"),
        ui=stack_d.get("ui"),
        auth=stack_d.get("auth"),
        db=stack_d.get("db"),
        payments=stack_d.get("payments"),
        email=stack_d.get("email"),
        test=stack_d.get("test"),
        ci=stack_d.get("ci"),
        storage=stack_d.get("storage"),
        deploy=stack_d.get("deploy"),
    )

    artifacts: dict[str, Artifact] = {}
    for path, entry in (d.get("artifacts") or {}).items():
        derived = [
            DerivedFrom(path=dep["path"], sha256=dep["sha256"])
            for dep in entry.get("derived_from") or []
        ]
        artifacts[path] = Artifact(
            sha256=entry["sha256"],
            produced_by=entry["produced_by"],
            produced_at=entry["produced_at"],
            derived_from=derived,
        )

    history = [
        HistoryEntry(
            skill=h["skill"],
            ran_at=h["ran_at"],
            inputs=h.get("inputs") or {},
            outputs=h.get("outputs") or [],
            phase_before=h.get("phase_before"),
            phase_after=h.get("phase_after"),
        )
        for h in d.get("history") or []
    ]

    return Meta(
        project_slug=d["project_slug"],
        project_name=d["project_name"],
        created_at=d["created_at"],
        updated_at=d["updated_at"],
        phase=d.get("phase", Phase.EMPTY.value),
        stack=stack,
        artifacts=artifacts,
        history=history,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def init_workflow(root: Path, name: str | None = None) -> Meta:
    """Create `<root>/.workflow/` and seed meta.json. Idempotent: if meta.json
    exists already, return its current contents instead of overwriting."""
    root = Path(root).resolve()
    if not root.exists():
        raise FileNotFoundError(f"Project root does not exist: {root}")

    workflow = root / ".workflow"
    workflow.mkdir(exist_ok=True)
    meta_path = workflow / "meta.json"

    if meta_path.exists():
        return load_meta(root)

    project_name = name or root.name
    now = _now_iso()
    meta = Meta(
        project_slug=_slugify(project_name),
        project_name=project_name,
        created_at=now,
        updated_at=now,
        phase=Phase.EMPTY.value,
    )
    save_meta(root, meta)
    return meta


def load_meta(root: Path) -> Meta:
    """Read meta.json from `<root>/.workflow/`."""
    meta_path = _meta_path(Path(root).resolve())
    if not meta_path.exists():
        raise FileNotFoundError(f"No .workflow/meta.json at {meta_path.parent.parent}")
    return _from_dict(json.loads(meta_path.read_text()))


def save_meta(root: Path, meta: Meta) -> None:
    """Write meta.json — refreshes `updated_at` automatically."""
    meta.updated_at = _now_iso()
    meta_path = _meta_path(Path(root).resolve())
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(json.dumps(_to_dict(meta), indent=2, ensure_ascii=False) + "\n")


def record_artifact(
    root: Path,
    path: str | Path,
    produced_by: str,
    derived_from: list[str | Path] | None = None,
) -> Artifact:
    """Hash a file and register it under meta.json#artifacts.

    `path` is interpreted relative to `root` if relative, absolute if absolute.
    The stored key is always relative-to-root (so meta.json is portable).

    `derived_from` is a list of paths (relative to root) — each is hashed
    NOW so we know which version of the upstream we derived from. When the
    upstream later changes, drift detection picks it up.
    """
    root = Path(root).resolve()
    target_abs = (root / Path(path)).resolve()
    if not target_abs.exists():
        raise FileNotFoundError(f"Cannot record artifact — file does not exist: {target_abs}")

    rel_path = str(target_abs.relative_to(root))
    sha = sha256_file(target_abs)

    deps: list[DerivedFrom] = []
    for dep in derived_from or []:
        dep_abs = (root / Path(dep)).resolve()
        if not dep_abs.exists():
            raise FileNotFoundError(f"Cannot derive from missing file: {dep_abs}")
        deps.append(DerivedFrom(
            path=str(dep_abs.relative_to(root)),
            sha256=sha256_file(dep_abs),
        ))

    artifact = Artifact(
        sha256=sha,
        produced_by=produced_by,
        produced_at=_now_iso(),
        derived_from=deps,
    )

    meta = load_meta(root)
    meta.artifacts[rel_path] = artifact
    save_meta(root, meta)
    return artifact


def set_phase(root: Path, phase: str | Phase, allow_regress: bool = False) -> Meta:
    """Bump phase forward. Refuses regression unless `allow_regress=True`."""
    if isinstance(phase, Phase):
        phase_value = phase.value
    else:
        phase_value = phase
        # Validate the string is a known phase.
        if phase_value not in {p.value for p in Phase}:
            raise ValueError(
                f"Unknown phase: {phase_value!r}. Valid: {[p.value for p in Phase]}"
            )

    root = Path(root).resolve()
    meta = load_meta(root)
    current_value = meta.phase

    try:
        cur_idx = Phase(current_value).index()
    except ValueError:
        cur_idx = -1
    new_idx = Phase(phase_value).index()

    if new_idx < cur_idx and not allow_regress:
        raise ValueError(
            f"Phase regression refused: current={current_value!r} → requested={phase_value!r}. "
            f"Set allow_regress=True if you really mean it."
        )

    meta.phase = phase_value
    save_meta(root, meta)
    return meta


def append_history(
    root: Path,
    skill: str,
    inputs: dict[str, Any] | None = None,
    outputs: list[str] | None = None,
    phase_after: str | Phase | None = None,
) -> Meta:
    """Append a skill run to meta.history. Optionally bumps phase forward."""
    root = Path(root).resolve()
    meta = load_meta(root)
    phase_before = meta.phase

    phase_after_val: str | None = None
    if phase_after is not None:
        phase_after_val = phase_after.value if isinstance(phase_after, Phase) else phase_after

    meta.history.append(HistoryEntry(
        skill=skill,
        ran_at=_now_iso(),
        inputs=inputs or {},
        outputs=outputs or [],
        phase_before=phase_before,
        phase_after=phase_after_val,
    ))

    if phase_after_val and phase_after_val in {p.value for p in Phase}:
        try:
            cur_idx = Phase(phase_before).index() if phase_before else -1
            new_idx = Phase(phase_after_val).index()
            if new_idx >= cur_idx:
                meta.phase = phase_after_val
        except ValueError:
            pass

    save_meta(root, meta)
    return meta


def check_drift(root: Path) -> DriftReport:
    """Build a drift report for all artifacts in meta.json.

    Reports four statuses per artifact:
      - fresh: on-disk hash matches recorded, all upstreams match too.
      - self-drift: the file has been edited since the producing skill
        last hashed it.
      - upstream-stale: file matches its hash but a `derived_from` input
        has drifted (directly or transitively).
      - missing: the file was recorded but no longer exists.

    Drift propagates transitively through `derived_from`: if A→B→C and A
    drifts, B and C both become upstream-stale.
    """
    root = Path(root).resolve()
    meta = load_meta(root)

    rows: dict[str, DriftRow] = {}

    # Pass 1: classify by self-state + immediate upstreams.
    for rel_path, artifact in meta.artifacts.items():
        abs_path = (root / rel_path).resolve()
        row = DriftRow(path=rel_path, produced_by=artifact.produced_by, status="fresh")

        if not abs_path.exists():
            row.status = "missing"
            row.detail = "file no longer exists on disk"
        else:
            on_disk = sha256_file(abs_path)
            if on_disk != artifact.sha256:
                row.status = "self-drift"
                row.detail = f"recorded {artifact.sha256[:8]} vs on-disk {on_disk[:8]}"
            else:
                upstream_issues: list[str] = []
                for dep in artifact.derived_from:
                    dep_abs = (root / dep.path).resolve()
                    if not dep_abs.exists():
                        upstream_issues.append(f"{dep.path} (missing)")
                        continue
                    cur_sha = sha256_file(dep_abs)
                    if cur_sha != dep.sha256:
                        upstream_issues.append(
                            f"{dep.path} ({dep.sha256[:8]} → {cur_sha[:8]})"
                        )
                if upstream_issues:
                    row.status = "upstream-stale"
                    row.detail = "; ".join(upstream_issues)

        rows[rel_path] = row

    # Pass 2: transitive propagation. If an upstream of mine is non-fresh,
    # and I'm currently fresh, mark me upstream-stale too.
    def is_stale(r: DriftRow) -> bool:
        return r.status in {"self-drift", "upstream-stale", "missing"}

    changed = True
    while changed:
        changed = False
        for rel_path, artifact in meta.artifacts.items():
            row = rows[rel_path]
            if is_stale(row):
                continue
            for dep in artifact.derived_from:
                dep_row = rows.get(dep.path)
                if dep_row and is_stale(dep_row):
                    row.status = "upstream-stale"
                    row.detail = f"transitively via {dep.path} ({dep_row.status})"
                    changed = True
                    break

    return DriftReport(rows=list(rows.values()))
