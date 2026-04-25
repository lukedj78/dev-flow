#!/usr/bin/env python3
"""Initialize a `.workflow/` directory in a project root.

Creates the folder if missing and writes a minimal `meta.json` consistent
with the dev-flow contract. Idempotent: if `meta.json` already exists,
prints its current phase and exits without overwriting.

Usage:
    python3 init_workflow.py <project-root> [--name "Project Name"]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


def slugify(name: str) -> str:
    s = re.sub(r'[^a-zA-Z0-9]+', '-', name).strip('-').lower()
    return s or 'project'


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('project_root', type=Path)
    ap.add_argument('--name', default=None, help='Human-readable project name (defaults to dir name)')
    args = ap.parse_args()

    root = args.project_root.resolve()
    if not root.exists():
        sys.stderr.write(f"Project root does not exist: {root}\n")
        sys.stderr.write("Create it first (mkdir -p) — init_workflow.py does not create the project root itself.\n")
        return 1

    workflow = root / '.workflow'
    workflow.mkdir(exist_ok=True)
    meta_path = workflow / 'meta.json'

    if meta_path.exists():
        meta = json.loads(meta_path.read_text())
        print(f"meta.json already exists. phase={meta.get('phase')!r}, name={meta.get('project_name')!r}")
        return 0

    name = args.name or root.name
    now = datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
    meta = {
        "project_slug": slugify(name),
        "project_name": name,
        "created_at": now,
        "updated_at": now,
        "phase": "empty",
        "stack": {
            "framework": None, "ui": None, "auth": None, "db": None,
            "payments": None, "deploy": None,
        },
        "history": [],
    }
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n")
    print(f"Initialized {meta_path} (phase=empty, slug={meta['project_slug']!r})")
    return 0


if __name__ == '__main__':
    sys.exit(main())
