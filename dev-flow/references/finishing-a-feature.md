# Finishing a feature — the five questions before main

The moment a piece of work is done is the only moment when the cost of a mistake is still cheap, and
it is the one moment dev-flow had no step for. `spec-review` existed and was invocable, and in
archistudio — 200 merged PRs, 94 branches — it had **never run once**, because nothing ever asked.

This is that step. It is a conversation, in order, and each question is only asked when the previous
one was answered.

## 1. Are the acceptance criteria true? — with output, not with an opinion

`tasks.md` carries acceptance criteria per task, and in a real project most of them are commands:
*"build verde"*, *"`setup_design_lint.py --check` passa"*, *"migrazioni eseguibili in locale e in
anteprima"*, *"regione UE verificata"*.

Go through them **one at a time** and, for each, do one of exactly two things:

- **run the command and show its output.** Not a summary of it — the output. "build verde ✓" is an
  opinion; the last ten lines of `pnpm build` are a fact the user can re-run.
- **say it needs a human eye**, and why. A criterion like *"il cambio lingua funziona"* or *"la pagina
  è leggibile da telefono"* is not something to claim. Name it and leave it open.

Then say which of the two each criterion was. **A criterion in the second group drops the work to
level 3 or worse** (`contracts.md`, "Intervention levels") — not as a punishment, but because nobody
else can check it.

Never write "lo sviluppo è finito" without that list. The sentence is worth exactly as much as the
output under it.

## 2. Merge this to `main`?

Ask it plainly, once, naming the branch and the target. This is the hinge of the whole step: the
review hangs off the *intention to merge*, which is a moment that exists, rather than off a phase in
`meta.json`, which is a value nobody looks at.

If the answer is no — the work continues, or waits — stop here. Nothing below runs.

## 3. Run the full review?

Say what it costs and what it looks at: three axes on the diff between the branch and the fixed point
(`spec-review`), a few thousand tokens, no changes to the code. Then ask.

If the answer is no, record that in the PR or the history — *"review skipped, by the user, on <sha>"* —
so the next session knows the diff was never read rather than read and found clean. **An unrun review
and a clean review must never look the same.**

## 4. Run it, and report three columns

`spec-review` spawns one sub-agent per axis, in parallel, and reports under `## Spec`, `## Standards`
and `## Risk` without merging them. Close with the **level**.

The level is mechanical (`contracts.md`): command-verified criteria plus zero findings is 1; mechanical
findings already fixed is 2; anything needing a decision is 3; a diff that exceeds its spec is 4. It is
not a feeling about the diff.

## 5. Act on the level, and only on the level

- **Level 1** — merge, then say what was merged and link the output that justified it.
- **Level 2** — list the findings and the fixes already applied, then merge unless the user objects.
- **Level 3** — ask the specific questions, one per finding, and **wait**. Each answer is either a fix
  or an acceptance written into the PR. An accepted trade that is not written down is not accepted;
  it is forgotten.
- **Level 4** — stop and explain. The diff and the spec disagree, and that is the user's to settle:
  change the PRD through `prd-from-idea/references/scope-check.md`, or remove the code.

## After the merge

`set-phase feature_complete` when the planned work is done — then `app-verification`, the five gates,
deploy. The level is recorded in `meta.json#spec_review.level`; it never bumps `phase` and never
blocks a gate.

## Two things this step must not become

**A checklist the agent ticks for itself.** Every question above produces either shown output or an
open item. If a run of this step produces neither, it did not happen.

**A wall.** It asks four questions at the end of a feature, not during it. If it ever fires more often
than that — on every commit, on every push — it will be switched off, and the gate layers that depend
on nobody switching off the hooks go with it. The same mistake cost a whole day on 2026-10-20: a check
that asked on one command in five, built by the person who had written the warning about walls two
sections above it in the same file.
