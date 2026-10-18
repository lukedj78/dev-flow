"""debt_model.py — one shape for every audit's finding, the fixed table that puts it in a band, the decisions that
keep it on purpose, and the order inside a band.

The audits dev-flow composes each speak their own language (`H/M/L`, `HIGH/MEDIUM/LOW`, `found`, `block`, a
shadscan disposition, vercel-doctor counts). `debt_sources.py` turns each into a `Finding`; this module decides
where it goes. Stdlib only.
"""

from __future__ import annotations

import hashlib
import subprocess
from dataclasses import dataclass
from pathlib import Path

BANDS = ("before-release", "with-features", "later")

# (source, check or "*", severity or "*", band) — the first row that matches wins. Repeated for the user in
# dev-flow/references/debt-audit.md; test_band_table_rows pins each row.
BAND_RULES: list[tuple[str, str, str, str]] = [
    ("app-security", "*", "*", "before-release"),         # secrets, authorization, vulnerable deps, exposed data
    ("compliance", "*", "H", "before-release"),
    ("compliance", "*", "*", "with-features"),
    ("registry-intake", "*", "block", "before-release"),
    ("registry-intake", "*", "*", "with-features"),
    ("observability", "errors", "*", "before-release"),   # an app online that does not know when it breaks
    ("observability", "*", "*", "later"),
    ("tests", "untested-mutation", "authz", "before-release"),   # writes, no test, and an authorization finding
    ("tests", "*", "*", "with-features"),
    ("shadscan", "*", "fix", "with-features"),
    ("shadscan", "*", "*", "later"),                      # verify / decide
    ("vercel-doctor", "*", "high", "with-features"),
    ("vercel-doctor", "*", "medium", "with-features"),
    ("vercel-doctor", "*", "*", "later"),
    ("launch-audit", "*", "*", "with-features"),
    ("promote-component", "*", "*", "later"),
    ("*", "*", "HIGH", "with-features"),                  # the prose recipes: state-discipline, data-fetching, forms
    ("*", "*", "MEDIUM", "with-features"),
    ("*", "*", "*", "later"),
]


@dataclass
class Finding:
    source: str
    check: str
    detail: str
    file: str | None = None
    line: int | None = None
    severity: str = ""
    routed_to: str = ""
    signal: bool = False   # a scanner's hit nobody has confirmed yet (app-security, compliance)
    stale: bool = False    # from a recorded run older than the last material change
    band: str = ""
    kept: str = ""         # why it is kept on purpose, when it is

    @property
    def id(self) -> str:
        return f"{self.source}:{self.check}:{self.file or '-'}"


def merge(findings: list[Finding]) -> list[Finding]:
    """One finding per id: a check reported at several places without a file (launch-audit's routes, a level's
    pieces) becomes one row listing every place, so a verdict, and new / closed, refer to one thing."""
    out: dict[str, Finding] = {}
    for f in findings:
        first = out.get(f.id)
        if first is None:
            out[f.id] = f
        else:
            # "<what> — <where>" rows of one check: keep <what> once and list every <where>
            head, _, tail = f.detail.partition(" — ")
            if tail and first.detail.startswith(head + " — "):
                if tail not in first.detail[len(head) + 3:].split("; "):
                    first.detail += "; " + tail
            elif f.detail not in first.detail.split("; "):
                first.detail += "; " + f.detail
            first.signal = first.signal or f.signal
            first.stale = first.stale or f.stale
    return list(out.values())


def band_for(f: Finding) -> str:
    for source, check, severity, band in BAND_RULES:
        if source in ("*", f.source) and check in ("*", f.check) and severity in ("*", f.severity):
            return band
    return "later"


def file_hash(root: Path, rel: str | None) -> str:
    """A short hash of the file's bytes, so a verdict knows when the code it judged has changed; "" when unreadable."""
    if not rel:
        return ""
    try:
        return hashlib.sha256((root / rel).read_bytes()).hexdigest()[:16]
    except OSError:
        return ""


def _gate_acceptances(meta: dict) -> dict[tuple[str, str], str]:
    """(source, check) → reason, from the keys each gate already writes. They name a check, not a file: a check the
    gate accepted is accepted wherever it appears, because that is what the gate decided."""
    out: dict[tuple[str, str], str] = {}
    for a in (((meta.get("security") or {}).get("findings") or {}).get("accepted") or []):
        if isinstance(a, dict) and a.get("check"):
            out[("app-security", str(a["check"]))] = str(a.get("reason") or "accepted in meta.json#security")
    for check, reason in ((meta.get("launch_audit") or {}).get("dismissed") or {}).items():
        out[("launch-audit", str(check))] = str(reason)
    shad = meta.get("shadscan") or {}
    for key in ("false_positives", "rules_left_red"):
        for rule, reason in (shad.get(key) or {}).items():
            out[("shadscan", str(rule))] = str(reason)
    return out


def apply_decisions(findings: list[Finding], meta: dict, reviewed: dict | None,
                    root: Path) -> tuple[list[Finding], list[Finding], list[str]]:
    """(open, kept, notes). Gate acceptances apply per check; `reviewed.json` verdicts per finding id, and a
    false_positive or accepted verdict lapses when the file has changed since. `compliance.flagged` is never kept:
    it means a legal decision is still owed."""
    notes: list[str] = []
    if reviewed is None:
        notes.append(".workflow/debt/reviewed.json could not be read — every verdict in it is ignored this run")
        reviewed = {}
    gates = _gate_acceptances(meta)
    flagged = {str(x) for x in ((meta.get("compliance") or {}).get("flagged") or [])}
    open_: list[Finding] = []
    kept: list[Finding] = []
    for f in findings:
        reason = gates.get((f.source, f.check))
        if reason is not None:
            f.kept = reason
            kept.append(f)
            continue
        v = reviewed.get(f.id) if isinstance(reviewed.get(f.id), dict) else None
        same = v is not None and v.get("hash", "") == file_hash(root, f.file)
        if v and v.get("verdict") == "confirmed":
            f.signal = False
        elif v and v.get("verdict") in ("false_positive", "accepted") and same:
            f.kept = str(v.get("reason") or v["verdict"])
            kept.append(f)
            continue
        if f.source == "compliance" and f.check in flagged:
            f.detail += " — a legal decision is still owed (compliance.flagged)"
        open_.append(f)
    return open_, kept, notes


def churn(root: Path, days: int = 90) -> dict[str, int]:
    """How many commits touched each file in the last `days`; {} without git or history."""
    try:
        out = subprocess.run(["git", "-C", str(root), "log", f"--since={days}.days", "--name-only", "--pretty=format:"],
                             capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return {}
    if out.returncode != 0:
        return {}
    counts: dict[str, int] = {}
    for line in out.stdout.splitlines():
        if line.strip():
            counts[line.strip()] = counts.get(line.strip(), 0) + 1
    return counts


def order(findings: list[Finding], churn_: dict[str, int]) -> list[Finding]:
    """The files touched most often first ("with the features" means that file will be reopened); ties, and
    findings without a file, keep the order the sources gave them."""
    return sorted(findings, key=lambda f: -churn_.get(f.file or "", 0))


def diff_runs(previous_ids: set[str], current_ids: set[str]) -> tuple[set[str], set[str]]:
    """(new, closed) since the last run."""
    return current_ids - previous_ids, previous_ids - current_ids
