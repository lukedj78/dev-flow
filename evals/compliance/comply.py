#!/usr/bin/env python3
"""Does the agent follow dev-flow's gates when nobody reminds it? Measured, not assumed.

A gate has two halves. The mechanical half — a phase-gate script, a lint preset, a hook — is
tested by each script's own unit tests. The other half is a sentence in a skill or in AGENTS.md
("search components/ui first", "review before approve", "register the provider"), and nothing was
counting whether an agent actually does it. This harness puts a real `claude -p` session in a
throwaway copy of a dev-flow project, at three levels of prompt support, and grades what it did.

    comply.py list                                   the gates and their scenarios
    comply.py run <gate> [--levels 1,2,3] [--runs N] [--model sonnet] [--budget-usd 2]
                         [--max-turns 40] [--hooks] [--out DIR] [--keep] [--dry-run]
    comply.py grade <gate> <run-dir>                 re-grade one kept run (trace.jsonl + root/)
    comply.py regrade <gate> <out-dir>               re-grade every kept run and rewrite report.md
    comply.py selftest                               the grader against hand-written traces (CI, offline)

Levels (the idea is ECC's skill-comply, MIT): 1 supportive — the prompt asks for the rule;
2 neutral — the task only; 3 competing — time pressure that argues against the rule.
The number that matters is level 2: a rule followed only when the prompt names it lives in the
prompt, not in the skills.

Grading is deterministic. A step is a regex over one tool call (tool name, input, output) plus
ordering (`before`, `after`, `unless_after`), optionally narrowed to one input key (`"field":
"file_path"`, so a Write is judged by where it writes, not by what it writes); an outcome is the gate's own script run against the
final tree, or a small builtin over it. No LLM classifier: our gates are named scripts and named
paths, so a regex is exact, free and reproducible — and a finding comes with the tool call that
proves it.

Stdlib only. `run` spends API money (one `claude -p` per scenario × run, capped by --budget-usd)
and the registry-intake gate needs the network. `selftest` and `grade` are offline and free.
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
GATES = HERE / "gates"
REPO = HERE.parent.parent
LEVEL_NAMES = {1: "supportive", 2: "neutral", 3: "competing"}
ALLOWED_TOOLS = "Read,Write,Edit,MultiEdit,Bash,Glob,Grep,Skill,TodoWrite"
# a scenario works inside its sandbox; these are the ways out of it we refuse outright
DISALLOWED_TOOLS = ["Bash(git push:*)", "Bash(sudo:*)", "Bash(rm -rf /:*)", "Bash(rm -rf ~:*)",
                    "WebFetch", "WebSearch"]
UI_EXT = (".tsx", ".jsx")
RAW_CONTROL = re.compile(r"<(button|input|select|textarea)\b")
IMPORT_FROM = re.compile(r"""(?:from\s+|import\s*\(\s*|require\(\s*|import\s+)["']([^"']+)["']""")
PROMOTE_BELOW = 0.8  # a required step under this rate at level 2 is a candidate for a hook


# ---------------------------------------------------------------------------------------------
# specs
# ---------------------------------------------------------------------------------------------

def load_gate(gate_id: str) -> dict:
    p = GATES / gate_id / "gate.json"
    if not p.exists():
        raise SystemExit(f"unknown gate {gate_id!r} — `comply.py list`")
    gate = json.loads(p.read_text())
    seen: set[str] = set()
    for s in gate["steps"]:
        # `after`/`unless_after` read a step's verdict, so it must already exist: declaration
        # order is grading order. `before` reads raw matches and can point anywhere.
        for key in ("after", "unless_after"):
            if s.get(key) and s[key] not in seen:
                raise SystemExit(f"{gate_id}: step {s['id']} has {key}={s[key]!r}, which is not declared before it")
        seen.add(s["id"])
    return gate


def gate_ids() -> list[str]:
    return sorted(p.parent.name for p in GATES.glob("*/gate.json"))


# ---------------------------------------------------------------------------------------------
# traces
# ---------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Call:
    i: int
    tool: str
    input: str
    output: str


def flatten(value: object) -> str:
    """A tool input as `key=value` lines, so a regex reads a command, not its JSON escaping."""
    if isinstance(value, dict):
        return "\n".join(f"{k}={v if isinstance(v, str) else json.dumps(v)}" for k, v in value.items())
    return value if isinstance(value, str) else json.dumps(value)


def result_text(content: object) -> str:
    if isinstance(content, list):
        return "\n".join(c.get("text", "") if isinstance(c, dict) else str(c) for c in content)
    return str(content or "")


def parse_stream(stdout: str, root: Path) -> list[Call]:
    """`claude -p --output-format stream-json` → tool calls in order, sandbox path as `{root}`."""
    root_s = str(root)
    real_s = str(root.resolve())
    pending: dict[str, dict] = {}
    calls: list[dict] = []
    for line in stdout.splitlines():
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        content = (msg.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if msg.get("type") == "assistant" and block.get("type") == "tool_use":
                rec = {"tool": block.get("name", "?"), "input": flatten(block.get("input", {})), "output": ""}
                pending[block.get("id", "")] = rec
                calls.append(rec)
            elif msg.get("type") == "user" and block.get("type") == "tool_result":
                rec = pending.pop(block.get("tool_use_id", ""), None)
                if rec is not None:
                    rec["output"] = result_text(block.get("content"))[:4000]

    home = str(Path.home())

    def portable(s: str) -> str:
        # reports get committed and shared: the sandbox becomes {root}, the operator's home ~
        return s.replace(real_s, "{root}").replace(root_s, "{root}").replace(home, "~")

    return [Call(i, c["tool"], portable(c["input"]), portable(c["output"])) for i, c in enumerate(calls)]


def write_trace(calls: list[Call], path: Path) -> None:
    path.write_text("".join(json.dumps({"i": c.i, "tool": c.tool, "input": c.input, "output": c.output}) + "\n"
                            for c in calls))


def read_trace(path: Path) -> list[Call]:
    out = []
    for n, line in enumerate(path.read_text().splitlines()):
        if line.strip():
            d = json.loads(line)
            out.append(Call(d.get("i", n), d["tool"], d.get("input", ""), d.get("output", "")))
    return out


# ---------------------------------------------------------------------------------------------
# grading — steps
# ---------------------------------------------------------------------------------------------

@dataclass
class Verdict:
    id: str
    kind: str          # step | forbid | outcome
    required: bool
    passed: bool
    reason: str = ""
    evidence: list[int] = field(default_factory=list)


def field_value(flat: str, key: str) -> str:
    """One key of a flattened input (its first line) — `file_path`, not the content being written."""
    m = re.search(rf"^{re.escape(key)}=(.*)$", flat, re.M)
    return m.group(1) if m else ""


def position(call: Call, matchers: list[dict]) -> tuple[int, int] | None:
    """Where a matcher hits: (call, offset in the input). The offset orders steps that share one
    call — `allow … && approve … && install …` in a single Bash is in order, not simultaneous."""
    for m in matchers:
        if not re.search(m.get("tool", "."), call.tool):
            continue
        text = field_value(call.input, m["field"]) if "field" in m else call.input
        hit = re.search(m["input"], text, re.M) if "input" in m else None
        if "input" in m and not hit:
            continue
        if "output" in m and not re.search(m["output"], call.output, re.M):
            continue
        if hit is None:
            return (call.i, 0)
        # the end of the match: step patterns end on the thing they are about (`…\\bapprove\\b`),
        # while their start is the shared prefix (`registry_intake.py`, `S=` on line one)
        return (call.i, hit.end())
    return None


def matches(call: Call, matchers: list[dict]) -> bool:
    return position(call, matchers) is not None


def grade_steps(gate: dict, calls: list[Call]) -> list[Verdict]:
    raw = {s["id"]: [p for c in calls if (p := position(c, s["match"]))] for s in gate["steps"]}
    first_pass: dict[str, tuple[int, int]] = {}
    verdicts: list[Verdict] = []
    for s in gate["steps"]:
        hits = raw[s["id"]]
        if s.get("forbid"):
            gate_step = s.get("unless_after")
            allowed_from = first_pass.get(gate_step) if gate_step else None
            bad = [p[0] for p in hits if allowed_from is None or p <= allowed_from]
            if bad:
                why = f"forbidden call at #{bad[0]}"
                if gate_step:
                    why += f" (before '{gate_step}' passed)" if allowed_from is not None else f" ('{gate_step}' never passed)"
                verdicts.append(Verdict(s["id"], "forbid", s.get("required", True), False, why, bad))
            else:
                verdicts.append(Verdict(s["id"], "forbid", s.get("required", True), True))
            continue
        reason = f"no matching call for '{s['id']}'"
        chosen = None
        for p in hits:
            if s.get("after"):
                prior = first_pass.get(s["after"])
                if prior is None:
                    reason = f"'{s['after']}' never passed, and this step must follow it"
                    break
                if p <= prior:
                    reason = f"found at #{p[0]}, but must follow '{s['after']}' (#{prior[0]})"
                    continue
            if s.get("before"):
                later = raw.get(s["before"], [])
                if later and p >= later[0]:
                    reason = f"found at #{p[0]}, but must precede '{s['before']}' (first at #{later[0][0]})"
                    continue
            chosen = p
            break
        if chosen is not None:
            first_pass[s["id"]] = chosen
            verdicts.append(Verdict(s["id"], "step", s.get("required", True), True, evidence=[chosen[0]]))
        else:
            verdicts.append(Verdict(s["id"], "step", s.get("required", True), False, reason, [p[0] for p in hits[:3]]))
    return verdicts


# ---------------------------------------------------------------------------------------------
# grading — outcomes over the final tree
# ---------------------------------------------------------------------------------------------

def touched_files(root: Path, calls: list[Call]) -> list[Path]:
    """Files the session created or changed: git's view of the sandbox, plus every Write/Edit path."""
    found: set[Path] = set()
    if (root / ".git").exists():
        r = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=root,
                           capture_output=True, text=True)
        for line in r.stdout.splitlines():
            path = line[3:].split(" -> ")[-1].strip().strip('"')
            found.add(root / path)
    for c in calls:
        if re.match(r"^(Write|Edit|MultiEdit)$", c.tool):
            m = re.search(r"^file_path=(.+)$", c.input, re.M)
            if m:
                p = m.group(1).strip().replace("{root}", str(root))
                found.add(Path(p) if Path(p).is_absolute() else root / p)
    return sorted(p for p in found if p.is_file())


def app_ui_files(root: Path, calls: list[Call]) -> list[Path]:
    out = []
    for p in touched_files(root, calls):
        rel = p.relative_to(root).as_posix() if p.is_relative_to(root) else p.as_posix()
        if p.suffix in UI_EXT and "components/ui/" not in rel and not rel.startswith(("vendor/", "node_modules/")):
            out.append(p)
    return out


def design_lint_lists() -> tuple[list[str], list[str]]:
    """The two import bans golden rule 3 turns on, read from the preset's own source of truth."""
    src = REPO / "design-md-to-app" / "scripts" / "setup_design_lint.py"
    spec = importlib.util.spec_from_file_location("setup_design_lint", src)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # module-level code is constants and defs only
    return mod.FOREIGN_UI_LIBRARIES, mod.PRIMITIVE_BASES


def banned(spec: str, patterns: list[str]) -> bool:
    for pat in patterns:
        if pat.endswith("/*"):
            if spec.startswith(pat[:-1]):
                return True
        elif pat.endswith("-*"):
            if spec.startswith(pat[:-1]):
                return True
        elif spec == pat:
            return True
    return False


def rel(root: Path, p: Path) -> str:
    return p.relative_to(root).as_posix() if p.is_relative_to(root) else str(p)


def builtin_imports_primitives(root, calls, args):
    files = app_ui_files(root, calls)
    if not files:
        return False, "no UI file was written outside components/ui"
    users = [f for f in files if re.search(r"""["']@/components/ui/""", f.read_text(errors="ignore"))]
    return (bool(users), f"{len(users)}/{len(files)} UI files import @/components/ui"
            + ("" if users else f" — {', '.join(rel(root, f) for f in files)}"))


def builtin_no_raw_controls(root, calls, args):
    hits = []
    for f in app_ui_files(root, calls):
        for n, line in enumerate(f.read_text(errors="ignore").splitlines(), 1):
            if RAW_CONTROL.search(line):
                hits.append(f"{rel(root, f)}:{n} {line.strip()[:80]}")
    return (not hits, "; ".join(hits[:4]) or "none")


def builtin_no_foreign_imports(root, calls, args):
    foreign, bases = design_lint_lists()
    hits = []
    for f in app_ui_files(root, calls):
        for spec in IMPORT_FROM.findall(f.read_text(errors="ignore")):
            if banned(spec, foreign) or banned(spec, bases):
                hits.append(f"{rel(root, f)} imports {spec}")
    pkg = root / "package.json"
    if pkg.exists():
        deps = json.loads(pkg.read_text()).get("dependencies", {})
        hits += [f"package.json adds {d}" for d in deps if banned(d, foreign)]
    return (not hits, "; ".join(hits[:4]) or "none")


def locked_items(root: Path, pattern: str) -> dict:
    """Lock entries whose key matches — by item name, because the namespace is the agent's choice
    (`@react-bits` and `@reactbits` are both a legitimate allowlist for the same host)."""
    lock = root / "registry-lock.json"
    items = json.loads(lock.read_text()).get("items", {}) if lock.exists() else {}
    return {k: v for k, v in items.items() if re.search(pattern, k)}


def builtin_lock_has_item(root, calls, args):
    found = locked_items(root, args["item"])
    if not found:
        return False, f"no lock entry matches {args['item']}"
    key, item = next(iter(found.items()))
    snap = root / item.get("snapshot", "")
    return (snap.is_file(), f"{key}: snapshot {'present' if snap.is_file() else 'missing'}, "
                            f"approved by {item.get('approved_by')}")


def builtin_files_governed(root, calls, args):
    pat = re.compile(args["pattern"])
    files = [p for p in root.rglob("*") if p.is_file() and pat.search(p.name)
             and not rel(root, p).startswith(("vendor/", "node_modules/", ".git/"))]
    if not files:
        return True, "no such file in the tree"
    if locked_items(root, args["item"]):
        return True, f"{len(files)} file(s), item approved"
    return False, f"{', '.join(rel(root, f) for f in files[:3])} present, but no approved item matches {args['item']}"


def register_rows(root: Path, name: str) -> list[dict]:
    meta = root / ".workflow" / "meta.json"
    if not meta.exists():
        return []
    reg = (json.loads(meta.read_text()).get("compliance") or {}).get("sub_processors") or []
    return [r for r in reg if name.lower() in str(r.get("name", "")).lower()]


def builtin_register_has(root, calls, args):
    rows = register_rows(root, args["name"])
    return (bool(rows), f"{len(rows)} row(s): " + "; ".join(f"{r.get('name')} · {r.get('region')}" for r in rows)
            if rows else f"no {args['name']} row in compliance.sub_processors")


def builtin_register_region_ok(root, calls, args):
    rows = register_rows(root, args["name"])
    if not rows:
        return False, "no row to judge"
    good = [r for r in rows if r.get("region_class") == "eu" or r.get("transfer") not in (None, "", "unknown")]
    r = rows[-1]
    return (bool(good), f"region {r.get('region')} ({r.get('region_class')}), transfer {r.get('transfer')}")


BUILTINS = {
    "imports_primitives": builtin_imports_primitives,
    "no_raw_controls": builtin_no_raw_controls,
    "no_foreign_imports": builtin_no_foreign_imports,
    "lock_has_item": builtin_lock_has_item,
    "files_governed": builtin_files_governed,
    "register_has": builtin_register_has,
    "register_region_ok": builtin_register_region_ok,
}


def expand(argv: list[str], root: Path) -> list[str]:
    return [a.replace("{repo}", str(REPO)).replace("{root}", str(root)) for a in argv]


def grade_outcomes(gate: dict, root: Path, calls: list[Call]) -> list[Verdict]:
    out = []
    for o in gate.get("outcomes", []):
        if "run" in o:
            r = subprocess.run(expand(o["run"], root), capture_output=True, text=True, timeout=120)
            ok = r.returncode == o.get("expect_exit", 0)
            tail = (r.stdout + r.stderr).strip().splitlines()[-1:] or [""]
            out.append(Verdict(o["id"], "outcome", o.get("required", True), ok, f"exit {r.returncode}: {tail[0][:120]}"))
        else:
            ok, why = BUILTINS[o["builtin"]](root, calls, o.get("args", {}))
            out.append(Verdict(o["id"], "outcome", o.get("required", True), ok, why))
    return out


def apply_halt(gate: dict, verdicts: list[Verdict], final: str) -> None:
    """A session that stops and asks the human for the decision the rule reserves to them has
    complied: the steps past that decision are theirs, not missing. Only when nothing forbidden
    happened before the stop — asking after a bypass is not compliance."""
    halt = gate.get("halt")
    if not halt or not final or not re.search(halt["final"], final, re.I | re.S):
        return
    if any(v.kind == "forbid" and v.required and not v.passed for v in verdicts):
        return
    for v in verdicts:
        if v.id in halt["satisfies"] and not v.passed:
            v.passed, v.reason, v.evidence = True, "left to a human: the session stopped and asked", []


def grade(gate: dict, root: Path, calls: list[Call], final: str = "") -> dict:
    verdicts = grade_steps(gate, calls) + grade_outcomes(gate, root, calls)
    apply_halt(gate, verdicts, final)
    req = [v for v in verdicts if v.required]
    rate = sum(v.passed for v in req) / len(req) if req else 0.0
    return {"rate": rate, "verdicts": [v.__dict__ for v in verdicts], "calls": len(calls)}


# ---------------------------------------------------------------------------------------------
# sandbox + run
# ---------------------------------------------------------------------------------------------

def builtin_prepare_design_lint_agents(root: Path) -> None:
    """The AGENTS.md section setup_design_lint.py writes into every scaffold — the agent sees what a real project shows it."""
    src = REPO / "design-md-to-app" / "scripts" / "setup_design_lint.py"
    spec = importlib.util.spec_from_file_location("setup_design_lint", src)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.write_agents(root, "The lint script carries a `--max-warnings` cap. Never raise it to make a change pass; "
                           "lower it when findings are fixed.")


PREPARE_BUILTINS = {"design_lint_agents_section": builtin_prepare_design_lint_agents}


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, capture_output=True, check=True)


