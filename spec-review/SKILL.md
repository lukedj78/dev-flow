---
name: spec-review
description: 'Review a diff on the two axes a dev-flow project can check that a generic reviewer cannot: the **spec** it was built from (`.workflow/PRD.md` + `tasks.md`) and the **contract** it was built under (golden rules, `meta.json#stack`). Two parallel sub-agents, reported side by side and never merged, with a Fowler smell baseline as the floor. Use when the user says "review this branch", "spec review", "review since <ref>", "does this match the PRD?", "controlla il diff contro la spec", or dev-flow proposes it after a feature lands. Requires `.workflow/`; without one use the built-in `/code-review`. Records `meta.json#spec_review`; no phase bump. Not for: generic review with no spec (built-in `/code-review`), UI quality (`shadscan`), legal (`compliance-audit`), Vercel cost (`vercel-doctor`), or running tests (`write-tests`).'
---

# spec-review — did we build what the PRD asked, the way the contract says?

Two-axis review of the diff between `HEAD` and a fixed point:

- **Spec** — does the change faithfully implement what `.workflow/PRD.md` / `tasks.md` asked for?
- **Standards** — does it obey the contract this project was built under?

Both run as **parallel sub-agents** so neither pollutes the other's context, then this skill reports
them side by side.

> **Credit.** The two-axis structure, the parallel-sub-agent split, the refusal to merge verdicts and
> the Fowler smell baseline are adapted from Matt Pocock's `code-review` skill
> ([mattpocock/skills](https://github.com/mattpocock/skills), MIT) and
> [the essay behind it](https://www.aihero.dev/skills-code-review). What's ours is the half his skill
> has to search for: in a dev-flow project the spec and the standards are **at known paths**.

## Why this is not `/code-review`

Claude Code ships a built-in `/code-review`, and Pocock's own write-up lists the name collision as a
known problem. This skill is deliberately **not** that, in name or in remit:

| | Built-in `/code-review` | `spec-review` |
|---|---|---|
| Reviews | the code, generically | the code **against this project's spec and contract** |
| Knows | the diff | `.workflow/PRD.md`, `tasks.md`, `meta.json#stack`, `#artifacts`, `#history` |
| Answers | "is this good code?" | "is this **the thing we said we'd build**, built **our way**?" |

Run both if you like — they don't overlap. **Without a `.workflow/`, this skill refuses** and points
at the built-in: with no spec and no declared stack, both of its axes are guesswork.

## Workflow

### 1. Pin the fixed point — and fail here, not inside a sub-agent

Whatever the user names is the fixed point (a SHA, `main`, a tag, `HEAD~5`). If they didn't say, ask.

```bash
git rev-parse <fixed-point>                    # must resolve
git diff <fixed-point>...HEAD --stat           # three-dot: compare against the merge-base
git log  <fixed-point>..HEAD --oneline         # the commits under review
```

**A bad ref or an empty diff must fail right here** — discovering it inside two parallel sub-agents
wastes both. Three dots, not two: you want the merge-base, not everything that landed on `main`
meanwhile. And **the diff excludes uncommitted work**, so commit (or stash) before asking for a review,
or the change you most want looked at is the one nobody sees.

### 2. Resolve the Spec axis — deterministic, not a search

This is where the contract earns its keep. In order:

1. **`.workflow/tasks.md`** — the tasks this branch claims to close. Match by branch name, by the task
   ids in the commit messages, or ask which ones are in scope.
2. **`.workflow/PRD.md`** — the requirement behind those tasks; the tasks are the decomposition, the PRD
   is the intent. A diff can satisfy every task and still miss what the PRD asked for.
3. **`meta.json#artifacts`** — what was produced and by which skill, so the reviewer knows whether a file
   is hand-written or generated (holding generated scaffolding to hand-written standards is noise).
4. **`linear-scrum` projects** — the issue in Linear is the live spec; `meta.json#linear` has the link.

If `.workflow/PRD.md` is absent (a project adopted mid-flight), say so and run the Spec axis against
`tasks.md` alone, or skip it and report that the axis was not run — **never invent the spec from the
diff**. A review that infers the requirements from the code it is reviewing always passes.

### 3. Resolve the Standards axis — the contract first, Fowler as the floor

A dev-flow project's documented standards are not a `CONTRIBUTING.md` someone may have written. They are:

| Source | What it binds |
|---|---|
| **Golden rules** (`references/contracts.md`) | ① identifiers, constants and comments in **English**; ② **i18n from day one** — no hardcoded user-facing copy, `en` + `it` minimum |
| **`meta.json#stack`** | the declared choices: `forms` (every form through `lib/forms/`), `ui` / `ui_base`, `i18n`, `db`, `deploy` — a diff that reaches for a different library than the one declared is a finding |
| **The discipline skills** | `state-discipline` (`useState` is the last resort), `data-fetching` (Server Components first; Server Actions never for reads), `transitions` (every transition ships a `prefers-reduced-motion` path), `composition-patterns-guide` (no boolean-prop pile-ups) |
| **The repo's own docs** | `CONTRIBUTING.md`, `CODING_STANDARDS.md`, `AGENTS.md`/`CLAUDE.md` if present — **these override everything above where they conflict**, including this skill |
| **Fowler baseline** | the floor, below — applies even when nothing above says anything |

**Skip anything tooling already enforces.** `biome`/`eslint`, `tsc`, and the three gates
(`shadscan`, `vercel-doctor`, `compliance-audit`) have their own runs; repeating them here produces a
long report that says nothing new. If the project has a lint gate, a review finding about formatting is
noise.

#### The smell baseline (Fowler, *Refactoring* ch. 3)

Each is a **labelled heuristic** — "possible Feature Envy" — never a hard violation, and **any documented
standard above overrides it**.

- **Mysterious Name** — a name that doesn't reveal what it does or holds. → rename; if no honest name comes, the design is murky.
- **Duplicated Code** — the same logic shape in more than one hunk. → extract, call from both.
- **Feature Envy** — a method reaching into another object's data more than its own. → move it onto the data it envies.
- **Data Clumps** — the same few params always travelling together. → one type, passed once.
- **Primitive Obsession** — a string or number standing in for a domain concept. → give the concept its own small type.
- **Repeated Switches** — the same cascade on the same type recurring. → polymorphism, or one shared map.
- **Shotgun Surgery** — one logical change forcing scattered edits. → gather what changes together.
- **Divergent Change** — one module edited for several unrelated reasons. → split it.
- **Speculative Generality** — abstraction for needs the spec doesn't have. → delete it. (This one pairs with the Spec axis: it is usually scope creep wearing a design hat.)
- **Message Chains** — long `a.b().c().d()` the caller shouldn't depend on. → hide the walk.
- **Middle Man** — a unit that mostly delegates onward. → cut it.
- **Refused Bequest** — a subclass ignoring most of what it inherits. → composition instead.

### 4. Spawn both sub-agents, in parallel, and forbid further delegation

Each gets the diff command, the commit list, its own sources **pasted in full** (a sub-agent has no
access to what you read), and an explicit **"do not spawn further agents"** — Pocock's write-up records
recursive spawning as a real failure mode when the brief doesn't forbid it.

**Spec brief** — *"Report: (a) requirements the spec asked for that are missing or partial; (b) behaviour
in the diff nobody asked for (scope creep); (c) requirements that look implemented but where the
implementation looks wrong. **Quote the PRD or task line for each finding.** Under 400 words."*

**Standards brief** — *"Report, per file/hunk: (a) every place the diff breaks a documented standard —
cite it (which rule, which file); (b) any baseline smell — name it and quote the hunk. Documented
breaches can be hard findings; baseline smells are always judgement calls; a documented standard
overrides the baseline. Skip anything lint/tsc/the gates enforce. Under 400 words."*

### 5. Report side by side — and do not merge

Present under `## Spec` and `## Standards`, verbatim or lightly cleaned. **Never merge or re-rank across
axes.** Close with the count per axis and the worst issue *within each*.

That separation is the whole point: a change can follow every convention and implement the wrong
feature (**Standards pass, Spec fail**), or do exactly what the PRD asked while ignoring the stack the
project declared (**Spec pass, Standards fail**). One combined verdict lets either hide behind the other.

**Findings are hypotheses.** Verify before acting — this whole session's `[VERIFY]` passes exist because
a confident report is not a correct one.

## `meta.json#spec_review` block

```jsonc
"spec_review": {
  "last_run_at": "<ISO>",
  "fixed_point": "main",              // what HEAD was compared against
  "commits": 7,
  "spec_sources": ["tasks.md#T12-T15", "PRD.md#3.2"],
  "spec_findings": { "missing": 1, "scope_creep": 2, "wrong": 0 },
  "standards_findings": { "hard": 1, "judgement": 4 },
  "axes_not_run": []                  // e.g. ["spec"] when there is no PRD — say so, never infer it
}
```

## dev-flow hook

Horizontal capability — run it on any diff. dev-flow proposes it **when a chunk of work lands**
(`page_generated`, `module_added`) rather than only before shipping: a spec finding is cheapest while
the branch is still open. It is *not* a fourth pre-deploy gate — `compliance-audit`, `vercel-doctor` and
`shadscan` read the finished artefact, this reads the **change**. Records `meta.json#spec_review` +
`history`; **never bumps `phase`**; never blocks anything.

## What this skill does NOT do

- **Not generic code review** — no `.workflow/`, no run; use the built-in `/code-review`.
- **Doesn't run tests, lint or typecheck** — it reads their results and skips what they cover.
- **Doesn't fix anything.** It reports. Fixes go to the owning skill (`forms`, `data-fetching`, …).
- **Doesn't merge the two axes**, and doesn't pick a winner between them.

## Reference files

- `references/contracts.md` — the `.workflow/` dev-flow contract (vendored).

## Sources

- <https://www.aihero.dev/skills-code-review> · [mattpocock/skills](https://github.com/mattpocock/skills) (MIT) — the two-axis structure and the smell baseline.
- Fowler, *Refactoring* (2nd ed.), ch. 3 — the smell catalogue.
