#!/usr/bin/env python3
"""Mutate `.workflow/meta.json` from the command line.

Three operations:

  1. record-artifact — hash a file on disk and store it in meta.json#artifacts.
     Skills call this after writing/updating any file that's part of the
     contract (DESIGN.md, registry.json, generated pages, schema, etc).
     This is the foundation of the drift-detection model: an artifact
     entry says "skill X wrote this file with this exact content at time T".
     If the on-disk hash drifts later, that artifact is "stale".

  2. set-phase — bump `phase` (only if monotonic forward) and `updated_at`.

  3. append-history — record a skill run with inputs, outputs, phase delta.

Usage:
    # Record an artifact
    python3 update_meta.py <project-root> record-artifact \
        --path .workflow/DESIGN.md \
        --produced-by image-to-design-md
    python3 update_meta.py <project-root> record-artifact \
        --path registry.json \
        --produced-by design-md-to-app \
        --derived-from .workflow/DESIGN.md

    # Set phase
    python3 update_meta.py <project-root> set-phase scaffolded

    # Append history
    python3 update_meta.py <project-root> append-history \
        --skill design-md-to-app \
        --inputs '{"design_md": ".workflow/DESIGN.md"}' \
        --outputs '["registry.json", "app/showcase/page.tsx"]' \
        --phase-after scaffolded
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Phase enum — must stay in sync with .workflow/contracts.md.
# Index = monotonic position. Skills MAY set a phase >= current; never <.
PHASES = [
    "empty",
    "idea_captured",
    "prd_drafted",
    "tasks_split",
    "design_extracted",
    # Monorepo-only mid-bootstrap checkpoint (turborepo root before apps are scaffolded)
    "monorepo_initialized",
    "scaffolded",
    "page_generated",
    "module_added",
    # Cross-stack terminal progression beyond module_added (web / mobile / agent / monorepo)
    "feature_complete",
    "deployed",
]

# Backwards-compatibility: accept the old kebab-case spelling. set-phase
# will normalize "module-added" to "module_added" on write.
PHASE_ALIASES = {
    "module-added": "module_added",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    """Stream the file through SHA-256. Works for any size."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_meta(root: Path) -> tuple[Path, dict[str, Any]]:
    meta_path = root / ".workflow" / "meta.json"
    if not meta_path.exists():
        sys.stderr.write(f"No .workflow/meta.json at {root}\n")
        sys.stderr.write("Run init_workflow.py first.\n")
        sys.exit(1)
    return meta_path, json.loads(meta_path.read_text())


def save_meta(meta_path: Path, meta: dict[str, Any]) -> None:
    meta["updated_at"] = now_iso()
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Operation: record-artifact
# ---------------------------------------------------------------------------


def cmd_record_artifact(args: argparse.Namespace) -> int:
    """Hash a file and record it under meta.json#artifacts.

    The artifact path is stored relative to the project root so the meta is
    portable. Hash is computed from the absolute path on disk.

    If the artifact already exists at the same path, its entry is replaced
    (this is the "I just rewrote this file, take a fresh hash" case).
    """
    root = args.project_root.resolve()
    meta_path, meta = load_meta(root)

    target_abs = (root / args.path).resolve()
    if not target_abs.exists():
        sys.stderr.write(f"Cannot record artifact — file does not exist: {target_abs}\n")
        return 1

    rel_path = str(target_abs.relative_to(root))
    sha = sha256_file(target_abs)

    artifacts = meta.setdefault("artifacts", {})
    entry: dict[str, Any] = {
        "sha256": sha,
        "produced_by": args.produced_by,
        "produced_at": now_iso(),
    }
    if args.derived_from:
        # Each input is a path relative to project root. We snapshot which
        # version we derived from by recording its current hash too — that's
        # how we'll later detect that an upstream changed and we're stale.
        deps = []
        for dep_path in args.derived_from:
            dep_abs = (root / dep_path).resolve()
            if not dep_abs.exists():
                sys.stderr.write(f"Cannot derive from missing file: {dep_abs}\n")
                return 1
            deps.append({
                "path": str(dep_abs.relative_to(root)),
                "sha256": sha256_file(dep_abs),
            })
        entry["derived_from"] = deps

    artifacts[rel_path] = entry
    save_meta(meta_path, meta)
    print(f"recorded artifact: {rel_path}  sha256={sha[:12]}…  by={args.produced_by}")
    if args.derived_from:
        print(f"  derived from: {', '.join(d['path'] for d in entry['derived_from'])}")
    return 0