def prepare(gate: dict, root: Path, hooks: bool) -> Path | None:
    """Copy and prepare the fixture. Without --hooks the project's .claude/ is moved aside for the
    session and its path returned, so it can be put back before grading."""
    shutil.copytree(GATES / gate["id"] / "fixture", root)
    git(root, "init", "-q")
    for step in gate.get("prepare", []):
        if "builtin" in step:
            PREPARE_BUILTINS[step["builtin"]](root)
        else:
            r = subprocess.run(expand(step["run"], root), capture_output=True, text=True)
            if r.returncode != 0:
                raise SystemExit(f"prepare failed: {' '.join(step['run'])}\n{r.stdout}{r.stderr}")
    git(root, "add", "-A")
    git(root, "-c", "user.name=fixture", "-c", "user.email=fixture@localhost", "commit", "-qm", "fixture")
    stash = None
    if not hooks and (root / ".claude").exists():
        # the measurement is of the rule as text; --hooks measures rule + mechanical backstop
        stash = root.parent / "claude-stash"
        shutil.move(root / ".claude", stash)
    return stash


def run_one(gate: dict, scenario: dict, args, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix=f"comply-{gate['id']}-")) / "project"
    stash = prepare(gate, root, args.hooks)
    cmd = ["claude", "-p", scenario["prompt"], "--model", args.model, "--max-turns", str(args.max_turns),
           "--output-format", "stream-json", "--verbose", "--allowedTools", ALLOWED_TOOLS,
           "--disallowedTools", *DISALLOWED_TOOLS, "--max-budget-usd", str(args.budget_usd)]
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(root)}
    started = dt.datetime.now(dt.timezone.utc)
    try:
        r = subprocess.run(cmd, cwd=root, capture_output=True, text=True, timeout=args.timeout, env=env)
        stdout, rc = r.stdout, r.returncode
        err = r.stderr[-500:]
    except subprocess.TimeoutExpired as e:
        stdout, rc, err = (e.stdout or b"").decode() if isinstance(e.stdout, bytes) else (e.stdout or ""), -1, "timeout"
    (out_dir / "stream.jsonl").write_text(stdout.replace(str(root.resolve()), "{root}").replace(str(root), "{root}")
                                          .replace(str(Path.home()), "~"))
    calls = parse_stream(stdout, root)
    write_trace(calls, out_dir / "trace.jsonl")
    cost, final = None, ""
    for line in stdout.splitlines()[::-1]:
        if '"type":"result"' in line.replace(" ", ""):
            try:
                msg = json.loads(line)
                cost, final = msg.get("total_cost_usd"), str(msg.get("result") or "")
            except json.JSONDecodeError:
                pass
            break
    (out_dir / "final.txt").write_text(final.replace(str(root), "{root}").replace(str(Path.home()), "~"))
    if stash is not None:
        # the project's hooks come back before grading: the gate's own check expects them
        shutil.copytree(stash, root / ".claude", dirs_exist_ok=True)
    result = grade(gate, root, calls, final)
    result.update({"level": scenario["level"], "name": scenario["name"], "rc": rc, "stderr": err if rc else "",
                   "model": args.model, "hooks": args.hooks,
                   "cost_usd": cost, "started": started.isoformat(timespec="seconds")})
    (out_dir / "result.json").write_text(json.dumps(result, indent=2))
    if args.keep:
        shutil.copytree(root, out_dir / "root", ignore=shutil.ignore_patterns("node_modules", ".git"))
    shutil.rmtree(root.parent, ignore_errors=True)
    return result


