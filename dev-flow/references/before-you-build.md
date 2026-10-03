# Before you build — the inventory step

The step that comes before a PRD, before a module and before a new skill: **does this already
exist?** It is the cheapest work in the flow and the one most often skipped, because the answer
feels obvious and is not.

**"We already have it" is the best outcome, and the most frequent.** On a machine that has been used
for a while there are dozens of installed skills, scripts written in March and forgotten,
subscriptions that already do the thing behind a menu nobody opened. The second-best outcome is a
live open-source piece to adapt. A new subscription is the last option.

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

### 2. In what the tools already do, paid or free

Ask which tools are already connected, and for each one ask whether it does this already. A CRM has
workflows, an ERP has automations, the mail has rules and scheduling, Linear has cycles and
templates, Vercel has cron, Neon has branching, Resend takes inbound mail. **This is the most boring
step and the one most often skipped. It is also the one that saves the most work.**

**On free tiers the second half of the question is the one that bites: where does the plan stop?**
A capability included up to a ceiling is still included — until the ceiling, which is where a
project quietly starts building what it already had. Write the ceiling into the plan beside the
capability (`Vercel cron: yes, 2 jobs on Hobby`), because that number, not the feature, is what the
decision rests on.

And when a plan's terms turn on **commercial use**, that is a condition, not a footnote: it holds
only while nothing ships commercially, and the day one does it is a licensing decision taken before
shipping. `references/resources.md` lists the rows that change.

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

   **Two things about this search that cost us an hour to learn.** Measured on 2026-10-03, looking
   for a gauge component:

   - **The star threshold hides exactly what you are looking for when the thing is new.** At
     `--min-stars 50`, `"react gauge component"` returned one repo (`antoniolago/react-gauge-component`,
     201 stars, MIT, alive) — a good find. At `--min-stars 0`, a bare `"gauge"` returned .NET and
     Android charting libraries with 5,000 stars and a test runner that happens to be called Gauge.
     High hides the new, low drowns it in the old. So run it **twice**: once with a threshold for the
     established answer, once with the specific words and no threshold for the recent one, and read
     the dates rather than the counts.
   - **`gh search repos` reads names and descriptions, not code and not sites.** `gauge-ui`, the
     registry we had just reviewed and recorded, does not come back for `"gauge ui shadcn"`, for
     `"shadcn gauge"`, or for its own name: six days old, three stars. **GitHub is the wrong channel
     for a shadcn registry** — those are found through their site and their `registry.json`
     (`research.py read <url>`), through a catalogue, or because somebody handed one over. When the
     thing you want is a registry item, say so in the plan instead of concluding it does not exist.
2. **Reddit**, because it is where people say what did not work. The post tells the success story,
   the comments tell the rest: open the thread, never stop at the title.
3. **X**, because it is where builders show last week's work. On these topics an eighteen-month-old
   post is prehistory.
4. **The web**, for official documentation: what the tool actually does and with which limits.

**Queries in English and generic** — the kind of problem, never the case. **No client names, no
people's names and no internal numbers in a search**: those leave the machine. Add an Italian query
when the subject is Italian (PA, fatturazione, normativa).

For what a `WebSearch` does badly — a whole Reddit thread, an X post, a paper, a page as clean
markdown — **`scripts/research.py`** is ours, stdlib only and no API key:

```bash
S=dev-flow/scripts/research.py
python3 $S status                              # which channels answer right now
python3 $S repos  "<topic in english>" --min-stars 20
python3 $S reddit "<problem in english>" [--sub <name>]
python3 $S thread <url>                        # the comments, where the post's story breaks
python3 $S hn     "<topic>" --min-points 50
python3 $S post   <url>                        # one X post, whole
python3 $S read   <url>                        # the page as markdown
python3 $S papers "<topic>"
```

Two of its behaviours are the reason it exists rather than a one-liner. It **never turns "I could
not look" into "there is nothing"**: exit `0` answered, `3` answered and empty, `4` unreachable, and
a `4` is written into the plan as *a channel not covered* — a tool that returns an empty list on a
429 converts ignorance into a fact, which is the same bug as a QA check reporting `pass` when the
decode failed. And `read` renders through `r.jina.ai`, a third party, so it **refuses loopback, the
private IPv4 ranges and the `.local` / `.internal` / `.test` suffixes outright**: a client's internal
host never reaches it, and there is no flag that overrides that.

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
