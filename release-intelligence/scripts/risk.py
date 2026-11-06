#!/usr/bin/env python3
"""risk.py — classify a release's risk from what the diff touches and what the gates already found.

    python3 risk.py <project-root> [--base <ref>] [--include-working] [--json]

Two halves, and the split is the point:

- **This script is the deterministic half.** It reads the diff and `meta.json`, matches a fixed list of
  signals, and returns the HIGHEST level any signal reached. Nothing here is a judgement: every signal
  names the file or the meta field that raised it, so the user can re-check it with one command.
- **The agent is the reasoning half**, and it may only **RAISE** the level, never lower it. A model that
  can talk itself down from `critical` is a model that ships a destructive migration on a Friday. The
  level this script prints is a floor; `release.py plan --raise-to` records the agent's increase with
  its reason, and there is no instruction that decreases it.

Levels, lowercase to match the contract's other enums: `low` < `medium` < `high` < `critical`.

Every threshold and every path pattern is overridable per project through
`meta.json#release.risk_policy` — the defaults below are a starting point, not a universal truth
(a design-system repo's `app/api/` means something different from a bank's).

`not checked` is never a pass. A signal this script cannot see (no git, no `meta.json`, a migration
directory it does not know) is reported as unchecked and listed in the output, because a release
classified `low` because nothing could be read is the one failure mode that matters here.

Stdlib only, like every script the skills ship.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

LEVELS = ("low", "medium", "high", "critical")


def worse(a: str, b: str) -> str:
    """The higher of two levels. Unknown values read as `low` so a typo cannot silence a real signal."""
    ia = LEVELS.index(a) if a in LEVELS else 0
    ib = LEVELS.index(b) if b in LEVELS else 0
    return LEVELS[max(ia, ib)]


# --- the signal table ------------------------------------------------------
#
# Each entry: (signal id, level, path regex). A changed file matching the regex raises the release to
# that level. Ordered by level so the output reads worst-first. Overridable through
# `meta.json#release.risk_policy.paths` — a project adds `{"payments": "critical"}` to re-level one,
# or `{"api": null}` to drop it.
PATH_SIGNALS: list[tuple[str, str, str]] = [
    # critical — the blast radius is not the code
    ("migration", "critical", r"(^|/)(drizzle|migrations|supabase/migrations)/.*\.sql$"
                              r"|(^|/)prisma/migrations/.*/migration\.sql$"),
    ("infra", "critical", r"(^|/)(Dockerfile|docker-compose\.ya?ml|fly\.toml|terraform/.*\.tf)$"),
    # high — authorization, money, and the edge that runs before every request
    ("auth", "high", r"(^|/)lib/auth(-client)?\.(ts|tsx|js)$"
                     r"|(^|/)app/api/auth/"
                     r"|(^|/)(middleware|proxy)\.(ts|js)$"
                     r"|(^|/)lib/(session|permissions|rbac|authz)\.(ts|tsx)$"),
    ("payments", "high", r"(^|/)(app/api/(stripe|webhooks?|payments?)/|lib/(server/)?(stripe|payments?|billing)\.)"),
    ("schema", "high", r"(^|/)lib/db/schema(/|\.(ts|js)$)|(^|/)drizzle\.config\.(ts|js)$"
                       r"|(^|/)prisma/schema\.prisma$"),
    # medium — a contract somebody else calls, and the platform config that decides cost and regions
    ("api", "medium", r"(^|/)app/api/.*/route\.(ts|js)$"),
    ("server_action", "medium", r"(^|/)lib/server/.*\.(ts|js)$"),
    ("platform_config", "medium", r"(^|/)(vercel\.json|next\.config\.(ts|js|mjs)|app\.config\.(ts|js)|eas\.json)$"),
    ("ci", "medium", r"(^|/)\.github/workflows/.*\.ya?ml$"),
]

# SQL that a `vercel rollback` does NOT undo. Each rule is (id, required, forbidden) and is matched
# case-insensitively against ONE statement at a time, never against the whole file: `ADD COLUMN tier
# text NOT NULL DEFAULT 'free'` is safe, and a single regex with a negative lookahead reports it as
# unsafe because `NOT NULL` is reached before `DEFAULT` (caught by its own test, 2026-11-06).
# `DROP INDEX` is deliberately absent: it costs performance, not data.
DESTRUCTIVE_SQL: list[tuple[str, list[str], list[str]]] = [
    ("drop_table", [r"\bDROP\s+TABLE\b"], []),
    ("drop_column", [r"\bDROP\s+COLUMN\b"], []),
    ("drop_constraint", [r"\bDROP\s+CONSTRAINT\b"], []),
    ("truncate", [r"\bTRUNCATE\b"], []),
    ("delete_rows", [r"\bDELETE\s+FROM\b"], []),
    ("type_change", [r"\bALTER\s+COLUMN\b", r"\bTYPE\b"], []),
    ("set_not_null", [r"\bSET\s+NOT\s+NULL\b"], []),
    ("rename", [r"\bRENAME\s+(COLUMN|TO)\b"], []),
    # Postgres rejects this on a non-empty table: a failed deploy, not a data loss. A DEFAULT in the
    # same statement makes it safe, which is why `forbidden` exists.
    ("add_not_null_without_default", [r"\bADD\s+COLUMN\b", r"\bNOT\s+NULL\b"], [r"\bDEFAULT\b"]),
]


def destructive_statements(sql: str) -> list[str]:
    """The ids of the destructive rules that match, judged one statement at a time."""
    found: list[str] = []
    for statement in sql.split(";"):
        if not statement.strip():
            continue
        for sid, required, forbidden in DESTRUCTIVE_SQL:
            if sid in found:
                continue
            if all(re.search(rx, statement, re.I) for rx in required) and \
                    not any(re.search(rx, statement, re.I) for rx in forbidden):
                found.append(sid)
    return found

# Size bands: (level, changed-file count). The largest band whose threshold the diff meets wins.
DEFAULT_SIZE_BANDS = {"medium": 15, "high": 60}


@dataclass
class Signal:
    id: str
    level: str
    why: str
    evidence: list[str] = field(default_factory=list)


@dataclass
class Assessment:
    level: str
    base: str | None
    changed_files: int
    signals: list[Signal]
    not_checked: list[str]
    reversible: bool
    destructive_migration: bool

    def as_dict(self) -> dict:
        d = asdict(self)
        d["signals"] = [asdict(s) for s in self.signals]
        return d


# --- git -------------------------------------------------------------------

def _git(root: Path, *args: str) -> tuple[int, str]:
    try:
        r = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as e:
        return 1, str(e)
    return r.returncode, (r.stdout or "") + ("" if r.returncode == 0 else r.stderr or "")


def detect_base(root: Path) -> str | None:
    """The branch this work forked from. Tried in order; None when none of them resolves."""
    for ref in ("origin/main", "origin/master", "main", "master"):
        code, out = _git(root, "merge-base", "HEAD", ref)
        if code == 0 and out.strip():
            return ref
    return None


def changed_files(root: Path, base: str | None, include_working: bool) -> tuple[list[str], list[str]]:
    """(paths, problems). Committed diff against `base`, plus the working tree when asked."""
    problems: list[str] = []
    paths: list[str] = []
    if base:
        code, out = _git(root, "diff", "--name-only", f"{base}...HEAD")
        if code == 0:
            paths += out.split()
        else:
            problems.append(f"git diff against {base} failed: the committed diff was not read")
    else:
        problems.append("no base branch resolved (origin/main, origin/master, main, master): "
                        "the committed diff was not read — pass --base <ref>")
    if include_working:
        code, out = _git(root, "status", "--porcelain")
        if code == 0:
            for line in out.splitlines():
                # "XY path" or "XY old -> new"; take the destination
                p = line[3:].strip()
                if " -> " in p:
                    p = p.split(" -> ", 1)[1]
                if p:
                    paths.append(p.strip('"'))
        else:
            problems.append("git status failed: uncommitted changes were not read")
    return sorted(set(paths)), problems


def added_sql(root: Path, base: str | None, files: list[str]) -> tuple[str, list[str]]:
    """(the added SQL text, problems). Only the `+` lines: an existing DROP is not this release's."""
    sql_files = [f for f in files if f.endswith(".sql")]
    if not sql_files:
        return "", []
    if base:
        code, out = _git(root, "diff", f"{base}...HEAD", "--unified=0", "--", *sql_files)
        if code == 0:
            return "\n".join(l[1:] for l in out.splitlines()
                             if l.startswith("+") and not l.startswith("+++")), []
    # No base, or the diff failed: read the files whole and say so, because a missed DROP is the
    # one thing this function exists to catch.
    text, problems = [], []
    for f in sql_files:
        p = root / f
        try:
            text.append(p.read_text(errors="ignore"))
        except OSError:
            problems.append(f"{f} could not be read: its SQL was not checked for destructive statements")
    return "\n".join(text), problems


