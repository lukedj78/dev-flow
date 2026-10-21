# The Risk axis — what does it cost if this change is wrong?

Third axis of `spec-review`, read by its own sub-agent, reported in its own column, **never merged with
the other two**. Spec asks *did we build what was asked*; Standards asks *was it built the way the
contract says*; this one asks the question neither of them can: **if this is wrong, what does it cost?**

Adapted from [`merge-risk`](https://github.com/warpdotdev/common-skills/blob/main/.agents/skills/merge-risk/SKILL.md)
(warpdotdev/common-skills, MIT, which credits Matt Pocock's `pr` skill). Two deliberate departures from
the original are at the bottom; read them before changing anything here.

## The five categories

Each gets a verdict — **⚠️ poor / 👀 decent / ✅ good** — and, for anything but ✅, *one line saying what
would move it up*. A verdict with no such line is not a finding, it is a mood.

### 1. Alignment — does the code do what the change says it does?

- Does the diff match its own PR description and its issue? Behaviour assumed rather than specified, and
  drive-by changes, must be written down.
- **Our version:** the Spec axis already compares the diff with `PRD.md` and `tasks.md`. This asks the
  narrower thing: does it match what the **author said** about it. A PR whose description omits a schema
  change is an alignment finding even when the PRD covers it.

### 2. Impact — how far does it reach?

- Blast radius, not diff size. Who consumes this, and what breaks for them: layout shift, mobile, a
  changed response shape, a renamed export.
- **Sensitive areas carry outsized risk regardless of size** — auth, permissions, payments, PII,
  secrets, data migrations, dependency bumps, infra and config. Flag any that are touched, and say
  explicitly whether the change **widens access, weakens validation, or logs sensitive data**.
- **Our additions**, each from a real incident in this repo:
  - a **hook** (`.claude/settings.json`) runs before every tool call in every session, so a change to
    one reaches far beyond its diff — measured at *one command in five* on 2026-10-20;
  - a **vendored file** (`contracts.md` in 41 skills, `registry_intake.py` in 9 projects) is already
    copied elsewhere by the time the review runs, so its rollback is not one revert;
  - a **phase gate** (`update_meta.py set-phase`) decides whether other work can proceed at all.

### 3. Verification — is the behaviour proved, and by what?

- A change to the user experience **needs end-to-end proof** — a screenshot or a recording, before *and*
  after. A change that could affect performance needs a measurement. When the proof is missing, that is
  a finding, not a note.
- Edge cases tested, or written down when they are not.
- **Our addition, and it is the sharp one:** for anything that **gates, filters or refuses** — a hook, a
  lint rule, a validator, a permission check — a test that the bad case is caught is **half a
  verification**. The other half is *how often it fires on ordinary work*, measured on real input. On
  2026-10-20 seven consecutive reviews of one gate found every bypass and none asked what it cost; it
  was asking on 72% of commands, and the measurement took one script and five minutes. **A screenshot
  cannot show a false-positive rate.**

### 4. Rollback cost — one-way door or two-way door?

- Can this be walked back after merge? A two-way door is cheap; a one-way door is not.
- **One-way doors in our stack, by name:** a data migration that drops or rewrites; anything already
  **published** (a pushed commit, an npm release, a deployed URL, an artifact someone else vendored); a
  record written to a shared tracker; a decision recorded in `registry-lock.json` with a `--by`; an email
  or webhook that has fired. "One revert" is the wrong unit when the thing is already copied.

### 5. Error detection — if it breaks in production, who finds out first?

- Critical flows monitored, so the answer is not *the user*. Look for **swallowed errors** and fallbacks
  that hide breakage — a `catch` that logs and continues, a default that masks an empty response.
- **Our addition:** `meta.json#observability` says what this project actually has. A finding here is only
  real against that: asking for alerting on a project with `observability: null` is a different (and
  earlier) conversation.

## The sixth question, which is ours

After the five, ask once:

> **What does this change cost when it is wrong, that none of the five categories asks?**

A rubric scores what it lists. Run the 2026-10-20 ask-gate commits through the five above and every one
scores ✅ — small diff, tests added, suite green, one-line revert, and the change *was* the error
detection. The two defects that mattered (a gate asking on a fifth of all commands; a hook walking
`/usr` for two minutes before every command) are not any of the five. **If the answer to the sixth
question is empty, say so — that is a finding of its own kind, not a pass.**

## Two departures from the original

**1. No score.** The original computes `Σ(verdict × weight) / Σ(weights)` with thresholds at 1.5 and
2.25, and instructs that the arithmetic be **kept internal**. We do not, for two reasons:

- it is arithmetic on judgements — ⚠️/👀/✅ are opinions, the weights (Impact 2×, Rollback 1.5×) have no
  stated basis, and 2.1 against 2.3 reads like a difference between measurements;
- a number whose calculation is hidden cannot be checked, which is the opposite of this repo's rule that
  a claim carries its evidence.

This matches what we already wrote elsewhere: `shadscan` says *"act on the pair, never on the score"*
and *"never optimise for the score"*; `launch-audit` *"reports, never blocks, never scores"*. If a score
is ever wanted for **ordering** many PRs, it is shown with its five inputs and it decides nothing.

**2. Verification is stricter.** The original accepts a screenshot as end-to-end proof. For a gate or a
filter we require a measurement on real input as well — see category 3.

## What this axis never does

- It **never blocks** a merge, a phase or a deploy. It produces a column and, through
  `contracts.md#intervention-levels`, a level.
- It **never decides** a one-way door is acceptable. That is the user's, in writing, on the PR.
- It is **not** a sixth pre-deploy gate: the five gates read the finished artefact, this reads the change.