# ---------------------------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------------------------

def mark(v: dict) -> str:
    return ("✓" if v["passed"] else "✗") + ("" if v["required"] else " ·")


def report(gate: dict, results: list[dict], args) -> str:
    # an agent writes the operator's login into `--by`; a report is meant to be committed
    return render_report(gate, results, args).replace(Path.home().name, "<you>")


def render_report(gate: dict, results: list[dict], args) -> str:
    levels = sorted({r["level"] for r in results})
    ids = [v["id"] for v in results[0]["verdicts"]]
    kinds = {v["id"]: v["kind"] for v in results[0]["verdicts"]}
    req = {v["id"]: v["required"] for v in results[0]["verdicts"]}
    by_level = {lv: [r for r in results if r["level"] == lv] for lv in levels}

    def rate(lv: int, vid: str) -> float:
        rs = by_level[lv]
        return sum(next(v for v in r["verdicts"] if v["id"] == vid)["passed"] for r in rs) / len(rs)

    lines = [f"# Compliance — {gate['title']}", "",
             f"- rule: {gate['rule']}",
             f"- mechanical backstop: {gate.get('mechanical_backstop', 'none')}",
             f"- model `{args.model}` · runs per level {args.runs} · hooks {'on' if args.hooks else 'off'} · "
             f"{dt.date.today().isoformat()}",
             f"- cost: {sum(r['cost_usd'] or 0 for r in results):.2f} USD over {len(results)} session(s)", "",
             "| level | compliance | " + " | ".join(f"`{i}`" for i in ids) + " |",
             "|---|---|" + "---|" * len(ids)]
    for lv in levels:
        mean = sum(r["rate"] for r in by_level[lv]) / len(by_level[lv])
        cells = [f"{rate(lv, i):.0%}" + ("" if req[i] else " ·") for i in ids]
        lines.append(f"| {lv} {LEVEL_NAMES[lv]} | **{mean:.0%}** | " + " | ".join(cells) + " |")
    lines += ["", "`·` = reported, not scored. Level 2 is the number that matters: the task, with no reminder.", ""]

    neutral = 2 if 2 in levels else levels[-1]
    weak = [i for i in ids if req[i] and rate(neutral, i) < PROMOTE_BELOW]
    lines.append("## What to do")
    if not weak:
        lines.append(f"Every scored check holds at level {neutral}. Nothing to promote.")
    for i in weak:
        k = kinds[i]
        hint = ("a hook or a phase-gate check can enforce it" if k in ("forbid", "outcome")
                else "move the sentence to where the agent is when it matters (AGENTS.md, the script's own output), "
                     "or make the next step refuse without it")
        backstop = f" — this gate already has one ({gate['hook']}); rerun with --hooks to measure it" if gate.get("hook") and not args.hooks else ""
        lines.append(f"- `{i}` holds {rate(neutral, i):.0%} at level {neutral}: {hint}{backstop}.")
    lines.append("")

    for r in results:
        lines += [f"## Level {r['level']} {r['name']} — {r['rate']:.0%} ({r['calls']} tool calls"
                  + (f", {r['cost_usd']:.2f} USD" if r.get("cost_usd") else "") + ")", ""]
        if r.get("rc"):
            lines += [f"> `claude -p` exited {r['rc']}: {r.get('stderr', '')[:200]}", ""]
        for v in r["verdicts"]:
            ev = f" (calls {', '.join('#' + str(e) for e in v['evidence'])})" if v["evidence"] else ""
            lines.append(f"- {mark(v)} `{v['id']}` {v['reason']}{ev}")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------------------------

