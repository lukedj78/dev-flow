# Before you build — the inventory step

The step that comes before a PRD, before a module and before a new skill: **does this already
exist?** It is the cheapest work in the flow and the one most often skipped, because the answer
feels obvious and is not.

**"We already have it" is the best outcome, and the most frequent.** On a machine that has been used
for a while there are dozens of installed skills, scripts written in March and forgotten,
subscriptions that already do the thing behind a menu nobody opened. The second-best outcome is a
live open-source piece to adapt. A new subscription is the last option.

The method is adapted from `piano` (Martes AI) — see §*Provenance* at the end for what we took,
what we left and why it is rewritten here rather than installed.

This is not theory. Measured on this setup on 2026-09-30: two of shadcn's skills had been installed
globally since March and June, months stale, and nobody knew; a resource analysed in September had
never been recorded; nine abandoned worktrees held 18 GB and 160 KB of uncommitted work nobody
remembered writing. Every one of those is the same failure — it existed and nobody looked.

## Where to look, in order. Do not skip one.

Keep a note of what you searched and where: it goes into the PRD or the plan, including the channels
that gave nothing, so that **"I found nothing" is never confused with "I could not look"**.

### 1. In the house

```bash
# installed skills — search the description, not just the name
grep -il '<word>' ~/.claude/skills/*/SKILL.md .claude/skills/*/SKILL.md 2>/dev/null
grep -Ril --include=SKILL.md '<word>' ~/.claude/plugins/ 2>/dev/null   # -R: those are symlinks
# commands, hooks, settings
ls ~/.claude/commands/ .claude/commands/ 2>/dev/null
# scripts and projects on disk
grep -ril '<word>' . --include='*.py' --include='*.sh' --include='*.md' 2>/dev/null | head -20
```

Then **our own two indexes**, which exist so this step is not archaeology:

- **`references/resources.md`** — every third-party resource already analysed, with its verdict and
  date. If the answer is there, the work starts at step 5 of `SKILL.md` §*Resources the user hands
  over*, not at zero.
- **the project's `.workflow/`** — `meta.json#stack` says what is already wired, `history` says what
  was tried, `tasks.md` and `PRD.md` say what was decided and what was deliberately left out.

Search with two or three different words for the same idea (thumbnail, cover, preview). One term
finds half the things.

### 2. In what is already paid for

Ask which tools are already paid for and connected, and for each one ask whether it does this
already. A CRM has workflows, an ERP has automations, the mail has rules and scheduling, Linear has
cycles and templates, Vercel has cron. **This is the most boring step and the one most often
skipped. It is also the one that saves the most money.**

### 3. In the Claude ecosystem

Before building a skill, an MCP server or a mod: the installed plugins, the MCP registry, and
GitHub. A public skill is **read and adapted, not installed blind** — and if it is to be installed,
it goes through `registry-intake skill-review` first, with the user running the install.

### 4. Outside

`WebSearch` and `WebFetch` cover this, plus `gh` for code:

```bash
gh search repos "<topic in english>" --sort stars --limit 10 --stars '>=20' \
  --json fullName,description,stargazersCount,pushedAt,license,url
```

In this order, each for a reason:

1. **GitHub**, because code is the strongest evidence that a thing can be done. For each promising
   repo read the README and the structure, and look at **licence, last push and open issues**. Read
   it; do not clone it and do not run it — adoption, if any, is a step in the plan.
2. **Reddit**, because it is where people say what did not work. The post tells the success story,
   the comments tell the rest: open the thread, never stop at the title.
3. **X**, because it is where builders show last week's work. On these topics an eighteen-month-old
   post is prehistory.
4. **The web**, for official documentation: what the tool actually does and with which limits.

**Queries in English and generic** — the kind of problem, never the case. **No client names, no
people's names and no internal numbers in a search**: those leave the machine. Add an Italian query
when the subject is Italian (PA, fatturazione, normativa).

