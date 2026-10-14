# Provisioning with the Vercel CLI (verified 2026-10-03, CLI 60.1.3)

The user is logged in; check with `vercel whoami`, `vercel teams ls`, `vercel domains ls`. Run every command with `--cwd <project>` or from the project folder: the user's own terminal may start elsewhere ("Your codebase isn't linked").

## Decide before creating
- **Plan.** Vercel's fair-use terms restrict **Hobby to non-commercial personal use** and define commercial as any deployment serving the financial gain of anyone involved, a paid consultant writing the code included. A company tool is arguably commercial. It is the user's call; record it as a known risk to revisit when the prototype becomes real use. Hobby functions run at most 300 s (Pro 800 s).
- **Regions.** The default is **US (`iad1`)** for functions, Blob and Neon. Choose the EU region first and verify after.

## GitHub repository
```bash
gh repo create <owner>/<name> --private --description "…" --source . --remote origin --push
```
Initial commit by file name (never `git add -A`: other files may sit in the tree). **Scan the staged diff for secrets first**: key-looking assignments, `eyJ…`, `sk-`, `re_`, `npg_`, `ghp_`, `xox`; and check `git ls-files` shows no `.env`, `.env.local` or `.vercel`. `.gitignore` needs `.env*` **and** `!.env.example`, or the example is ignored. Optional, when the tracker is GitHub: `python3 scripts/make_issues.py --repo <owner>/<name> --tasks .workflow/tasks.md --map .workflow/github-issues.json` (one issue per task, resumable, 2 s apart, labels by area and type), then verify the totals from GitHub itself.

Two things to know about `make_issues.py`. ① **It sets no milestones.** Assign them afterwards from each epic's `Milestone:` line in `tasks.md`: create the milestone, then `gh issue edit <n> --milestone "<title>"` per issue. ② **A comma breaks a label**: GitHub answers HTTP 422 to a label name containing `,`, so `area_label` strips commas from the epic name (`Epic: Search, filters` → `area: search filters`).

## Issues written to the standard

