# The scope check — before a new request becomes work

A request the PRD does not contain can arrive in several ways: a feature asked in chat, a story added in revise
mode, a task added to `tasks.md`, a `scope_creep` finding from `spec-review`, or an issue created mid-sprint in
Linear. Whichever way it comes, it passes this check before anyone builds it. The point is not to say no. It is that
"the code is cheap" is not a reason by itself, the same rule `founder-intelligence` already applies at stage 9.

## Four questions, one line each

1. **Is it already in the PRD?** If it is in a story, an acceptance criterion or a task, there is nothing to decide:
   build it.
2. **Does it contradict a Non-goal, or the line "Not before launch, whatever the evidence"?** If so, propose
   **reject**, unless the user changes that line on purpose.
3. **Does it meet the evidence in `## Scope rules`?** Say what evidence exists and where it comes from: an
   interview, a metric, a blocked story.
4. **What does it displace?** Name the story or task that slips to make room for it.

## Four outcomes: you propose one, the user decides

| Outcome | What happens |
|---|---|
| **add** | It becomes a story or an acceptance criterion in the PRD, then `prd-to-tasks` runs in revise mode. |
| **defer** | It goes to Post-MVP, together with the evidence it is missing. |
| **reject** | It goes to Non-goals, with the reason. |
| **experiment** | It becomes a bounded trial with scope, objective, constraints and acceptance, the same shape as `founder-intelligence`'s `approved_experiment`. |

**"Do it anyway."** If the user overrides the check, the outcome is **add**, with the user's reason recorded word
for word. The check never becomes an obstacle.

## Record it, once

```bash
python3 <skills>/prd-from-idea/scripts/scope.py record <root> --request "export to CSV" --decision defer \
  --reason "one request; the rule asks for three test users" --by user
python3 <skills>/dev-flow/scripts/update_meta.py <root> append-history --skill prd-from-idea \
  --inputs '{"scope_change": "export to CSV"}' --outputs '["PRD.md"]'
```

`record` adds one row to `## Scope changes` at the end of the PRD, creating the section the first time. It escapes
`|` and folds newlines, so the table holds. That row is the only place the decision is written. There is no
`meta.json` field, so there is no second register to fall out of step.

`scope.py check <root>` reports a PRD whose `## Scope rules` is missing or still has a line to fill. `show_state.py`
reports the same as a note. Neither blocks anything.

## Descope: taking something out

- The story moves to Post-MVP, or to Non-goals, with a row in `## Scope changes` (decision **defer** or
  **reject**).
- Its tasks in `tasks.md` stay, struck through: `~~…~~ cut <date>: <reason>`. Nobody loses track of what was
  planned.
- Its Linear issues go back to the backlog with the reason in a comment (`linear-scrum`, Sync mode).

## Founder path

The rules come from Playbook §12, copied without changes. A request that touches a decision the Playbook locks in
§18 (segment, MVP scope and exclusions, metrics, constraints) does not go through this check: it goes back to
`founder-intelligence` (`dev-flow/references/policies.md`), because a revision needs a new approval from the
founder.
