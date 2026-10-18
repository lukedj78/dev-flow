---
name: founder-intelligence
description: 'The full check of a commercial idea before dev-flow builds it: research, founder interview, competitors, customer-discovery kit and synthesis of real interviews, business model, MVP boundaries, feasibility and reuse, go-to-market, validation roadmap, in an evidence-tagged `.workflow/founder/founder-playbook.md` the founder approves. The alternative door to dev-flow''s inventory step for a product whose market is not settled; dev-flow asks which door on every new idea. Also invocable later on an existing project. No PRD before approval: `update_meta.py set-phase` refuses it once started. Triggers: "fammi un controllo completo dell''idea", "vale la pena costruirlo?", "is this worth building", "analisi di mercato per la mia idea", "founder playbook", "rivediamo la strategia di prodotto". Not for: the PRD itself (prd-from-idea), technical tasks, refactors, prototypes or internal tools (dev-flow direct), pre-deploy launch checks (launch-audit).'
---

# founder-intelligence — what is worth building, and why

dev-flow decides *how* to build. This skill decides *whether*, and *what first*, for a commercial idea
whose market is not settled. It ends with a **Founder's Playbook** the founder approves; only then does
dev-flow write a PRD. The method is adapted from Anthropic's *The Founder's Playbook* (May 2026): the Idea
stage, plus the scope part of the MVP stage. The goal is **problem-solution fit**, and its main evidence is
conversations with real people. A prototype is a better way to have those conversations, not a substitute.

## When to use it, and when not

The two doors (the user's decision, 2026-10-17):

- **This skill**: a new product to sell, external paying users, an unclear market or competition, a user
  who talks about customers, pricing, a startup. It **replaces** dev-flow's inventory step: the same verdict
  is recorded at stage 10, so the gate is the same on both paths.
- **dev-flow direct**: a prototype, a refactor, an internal tool, a technical task, a product already
  decided. Unchanged: inventory, then `prd-from-idea`.

The user does not have to remember this skill's name: on every new idea dev-flow asks which kind of project
it is, and the answer picks the door. "Fammi un controllo completo dell'idea" or "vale la pena costruirlo?" lead
here directly. **Later invocation**: on a project already past the PRD, run in `existing` mode. The
project's PROJECT.md, PRD.md, tasks and code are the starting context, and the result is `handoff.md`.

## Rules that do not bend

1. **Evidence before opinion.** Every material claim carries a class (`[source]` `[founder]` `[interview]`
   `[estimate]` `[hypothesis]`) and every fact a row in `sources.md`. Rules: `references/evidence.md`.
2. **Never simulate.** No invented interviews, customers, surveys, testimonials, purchases or commitments.
   No quotation or page attributed to a source that was not read. Without primary evidence, say so and
   propose the experiment that would produce it.
3. **Pressure-test, do not confirm.** An AI asked for support finds it. Stage 3 argues against the idea
   before any interview, and every synthesis lists the evidence against as carefully as the evidence for.
4. **Research before questions.** Never ask the founder what research can establish; never ask twice what
   §18 *Questions and decisions* already records.
5. **State the research limits.** Without web search the Playbook says so at the top and every market claim
   is marked preliminary.
6. **Nothing is approved for the founder.** Only their own words approve (`founder.py approve --user-said`).
   In an autonomous run the skill may reach `READY_FOR_FOUNDER_APPROVAL`; it never approves.
7. **A score is not viability.** No numeric rating stands in for evidence.

## How it runs

```bash
F=founder-intelligence/scripts/founder.py
python3 $F start <root> --mode new        # --mode existing on a project past the PRD
python3 $F status <root>                   # labels, open hypotheses, Playbook changed since approval?
```

`start` creates `meta.json#founder` and `.workflow/founder/`: the Playbook (from
`assets/founder-playbook.md`), `sources.md` and `interviews/`. Then the stages, loading one section of
`references/stages.md` at a time:

| # | Stage | # | Stage |
|---|---|---|---|
| 1 | Intake | 8 | Business model and economics |
| 2 | Testable problem hypothesis | 9 | MVP scope and measurement |
| 3 | Devil's advocate | 10 | Feasibility, and what already exists (records the inventory verdict) |
| 4 | Founder interview | 11 | Go-to-market |
| 5 | Market and competitors | 12 | Validation roadmap and risk register |
| 6 | Customer discovery (kit, then synthesis of real notes) | 13 | Synthesis and readiness |
| 7 | Opportunity and positioning | | |

Go back when a finding changes the direction, and redo only the stage it touches. Customer discovery uses
`references/interviews.md`.

**Talking with the founder.** Start from whatever they gave, even three lines. Do the research that needs
no one first. Ask in batches of three or four, saying why a question matters when it is not obvious. Record
each answer and decision in §18 with its date. Present an interim conclusion when it changes the direction:
narrowing, a different segment, a different model, postponing and stopping are legitimate outcomes. When
the founder changes a decision, update only the sections it touches and add a line to the revision log.

**Resuming.** The state lives in files: run `founder.py status`, then read the Playbook's §18 and §16
before asking anything.

## Readiness and approval

At the end of stage 13: `founder.py record <root> --research complete --open H2 H5`. The labels are derived
(contract, `founder` field): `RESEARCH_COMPLETE`, `NEEDS_VALIDATION` (open hypotheses, shown alongside),
`READY_FOR_FOUNDER_APPROVAL`, `APPROVED_FOR_DEVFLOW`, `REVISE_OR_STOP`. Research complete is not market
validation, and approval is not product-market fit: say both when presenting.

Present the conclusions, the strongest evidence, the strongest case against, the open hypotheses, the
recommended next step and the alternatives. Then the founder decides:

```bash
python3 $F approve <root> --user-said "<their words>"                      # full development
python3 $F approve <root> --user-said "<their words>" --experiment-scope "..." \
    --experiment-objective "..." --experiment-constraints "..." --experiment-acceptance "..."   # one experiment only
python3 $F decide  <root> revise|stop --reason "<their reason>"
python3 $F bypass  <root> --reason "<why the direct path after all>"
```

`approve` refuses before `--research complete`, without an inventory verdict, or without the approval
markers in the Playbook. It writes the approval record into the Playbook and hashes the result. **A Playbook
edited after approval needs a new approval**: `dev-flow/scripts/founder_gate.py` compares the hash at the
crossing into `prd_drafted`. A rejected recommendation is recorded with the founder's reason and not pushed
again; offer the alternatives instead.

## The hand-off

- **New project, approved**: `prd-from-idea` reads the Playbook, does not re-ask what it answers, and
  carries the decisions marked *locked* in §18 into PROJECT.md and PRD.md unchanged, with the open
  hypotheses in §Open questions. `approved_experiment` limits the PRD to the experiment.
- **Existing project**: `handoff.md` lists each proposed change to the PRD, scope or metrics, with its
  reason and source. The founder accepts or rejects each in chat; mark them in the file, then `approve`.
  dev-flow applies the accepted ones with `prd-from-idea` and `prd-to-tasks`.
- **A later contradiction**: a downstream skill that finds a constraint breaking a locked decision flags it
  and offers to come back here; it does not change the decision silently (`dev-flow/references/policies.md`).

## Contract

Writes `meta.json#founder` (only through `founder.py`), `.workflow/founder/` and, at stage 10,
`meta.json#inventory` through `dev-flow/scripts/inventory.py record`. Never bumps `phase`. Reads
`meta.json`, PROJECT.md, PRD.md and tasks.md. Shapes: `references/contracts.md`, `founder` field.
