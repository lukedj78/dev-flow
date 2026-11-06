# review-quality — is the review any good?

`evals/compliance` asks whether an agent follows the rules when nobody reminds it. This folder asks
the next question: when the review *runs*, does it find the defect — and does it stay quiet about the
thing that only looks like one?

Two halves, deliberately split by what can be checked without a model.

| | `score_review.py` | `rubric.md` |
|---|---|---|
| Asks | did it find the defect, did it trip the trap, did it grade the severity | is the finding well-argued, is the fix good |
| How | deterministic matching on file, line and required terms | a model reads the review against the rubric |
| Repeatable | **yes** — the same review always scores the same | no |
| Runs in CI | yes (`--self-test`, 12 checks) | no — it costs a model call |

## Why the traps matter more than the expectations

A review that reports twenty findings is not better than one that reports three; it is louder, and a
reviewer a team learns to ignore costs more than one that misses a medium finding. So every case
carries **`traps`**: correct code that pattern-matches a defect, a preference with no documented
standard behind it, a risk already accepted in writing. **Firing on a trap fails the case, even when
every expectation was found.**

The arithmetic refuses to reward volume: findings that match neither an expectation nor a trap are
counted and neither credited nor penalised, because a case knows its own defects, not every true
thing about the diff.

And the verdict is not a percentage. *"Four of five authorization holes"* is not 80% — it is one left.

## The cases are real

Every case in `cases/` is an incident from this repository, with its date and where it is recorded.
None is invented, because an invented case measures a reviewer against a guess about what goes wrong.

| Case | What it is |
|---|---|
| `ask-gate-false-positive-rate` | **The canonical one.** 2026-10-20: small diff, tests added, suite green, one-line revert — all five risk categories score well, and the gate asked on 72% of commands. Nothing in the five asks how often a gate fires on ordinary work. Its traps are the two findings a reviewer reaches for instead. |
| `destructive-migration-per-statement` | 2026-11-06: `ADD COLUMN … NOT NULL` with no `DEFAULT` fails on a non-empty table; the same statement **with** a `DEFAULT` is routine. The trap is the safe one. |
| `invented-api-in-docs` | 2026-11-06: a documented export that does not exist in the shipped package. Invisible to every test and lint; found only by comparing the claim with the artefact. |
| `agent-approves-itself` | 2026-09-15, measured: the agent allowlisted and approved a registry item itself and wrote the OS login into `--by`. An authorization that exists only as an instruction is not a control. |

## Running it

```bash
python3 score_review.py --self-test                              # the grader's own 12 checks
python3 score_review.py cases/ask-gate-false-positive-rate.json --review /tmp/findings.json
```

`--review` takes `spec-review/scripts/findings.py status --json` output directly, or a bare list of
findings. Exit 0 only on `PASS`.

## Adding a case

1. **Take it from something that actually happened** — a reverted change, an escaped defect, a
   production incident, a finding a review missed, or a false positive someone complained about.
2. Write `source` (where it is recorded and when) and `why_this_case_exists` in prose. A case whose
   purpose is not written down gets misread the first time it fails.
3. **Give it at least one trap.** A case with expectations only rewards a reviewer that reports
   everything, which is the behaviour this folder exists to measure against.
4. `must_mention` holds the terms the finding has to contain — the *defect*, not the wording. Keep
   them few and necessary; three terms is usually one too many.
5. Run the case against the current review before committing it, and record the baseline. A case that
   has never been run against anything is a hypothesis.

## What a comparison is for

The point of a dataset is **a change to a prompt, a rubric or a brief is only an improvement if it
moves these numbers**. Run the whole folder before and after; a change that fixes one case and breaks
another is a trade to decide, not progress. That comparison is the input to
`spec-review/references/self-improvement.md`, and nothing promotes itself on the strength of it.

## Limits, stated

- **Four cases are not a benchmark.** They are the cases we have written down; the sample is this
  repo's own history and it is biased toward the defects we already learned to look for.
- **Matching is lexical.** A reviewer that describes the ask-gate defect without using the words
  *"how often"* scores as having missed it. That is a deliberate trade for repeatability, and it means
  a `FAIL` is read, not obeyed.
- **No case covers a frontend regression or a performance cliff**, because we have not written one
  down yet. An empty area of the dataset is not a clean area.
