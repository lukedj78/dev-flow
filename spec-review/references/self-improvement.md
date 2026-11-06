# Improving the review — the loop, and the gate on it

The review's own instructions are code that nobody tests. A brief that misses a class of defect keeps
missing it, quietly, release after release, and the only signal is an incident months later. This file
is the cycle that closes that gap — and the gate that keeps it from becoming an agent editing its own
rules.

## 🔴 The rule the whole cycle exists to respect

**Nothing promotes itself.** An agent may measure, propose, and show a comparison. It may not change
the review instructions, the risk categories, a severity rule or a brief that other sessions will run.
That is a human decision, taken on evidence, and recorded.

The reason is not caution in the abstract. A review policy that an agent can edit is a review policy
that an agent can relax — and the easiest way to make a failing eval pass is to change what the eval
asks. That is self-improvement in form and self-exemption in substance.

## The six steps

### 1. Collect

What is already recorded, no new instrumentation:

| Signal | Where |
|---|---|
| findings per axis, per round, resolved / rejected / **reopened** | `meta.json#spec_review` (`findings.py status --json`) |
| rounds used against the cap | `#spec_review.rounds` |
| the level each review closed at, and who decided | `#spec_review.level` |
| what shipped and what broke after it | `#release.releases[]` events — `rollback:*`, `stage_refused:*` |
| escaped defects | a bug triaged on the tracker (`scrum` Triage) that a review had seen the diff of |
| the deterministic review score | `evals/review-quality/score_review.py` |

**Reopened findings and escaped defects are the two that matter.** A finding that comes back means the
fix did not hold or the reviewer is arguing with itself; a defect that shipped through a review is the
only unambiguous miss. Everything else is context.

### 2. Find the pattern — three occurrences, not one

A single miss is an anecdote. Look for **the same class of defect missed three times**, or the same
false positive raised three times. Write it as a class, not as an instance:

- *"Risk findings on hooks never mention the firing rate"* — a class.
- *"F7 in the orders branch was wrong"* — an instance, and acting on it overfits the brief to one diff.

If the pattern is *"the reviewer missed a frontend regression"* and the dataset has no frontend case,
the finding is about **the dataset**, and step 3 writes a case rather than touching a brief.

### 3. Propose — one change, with what it predicts

A proposal states:

- the **class** and the three occurrences, with links;
- the **one** change — a line in a brief, a category in `risk.md`, a severity rule, a dataset case;
- what it should move: *"`ask-gate-false-positive-rate` goes from FAIL to PASS, and no other case
  regresses"*;
- the **cost**, when the change makes a review longer or more expensive.

One change per proposal. Two changes measured together cannot be told apart, which is how a rubric
accumulates lines nobody can justify.

### 4. Test against the dataset

```bash
cd evals/review-quality
for c in cases/*.json; do python3 score_review.py "$c" --review "$BASELINE/$(basename $c)"; done
```

Run every case **before and after**, on the same model, and record which model and which date. A
change that fixes one case and breaks another is **a trade to decide, not progress** — bring both
results.

⚠️ **A proposal that no case can measure does not get promoted on the strength of an argument.** It
gets a case written first. That is the slow path and it is the whole point: the dataset is what stops
a plausible rewrite from landing because it reads well.

### 5. Show the comparison

Before / after, per case, plus the judge's one line (`evals/review-quality/rubric.md`) on the most
costly thing the old review got wrong. Nothing aggregated into a score — the same reason `risk.md`
refuses one.

### 6. The human decides, and it is recorded

The user approves or refuses. On approval the change lands as an ordinary commit — reviewed like any
other, with the comparison in its message — and the baseline is re-recorded. On refusal the proposal
is kept with the reason, so the next session does not re-derive it.

## Where `skill-doctor` fits, and where it does not

The repo's own `skill-doctor.sh` (in its top-level scripts folder) wraps an external collector that reads how skills are actually used and
drafts edits. It is useful for **step 2** — spotting a skill that never fires, a reference nothing
reads, a description that does not match the body (it is exactly the class of defect that left
`spec-review`'s own description saying *"two axes"* for weeks after the third one shipped).

It is **not** the promotion mechanism. Its drafts are input to step 3, they go through step 4 like any
other proposal, and its own header records why it is run with `--skills-dir` and without
`--include-global-skills`: with the wrong flags it reads the *installed* copies and writes edits
against them.

## Two failure modes to name in advance

**Overfitting to the dataset.** Four cases from this repo's history are not the space of defects. A
brief tuned until all four pass may simply have learned the four. The guard is step 2's three-occurrence
rule — a change answers a pattern observed in real reviews, and the dataset only checks it did not
break anything.

**Rubric creep.** Every proposal adds a line, nothing removes one, and after a year the brief is
longer than the diff it reviews. A brief has a budget (`SKILL.md` caps each axis at 400 words for a
reason). **A proposal that adds a line should say which line it replaces.**
