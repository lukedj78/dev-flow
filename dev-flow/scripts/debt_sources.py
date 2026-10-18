"""debt_sources.py — where the debt audit's findings come from, each turned into a `debt_model.Finding`.

Three kinds of source:
- the sibling skills' local scanners, run by path in a subprocess (app-security, launch-audit, observability,
  compliance, registry-intake, promote-component) — a skill that is not installed, a script that fails, times out
  or prints something unreadable makes its source "not checked", never ok;
- recorded results of the CLIs that need the network (shadscan's JSON, vercel-doctor's counts), read, not run;
- `.workflow/debt/manual.json`, where the agent writes what the prose recipes (state-discipline, data-fetching,
  forms) found, in the same shape.

Stdlib only.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))
from debt_model import Finding  # noqa: E402

SKILLS_ROOT = Path(__file__).resolve().parents[2]
LOCATION = re.compile(r"^([\w./@\[\]()+-]+\.[A-Za-z]{1,5}):(\d+)\b\s*(.*)$")
# app-security checks that are about who may call the code: an untested mutation on one of these files goes first
AUTHZ_CHECKS = {"server-action-unauthenticated", "route-handler-unauthenticated", "query-by-id-unscoped"}


@dataclass
class Source:
    name: str
    status: str        # fresh | partial | stale | missing | not checked | not applicable
    reason: str = ""


def _located(source: str, check: str, detail: str, where: str, **kw) -> Finding:
    m = LOCATION.match(where.strip())
    if m:
        extra = f" ({m.group(3)})" if m.group(3) else ""
        return Finding(source, check, detail + extra, file=m.group(1), line=int(m.group(2)), **kw)
    return Finding(source, check, f"{detail} — {where}" if where else detail, **kw)


def _status_rows(source: str, keep: str, severity: Callable[[dict], str], signal: bool) -> Callable[[str], list[Finding]]:
    def parse(out: str) -> list[Finding]:
        rows = json.loads(out)
        if not isinstance(rows, list):
            raise ValueError("not a list")
        found: list[Finding] = []
        for r in rows:
            if r.get("status") != keep:
                continue
            kw = dict(severity=severity(r), routed_to=r.get("routed_to") or "", signal=signal)
            for w in (r.get("where") or [""]):
                found.append(_located(source, r["check"], r.get("detail", ""), str(w), **kw))
        return found
    return parse


def _observability(out: str) -> list[Finding]:
    rows = json.loads(out)
    return [Finding("observability", r["level"], r.get("detail", ""), severity=r["level"], routed_to="module-add observability")
            for r in rows if r.get("status") == "found"]


def _compliance(out: str) -> list[Finding]:
    data = json.loads(out)
    return [Finding("compliance", str(f["id"]), f"{f.get('title', '')} (art. {f.get('article', '?')})",
                    severity=str(f.get("severity", "")), routed_to="compliance-audit", signal=True)
            for f in data["findings"]]


def _registry(out: str) -> list[Finding]:
    lines = [l.strip() for l in out.splitlines()[1:] if l.strip()]
    return [Finding("registry-intake", "check", l, severity="block", routed_to="registry-intake") for l in lines]


def _promote(out: str) -> list[Finding]:
    found = []
    for line in out.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 4 and cells[3].startswith("Promote"):
            found.append(Finding("promote-component", cells[0].strip("`"), cells[3], severity="promote",
                                 routed_to="promote-component"))
    return found


# name → (script relative to SKILLS_ROOT, args after the root, timeout in seconds, parser of stdout)
SCANNERS: dict[str, tuple[str, list[str], int, Callable[[str], list[Finding]]]] = {
    "app-security": ("app-security/scripts/scan_security.py", ["--json"], 1800,
                     _status_rows("app-security", "found", lambda r: "found", signal=True)),
    "launch-audit": ("launch-audit/scripts/scan_launch.py", ["--json"], 120,
                     _status_rows("launch-audit", "missing", lambda r: "missing", signal=False)),
    "observability": ("module-add/scripts/observability_check.py", ["--json"], 120, _observability),
    "compliance": ("compliance-audit/scripts/scan.py", [], 120, _compliance),
    "registry-intake": ("registry-intake/scripts/registry_intake.py", ["check"], 120, _registry),
    "promote-component": ("promote-component/scripts/scan_promotion.py", [], 120, _promote),
}


def _args(name: str, args: list[str], meta: dict) -> list[str]:
    if name == "observability" and not ((meta.get("stack") or {}).get("observability")):
        return [*args, "--all"]   # never chosen: an app online without error tracking is itself a finding
    return args


def run_scanners(root: Path, meta: dict, skip: set[str], web: bool) -> tuple[list[Finding], list[Source]]:
    findings: list[Finding] = []
    sources: list[Source] = []
    for name, (rel, args, timeout, parse) in SCANNERS.items():
        if name in skip:
            sources.append(Source(name, "not checked", "skipped"))
            continue
        if name == "launch-audit" and not web:
            sources.append(Source(name, "not applicable", "web only"))
            continue
        if name == "registry-intake" and not (root / "registry-lock.json").is_file():
            sources.append(Source(name, "not checked", "no registry-lock.json — registry intake is not set up"))
            continue
        script = SKILLS_ROOT / rel
        if not script.is_file():
            sources.append(Source(name, "not checked", "not installed"))
            continue
        a = _args(name, args, meta)
        # registry_intake.py takes its subcommand first (`check <root>`); the others take the root first
        cmd = [sys.executable, str(script), *a, str(root)] if name == "registry-intake" \
            else [sys.executable, str(script), str(root), *a]
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            sources.append(Source(name, "not checked", f"timed out after {timeout}s"))
            continue
        except OSError as e:
            sources.append(Source(name, "not checked", f"could not run: {e}"))
            continue
        try:
            got = parse(out.stdout) if name != "registry-intake" or out.returncode == 1 else []
        except (ValueError, KeyError, TypeError, AttributeError) as e:
            tail = (out.stderr or out.stdout).strip().splitlines()[-1:] or [""]
            sources.append(Source(name, "not checked", f"unreadable output ({type(e).__name__}): {tail[0][:160]}"))
            continue
        findings += got
        notes = _unseen(out.stdout)
        sources.append(Source(name, "partial", notes) if notes else Source(name, "fresh"))
    return findings, sources


def _unseen(stdout: str) -> str:
    """What a scanner reported it could not check (gitleaks not installed, a region not visible): its source ran only
    in part, and the report must say where it did not look."""
    try:
        rows = json.loads(stdout)
    except ValueError:
        return ""
    if not isinstance(rows, list):
        return ""
    return "; ".join(f"{r.get('check') or r.get('level')}: {r.get('detail', '')}" for r in rows
                     if isinstance(r, dict) and r.get("status") in ("not checked", "unknown"))


def _older(ran_at: str | None, last_change: str | None) -> bool:
    return bool(last_change) and (not ran_at or str(ran_at) < str(last_change))


def recorded(root: Path, meta: dict, last_change: str | None) -> tuple[list[Finding], list[Source]]:
    """shadscan and vercel-doctor, read from what their last run left; stale when older than the last change."""
    findings: list[Finding] = []
    sources: list[Source] = []
    shad = root / "docs" / "ui" / "shadscan.json"
    if not shad.is_file():
        sources.append(Source("shadscan", "missing", "never run (docs/ui/shadscan.json)"))
    else:
        stale = _older((meta.get("shadscan") or {}).get("last_run_at"), last_change)
        try:
            items = ((json.loads(shad.read_text(encoding="utf-8")).get("agentHandoff") or {}).get("actionables") or [])
            for a in items:
                rule = str(a.get("ruleId") or a.get("rule") or a.get("id") or "rule")
                f = _located("shadscan", rule, str(a.get("title") or a.get("message") or rule), str(a.get("file") or ""),
                             severity=str(a.get("disposition") or ""), routed_to="shadscan", stale=stale)
                if f.line is None and isinstance(a.get("line"), int):
                    f.line = a["line"]
                findings.append(f)
            sources.append(Source("shadscan", "stale" if stale else "fresh"))
        except (ValueError, AttributeError) as e:
            sources.append(Source("shadscan", "not checked", f"docs/ui/shadscan.json unreadable ({type(e).__name__})"))
    vd = meta.get("vercel_doctor") or {}
    counts = vd.get("findings") if isinstance(vd.get("findings"), dict) else None
    if counts is None:
        sources.append(Source("vercel-doctor", "missing", "never run (meta.json#vercel_doctor)"))
    else:
        stale = _older(vd.get("last_run_at"), last_change)
        for sev in ("high", "medium", "low"):
            n = counts.get(sev) or 0
            if n:
                findings.append(Finding("vercel-doctor", sev, f"{n} {sev} findings — docs/vercel/doctor-report.md",
                                        severity=sev, routed_to="vercel-doctor", stale=stale))
        sources.append(Source("vercel-doctor", "stale" if stale else "fresh"))
    return findings, sources


def manual(root: Path) -> tuple[list[Finding], Source]:
    """What the agent recorded from the prose recipes, in the shared shape."""
    p = root / ".workflow" / "debt" / "manual.json"
    if not p.is_file():
        return [], Source("manual", "missing", "no .workflow/debt/manual.json — the recipes have not been run")
    try:
        rows = json.loads(p.read_text(encoding="utf-8"))
        found = [Finding(str(r["source"]), str(r["check"]), str(r.get("detail", "")), file=r.get("file"),
                         line=r.get("line"), severity=str(r.get("severity", "")), routed_to=str(r.get("routed_to") or r["source"]))
                 for r in rows]
    except (ValueError, KeyError, TypeError, AttributeError, OSError) as e:
        return [], Source("manual", "not checked", f".workflow/debt/manual.json unreadable ({type(e).__name__})")
    return found, Source("manual", "fresh")


def last_material_change(meta: dict) -> tuple[str | None, str | None]:
    """(ran_at, skill) of the latest history entry by a skill that changes what the app does."""
    import show_state   # lazy: show_state is the router, and it must not need this module to start
    changes = [h for h in meta.get("history") or [] if isinstance(h, dict)
               and h.get("skill") in show_state.MATERIAL_SKILLS and h.get("ran_at")]
    if not changes:
        return None, None
    last = max(changes, key=lambda h: str(h["ran_at"]))
    return str(last["ran_at"]), str(last["skill"])