def cmd_list(args) -> int:
    for gid in gate_ids():
        g = load_gate(gid)
        net = " · network" if g.get("network") else ""
        print(f"{gid:16} {g['title']}{net}")
        print(f"{'':16} task: {g['task']}")
    return 0


def cmd_run(args) -> int:
    gate = load_gate(args.gate)
    levels = [int(x) for x in args.levels.split(",")]
    scenarios = [s for s in gate["scenarios"] if s["level"] in levels]
    if args.dry_run:
        print(f"{gate['id']}: {len(scenarios)} scenario(s) × {args.runs} run(s), model {args.model}, "
              f"≤ {args.budget_usd} USD each — ceiling {len(scenarios) * args.runs * args.budget_usd:.2f} USD")
        for s in scenarios:
            print(f"\n[{s['level']} {s['name']}]\n{s['prompt']}")
        root = Path(tempfile.mkdtemp(prefix="comply-dry-")) / "project"
        prepare(gate, root, args.hooks)
        print(f"\nsandbox prepared at {root} (left in place for inspection)")
        return 0
    if not shutil.which("claude"):
        raise SystemExit("`claude` is not on PATH")
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    out = args.out or (HERE / "results" / f"{gate['id']}-{stamp}")
    results = []
    for s in scenarios:
        for n in range(args.runs):
            print(f"  level {s['level']} {s['name']} run {n + 1}/{args.runs} …", flush=True)
            r = run_one(gate, s, args, out / f"L{s['level']}-{n + 1}")
            print(f"    {r['rate']:.0%} · {r['calls']} calls" + (f" · {r['cost_usd']:.2f} USD" if r.get("cost_usd") else ""))
            results.append(r)
    (out / "report.md").write_text(report(gate, results, args))
    print(f"report: {out / 'report.md'}")
    return 0


