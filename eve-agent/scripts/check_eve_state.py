#!/usr/bin/env python3
"""check_eve_state.py — report the state of the eve agent in a monorepo.

Usage:
    python scripts/check_eve_state.py <project-root>

Prints whether the eve agent is scaffolded, what capabilities exist, the tracked
`stack.agent` value from .workflow/meta.json (if present), and a proposed next step.
Pure standard library; no dependencies.
"""
import json
import sys
from pathlib import Path


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


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python scripts/check_eve_state.py <project-root>")
        return 2

    root = Path(sys.argv[1]).expanduser().resolve()
    if not root.is_dir():
        print(f"error: not a directory: {root}")
        return 2

    agent_app = root / "apps" / "agent"
    agent_dir = agent_app / "agent"          # the agent/ source folder
    evals_dir = agent_app / "evals"          # SIBLING of agent/, not inside it
    meta_path = root / ".workflow" / "meta.json"

    # --- meta.json (dev-flow contract) ---
    tracked_agent = None
    meta_present = meta_path.is_file()
    if meta_present:
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            tracked_agent = (meta.get("stack") or {}).get("agent")
        except (json.JSONDecodeError, OSError) as exc:
            print(f"warning: could not read meta.json: {exc}")

    scaffolded = agent_dir.is_dir()

    print("=" * 56)
    print(f"project root : {root}")
    print(f".workflow    : {'present' if meta_present else 'absent (not a dev-flow project)'}")
    print(f"stack.agent  : {tracked_agent or '(unset)'}")
    print(f"apps/agent   : {'scaffolded' if scaffolded else 'NOT scaffolded'}")
    print("=" * 56)

    if scaffolded:
        has_agent_ts = (agent_dir / "agent.ts").is_file()
        has_instructions = (agent_dir / "instructions.md").is_file()
        tools = _list_files(agent_dir / "tools", ".ts")
        skills = _list_files(agent_dir / "skills", ".md")
        channels = _list_files(agent_dir / "channels")
        connections = _list_files(agent_dir / "connections")
        schedules = _list_files(agent_dir / "schedules")
        subagents = _list_files(agent_dir / "subagents")
        hooks = _list_files(agent_dir / "hooks")
        # evals can be nested (evals/weather/x.eval.ts) — count *.eval.ts recursively
        eval_files = sorted(p.name for p in evals_dir.rglob("*.eval.ts")) if evals_dir.is_dir() else []
        has_eval_config = (evals_dir / "evals.config.ts").is_file()
        evals = eval_files
        print(f"agent.ts     : {'present' if has_agent_ts else 'MISSING'}")
        print(f"instructions : {'present' if has_instructions else 'MISSING'}")
        print(f"tools        : {', '.join(tools) or '(none)'}")
        print(f"skills       : {', '.join(skills) or '(none)'}")
        print(f"channels     : {', '.join(channels) or '(none)'}")
        print(f"connections  : {', '.join(connections) or '(none)'}")
        print(f"schedules    : {', '.join(schedules) or '(none)'}")
        print(f"subagents    : {', '.join(subagents) or '(none)'}")
        print(f"hooks        : {', '.join(hooks) or '(none)'}")
        evals_note = "" if has_eval_config else "  (no evals.config.ts)"
        print(f"evals        : {', '.join(evals) or '(none)'}  (apps/agent/evals, sibling of agent/){evals_note}")
        print("-" * 56)
        print("MODE: capability — add one tool/skill/channel/connection/schedule/subagent/hook/eval.")
        print("Next: read node_modules/eve/docs/, then add a single file and an eval.")
        if not evals:
            print("WARN: no *.eval.ts found — `eve eval` has no gate to enforce.")
    else:
        print("MODE: scaffold — set up apps/agent once.")
        print("Next: read node_modules/eve/docs/ and follow references/eve-scaffold.md.")
        if not (root / "turbo.json").is_file():
            print("NOTE: no turbo.json found — bootstrap the monorepo before scaffolding.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