# ---------------------------------------------------------------------------
# Operation: set-phase
# ---------------------------------------------------------------------------


def cmd_set_phase(args: argparse.Namespace) -> int:
    root = args.project_root.resolve()
    meta_path, meta = load_meta(root)

    # Normalize aliases (e.g. legacy kebab "module-added" → "module_added")
    requested = PHASE_ALIASES.get(args.phase, args.phase)

    if requested not in PHASES:
        sys.stderr.write(f"Unknown phase: {args.phase!r}\n")
        sys.stderr.write(f"Valid phases: {', '.join(PHASES)}\n")
        return 1

    current_raw = meta.get("phase", "empty")
    current = PHASE_ALIASES.get(current_raw, current_raw)
    cur_idx = PHASES.index(current) if current in PHASES else -1
    new_idx = PHASES.index(requested)

    if new_idx < cur_idx and not args.allow_regress:
        sys.stderr.write(
            f"Phase regression refused: current={current!r} → requested={requested!r}\n"
            f"Use --allow-regress only if you know what you're doing (e.g., manual reset).\n"
        )
        return 1

    meta["phase"] = requested
    save_meta(meta_path, meta)
    print(f"phase: {current_raw} → {requested}")
    return 0


# ---------------------------------------------------------------------------
# Operation: append-history
# ---------------------------------------------------------------------------


def cmd_append_history(args: argparse.Namespace) -> int:
    root = args.project_root.resolve()
    meta_path, meta = load_meta(root)

    try:
        inputs = json.loads(args.inputs) if args.inputs else {}
        outputs = json.loads(args.outputs) if args.outputs else []
    except json.JSONDecodeError as e:
        sys.stderr.write(f"--inputs / --outputs must be valid JSON: {e}\n")
        return 1

    # `set-phase` rejects an unknown phase; this used to accept one, write it into
    # history, and then silently skip the bump — so a caller that mistyped got a
    # success line, a history entry naming a phase that does not exist, and a
    # project still sitting on the previous one. Found the first time a new project
    # was taken through the whole flow: `tasks_ready` for `tasks_split`.
    phase_after = None
    if args.phase_after:
        phase_after = PHASE_ALIASES.get(args.phase_after, args.phase_after)
        if phase_after not in PHASES:
            sys.stderr.write(f"Unknown phase: {args.phase_after}\n")
            sys.stderr.write(f"Valid phases: {', '.join(PHASES)}\n")
            return 2

    history = meta.setdefault("history", [])
    history.append({
        "skill": args.skill,
        "ran_at": now_iso(),
        "inputs": inputs,
        "outputs": outputs,
        "phase_before": meta.get("phase"),
        "phase_after": phase_after,
    })

    if phase_after:
        cur_raw = meta.get("phase", "empty")
        cur = PHASE_ALIASES.get(cur_raw, cur_raw)
        cur_idx = PHASES.index(cur) if cur in PHASES else -1
        new_idx = PHASES.index(phase_after)
        if new_idx >= cur_idx:
            meta["phase"] = phase_after

    save_meta(meta_path, meta)
    print(f"history += {{ skill: {args.skill}, phase_after: {args.phase_after} }}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("project_root", type=Path)
    sub = ap.add_subparsers(dest="op", required=True)

    p_art = sub.add_parser("record-artifact", help="Hash a file and store under meta#artifacts")
    p_art.add_argument("--path", required=True, help="Path to the artifact, relative to project root")
    p_art.add_argument("--produced-by", required=True, help="Skill name that wrote this artifact")
    p_art.add_argument(
        "--derived-from",
        nargs="*",
        default=[],
        help="Paths (relative to project root) of inputs this artifact was derived from",
    )
    p_art.set_defaults(func=cmd_record_artifact)

    p_ph = sub.add_parser("set-phase", help="Bump meta#phase (forward-only by default)")
    p_ph.add_argument("phase")
    p_ph.add_argument("--allow-regress", action="store_true")
    p_ph.set_defaults(func=cmd_set_phase)

    p_h = sub.add_parser("append-history", help="Append a skill run to meta#history")
    p_h.add_argument("--skill", required=True)
    p_h.add_argument("--inputs", default="{}", help="JSON object string")
    p_h.add_argument("--outputs", default="[]", help="JSON array string")
    p_h.add_argument("--phase-after", default=None)
    p_h.set_defaults(func=cmd_append_history)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
