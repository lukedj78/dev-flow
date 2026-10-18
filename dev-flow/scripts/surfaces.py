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


ROUTE_DIRS = ("app", "src/app", "pages", "src/pages")


def is_next(base: Path) -> bool:
    """A Next.js app in this directory: a route directory, and next declared (or a next.config, or no package.json
    at all). `next` alone is not enough — a shared UI package lists it for its types (final review, 2026-10-18)."""
    if is_expo(base) or not any((base / d).is_dir() for d in ROUTE_DIRS):
        return False
    return "next" in dependencies(base) or any(base.glob("next.config.*")) or not (base / "package.json").is_file()


def is_eve(base: Path) -> bool:
    return (base / "agent" / "agent.ts").is_file() or (base / "agent" / "agent.js").is_file()


def _workspace_globs(root: Path) -> list[str]:
    """The workspace globs the project declares: pnpm-workspace.yaml `packages:`, package.json `workspaces`."""
    globs: list[str] = []
    in_packages = False
    for line in _read(root / "pnpm-workspace.yaml").splitlines():
        if re.match(r"^packages\s*:", line):
            in_packages = True
            continue
        if in_packages:
            m = re.match(r"^\s+-\s*['\"]?([^'\"#]+?)['\"]?\s*(#.*)?$", line)
            if m:
                globs.append(m.group(1).strip())
            elif line.strip() and not line.startswith((" ", "\t")):
                in_packages = False
    ws = package(root).get("workspaces")
    globs += ws if isinstance(ws, list) else list((ws or {}).get("packages") or []) if isinstance(ws, dict) else []
    return [g for g in globs if isinstance(g, str) and not g.startswith("!")]


def source_roots(root: Path) -> list[Path]:
    """The project root, plus every workspace directory: the declared workspace globs, and apps/* and packages/*."""
    found: set[Path] = set()
    for g in _workspace_globs(root) + ["apps/*", "packages/*"]:
        for p in root.glob(g.rstrip("/")):
            if p.is_dir() and not p.name.startswith(".") and "node_modules" not in p.parts and p != root:
                found.add(p)
    return [root] + sorted(found)


def _services(meta: dict | None) -> dict[str, dict]:
    stack = (meta or {}).get("stack") or {}
    services = ((stack.get("monorepo") or {}).get("services")) or []
    return {str(s.get("path", "")).strip("/"): s for s in services if isinstance(s, dict) and s.get("path")}


def _mounts_eve(base: Path) -> bool:
    return any(re.search(r"\bwithEve\s*\(", _read(p)) for p in base.glob("next.config.*"))


def _one(base: Path, rel: str, services: dict[str, dict], opted: set[str] = frozenset()) -> list[Surface]:
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
    # a shared package (packages/*) is a library — its `dev` is `tsc -w`, its `bin` a migration — unless the project
    # opts it in (stack_config.verification_surfaces); an app, or the root, is something to run
    if rel.startswith("packages/") and rel not in opted:
        return []
    pkg = package(base)
    if pkg.get("bin"):
        return [Surface("cli", named("cli"), rel)]
    scripts = pkg.get("scripts") or {}
    if not root and ("start" in scripts or "dev" in scripts):
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
    opted = {str(x).strip("/") for x in (((meta or {}).get("stack_config") or {}).get("verification_surfaces") or [])}
    out = [s for base in source_roots(root)
           for s in _one(base, "." if base == root else base.relative_to(root).as_posix(), services, opted)]
    seen: dict[str, int] = {}
    for s in sorted(out, key=lambda s: s.path):   # two surfaces never share a manual: the second takes its path's name
        if s.name in seen:
            s.name = s.path.replace("/", "-")
        seen[s.name] = 1
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
