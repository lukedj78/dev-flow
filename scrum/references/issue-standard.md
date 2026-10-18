# The issue standard — every tracker


**The rule** (the user's, 2026-10-14): an issue is written with the precision of smart-travel's best ones (`lukedj78/smart-travel` #194, #210), never left as the one-line stub the push creates. A stub forces whoever picks the issue up to reopen the PRD, the research and the tasks to find out what was decided. A full body carries the decisions with it.

**The body, in the project's language, these headings in this order:**
1. One intro line: sprint (milestone), priority, epic and user story, and why the task matters or what it blocks.
2. `**Cosa fare:**` (*What to do*): one to three concrete sentences, then `Riferimento:` with the link to the task line in `tasks.md`.
3. `## Cosa è stato deciso` (*What was decided*): six to ten bullets, each `**topic** — the concrete decision ([file#Ln](link))`, drawn from the story and its acceptance, the technical constraints, non-goals, the *what exists already* rows, open questions and the research notes. **Every link is pinned to a commit SHA** (`/blob/<sha>/…#L<n>`), so a later edit does not move it, and **every line number is checked with `grep -n`**. A recommendation that no source made is labelled *Proposta* (proposal), never presented as decided.
4. `## Criteri di accettazione` (*Acceptance criteria*): a `- [ ]` checklist, testable.
5. `## File probabilmente coinvolti` (*Files likely touched*) and `## Dipendenze` (*Dependencies*): `Prima:` / `Dopo:` (before / after), naming the other tasks by their exact titles.
6. `## Schermate coinvolte` (*Screens involved*): the screens and the canvas area. Their IDs are linked after `wireframe-canvas` posts the PNGs.
7. `## Fatto per la verifica` (*Done for verification*): a checklist covering criteria and tests green, `spec-review` on the diff, and for UI also «canvas board approved before the code», i18n, primitives only. For agent tasks: eval green, identity from the session. For skill-owned tasks: which skill to invoke.
8. Last line: estimate and sources.

**How:** create the issues first (Setup: `github_sync.py` on GitHub, the MCP on Linear and Jira), then write one body file per task under `.workflow/issue-bodies/<slug>.md` and apply each with the tracker's edit — `gh issue edit <n> --body-file <file>`, Linear `save_issue` description, Jira `editJiraIssue` description — about 1 s apart.
- Write one sample first and get the user's yes on it.
- For more than about 20 issues, split the bodies across parallel sub-agents, each given the approved sample, the same sources and a disjoint range of an index (`_index.json`: title, slug, `tasks.md` line, sprint, priority, story and its PRD line).
- Check the result before posting: every heading present, links pinned, line numbers real.

On GitHub the intro line names the milestone; on Linear the cycle; on Jira the sprint. The sprint rules per tracker
are in `github.md`, `linear.md` and `jira.md`.
