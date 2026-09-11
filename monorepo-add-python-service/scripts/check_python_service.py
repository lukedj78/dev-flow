#!/usr/bin/env python3
"""check_python_service.py — signals about a scaffolded Python service, never a verdict.

Every line it prints is an observation with its source. It does not decide whether the
service is "ready": a reader has to look at the signals and the code. That is the repo's
rule for scripts, and it is not ceremony — a script that prints PASS is a script people
stop reading.

Usage:
  check_python_service.py <project-root> [--name ml]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

OK, MISS, INFO = "·", "!", " "


def signal(mark: str, text: str) -> None:
    print(f"  {mark} {text}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("project_root", type=Path)
    ap.add_argument("--name", default="ml")
    args = ap.parse_args()

    root: Path = args.project_root.resolve()
    name: str = args.name
    module = name.replace("-", "_")
    app = root / "apps" / name

    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2

    print(f"signals for apps/{name} in {root}")

    # --- toolchain ---------------------------------------------------------
    uv = shutil.which("uv")
    if uv:
        try:
            version = subprocess.run([uv, "--version"], capture_output=True, text=True,
                                     timeout=20).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            version = "(present, version unreadable)"
        signal(OK, f"uv: {version}  [{uv}]")
    else:
        signal(MISS, "uv: not on PATH — curl -LsSf https://astral.sh/uv/install.sh | sh")

    # --- the app -----------------------------------------------------------
    if not app.is_dir():
        signal(MISS, f"apps/{name}/ does not exist — the scaffold has not run")
        return 0

    pinned = app / ".python-version"
    if pinned.is_file():
        signal(OK, f"python pinned: {pinned.read_text(encoding='utf-8').strip()}")
    else:
        signal(MISS, ".python-version missing — `uv run` will resolve whatever it finds")

    pkg = app / "package.json"
    if pkg.is_file():
        try:
            scripts = json.loads(pkg.read_text(encoding="utf-8")).get("scripts", {})
        except json.JSONDecodeError:
            scripts = {}
            signal(MISS, "package.json is not valid JSON")
        present = [s for s in ("dev", "test", "lint", "typecheck", "build", "openapi")
                   if s in scripts]
        missing = [s for s in ("dev", "test", "lint", "typecheck", "build", "openapi")
                   if s not in scripts]
        signal(OK, f"bridge scripts: {', '.join(present) or 'none'}")
        if missing:
            signal(MISS, f"bridge scripts absent: {', '.join(missing)} — turbo cannot run them")
    else:
        signal(MISS, "package.json missing — pnpm does not see this directory as a member")

    lock = app / "uv.lock"
    signal(OK if lock.is_file() else MISS,
           "uv.lock present" if lock.is_file()
           else "uv.lock missing — run `uv lock`; `uv sync --locked` and the Dockerfile need it")

    # --- workspace + task graph -------------------------------------------
    ws = root / "pnpm-workspace.yaml"
    if ws.is_file():
        globbed = bool(re.search(r"^\s*-\s*['\"]?apps/\*", ws.read_text(encoding="utf-8"), re.M))
        signal(OK if globbed else MISS,
               "pnpm-workspace.yaml globs apps/*" if globbed
               else "pnpm-workspace.yaml does NOT glob apps/* — the service is invisible to pnpm")
    else:
        signal(MISS, "no pnpm-workspace.yaml at the root")

    turbo = root / "turbo.json"
    if turbo.is_file():
        try:
            tasks = json.loads(turbo.read_text(encoding="utf-8")).get("tasks", {})
        except json.JSONDecodeError:
            tasks = {}
            signal(MISS, "turbo.json is not valid JSON")
        if "openapi" in tasks:
            task = tasks["openapi"]
            inputs = task.get("inputs") or []
            signal(OK, "turbo task `openapi` registered")
            if inputs and "$TURBO_DEFAULT$" not in inputs:
                signal(MISS, "`openapi.inputs` omits $TURBO_DEFAULT$ — turbo then ignores "
                             ".gitignore and hashes __pycache__/.venv, so the cache never hits "
                             "again (turborepo.dev/docs/reference/configuration#inputs)")
        else:
            signal(MISS, "turbo task `openapi` not registered in turbo.json")
        dev = tasks.get("dev", {})
        if dev.get("persistent") is not True:
            signal(MISS, "turbo task `dev` is not persistent — a long-running server should be")
    else:
        signal(MISS, "no turbo.json at the root")

    # --- the generated client ---------------------------------------------
    schema = app / "openapi.json"
    client_dir = root / "packages" / "api" / "src" / name
    generated = client_dir / "schema.d.ts"
    if not schema.is_file():
        signal(MISS, "openapi.json not exported yet — run the `openapi` script")
    elif not generated.is_file():
        signal(MISS, f"client not generated — {generated.relative_to(root)} is absent")
    else:
        s_mtime, g_mtime = schema.stat().st_mtime, generated.stat().st_mtime
        if g_mtime >= s_mtime:
            signal(OK, "client is at least as new as the schema")
        else:
            delta = int(s_mtime - g_mtime)
            signal(MISS, f"client is {delta}s OLDER than openapi.json — it was generated from "
                         "an earlier schema; apps/web may be compiling against a stale contract")

    api_pkg = root / "packages" / "api" / "package.json"
    if api_pkg.is_file():
        try:
            data = json.loads(api_pkg.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
        deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
        slug_edge = [k for k in deps if k.endswith(f"/{name}")]
        signal(OK if slug_edge else MISS,
               f"packages/api depends on {slug_edge[0]} (the ordering edge)" if slug_edge
               else f"packages/api has no workspace dependency on the service — without it "
                    f"turbo has no reason to export the schema before generating the client")

    # --- how apps/web reaches it ------------------------------------------
    env_name = f"{name.upper().replace('-', '_')}_SERVICE_URL"
    web = root / "apps" / "web"
    if web.is_dir():
        hits = []
        for path in web.rglob("*.ts*"):
            if any(part in {"node_modules", ".next"} for part in path.parts):
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if re.search(r"fetch\(\s*[\"'`]https?://[^\"'`]*:%s" % re.escape(str(8000)), text):
                hits.append(path.relative_to(root))
        if hits:
            signal(MISS, "hand-written fetch to a localhost service port in: "
                         + ", ".join(str(h) for h in hits[:3])
                         + " — that call bypasses the typed client and its compile-time gate")
        signal(INFO, f"apps/web should read the base URL from {env_name} (server-side, "
                     f"not NEXT_PUBLIC_)")

    print("\nThese are signals, not a verdict. Run the service and the tests before trusting any of them:")
    print(f"  pnpm turbo dev --filter '*/{name}'   # then curl localhost:<port>/health")
    print(f"  pnpm turbo test lint --filter '*/{name}'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
