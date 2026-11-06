# The review cycle — iterating without looping

`spec-review`'s three axes are **one pass**: spawn, report, close with a level. That is the right
default and it is not enough for a branch an agent wrote, because the implementer's own corrections
are never reviewed by anyone. This file is the loop, and the three refusals that keep it from becoming
a way to spend tokens until the agent agrees with itself.

The state lives in `meta.json#spec_review`, written only through `scripts/findings.py`.

## The two roles, and why they must not be one agent

| | **Implementer** | **Reviewer** |
|---|---|---|
| Has | the task, the conversation, the reasons | the diff, the spec, the contract — **not the reasoning** |
| Produces | the change, the tests it ran, a summary | structured findings |
| Must not | review its own work | accept the implementer's conclusions |

**The reviewer is deliberately given less.** An agent handed *"here is my change and here is why it is
right"* returns that hypothesis confirmed; it is the best-documented failure of delegated review.
So the reviewer's brief carries the diff, the spec at its known path, the contract, and **not** the
implementer's justification. Where the implementer's reasoning matters, it arrives as a finding's
resolution — argued on the record, not assumed up front.

The axes already enforce the structural half of this: three sub-agents, each with its own sources
pasted in full, **forbidden from spawning further agents**, and reported side by side without being
merged (`SKILL.md` §4–5).

## One round

```
open ──► the three axes run ──► findings recorded ──► implementer answers each one
                                                              │
                        ┌─────────────────────────────────────┤
                        │                                     │
                   fixed / rejected / accepted          needs a human
                        │                                     │
                        ▼                                     ▼
                    iterate ──► re-review the new diff    STOP — ask, and wait
```

```bash
python3 spec-review/scripts/findings.py <root> open --fixed-point main --profile standard
python3 spec-review/scripts/findings.py <root> add --axis risk --severity high \
    --category rollback --file lib/db/schema.ts --line 42 \
    --summary "the migration drops client_choice with no backfill" --needs-human
python3 spec-review/scripts/findings.py <root> resolve F3 --as fixed --sha abc1234
python3 spec-review/scripts/findings.py <root> iterate
```

## 🔴 The three refusals

### 1. A round cannot close while a finding needs a human

`iterate` refuses and names them. This is not an exception to the loop — it is the loop's purpose.
When the two agents disagree about a product decision, an architectural trade-off or an ambiguous
requirement, **there is no technically correct answer to converge on**, and another round produces a
longer argument, not a resolution.

What belongs on `--needs-human`: a one-way door that may be fine; a requirement the PRD does not
settle; a trade between two things the project values; anything where the fix changes behaviour the
user asked for. What does not: a defect with one correct fix — that is `fixed`, and the agent does it.

### 2. The cap is real, and reaching it is information

| profile | rounds | for |
|---|---|---|
| `light` | 1 | documentation, copy, a contained fix |
| `standard` | 3 | ordinary feature work |
| `strict` | 5 | auth, payments, schema, infrastructure, anything multi-tenant |

`iterate` refuses past the cap and says what to do instead: close at level 3 and take the open
findings to the user. **A review that has not converged in three rounds has found something a fourth
round will not settle** — usually a spec that is wrong, which is `prd-from-idea/references/scope-check.md`,
not a review problem.

⚠️ **The profile is depth, never subtraction.** It sets how many rounds and how deep the briefs go. It
does **not** drop an axis, lower a severity, or skip a check because the diff is small —
`contracts.md` defines an intervention level by *who can check a finding*, and a diff's size cannot
change who can check it. The 2026-10-20 measurement is the proof: those commits were small, tested
and green, and two of them were the day's worst defects. A profile that subtracts checks from small
changes is a profile aimed exactly at them.

### 3. A finding that comes back is counted, not re-filed

Identity is `(axis, category, file, line, summary)` hashed — **not the wording**, so a reviewer
rephrasing the same defect does not create a second finding. When a resolved finding reappears,
`findings.py` restores it and increments `reopened`.

That count is the cycle's own quality signal, and the sharpest one available:

- a **fixed** finding that reopens means the fix did not hold;
- a **rejected** finding that reopens means the reviewer is re-reporting what the implementer argued
  away — which is the loop arguing with itself, and the case the cap exists for.

`evals/review-quality/` reads it, which is why it is a number and not a sentence.

## Structured findings

Every finding carries: `id`, `fingerprint`, `axis`, `severity`, `category`, `file`, `line`, `summary`,
`evidence`, `impact`, `suggestion`, `confidence`, `needs_human`, `resolution`, `found_in_round`, and on
resolution a `resolution_note`, a `resolution_quote` (for an acceptance) and a `resolution_sha`.

Four rules about what goes in:

- **`rejected` needs a reason** and `accepted` needs **the user's own words** — enforced, because an
  acceptance given out loud is, a month later, indistinguishable from something nobody noticed.
- **Severity is about consequence, not confidence.** A possible authorization hole is `high` with
  `confidence: low`; those are two fields because they are two facts.
- **`critical` and `high`, left open, make level 1 and 2 impossible.** `close --level 1|2` refuses.
  Levels 1 and 2 mean the agent merges, and an unresolved high finding is precisely what is not the
  agent's to wave through.
- **Distinguish a defect from a preference.** A style opinion with no documented standard behind it is
  `info` at most, or it is not a finding. `SKILL.md`'s Standards axis already says a documented breach
  can be a hard finding while a baseline smell is always a judgement call.

## What reaches GitHub

**Not all of it.** The findings list is the working record; a PR carries only what a human needs to
act on:

- every finding still **open** at close, with its severity;
- every **accepted** trade, with the user's words — this is the one that must not stay in `meta.json`,
  because the reviewer of the PR cannot see that file;
- the **level**, and what it means for who merges.

A `rejected` finding does not go to GitHub. Neither does a fixed one, beyond the commit that fixed it.
`references/pr-documentation.md` is the template, and *"do not flood GitHub with agent-generated
comments"* is a rule, not a preference.

## Where the cycle sits

It is the inside of step 4 of `dev-flow/references/finishing-a-feature.md` — which already owns the
moment, asks whether to merge, and acts on the level. Nothing here replaces that conversation; this is
what happens between *"run the full review?"* and the three columns, when the first pass found
something worth a second look.

**When not to loop at all.** A clean first pass closes at level 1 or 2 and stops. Running a second
round on a review with nothing open is how a cycle becomes a ritual — and `finishing-a-feature.md`'s
own warning applies: *if it ever fires more often than that, it will be switched off.*