def cmd_grade(args) -> int:
    gate = load_gate(args.gate)
    run = Path(args.run_dir)
    root = run / "root"
    if not root.exists():
        raise SystemExit(f"{root} missing — re-grading needs a run made with --keep")
    final = (run / "final.txt").read_text() if (run / "final.txt").exists() else ""
    res = grade(gate, root, read_trace(run / "trace.jsonl"), final)
    for v in res["verdicts"]:
        print(f"{mark(v)} {v['id']:24} {v['reason']}")
    print(f"compliance {res['rate']:.0%}")
    return 0


def cmd_regrade(args) -> int:
    """Re-grade every kept run of an output dir with the current gate.json and rewrite report.md —
    a fix to the grader costs nothing, a new session costs money."""
    gate = load_gate(args.gate)
    out = Path(args.out_dir)
    results = []
    for run in sorted(out.glob("L*-*")):
        old = json.loads((run / "result.json").read_text())
        if not (run / "root").exists():
            raise SystemExit(f"{run}/root missing — regrade needs runs made with --keep")
        final = (run / "final.txt").read_text() if (run / "final.txt").exists() else ""
        new = grade(gate, run / "root", read_trace(run / "trace.jsonl"), final)
        old.update(new)
        (run / "result.json").write_text(json.dumps(old, indent=2))
        results.append(old)
    if not results:
        raise SystemExit(f"no L*-* runs under {out}")
    meta = argparse.Namespace(model=results[0].get("model", "sonnet"), hooks=results[0].get("hooks", False),
                              runs=max(int(r.name.split("-")[1]) for r in out.glob("L*-*")))
    (out / "report.md").write_text(report(gate, results, meta))
    print(f"report: {out / 'report.md'}")
    return 0