**The rule** (the user's, 2026-10-14): an issue is written with the precision of smart-travel's best ones (`lukedj78/smart-travel` #194, #210), never left as the one-line stub `make_issues.py` creates. A stub forces whoever picks the issue up to reopen the PRD, the research and the tasks to find out what was decided. A full body carries the decisions with it.

**The body, in the project's language, these headings in this order:**
1. One intro line: sprint (milestone), priority, epic and user story, and why the task matters or what it blocks.
2. `**Cosa fare:**` (*What to do*): one to three concrete sentences, then `Riferimento:` with the link to the task line in `tasks.md`.
3. `## Cosa è stato deciso` (*What was decided*): six to ten bullets, each `**topic** — the concrete decision ([file#Ln](link))`, drawn from the story and its acceptance, the technical constraints, non-goals, the *what exists already* rows, open questions and the research notes. **Every link is pinned to a commit SHA** (`/blob/<sha>/…#L<n>`), so a later edit does not move it, and **every line number is checked with `grep -n`**. A recommendation that no source made is labelled *Proposta* (proposal), never presented as decided.
4. `## Criteri di accettazione` (*Acceptance criteria*): a `- [ ]` checklist, testable.
5. `## File probabilmente coinvolti` (*Files likely touched*) and `## Dipendenze` (*Dependencies*): `Prima:` / `Dopo:` (before / after), naming the other tasks by their exact titles.
6. `## Schermate coinvolte` (*Screens involved*): the screens and the canvas area. Their IDs are linked after `wireframe-canvas` posts the PNGs.
7. `## Fatto per la verifica` (*Done for verification*): a checklist covering criteria and tests green, `spec-review` on the diff, and for UI also «canvas board approved before the code», i18n, primitives only. For agent tasks: eval green, identity from the session. For skill-owned tasks: which skill to invoke.
8. Last line: estimate and sources.

**How:** create the issues with `make_issues.py` (titles, labels, map), then write one body file per task under `.workflow/issue-bodies/<slug>.md` and apply them with `gh issue edit <n> --body-file <file>`, 1 s apart.
- Write one sample first and get the user's yes on it.
- For more than about 20 issues, split the bodies across parallel sub-agents, each given the approved sample, the same sources and a disjoint range of an index (`_index.json`: title, slug, `tasks.md` line, sprint, priority, story and its PRD line).
- Check the result before posting: every heading present, links pinned, line numbers real.

**Scrum on GitHub: one milestone per sprint.** Size the sprints from `tasks.md` estimates and the capacity the user gives (hours per sprint, sprint length):
- Pack in dependency order: setup and domain first, then the epics. Start a new sprint at the boundary between priority bands, so the first release closes on a sprint boundary.
- Name each milestone by its goal (`Sprint 1 — Fondamenta`, not `Sprint 1`).
- In the description: the sprint goal in a sentence, dates, load against capacity, priorities, stories, ceremonies, Definition of Done.
- Set `due_on` to the sprint's last day.
- Add `priority: P1|P2|P3` labels.
- Assign every issue (`gh issue edit <n> --milestone "<title>" --add-label "priority: Pn"`).
- Write the plan to `.workflow/sprints.md`.

Spare capacity in the last sprint of a release is kept for testing and review, not filled.

## Project
```bash
vercel project add <name>
vercel link --yes --project <name>      # writes .vercel/ and .env.local (OIDC token); adds both to .gitignore
```
Function region: `PATCH /v9/projects/<id>` with `{"resourceConfig":{"functionDefaultRegions":["fra1"]}}` via `vercel api … --input file`, then **read it back with `vercel api /v9/projects/<id>`** (`vercel project inspect` keeps showing `iad1`).
**Do not connect Git yet** (`vercel git connect`): the first push would publish the repo's documents at a public `*.vercel.app` URL. Connect when the app exists. Do not assign the custom domain before the first deploy.

## Postgres: Neon through the marketplace
```bash
vercel integration add neon --name <db> -m region=fra1 -m auth=false
```
- Metadata keys are not in `--help`. They are in `vercel api /v1/integrations/configuration/<icfg_id>/products` (`metadataSchema`). For Neon: `region` (Vercel region codes) and `auth` (**Neon Auth is on by default**: turn it off if the stack uses its own auth).
- **The region cannot be changed afterwards.** Omitting `-m region=` put the first database in Virginia. Fix: `vercel integration resource remove <db> --disconnect-all --yes`, recreate, and **verify** from `PGHOST` in `.env.local` (`…eu-central-1.aws.neon.tech`). Never print credentials.
- After removing a resource, delete its leftover variables from `.env.local`.
- The install adds `neondatabase/agent-skills` into the repo (`.agents/`, `.claude/skills/`, `skills-lock.json`), **every time**. Move them out of the repo and decide (see SKILL.md rule 3). Free plan: 1 GB per project; vector embeddings can fill it.
- A first-time marketplace integration returns `userActionRequired` with a `verification_uri`: a human accepts the terms in the browser. Neon needed no step because the team already had it.

## Files: Blob
```bash
vercel blob create-store <name> --access private --region fra1 --yes
```
Without `--yes` the CLI returns `confirmation_required` as JSON. It links the store and writes `BLOB_READ_WRITE_TOKEN`.

## Email: Resend
- **The marketplace route collided with an account the user already had** (their zone already held Resend records for another subdomain) and stalled in the browser. Prefer the existing account.
- The user creates a **Full access** key at resend.com and stores it themselves: `vercel env add RESEND_API_KEY --cwd <project>` (value hidden; choose all environments). Never in chat.
- Pull it (`vercel env pull .env.local --yes`) and call the API from a script that never prints it: `POST /domains {"name":"app.example.com","region":"eu-west-1"}` → records. Free plan: 3 domains.
- Records Resend returned for a sub-domain `app.example.com` of a zone `example.com`: TXT `resend._domainkey.app` (DKIM), MX `send.app` priority 10, TXT `send.app` (SPF), CNAME `rsend.app`. All on technical names, so they do not touch the site. Add each with `vercel dns add <zone> <name> <TYPE> <value> [priority]`, from a script (TXT values contain spaces and `=`). Works because the zone uses Vercel's nameservers.
- Verify: `POST /domains/<id>/verify`, then poll `GET /domains/<id>`; it took about 90 s.
- **Narrow the key**: `POST /api-keys {"name":"…-send","permission":"sending_access","domain_id":"<id>"}`; test it with a send to `delivered@resend.dev` (Resend's sink, never delivered to a real inbox); replace the variable in every environment (value on stdin, `--sensitive --force`); only then `DELETE /api-keys/<old id>`.
- Remove a half-installed marketplace integration with `vercel integration remove resend --yes` once it has no resources.

## Variables
```bash
printf '%s\n' "$VALUE" | vercel env add NAME production --sensitive --force   # same for preview, development
vercel env pull .env.local --yes
```
Generate secrets locally (`secrets.token_bytes(32)`) and pass them on stdin, never in arguments or chat. Config (non-secret) values use `--no-sensitive`. App URLs: production at the real domain, development at `http://localhost:3000`, preview left to Vercel.

## Record it
`data_residency.py add` one row per service (region, transfer basis, DPA "to verify"); `render`. Services without a known EU region are flagged, not blocked. Write `docs/infrastructure.md` (what, where, how, open risks, lessons): names and ids only, no values.
