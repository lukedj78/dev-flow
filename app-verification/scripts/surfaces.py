#!/usr/bin/env python3
"""surfaces.py — what a project is made of, detected in one place.

    python3 surfaces.py <project-root> [--json]

A surface is a part of the project a person (or a client) can start and use: a web app, a mobile app, an agent, an
HTTP service, a command-line tool, or anything else in `apps/*` / `packages/*` with a `dev` or `start` script.
Shared packages with nothing to start (types, config, a component library) are not surfaces.

This is the one answer to "what is this project made of?". It used to have three: app-security's own Next/Expo
detection, show_state's framework switch, and app-verification's `--app` flag — and one of them missed Expo
configured by `app.config.ts`. The canonical copy lives in `dev-flow/scripts/`; skills that install standalone carry
a byte copy, and `scripts/lint_skills.py` (VENDORED_SOURCE) fails on drift — edit this one and copy it across.

Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

KINDS = ("web", "mobile", "agent", "api", "cli", "other")


@dataclass
class Surface:
    kind: str           # one of KINDS
    name: str           # the manual's suffix: web / mobile / agent for a single app, the directory name in apps/*
    path: str           # relative to the project root, "." for the root
    mounted_in: str | None = None   # the surface that serves this one (an eve agent mounted by withEve() in Next)


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def package(base: Path) -> dict:
    try:
        data = json.loads(_read(base / "package.json") or "{}")
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def dependencies(base: Path) -> set[str]:
    pkg = package(base)
    return set(pkg.get("dependencies") or {}) | set(pkg.get("devDependencies") or {})


def is_expo(base: Path) -> bool:
    """Expo Router has an app/ directory too: expo without next in package.json, app.config.*, or app.json."""
    deps = dependencies(base)
    if "next" in deps:
        return False
    return ("expo" in deps or any(base.glob("app.config.*"))
            or ((base / "app.json").is_file() and '"expo"' in _read(base / "app.json")))


def is_next(base: Path) -> bool:
    """A Next.js app in this directory (not anywhere below it)."""
    return "next" in dependencies(base) and not is_expo(base)


def is_eve(base: Path) -> bool:
    return (base / "agent" / "agent.ts").is_file() or (base / "agent" / "agent.js").is_file()


def source_roots(root: Path) -> list[Path]:
    """The project root, plus every app and package directory of a monorepo."""
    out = [root]
    for group in ("apps", "packages"):
        if (root / group).is_dir():
            out += sorted(p for p in (root / group).iterdir() if p.is_dir() and not p.name.startswith("."))
    return out


def _services(meta: dict | None) -> dict[str, dict]:
    stack = (meta or {}).get("stack") or {}
    services = ((stack.get("monorepo") or {}).get("services")) or []
    return {str(s.get("path", "")).strip("/"): s for s in services if isinstance(s, dict) and s.get("path")}


def _mounts_eve(base: Path) -> bool:
    return any(re.search(r"\bwithEve\s*\(", _read(p)) for p in base.glob("next.config.*"))


def _one(base: Path, rel: str, services: dict[str, dict]) -> list[Surface]:
    """The surfaces one directory provides: usually one, two when a Next app serves an eve agent. A single app at
    the root is named after its kind (verify-web); an app in apps/* after its directory (verify-admin)."""
    root = rel == "."
    named = lambda kind: kind if root else base.name   # noqa: E731
    if rel in services:
        return [Surface("api", named("api"), rel)]
    if is_expo(base):
        return [Surface("mobile", named("mobile"), rel)]
    if is_next(base):
        web = Surface("web", named("web"), rel)
        if not is_eve(base):
            return [web]
        agent = Surface("agent", "agent" if root else f"{base.name}-agent", "agent" if root else f"{rel}/agent",
                        mounted_in=web.name if _mounts_eve(base) else None)
        return [web, agent]
    if is_eve(base):
        return [Surface("agent", named("agent"), rel)]
    pkg = package(base)
    if pkg.get("bin"):
        return [Surface("cli", named("cli"), rel)]
    scripts = pkg.get("scripts") or {}
    if not root and ("dev" in scripts or "start" in scripts):
        return [Surface("other", base.name, rel)]
    return []


def surfaces(root: Path, meta: dict | None = None) -> list[Surface]:
    """Every surface of the project, sorted by path. `meta` is `.workflow/meta.json` (read from disk when None)."""
    root = root.resolve()
    if meta is None:
        try:
            meta = json.loads(_read(root / ".workflow" / "meta.json") or "{}")
        except ValueError:
            meta = {}
    services = _services(meta)
    out = [s for base in source_roots(root)
           for s in _one(base, "." if base == root else base.relative_to(root).as_posix(), services)]
    return sorted(out, key=lambda s: s.path)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("project_root", type=Path)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    found = surfaces(a.project_root)
    if a.json:
        print(json.dumps([asdict(s) for s in found], indent=2))
    else:
        for s in found:
            print(f"{s.kind:6} {s.name:16} {s.path}" + (f"  (served by {s.mounted_in})" if s.mounted_in else ""))
        if not found:
            print("no surface found — nothing in this project can be started")
    return 0


if __name__ == "__main__":
    sys.exit(main())
