#!/usr/bin/env python3
"""check_eve_state.py — report the state of the eve agent in a project.

Usage:
    python scripts/check_eve_state.py <project-root>

Finds the agent in any of the layouts SKILL.md describes — `apps/agent/agent` (B), `apps/web/agent`
(A inside a monorepo), `agent/` at the root (A or C) — and prints what capabilities exist, the
capability packages in `capabilities/*` with their mounts, whether the scaffold defences are in place
(`defaultTools: false`, the eve version pin), the tracked `stack.agent` value from
.workflow/meta.json (if present), and a proposed next step.
Pure standard library; no dependencies.
"""
import json
import re
import sys
from pathlib import Path

# Where the agent's `agent/` folder can live, in the order SKILL.md lists the layouts.
CANDIDATES = (
    ("apps/agent", "B — monorepo, apps/agent"),
    ("apps/web", "A in apps/web — monorepo, agent inside the web app"),
    (".", "A or C — agent/ at the repo root"),
)


def _list_files(directory: Path, suffix: str = "") -> list[str]:
    if not directory.is_dir():
        return []
    out = []
    for p in sorted(directory.iterdir()):
        if p.name.startswith("."):
            continue
        if p.is_file() and (suffix == "" or p.name.endswith(suffix)):
            out.append(p.stem if suffix else p.name)
        elif p.is_dir():
            out.append(p.name + "/")
    return out


def find_agent_app(root: Path) -> tuple[Path | None, str]:
    for rel, label in CANDIDATES:
        app = (root / rel).resolve()
        if (app / "agent" / "agent.ts").is_file() or (app / "agent" / "instructions.md").is_file():
            return app, label
    return None, ""


def installed_eve_version(app: Path, root: Path) -> str | None:
    for base in (app, root):
        pkg = base / "node_modules" / "eve" / "package.json"
        if pkg.is_file():
            try:
                return json.loads(pkg.read_text(encoding="utf-8")).get("version")
            except (json.JSONDecodeError, OSError):
                return None
    return None


def capability_packages(root: Path) -> list[str]:
    caps = root / "capabilities"
    if not caps.is_dir():
        return []
    return sorted(p.name for p in caps.iterdir() if p.is_dir() and (p / "package.json").is_file())


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python scripts/check_eve_state.py <project-root>")
        return 2

    root = Path(sys.argv[1]).expanduser().resolve()
    if not root.is_dir():
        print(f"error: not a directory: {root}")
        return 2

    meta_path = root / ".workflow" / "meta.json"
    meta: dict = {}
    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            print(f"warning: could not read meta.json: {exc}")
    stack = meta.get("stack") or {}
    stack_config = meta.get("stack_config") or {}
    tracked_agent = stack.get("agent")
    pinned_eve = stack_config.get("eve_version")
    cap_mode = stack_config.get("agent_capabilities")

    app, layout = find_agent_app(root)
    agent_dir = app / "agent" if app else None

    print("=" * 64)
    print(f"project root : {root}")
    print(f".workflow    : {'present' if meta_path.is_file() else 'absent (not a dev-flow project)'}")
    print(f"stack.agent  : {tracked_agent or '(unset)'}")
    where = (str(app.relative_to(root)) if app != root else ".") if app else ""
    print("agent        : " + (f"scaffolded in {where}/agent  [{layout}]" if app else "NOT scaffolded"))
    print("=" * 64)

    if not app:
        print("MODE: scaffold — set the agent up once (layout: SKILL.md, 'Which layout?').")
        print("Next: read node_modules/eve/docs/ and follow references/eve-scaffold.md.")
        if stack.get("framework") == "monorepo" and not (root / "turbo.json").is_file():
            print("NOTE: no turbo.json found — bootstrap the monorepo before scaffolding.")
        return 0

    evals_dir = app / "evals"  # SIBLING of agent/, not inside it
    agent_ts = agent_dir / "agent.ts"
    agent_src = agent_ts.read_text(encoding="utf-8") if agent_ts.is_file() else ""
    print(f"agent.ts     : {'present' if agent_src else 'MISSING'}")
    print(f"instructions : {'present' if (agent_dir / 'instructions.md').is_file() or (agent_dir / 'instructions').is_dir() else 'MISSING'}")
    for name, sub, suffix in (("tools", "tools", ".ts"), ("skills", "skills", ""), ("channels", "channels", ""),
                              ("connections", "connections", ""), ("schedules", "schedules", ""),
                              ("subagents", "subagents", ""), ("hooks", "hooks", ""), ("extensions", "extensions", ".ts")):
        print(f"{name:<13}: {', '.join(_list_files(agent_dir / sub, suffix)) or '(none)'}")
    evals = sorted(p.name for p in evals_dir.rglob("*.eval.ts")) if evals_dir.is_dir() else []
    note = "" if (evals_dir / "evals.config.ts").is_file() else "  (no evals.config.ts)"
    print(f"evals        : {', '.join(evals) or '(none)'}{note}")

    # Scaffold defences (SKILL.md, Scaffold mode).
    warnings = []
    if agent_src and not re.search(r"defaultTools\s*:\s*false", agent_src):
        warnings.append("agent.ts has no `defaultTools: false` — bash, file and web tools reach the model (Scaffold step 4).")
    installed = installed_eve_version(app, root)
    print(f"eve          : installed {installed or '(not installed)'} · pinned {pinned_eve or '(stack_config.eve_version unset)'}")
    if installed and pinned_eve and installed != pinned_eve:
        warnings.append(f"installed eve {installed} differs from stack_config.eve_version {pinned_eve} — fix the pin first.")
    if tracked_agent == "eve" and not pinned_eve:
        warnings.append("stack_config.eve_version is unset — record the exact version (Scaffold step 12).")
    if layout.startswith("A") and (app / "next.config.ts").is_file():
        cfg = (app / "next.config.ts").read_text(encoding="utf-8")
        if "withEve" in cfg and ".well-known/workflow" not in cfg:
            warnings.append("next.config.ts uses withEve but does not forward /.well-known/workflow/* "
                            "(eve-web-integration.md §Workflow callbacks).")

    # Capability packages (references/capability-package.md).
    caps = capability_packages(root)
    mounts = {m for m in _list_files(agent_dir / "extensions", ".ts")}
    if caps or cap_mode == "packages":
        print("-" * 64)
        print(f"capabilities : {', '.join(caps) or '(none)'}  (stack_config.agent_capabilities = {cap_mode or 'unset'})")
        for cap in caps:
            mount = cap.replace("-", "_")
            if mount not in mounts:
                warnings.append(f"capability package `{cap}` has no mount agent/extensions/{mount}.ts")
        for m in sorted(mounts):
            src = (agent_dir / "extensions" / f"{m}.ts").read_text(encoding="utf-8")
            if "capability-" in src and m.replace("_", "-") not in caps:
                warnings.append(f"mount `{m}.ts` points at a capability package that is not in capabilities/")

    print("-" * 64)
    print("MODE: capability — add one tool/skill/channel/connection/schedule/subagent/hook/eval"
          + (" or capability package" if cap_mode == "packages" else "") + ".")
    print("Next: read node_modules/eve/docs/, then add a single file (or package) and an eval.")
    if not evals:
        warnings.append("no *.eval.ts found — `eve eval` has no gate to enforce.")
    for w in warnings:
        print(f"WARN: {w}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
