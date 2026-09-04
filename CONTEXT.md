# CONTEXT — the language of dev-flow

The suite is 46 skills and ~260 markdown files written over months. Words drift. This is the **ubiquitous language**: use these terms exactly, and avoid the listed alternatives, so a phrase means the same thing in every skill.

Each entry gives the meaning, then `_Avoid_:` — wordings that are ambiguous or already mean something else here.

---

## The unit of work

**Skill**
One directory at the repo root containing a `SKILL.md`. The thing a coding agent loads. There are 46.
_Avoid_: command, plugin (a **plugin** is the packaging of all 46 — see below), prompt, agent.

**SKILL.md**
The skill itself: YAML frontmatter (`name`, `description`) plus the instructions. The `description` is what makes the skill trigger, so it carries the `Triggers:` and `Not for:` markers.
_Avoid_: manifest (that's `plugin.json`), spec, prompt file.

**Reference**
A file under a skill's `references/`. Either a **how-to** (doc-grounded instructions for a library — the thing rule zero demands) or a **recipe** (an audit recipe, a mapping, a checklist).
_Avoid_: doc, guide, documentation — those read as "the README". A citation to an upstream page is a **source**, not a reference.

**Script**
An executable under a skill's `scripts/` (Python or shell) plus its test. Scripts produce **signals**, never verdicts — a scan result must be verified in code before it is reported.
_Avoid_: tool (means something else to an agent runtime), checker.

**Bundle**
A generated `dist/<skill>.skill` archive. Build output, never edited by hand.
_Avoid_: package, release.

---

## Classification

**Family**
One of exactly six: `core` · `web` · `agent` · `mobile` · `monorepo` · `refactor`. Defined **once**, in the `TAXONOMY` map in `scripts/build_skills_registry.py`, and published in `skills.json`. An unclassified skill is a build error.
_Avoid_: category, group, bucket, stack (a **stack** is the project's technology choices, see below). Never restate family counts anywhere without regenerating `skills.json`.

**Role**
What a skill *does*: `orchestrator` (only `dev-flow`) · `discovery` (turns input into artefacts: PRD, DESIGN.md) · `operative` (changes the codebase) · `knowledge` (teaches a discipline, changes little).
_Avoid_: type, kind.

**Discipline skill**
A horizontal, trigger-driven skill that enforces a way of working rather than advancing the build: `forms`, `data-fetching`, `state-discipline`, `transitions`. They never bump `phase`.
_Avoid_: rule skill, lint skill, convention skill.

**Gate**
A skill dev-flow proposes before deploying, which reports and never blocks: `compliance-audit` (legal risk) and `vercel-doctor` (cost/perf risk).
_Avoid_: check, validation, guard.

---

## The contract

**Contract**
`dev-flow/references/contracts.md` — the canonical document defining `.workflow/`, the `meta.json` schema, the phase enum, rule zero and the golden rules. Physically copied ("vendored") into every skill's `references/`; the copies must stay byte-identical.
_Avoid_: spec, schema, protocol (the *schema* is one section of the contract).

**`.workflow/`**
The per-project state folder: `meta.json` plus `PROJECT.md` / `PRD.md` / `tasks.md` / `DESIGN.md` / `screenshots/`. Lives in the **user's project**, never in this repo.
_Avoid_: workspace, config folder, state dir.

**Phase**
The project's position in the pipeline, one value of the canonical enum (`empty` → … → `deployed`). Monotonic: a skill never moves it backwards.
_Avoid_: step, stage, status.

**Stack**
The `meta.json#stack` block — the project's technology choices (`framework`, `ui`, `auth`, `db`, `i18n`, `locales`, `maps`, `agent`, …).
_Avoid_: tech, config, setup. Note: **"web stack"/"mobile stack"** as a *family* of skills is a different sense — prefer "the web family".

**Vendored**
A file physically duplicated into a skill so the skill is self-contained when installed alone (only `contracts.md` is vendored). Duplicates are regenerated, never edited in place.
_Avoid_: copied, synced, shared.

---

## Knowledge

**Rule zero / Knowledge principle**
Never invent an API. Ground every claim in official documentation or installed source; ship the *how*, not just the name; mark moving surfaces `[VERIFY]`; re-verify periodically.
_Avoid_: guideline, best practice — it is a rule.

**Golden rule**
The two project-level non-negotiables: ① code is written in English; ② every frontend ships i18n from day one (minimum `en` + `it`).
_Avoid_: convention, preference.

**`[VERIFY]`**
An inline marker meaning "confirm this identifier against the installed version before relying on it". Used for beta or fast-moving upstreams.
_Avoid_: TODO, FIXME, TBD.
⚠️ It does two jobs, and conflating them is what lets a marker rot: **an open question** ("I don't know") versus **a standing disclaimer** ("this will age"). The second multiplies without bound — every version number moves — and if everything is marked, nothing is. Prefer converting a disclaimer into a **stamp**: *verified against `pkg@x.y.z` on `YYYY-MM-DD`; re-check on a major*. Same caution, plus the baseline the next pass starts from.

**Maintenance rule — a skill edit is not done until it is installed**
_(Not a third golden rule: ① and ② above bind the projects dev-flow builds. This one binds this repo.)_
Editing a skill in this repo changes nothing for the agent: it loads `~/.claude/skills`. So every skill change ends with **`./install.sh`**, and lint **check 12** exists to make the gap visible when it doesn't (it reports, never fails — a divergence is a fact about your machine, not about the commit).
⚠️ **Running `skill-doctor` right after an edit tells you nothing**, and it is worth knowing why rather than doing it out of habit: it grades **past conversations**. Re-run immediately after a change and every number is identical, because the sessions it reads are the ones that used the *old* text. The cadence that works is **install on every edit, `skill-doctor` periodically** — once the edited skills have actually been used enough to have a history worth grading.
_Avoid_: "run the doctor after each change" — it is the linter's job to judge an edit, and the doctor's job to judge a habit.

**Verification pass** vs **skill-doctor**
Two different axes of decay, and neither sees the other. A **verification pass** asks *is this still true?* and answers it against the upstream — `npm pack` and read the `.d.ts`, `curl` every cited URL, diff the shipped docs. **`skill-doctor`** (Warp, MIT — install it, this repo does not ship a copy) asks *is this working?* and answers it against **local agent conversation transcripts**, scoring efficiency and code quality and drafting the edits the failed conversations justify. A skill can be perfectly accurate and never fire; a skill can fire reliably and be wrong.
_Avoid_: calling either one "an audit" — `compliance-audit` is a different thing entirely.

**Watch pass**
A dated sweep of an upstream changelog, logged in `docs/vercel-changelog-watch.md` with each entry classified applied / watch / not relevant.
_Avoid_: update, sync, review.

---

## ⚠️ "Registry" — three different things

This word is overloaded. Always qualify it:

| Say | Meaning |
|---|---|
| **the skills registry** | `skills.json`, generated from the taxonomy |
| **a shadcn registry** | a component source installed via the shadcn CLI (`@coss/*`, `@mapcn/*`, `@heroicons-animated/*`) |
| **the eve registry** | eve's integrations catalogue (`eve add`, `eve registry search`) |

_Avoid_: bare "the registry".

## ⚠️ "Skill" — ours vs eve's

An **eve agent skill** is a markdown file under `agent/skills/` inside a *user's* eve agent — procedural knowledge the model loads at runtime with `load_skill`. It is **not** one of our 46 skills. Write "an eve agent skill" in full whenever both could be meant.

## ⚠️ `design.md` — two unrelated artefacts

| Say | Meaning |
|---|---|
| **a DESIGN.md** | the Google design.md spec: design tokens in YAML frontmatter, prose body. `.workflow/DESIGN.md` in the dev-flow contract; what `design-md-to-app` consumes and `figma-to-design-md` / `image-to-design-md` produce. |
| **a design skill at a URL** | an Agent Skill whose subject is brand judgement — frontmatter of `name` + `description`, guidance in prose, **no tokens**. `https://vercel.com/design.md` is the reference example. |

They share a filename and nothing else. `parse_design_md.py` rejects the second shape by frontmatter
signature, because it used to accept it silently and every token in the resulting app was invented.
_Avoid_: bare "design.md" when either could be meant.

## ⚠️ "Module"

A **module** is a `module-add` capability wired into a scaffolded app (`auth`, `db`, `payments`, `email`, `storage`, `deploy`, `motion`, `voice`, `realtime`, `ci`, `test`). Not an npm module, not an ES module.
_Avoid_: integration, package, feature.

---

## Write decisions the reader can observe

A line in a skill earns its place when a reader can check whether it was followed. Prefer the
observable form to the evaluative one:

| Instead of | Write |
|---|---|
| "tables should feel less cramped" | "evidence tables use the full available width" |
| "keep the hierarchy clean" | "one `h1`; headings in order; no size skips" |
| "use realistic placeholder data" | the banned list and the replacement list — as `anti-slop-fallbacks.md` does |

Two reasons this is not a style preference. An agent cannot act on "clean" and will substitute its
own default, which is exactly the default the line was written to prevent. And an unobservable line
cannot be checked by a linter, a reviewer or an eval — it can only be argued about.

The test before shipping a line: **what would I look at to decide whether this was followed?** If the
answer is "how it feels", rewrite it or delete it.

## Distribution

**Plugin**
The whole suite packaged for Claude Code (`.claude-plugin/plugin.json`), installed from the marketplace. Singular — there is one plugin containing 46 skills.
_Avoid_: extension, bundle, pack.

**Marketplace**
The catalogue entry (`.claude-plugin/marketplace.json`) that makes this repo installable with `/plugin marketplace add`.
_Avoid_: store, repo.

## ⚠️ The vendored contract is duplication **on purpose**

`references/contracts.md` is **byte-identical in 33 skills** — roughly 1 MB of the same file. It looks
like waste, and sooner or later someone will try to "fix" it with a symlink, a single shared copy, or a
build step that injects it.

**Don't.** A skill has to work when it is installed *alone* — as `dist/<name>.skill`, or by copying one
folder into `~/.claude/skills/`. There is no repo around it then, and nothing to resolve a symlink
against. The duplication is what makes single-skill installs possible; removing it trades a megabyte for
a broken install path.

What keeps it honest is the invariant, not the count: **every copy must be byte-identical to
`dev-flow/references/contracts.md`**, which is canonical. Change it there, re-vendor to all of them, and
verify one hash comes back:

```bash
for f in */references/contracts.md; do md5 -q "$f"; done | sort -u | wc -l   # must print 1
```

The **eleven skills without one are also deliberate**: the ten mobile `knowledge` skills teach a stack
and never touch `.workflow/`, and `eve-registry-porting` cites it zero times. Carrying a contract they
never read would be the real noise. The rule is *"vendor it where the skill reads or writes
`.workflow/`"* — not *"vendor it everywhere"*.

---

Adding a term that could be read two ways? Add it here in the same commit.