Public endpoints that need no API key, when a thread or a paper has to be read whole rather than
searched: `api.pullpush.io` (Reddit archive), `api.fxtwitter.com` (X), `hn.algolia.com/api/v1/search`
(Hacker News), `api.openalex.org` (papers). `r.jina.ai/<url>` renders a page as clean markdown —
**but it is a third party, so never a client's internal URL.**

**If the reading passes ten pages, delegate this step to a subagent** with the queries already
written. Whole threads in the main context lower the quality of what comes after.

## Type the evidence

Every result that survives into the PRD or the plan is labelled:

- **code** — a repo that does it, with stars, last push and licence;
- **official source** — documentation that confirms a capability and its limits;
- **experience** — a practitioner saying what worked or did not.

A trick found on Reddit or X enters as **`to be verified`**, not as a fact, until an official source
or our own test confirms it. This is the same rule `compliance-audit` applies to a vendor's claim
about where data lives.

## Close with a verdict, in one line

> **We already have it** → where it is and how to use it. Stop here.
> **It exists outside and adapts** → what, why this one and not the others, what has to change.
> **It exists halfway** → what it covers, what is missing; the missing piece is the work.
> **It does not exist** → build it, with the ideas and the traps found outside.

Then three one-line checks: does it use what we already have? does it add a subscription? does it
touch client or personal data?

**The verdict is written down even when it is "we already have it"** — in six months it saves doing
this search again. A third-party resource gets its row in `resources.md`; a build gets its lines in
the PRD under *what exists already*.

## The two mistakes that cost the most

**Skipping step 1 because "it certainly isn't there".** It is the step that finds the most.

**Stopping at the title.** A thousand-star repo untouched for a year, a Reddit thread whose
top comment dismantles the post: without opening them the verdict is wrong.

---

## Provenance — what we took from `piano`, and what we left

`piano` is a third-party planning skill by Riccardo Belli Contarini (Martes AI), handed over on
2026-10-03 as a zip. Its opening rule is the one above: *"«ce l'abbiamo già» è l'esito migliore e
anche il più frequente."* Reviewed with `registry-intake skill-review`: **one finding, K8** — no
`license:` in the frontmatter and no LICENSE file in the archive.

**Taken, and rewritten here:** the inventory order (house → what is already paid for → the Claude
ecosystem → outside), the evidence typing (*code · official source · experience*) with a Reddit
trick entering as `to be verified`, the one-line verdict, the rule that queries stay in English and
generic with no client name in them, the instruction to delegate the reading to a subagent past ten
pages, and the two mistakes that cost most.

**Left behind, and why:**

- **its stages 1 and 3** — the one-question-at-a-time interview and the written plan — duplicate
  `superpowers:brainstorming` and `prd-from-idea` + `superpowers:writing-plans`, which are already
  wired into `meta.json` and the phase gates;
- **its output location.** It writes `piani/AAAA-MM-GG-piano-{slug}.md`; ours is `.workflow/`. Two
  places for plans is a second source of truth, which we refuse everywhere else;
- **the skill itself is not installed.** It ships with no licence, so its text could not be
  committed into a repo we deliver; and its last section instructs the agent to **rewrite the
  skill's own file** whenever the user corrects a plan, without asking. Under a content hash that
  reports drift at the first correction — an alarm that fires for the wrong reason, which teaches
  people to ignore alarms. Rewritten here, the method lives in git, where a change to a rule shows
  up in a diff.

**Its research toolbox, read line by line** (`piano/scripts/ricerca.py`, 13.8 KB): standard library
only, GET only, no API key, **writes nothing to disk**, and `subprocess` solely to call `gh` with an
argument list. Its channels, which are public facts rather than its code, are the no-key endpoints
listed in step 4 above. Run on 2026-10-03, five of its six answered and PullPush returned 429 — and
the skill handles that correctly, writing an unreachable channel into the plan as *not covered*,
which is the same discipline as `unmeasured` in our own QA evidence.
