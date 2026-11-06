# The judge's rubric — grading the reasoning, never the count

`score_review.py` answers what can be checked without a model: was the defect found, was a trap
tripped, was the severity graded right. This rubric is for the half that needs a reader — and its
first instruction is the one that makes it worth running.

> **Grade the evidence and the reasoning. Never reward the number of findings.**
> A review with three well-evidenced findings is better than one with twelve, and a judge that counts
> is a judge that trains the reviewer to pad.

Run it with any model; the rubric is the artefact, not the provider. Record which model and which date
with the result, because a score without them cannot be compared to anything.

## The seven dimensions

Each is graded **good / adequate / poor**, with one line of justification quoting the review. A grade
with no quote is not a grade.

### 1. Evidence
Does each finding point at something the reader can check — a file and line, a quoted hunk, a command
and its output, a doc reference? **poor** when a finding asserts a problem without saying how it was
established. A finding that cannot be checked cannot be acted on.

### 2. Accuracy
Is each finding true of this diff? Check two or three against the code. **poor** when a finding
describes code that is not there, or misreads what it does. Confidently wrong is worse than vague:
the 2026-08-26 sweep of this repo found that of ~55 `[VERIFY]` markers closed, a handful were
confidently wrong rather than merely unchecked.

### 3. Defect versus preference
Is each finding a defect, a documented-standard breach, or a taste? All three are legitimate — the
question is whether the review **says which**. **poor** when a preference is dressed as a defect, or
when a severity is used to make a nit feel important.

### 4. Severity calibration
Does severity track consequence, not confidence or effort? A possible authorization hole is `high`
with low confidence. **poor** on under-grading something that reaches auth, money, PII or a schema —
that is how a high finding gets merged at level 2.

### 5. The fix
Is the suggestion specific, correct, and the smallest thing that resolves the finding? **poor** when
it is *"consider refactoring"*, when it would introduce a second problem, or when it rewrites more
than the finding requires.

### 6. Coverage of the axes
Did each axis answer its own question, or did one substitute for another? The common failure is a
reviewer that cannot judge Risk and files Standards findings instead — which is why
`invented-api-in-docs` carries a scope-creep trap. **poor** when an axis reports nothing and does not
say that it found nothing.

### 7. The sixth question
`risk.md` asks, after the five categories: *what does this change cost when it is wrong, that none of
the five asks?* **poor** when it is skipped or answered with a restatement of one of the five. An
empty answer is a legitimate finding of its own kind **when it is stated as empty** — silence is not.

## Scoring, and what it is not

Report the seven grades and a one-paragraph verdict. **Do not average them into a number.** The
reason is the same one `risk.md` gives for refusing a risk score: arithmetic on judgements reads like
a measurement, and a number whose basis is an opinion cannot be checked. This repo says it in three
other places — `shadscan`'s *"never optimise for the score"*, `launch-audit`'s *"reports, never
blocks, never scores"*, `risk.md`'s *"no score"*.

What the judge **does** produce, and what makes it useful: **the single most costly thing this review
got wrong**, named, with the quote. One line. That is the line that goes into a self-improvement
proposal, and `score_review.py`'s deterministic verdict is what decides whether the proposal helped.

## What the judge may never do

- **Grade a review it wrote**, or a review by the same session. Separate call, separate context.
- **Read the implementer's justification.** The judge sees the diff, the review and the case's
  `why_this_case_exists` — not the reasoning that produced either.
- **Change a case.** A case that seems unfair is a finding about the case, reported, not edited. *A
  finding may not be deleted because it inconveniences a hypothesis.*