# --- policy ----------------------------------------------------------------

def load_policy(meta: dict) -> dict:
    rel = meta.get("release")
    policy = rel.get("risk_policy") if isinstance(rel, dict) else None
    return policy if isinstance(policy, dict) else {}


def path_signals(policy: dict) -> list[tuple[str, str, str]]:
    """The signal table with the project's re-levelling applied. A level of null drops the signal."""
    overrides = policy.get("paths") if isinstance(policy.get("paths"), dict) else {}
    out = []
    for sid, level, pattern in PATH_SIGNALS:
        if sid in overrides:
            new = overrides[sid]
            if new is None:
                continue
            level = new if new in LEVELS else level
        out.append((sid, level, pattern))
    return out


def size_bands(policy: dict) -> dict[str, int]:
    bands = policy.get("size_bands")
    if isinstance(bands, dict) and all(isinstance(v, int) for v in bands.values()):
        return {k: v for k, v in bands.items() if k in LEVELS}
    return dict(DEFAULT_SIZE_BANDS)


# --- meta.json evidence ----------------------------------------------------
#
# The five pre-deploy gates and spec-review have already measured this project. Re-scanning would
# be a second opinion from the same evidence; reading what they wrote is free and is the house rule
# (`meta.json` is the single source of truth).

def meta_signals(meta: dict) -> tuple[list[Signal], list[str]]:
    signals: list[Signal] = []
    unchecked: list[str] = []

    sec = meta.get("security")
    if isinstance(sec, dict):
        open_findings = (sec.get("findings") or {}).get("open")
        if isinstance(open_findings, int) and open_findings > 0:
            signals.append(Signal("security_findings", "high",
                                  f"app-security has {open_findings} open finding(s)",
                                  ["meta.json#security.findings.open"]))
        tools = sec.get("tools") or {}
        skipped = [k for k, v in tools.items() if v == "not-run"]
        if skipped:
            unchecked.append(f"app-security did not run: {', '.join(sorted(skipped))} "
                             f"(meta.json#security.tools) — not clean, unchecked")
    else:
        unchecked.append("app-security has never run (no meta.json#security): the attack surface is unchecked")

    debt = meta.get("debt_audit")
    if isinstance(debt, dict):
        before = (debt.get("bands") or {}).get("before_release")
        if isinstance(before, int) and before > 0:
            signals.append(Signal("debt_before_release", "medium",
                                  f"the debt audit has {before} finding(s) banded `before_release`",
                                  ["meta.json#debt_audit.bands.before_release"]))

    review = meta.get("spec_review")
    if isinstance(review, dict):
        level = review.get("level")
        if isinstance(level, int) and level >= 3:
            signals.append(Signal("spec_review_level", "medium",
                                  f"spec-review closed at intervention level {level}: a person settled something",
                                  ["meta.json#spec_review.level"]))

    ver = meta.get("verification")
    if not isinstance(ver, dict) or not ver.get("proven_at"):
        unchecked.append("no verification manual proven (meta.json#verification): "
                         "nothing says the feature was driven on the real app")

    return signals, unchecked