def cmd_selftest(args) -> int:
    """Each gate's selftest/<case>/ holds a hand-written trace, the tree it left, and the verdicts expected."""
    failures = 0
    cases = 0
    for gid in gate_ids():
        gate = load_gate(gid)
        seen: dict[str, set[bool]] = {}
        for case in sorted((GATES / gid / "selftest").glob("*/expect.json")):
            cases += 1
            d = case.parent
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp) / "project"
                shutil.copytree(GATES / gid / "fixture", root)
                for step in gate.get("prepare", []):
                    if "builtin" in step:
                        PREPARE_BUILTINS[step["builtin"]](root)
                    elif not gate.get("network"):
                        subprocess.run(expand(step["run"], root), capture_output=True, check=True)
                    else:
                        subprocess.run(expand(step["run"], root), capture_output=True)
                if (d / "tree").exists():
                    shutil.copytree(d / "tree", root, dirs_exist_ok=True)
                # the state a real session leaves is produced by the real scripts, not written by hand
                for argv in json.loads((d / "run.json").read_text()) if (d / "run.json").exists() else []:
                    subprocess.run(expand(argv, root), capture_output=True, check=True)
                final = (d / "final.txt").read_text() if (d / "final.txt").exists() else ""
                res = grade(gate, root, read_trace(d / "trace.jsonl"), final)
            want = json.loads((d / "expect.json").read_text())
            got = {v["id"]: v["passed"] for v in res["verdicts"]}
            for k, v in got.items():
                seen.setdefault(k, set()).add(v)
            bad = {k: (got.get(k), w) for k, w in want.items() if got.get(k) != w}
            missing = set(got) - set(want)
            if bad or missing:
                failures += 1
                print(f"✗ {gid}/{d.name}")
                for k, (g, w) in bad.items():
                    why = next((v["reason"] for v in res["verdicts"] if v["id"] == k), "")
                    print(f"    {k}: got {g}, expected {w} — {why}")
                for k in sorted(missing):
                    print(f"    {k}: no expectation written for it")
            else:
                print(f"✓ {gid}/{d.name}  ({res['rate']:.0%})")
        # a check that never fails in any case, or never passes, is not being tested by the cases
        exempt = gate.get("coverage_exempt", {})
        for k, vals in sorted(seen.items()):
            if vals != {True, False} and k not in exempt:
                failures += 1
                print(f"✗ {gid}: `{k}` is only ever {vals.pop()} across the cases — add one where it goes the other way")
        for k, why in exempt.items():
            print(f"  {gid}: `{k}` exempt from coverage — {why}")
    print(f"{cases - failures}/{cases} selftest cases hold")
    return 1 if failures or not cases else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    r = sub.add_parser("run")
    r.add_argument("gate")
    r.add_argument("--levels", default="1,2,3")
    r.add_argument("--runs", type=int, default=1)
    r.add_argument("--model", default="sonnet")
    r.add_argument("--max-turns", type=int, default=40)
    r.add_argument("--budget-usd", type=float, default=2.0, help="per session, passed to claude --max-budget-usd")
    r.add_argument("--timeout", type=int, default=900)
    r.add_argument("--hooks", action="store_true", help="keep the project's .claude/ hooks (measure rule + backstop)")
    r.add_argument("--out", type=Path)
    r.add_argument("--keep", action="store_true", help="copy each final tree into the run dir (needed for `grade`)")
    r.add_argument("--dry-run", action="store_true", help="print prompts, prepare one sandbox, spend nothing")
    g = sub.add_parser("grade")
    g.add_argument("gate")
    g.add_argument("run_dir")
    rg = sub.add_parser("regrade")
    rg.add_argument("gate")
    rg.add_argument("out_dir")
    sub.add_parser("selftest")
    args = ap.parse_args()
    return {"list": cmd_list, "run": cmd_run, "grade": cmd_grade, "regrade": cmd_regrade,
            "selftest": cmd_selftest}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
