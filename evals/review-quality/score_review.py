#!/usr/bin/env python3
"""score_review.py — did the review find the defect, and did it stay quiet about the trap?

    python3 score_review.py cases/<case>.json --review <findings.json> [--json]
    python3 score_review.py --self-test

A review that reports twenty findings is not better than one that reports three; it is louder. So the
arithmetic here deliberately rewards **neither volume nor confidence**. Every case carries two lists,
and the second one is the half that makes the score mean something:

- `expected` — defects that are really there. A review that misses one has a **false negative**, and
  for the cases taken from this repo's own history we know they are there because they shipped.
- `traps` — things a review is **expected to stay quiet about**: correct code that pattern-matches a
  defect, a style preference with no documented standard, a risk already accepted in writing. A
  finding on a trap is a **false positive**, and a reviewer that fires on these is one a team learns
  to ignore, which costs more than missing a medium finding.

Matching is **deterministic**: a finding matches an expectation when the file matches, the line is
within the expectation's tolerance, and the expectation's `must_mention` terms all appear in the
finding's text. No model, no embedding, no judgement — so the same review always scores the same, and
a change to a prompt or a rubric can be compared against a baseline.

**What this does NOT score**, stated here so nobody reads a number as more than it is: whether a
suggested fix is good, whether the wording is clear, whether the reasoning holds. Those need a model
(`rubric.md`), and the rubric's instruction is to grade the *evidence and the reasoning*, never the
count. This file grades what can be checked without one.

Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

SEVERITIES = ["info", "low", "medium", "high", "critical"]

#: Default line tolerance. A reviewer pointing at the function rather than the exact line has found
#: the defect; one pointing at another file has not.
DEFAULT_TOLERANCE = 12


def rank(sev: object) -> int:
    return SEVERITIES.index(sev) if isinstance(sev, str) and sev in SEVERITIES else -1


def text_of(finding: dict) -> str:
    """Everything a finding says, lowercased — matched against `must_mention`."""
    parts = [finding.get(k) for k in ("summary", "evidence", "impact", "suggestion", "category")]
    return " ".join(str(p) for p in parts if p).lower()


def same_file(expected: object, actual: object) -> bool:
    """Suffix match, so `lib/db/schema.ts` matches `apps/web/lib/db/schema.ts` in a monorepo."""
    if not expected:
        return True            # an expectation with no file is about the change as a whole
    if not isinstance(actual, str) or not actual:
        return False
    e, a = str(expected).lstrip("./"), actual.lstrip("./")
    return a.endswith(e) or e.endswith(a)


def line_close(expected: dict, actual: dict) -> bool:
    want = expected.get("line")
    if want is None:
        return True
    got = actual.get("line")
    if not isinstance(got, int):
        return False           # the expectation names a line; a finding without one did not locate it
    return abs(got - int(want)) <= int(expected.get("tolerance", DEFAULT_TOLERANCE))


def mentions(expected: dict, actual: dict) -> bool:
    terms = expected.get("must_mention") or []
    if not isinstance(terms, list):
        return False
    body = text_of(actual)
    return all(str(t).lower() in body for t in terms)


def matches(expected: dict, actual: dict) -> bool:
    if expected.get("axis") and actual.get("axis") != expected["axis"]:
        return False
    return (same_file(expected.get("file"), actual.get("file"))
            and line_close(expected, actual)
            and mentions(expected, actual))


@dataclass
class Result:
    case: str
    found: list[str] = field(default_factory=list)          # expectation ids the review caught
    missed: list[str] = field(default_factory=list)          # false negatives
    tripped: list[str] = field(default_factory=list)         # trap ids the review fired on
    severity_off: list[dict] = field(default_factory=list)   # caught, but graded too low or too high
    unmatched: int = 0                                       # findings matching nothing in the case
    total_findings: int = 0

    @property
    def recall(self) -> float:
        n = len(self.found) + len(self.missed)
        return len(self.found) / n if n else 1.0

    @property
    def trap_rate(self) -> float:
        return len(self.tripped) / self._traps if self._traps else 0.0

    def as_dict(self, traps: int) -> dict:
        self._traps = traps
        d = asdict(self)
        d["recall"] = round(self.recall, 3)
        d["trap_rate"] = round(self.trap_rate, 3)
        d["verdict"] = self.verdict(traps)
        return d

    def verdict(self, traps: int) -> str:
        """A case passes only when it caught every expectation it was built for and tripped no trap.

        Deliberately not a percentage: a review that finds four of five authorization holes has not
        scored 80%, it has left one.
        """
        if self.missed:
            return "FAIL — missed a defect this case exists to catch"
        if self.tripped:
            return "FAIL — fired on a trap: correct code reported as a defect"
        if self.severity_off:
            return "WARN — found everything, graded a severity wrong"
        return "PASS"


def score(case: dict, findings: list[dict]) -> Result:
    r = Result(case=case.get("id", "<unnamed>"), total_findings=len(findings))
    claimed: set[int] = set()

    for exp in case.get("expected", []):
        hit = next((i for i, f in enumerate(findings) if i not in claimed and matches(exp, f)), None)
        if hit is None:
            r.missed.append(exp.get("id", "<unnamed>"))
            continue
        claimed.add(hit)
        r.found.append(exp.get("id", "<unnamed>"))
        want = exp.get("severity")
        got = findings[hit].get("severity")
        if want and rank(got) != rank(want):
            # Under-grading is the dangerous direction: it is how a high finding gets merged at level 2.
            r.severity_off.append({"id": exp.get("id"), "expected": want, "actual": got,
                                   "direction": "under" if rank(got) < rank(want) else "over"})

    for trap in case.get("traps", []):
        hit = next((i for i, f in enumerate(findings) if i not in claimed and matches(trap, f)), None)
        if hit is not None:
            claimed.add(hit)
            r.tripped.append(trap.get("id", "<unnamed>"))

    r.unmatched = len(findings) - len(claimed)
    return r


def render(case: dict, r: Result) -> str:
    traps = len(case.get("traps", []))
    lines = [f"{r.case}: {r.verdict(traps)}",
             f"  expected {len(case.get('expected', []))} · found {len(r.found)} · missed {len(r.missed)}",
             f"  traps {traps} · tripped {len(r.tripped)}",
             f"  findings reported {r.total_findings} · matching nothing in this case {r.unmatched}"]
    for mid in r.missed:
        exp = next((e for e in case["expected"] if e.get("id") == mid), {})
        lines.append(f"  MISSED {mid}: {exp.get('why') or exp.get('must_mention')}")
    for tid in r.tripped:
        trap = next((t for t in case["traps"] if t.get("id") == tid), {})
        lines.append(f"  TRAP   {tid}: {trap.get('why') or 'reported correct code as a defect'}")
    for s in r.severity_off:
        lines.append(f"  SEVERITY {s['id']}: graded {s['actual']} where the case says {s['expected']} "
                     f"({s['direction']}-graded)")
    if r.unmatched:
        lines.append("  Findings matching nothing in the case are neither credited nor penalised: a case "
                     "knows its own defects, not every true thing about the diff.")
    return "\n".join(lines)


def load_json(path: Path) -> object:
    return json.loads(path.read_text())


def findings_from(obj: object) -> list[dict]:
    """Accepts `findings.py status --json` output (the whole block) or a bare list."""
    if isinstance(obj, dict):
        got = obj.get("findings")
        return [f for f in got if isinstance(f, dict)] if isinstance(got, list) else []
    if isinstance(obj, list):
        return [f for f in obj if isinstance(f, dict)]
    return []


def self_test() -> int:
    """Enough to prove the arithmetic, so a grader that lies is caught before it grades anything."""
    case = {
        "id": "self-test",
        "expected": [
            {"id": "E1", "file": "lib/db/schema.ts", "line": 40, "severity": "critical",
             "must_mention": ["drop"], "why": "the migration drops a column"},
            {"id": "E2", "file": "app/api/orders/route.ts", "severity": "high",
             "must_mention": ["owner"], "why": "no owner filter"},
        ],
        "traps": [
            {"id": "T1", "file": "lib/db/seed.ts", "must_mention": ["drop"],
             "why": "a DROP in a seed script for a local database is not a production defect"},
        ],
    }
    checks: list[tuple[str, bool]] = []

    perfect = [
        {"file": "lib/db/schema.ts", "line": 42, "severity": "critical", "summary": "the migration will DROP client_choice"},
        {"file": "app/api/orders/route.ts", "severity": "high", "summary": "query by id with no owner filter"},
    ]
    r = score(case, perfect)
    checks.append(("a review that finds both and trips nothing PASSes", r.verdict(1) == "PASS"))
    checks.append(("recall is 1.0", r.recall == 1.0))

    r = score(case, perfect[:1])
    checks.append(("a missed defect FAILs", r.verdict(1).startswith("FAIL") and r.missed == ["E2"]))

    noisy = perfect + [{"file": "lib/db/seed.ts", "severity": "high", "summary": "this will drop data"}]
    r = score(case, noisy)
    checks.append(("firing on a trap FAILs even with everything found", r.tripped == ["T1"]))

    under = [
        {"file": "lib/db/schema.ts", "line": 42, "severity": "low", "summary": "the migration will DROP client_choice"},
        {"file": "app/api/orders/route.ts", "severity": "high", "summary": "no owner filter on the query"},
    ]
    r = score(case, under)
    checks.append(("under-grading a severity is a WARN, not a pass",
                   r.verdict(1).startswith("WARN") and r.severity_off[0]["direction"] == "under"))

    volume = perfect + [{"file": "README.md", "severity": "info", "summary": f"nit {i}"} for i in range(20)]
    r = score(case, volume)
    checks.append(("twenty extra findings do not improve the verdict", r.verdict(1) == "PASS" and r.unmatched == 20))

    wrong_file = [
        {"file": "lib/db/other.ts", "line": 42, "severity": "critical", "summary": "the migration will DROP something"},
        {"file": "app/api/orders/route.ts", "severity": "high", "summary": "no owner filter"},
    ]
    r = score(case, wrong_file)
    checks.append(("pointing at the wrong file is not finding it", "E1" in r.missed))

    monorepo = [
        {"file": "apps/web/lib/db/schema.ts", "line": 41, "severity": "critical", "summary": "DROP column"},
        {"file": "apps/web/app/api/orders/route.ts", "severity": "high", "summary": "no owner filter"},
    ]
    r = score(case, monorepo)
    checks.append(("a monorepo prefix still matches", r.verdict(1) == "PASS"))

    far = [
        {"file": "lib/db/schema.ts", "line": 400, "severity": "critical", "summary": "DROP column"},
        {"file": "app/api/orders/route.ts", "severity": "high", "summary": "no owner filter"},
    ]
    r = score(case, far)
    checks.append(("a line 358 away is outside tolerance", "E1" in r.missed))

    checks.append(("findings_from reads a findings.py block",
                   len(findings_from({"findings": perfect, "level": 3})) == 2))
    checks.append(("findings_from reads a bare list", len(findings_from(perfect)) == 2))
    checks.append(("an unknown severity ranks below info", rank("urgent") == -1))

    bad = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(f"  {'✓' if ok else '✗'} {name}")
    print(f"\n{len(checks) - len(bad)}/{len(checks)} checks passed")
    return 1 if bad else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("case", nargs="?", type=Path)
    ap.add_argument("--review", type=Path, default=None,
                    help="findings.py status --json output, or a bare list of findings")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)

    if a.self_test:
        return self_test()
    if a.case is None or a.review is None:
        ap.error("a case file and --review are required (or --self-test)")
    case = load_json(a.case)
    if not isinstance(case, dict):
        print(f"{a.case}: not a case object", file=sys.stderr)
        return 2
    findings = findings_from(load_json(a.review))
    r = score(case, findings)
    traps = len(case.get("traps", []))
    print(json.dumps(r.as_dict(traps), indent=2) if a.json else render(case, r))
    return 0 if r.verdict(traps) == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