# --- the assessment --------------------------------------------------------

def assess(root: Path, base: str | None = None, include_working: bool = False,
           meta: dict | None = None) -> Assessment:
    if meta is None:
        meta = read_meta(root)
    policy = load_policy(meta)
    if base is None:
        base = detect_base(root)

    files, problems = changed_files(root, base, include_working)
    signals: list[Signal] = []
    unchecked = list(problems)

    for sid, level, pattern in path_signals(policy):
        rx = re.compile(pattern)
        hits = [f for f in files if rx.search(f)]
        if hits:
            signals.append(Signal(sid, level, f"the diff touches the {sid} surface",
                                  sorted(hits)[:10]))

    destructive = False
    if any(s.id == "migration" for s in signals):
        sql, sql_problems = added_sql(root, base, files)
        unchecked += sql_problems
        found = destructive_statements(sql)
        if found:
            destructive = True
            signals.append(Signal("destructive_migration", "critical",
                                  "the migration contains statements a deployment rollback does not undo: "
                                  + ", ".join(found),
                                  ["expand/contract: references/database-migrations.md"]))

    bands = size_bands(policy)
    for level in ("high", "medium"):
        if level in bands and len(files) >= bands[level]:
            signals.append(Signal("size", level,
                                  f"{len(files)} changed files (>= the {level} band of {bands[level]})", []))
            break

    ms, mu = meta_signals(meta)
    signals += ms
    unchecked += mu

    level = "low"
    for s in signals:
        level = worse(level, s.level)

    signals.sort(key=lambda s: (-LEVELS.index(s.level), s.id))
    return Assessment(
        level=level, base=base, changed_files=len(files), signals=signals,
        not_checked=unchecked,
        # A migration is the canonical irreversible release: rolling the code back leaves the schema.
        reversible=not any(s.id in ("migration", "destructive_migration", "infra") for s in signals),
        destructive_migration=destructive,
    )


def read_meta(root: Path) -> dict:
    path = root / ".workflow" / "meta.json"
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def render(a: Assessment) -> str:
    out = [f"risk: {a.level.upper()}  ({a.changed_files} changed files"
           + (f", base {a.base}" if a.base else ", no base resolved") + ")"]
    out.append(f"reversible by a deployment rollback: {'yes' if a.reversible else 'NO'}")
    if a.signals:
        out.append("")
        out.append("signals (worst first):")
        for s in a.signals:
            out.append(f"  [{s.level:8}] {s.id} — {s.why}")
            for e in s.evidence:
                out.append(f"             {e}")
    else:
        out.append("")
        out.append("no signal matched: the floor is `low`.")
    if a.not_checked:
        out.append("")
        out.append("NOT CHECKED (never a pass):")
        for u in a.not_checked:
            out.append(f"  - {u}")
    out.append("")
    out.append("This level is a FLOOR. The agent may raise it with a reason "
               "(`release.py plan --raise-to <level> --reason \"...\"`); nothing lowers it.")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("project_root", type=Path)
    ap.add_argument("--base", default=None, help="the ref this work forked from; auto-detected when omitted")
    ap.add_argument("--include-working", action="store_true",
                    help="also count uncommitted changes (git status --porcelain)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    root = a.project_root
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2
    result = assess(root.resolve(), base=a.base, include_working=a.include_working)
    print(json.dumps(result.as_dict(), indent=2) if a.json else render(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
