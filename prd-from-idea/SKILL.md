---
name: prd-from-idea
description: 'Turn a raw product idea — a paragraph, a Notion dump, a half-formed thought, or a brief that arrived as a **file** (`.docx`, `.pdf`, `.pptx`, `.xlsx`: an RFP, a client deck, a Word spec — converted to Markdown first with `anydoc`) — into a structured PROJECT.md (high-level brief) and PRD.md (product requirements document) inside a project''s `.workflow/` folder, following the dev-flow contract. Use when the user pastes a product idea and says "let''s plan this", "draft a PRD", "what would this look like as a project", "fammi il PRD da questo PDF", "PRD da questo documento/RFP", or starts a new project from scratch. Also use when a `.workflow/` exists at phase `empty` or `idea_captured` and the orchestrator routes here. Not for: writing code, designing UI, or producing task lists (those are downstream skills).'
---

# prd-from-idea — idea → PROJECT.md + PRD.md

This skill turns an unstructured product idea into two artifacts that downstream skills depend on:

1. **`PROJECT.md`** — the strategic brief. One page. Audience, problem, value proposition, success criteria. The piece other humans read.
2. **`PRD.md`** — the product requirements doc. Several pages. User stories, acceptance criteria, non-goals, open questions. The piece engineers and downstream skills consume.

The skill is interactive — it asks the user a small number of high-leverage questions and turns the answers into the docs. It does **not** invent PRD content from nothing. When nobody can answer (an autonomous run), it derives the answers from the brief and records them as assumptions instead — see Step 3 §Autonomous runs.

## When this skill applies

- A user pastes a product idea ("I want to build a dashboard for X") and asks to start.
- Orchestrator (`dev-flow`) routes here when `phase` is `empty` or `idea_captured`.
- A `PROJECT.md` exists but `PRD.md` doesn't — the skill expands the brief into requirements.

If a `PRD.md` already exists, the skill enters **revise mode**: it reads the current PRD, asks what's wrong, and edits in place. It does not silently overwrite. A change that **adds or removes a story** is a scope change: it passes the scope check first (`references/scope-check.md`) and is recorded with `scripts/scope.py record`, one row in `## Scope changes`. A PRD that predates `## Scope rules` gets the section here (question 7b).

## Contract

This skill follows the dev-flow contract — see `references/contracts.md` (vendored copy) for the canonical schema. Key facts:
- Output goes into `<project-root>/.workflow/`.
- Set `phase = "idea_captured"` after writing `PROJECT.md`; set `phase = "prd_drafted"` after writing `PRD.md`.
- Append a `history` entry to `meta.json` for every run.

## ⚠️ Step 0 — the brief arrived as a file, not as a paste

The description above says "a user pastes a product idea", and often they don't: a real brief arrives
as **`.docx`, `.pptx`, `.pdf`, `.xlsx`** — an RFP, a client deck, a spec someone wrote in Word. Do not
ask the user to paste it, and do not summarise it from a partial read.

```bash
npx @firecrawl/anydoc brief.docx -o .workflow/_source/brief.md   # Word, PowerPoint, Excel,
npx @firecrawl/anydoc rfp.pdf                                    # OpenDocument, RTF, EPUB, CSV, PDF
```

[`anydoc`](https://github.com/firecrawl/anydoc) (Firecrawl, MIT, `@firecrawl/anydoc@0.2.4`) is a Rust
binary that converts all of those to GitHub-Flavored Markdown, and it ships **its own agent skill** —
`npx skills add firecrawl/anydoc` — so this file does not restate its CLI.

⚠️ **The one thing to decide before running it on someone else's document.** Conversion is **local**:
text-based PDFs included, nothing leaves the machine. But a **scanned or image-only PDF fails with
`NeedsOcr`**, and the opt-in `--ocr hosted` sends it to Firecrawl Parse — where, in the project's own
words, *"the whole document goes, since Parse has no page selection."* Not the scanned pages: the
document.

So for a client RFP, a tender, anything under NDA or covering personal data, **`--ocr hosted` is a
data transfer, and it needs the same answer `compliance-audit` asks under R3** — not a convenience
flag. Convert locally, or get permission first. If the pages are scanned and you cannot send them,
say so and work from what converts.

Keep the converted Markdown under `.workflow/_source/` so the PRD's provenance is inspectable, and
record the original filename in `PROJECT.md`. A requirement traced to a page of the client's own
document is worth more than the same sentence with no source.

## Workflow

### Step 1 — Locate the project root + read state

If invoked by the orchestrator, the project root is given. Otherwise ask the user.

Read `.workflow/meta.json`. If absent, ask the user whether to initialize the project here (run `dev-flow`'s `init_workflow.py`). Don't guess.

**Founder path.** If `meta.json#founder` exists with `decision` `approved` or `approved_experiment`, read the approved Playbook (`founder.playbook`, normally `.workflow/founder/founder-playbook.md`) before anything else: it is the input to this skill. If the decision is still `pending` or `revise`, stop and send the user back to `founder-intelligence` — `set-phase prd_drafted` would refuse anyway.

### Step 2 — Determine which artifact to produce

| State | Action |
|---|---|
| `PROJECT.md` missing | Produce `PROJECT.md` first, then ask if user wants to continue to PRD |
| `PROJECT.md` exists, `PRD.md` missing | Read `PROJECT.md`, produce `PRD.md` building on it |
| Both exist | Ask user which to revise (don't overwrite blindly) |

### Step 3 — Interview the user (the high-leverage questions)

For `PROJECT.md`, ask **at most 7 questions**, in this order. Skip any the user already answered in their initial paste.

🔴 **Questions 1–5 are about the problem, and nothing displaces them.** Measured on a real run
(2026-11-17): the interview opened with *"who is the agent that will use the panel, and where does it
run?"*, then scope, then *"what should happen for the actions the agent must not take alone?"*, and
only reached *"where do the settings live today?"* fourth. The user's words: *"I expected the general
questions, the typical ones of the flow."* They were right — three of those four were stack and policy
questions, interleaved with the product ones.

The cause is worth naming, because it will happen again with the next section somebody adds: the PRD
template carries concrete, actionable material (tables, verdicts, example rows), and concrete material
attracts an interview more strongly than five abstract questions do. So:

- **Nothing from a later template section is asked during the PROJECT.md interview.** Not §Agent
  authority, not §Measurement beyond its single opt-in question. If a section has a condition, it is
  filled when that condition is known, not while the product is still being described.
- **A paste that describes the solution does not answer questions 2–5.** "It must let an agent change
  the settings" says what it does, not what hurts, who suffers, how they cope today, or what winning
  looks like. Ask them anyway; skipping is for a paste that answered them, not for one that was
  detailed about something else.
- **One question at a time, and open.** A multiple-choice list for question 2 is a scope checklist
  wearing a product question's clothes.

**From an approved Playbook**, questions 1–5 (audience, problem, current alternatives, wedge, success) are already answered: write them from the Playbook, citing the section (`Playbook §3`, `§4`, `§6`, `§9`, `§12`), and do not ask them again. The technical questions (6 onward) are still asked. Decisions the Playbook marks as **locked** in §18 — segment, MVP scope and exclusions, success metrics, constraints — go into PROJECT.md and PRD.md unchanged (Non-goals take the MVP exclusions; the metrics decided before launch go into `## Measurement`, and `stack.analytics` starts as `["traffic", "product"]`, or `["product"]` on Expo — the founder already chose to measure); its open hypotheses go into PRD §Open questions with their H-ids. `## Scope rules` takes the evidence and the exclusions from Playbook §12, and `Who decides` is the founder — question 7b is not asked. With `approved_experiment`, the PRD covers only `founder.experiment` (scope, objective, constraints, acceptance). A technical constraint that contradicts a locked decision is flagged to the user with an offer to return to `founder-intelligence`, never resolved silently (`dev-flow/references/policies.md`).

1. **Who is this for?** (target audience — be specific: not "B2B" but "Series A SaaS founders running 10–30 person teams")
2. **What's the problem they have right now?** (in their own words, not yours)
3. **How do they solve it today?** (status quo / competitors)
4. **What's the wedge?** (the one thing this product does better than the status quo — be ruthless, one sentence)
5. **What does success look like in 6 months?** (one or two measurable signals — MAU, revenue, retention, qualitative quotes)
   Then, once: **"Do you want to measure how the product is used?"** Measurement is opt-in. **No** — a prototype, an
   internal tool — ends the subject: no `## Measurement`, no `stack.analytics`, no follow-up. **Yes** asks, in one
   batch, the moment a user first gets the value (the **activation event**, a `snake_case` past-tense name such as
   `invoice_sent`), how many activated users should be back after a week and after a month (**D7/D30**), what would
   look like traction but is not (**false positives**), and which **events** to record; record `stack.analytics` as
   `["traffic", "product"]` unless the user narrows it — `["product"]` when `stack.framework = "expo-rn"`, which has no
   traffic level. The D7/D30 targets mean "back on day 7 / day 30", the definition the SQL uses. It can also be switched on later with `module-add analytics`
   (`rn-module-add analytics` on Expo).
6. **What's the primary target — web, mobile (iOS+Android), both (monorepo), or desktop?** (forces a stack decision early). Map the answer → `meta.json#stack.framework`:
   - "web" / "web app" / no answer → `stack.framework: "next"` (current default for web)
   - "mobile" / "iOS" / "Android" / "mobile app" / "native app" → `stack.framework: "expo-rn"`
   - "both" / "monorepo" / "web + mobile" / "stesso prodotto su entrambi" → `stack.framework: "monorepo"`
   - "desktop" → out of scope for this skill set — refuse politely and refer the user to Tauri/Electron docs.
7. **(Web only OR monorepo: ask for the web side)** **Which UI library — shadcn/ui, Base UI, MUI, or Coss/UI?**
   *(A fifth, UI SDK, is offered by you and only on a signal — see the `ui-sdk` row below. Do not put it in the question.)* Map the answer → `meta.json#stack.ui` (for `framework="next"`) or `meta.json#stack.monorepo.web.ui` (for `framework="monorepo"`):
   - "shadcn" / "shadcn/ui" / "i want to own the source" → `"shadcn"`
   - "base ui" / "base-ui" / "headless library no CLI" → `"base-ui"`
   - "mui" / "material ui" / "material design" / "internal tool with lots of tables" → `"mui"`
   - "coss" / "coss/ui" / "cal.com design system" / "cal.com style" → `"coss"` (Coss/UI, the Cal.com design system built on Base UI — requires Tailwind v4)
   - "ui-sdk" / "ui sdk" / "vercel ui sdk" → `"ui-sdk"` — **but do not offer it in the question above.** It is beta
     (`0.1.0-beta.x`) and earns a project only on one of two signals, both of which the user has already told you by
     now, so **you offer it, they do not have to know it exists**: the product must run on **more than one framework**
     (it is the only option that ships React, Vue, Svelte, Solid and web components from one definition), or **an agent
     will operate the interface itself** — not an agent that writes the app, one that reads the page and changes
     controls at runtime. With a signal present, name it as a fifth option *with its cost* ("beta, APIs may move") and
     let the user choose. With neither, do not mention it: a new library from Vercel is exactly the thing to propose
     because it is new rather than because it fits. `design-md-to-app/references/library-choice.md` has the full
     signals and the catalogue comparison.
   - No clear answer → default to `"shadcn"` (most flexible / well-trodden path), explain briefly, let the user override.

   For mobile-only (`framework="expo-rn"`) and the mobile side of monorepo, UI is fixed at `"nativewind"` — no question asked.

8. **(Web only OR monorepo: ask for the web side)** **Which form library — TanStack Form (default, recommended) or react-hook-form?** Map to `meta.json#stack.forms` (web stack) or `meta.json#stack.monorepo.web.forms` (monorepo):
   - "tanstack" / "tanstack-form" / no answer / "default" → `"tanstack-form"` (recommended — the `forms` skill scaffolds `lib/forms/` on top of `@tanstack/react-form` with dirty tracking + baseline reset built-in + Zod-native validators).
   - "rhf" / "react-hook-form" / "I know rhf better" → `"react-hook-form"` (the `forms` skill scaffolds the same `lib/forms/` surface — `useEditForm` / `useCreateForm` / `FormProvider` / `FormField` / `FormActions` / `mapFormError` — but built on `react-hook-form` + `@hookform/resolvers/zod` underneath). Consumer code is identical.

   Skip Q8 for mobile-only projects — RN forms use a different ecosystem (controlled state via React Hook Form-native or vanilla, no consensus toolkit yet).

   **For Next.js projects (web only or web side of monorepo)**, also write `stack.nextjs_version = "16"` (App Router canonical). The dev-flow web skills target Next.js 16 + App Router exclusively — they refuse to apply to Pages Router or Next.js 15.

9. **Does the product need an agent engine (eve)?** (does an AI agent need to take actions, orchestrate tools, run autonomously, or converse with users beyond a plain LLM call?) Map the answer → `meta.json#stack.agent`:
   - "yes" / "it needs an AI agent" / "autonomous actions" / "tool-calling agent" → `"eve"` (the `eve-agent` skill scaffolds the agent engine; `dev-flow` routes to it alongside the frontend skills).
   - "no" / "just a chatbot wrapper" / no clear need → `null`.

   Applies regardless of framework — `eve` is a server-side engine that can sit behind web, mobile, or monorepo frontends.

   ⚠️ **If the answer is `eve`, the shape is a separate question and you must ask it — never derive it.** `stack.agent = "eve"` says nothing about whether the agent lives *inside* the web app or in `apps/agent`, and the two are different projects to work in. Ask the one question that decides it: **does the agent have a second consumer, its own deploy cadence, or channels beyond the web UI?** No second consumer means `framework: "next"` with the agent inside the app — the house default. Two agent *roles* is not two apps: one agent can resolve a different tool set per principal with `defineDynamic`, which is a stronger boundary than two processes because it comes from authenticated identity. See `dev-flow` §Topology policy.

### Route groups deduction (web + monorepo)

For `framework ∈ {next, monorepo}`, deduce which Next.js route groups to scaffold from Q1-Q5 answers. Write the array in `meta.json#stack.route_groups`:

| PRD indicators | route_groups value |
|---|---|
| SaaS with public landing + login + dashboard (B2B/B2C) | `["(marketing)", "(auth)", "(app)"]` |
| Internal tool / back-office (only authenticated users) | `["(auth)", "(app)"]` |
| Marketing site / blog only (no app) | `["(marketing)"]` |
| Documentation site (flat, no groups) | `[]` |

For mobile (`framework="expo-rn"`), the equivalent deduction also writes `route_groups`:

| PRD indicators | route_groups value |
|---|---|
| Consumer app (with login + tabs nav) | `["(auth)", "(app)", "(tabs)"]` |
| App with login but no tabs (single screen flow) | `["(auth)", "(app)"]` |

The user can override at any time by saying "add (marketing) group" etc. — the scaffold skill will create the group.

### Writing the stack into meta.json

Depending on Q6, write to `meta.json` immediately:

```json
// framework="next" (web only)
"stack": { "framework": "next", "ui": "<shadcn|base-ui|mui|coss>", "route_groups": ["(marketing)", "(auth)", "(app)"], "auth": null, "db": null, "agent": null, ... }

// framework="expo-rn" (mobile only)
"stack": { "framework": "expo-rn", "ui": "nativewind", "route_groups": ["(auth)", "(app)", "(tabs)"], "auth": null, "db": null, "agent": null, ... }

// framework="monorepo"
"stack": {
  "framework": "monorepo",
  "monorepo": {
    "web":    { "framework": "next",    "ui": "<shadcn|base-ui|mui|coss>" },
    "mobile": { "framework": "expo-rn", "ui": "nativewind" }
  },
  "auth": null, "db": null, "storage": null, "payments": null, "deploy": null, "agent": null
}
```

`stack.agent` is `null` by default, or `"eve"` when Q9 is answered yes (see Q9 above).

Downstream skills (`prd-to-tasks`, `dev-flow` routing, `design-md-to-app`, `rn-bootstrap`, `monorepo-bootstrap`, `eve-agent`) all read `stack.framework` and branch accordingly. `eve-agent` additionally reads `stack.agent`. Other `stack.*` keys (`auth`, `db`, `payments`, `deploy`) remain `null` at this stage.

For `PRD.md`, after `PROJECT.md` is in place, ask:

6. **What are the 3–5 user stories that define an MVP?** (in `As a … I want … so that …` form; if user gives more, ask which 3–5 are non-negotiable)
7. **What is explicitly out of scope?** (forces clarity)
7b. **Quale prova ti farebbe aggiungere una funzione prima del lancio?** — the PRD's `## Scope rules` (three lines:
   the evidence that lets a feature in, what never enters before launch whatever the evidence, who decides). With no
   answer, propose one ("three test users hit the same wall, or a story cannot be completed without it") and mark it
   as your proposal. On the founder path it is not asked: the evidence and the exclusions come from Playbook §12, and `Who decides` is the founder.
8. **What technical constraints exist?** (must use Postgres, must be GDPR-compliant, must integrate with X, etc. — `null` is a fine answer)
8b. **Dove gestiamo il lavoro: Linear, Jira o GitHub?** — the project's tracker, where `scrum` will run the sprints.
   🔴 **Ask it, with `AskUserQuestion`, like every other closed choice** (`contracts.md` §Asking the user). Measured
   2026-11-18 on a real run: this one was *assumed* and Linear appeared in the plan without anyone choosing it. The
   cause is the wording this line used to carry — *"propose the default"* — which an agent reads as **state it**, not
   as **ask it**. "Propose" means the recommended option goes first inside the widget and marked; it never means
   skipping the question.
   The recommended option is the tracker the project or the client **already uses** — an existing repo with issues, a
   client's Jira — and Linear only when there is no such signal. Say which of the two cases you are in, in the option's
   one-line description, so the user can correct the premise rather than just the answer.
   Record it with `scrum/scripts/meta_tracker.py <root>/.workflow/meta.json choose --provider linear|jira|github`.
   Only on an autonomous run (§Autonomous runs below — nobody can answer) is it taken without asking: Linear, recorded
   as `Assumed:`.

If the user pastes a long brief, parse it and ask only the unanswered questions. Don't make them re-state things they already wrote.

#### Autonomous runs — nobody to interview

When no one can answer — a background or `claude -p` session, a batch rebuild from a brief, or the user said "don't ask, go end-to-end" (the detection rule is `dev-flow` §Autonomous runs: when in doubt, it is interactive) — do not stall on the interview and do not invent:

1. Answer each question **from the brief**: the pasted idea, the converted document under `.workflow/_source/`, a transcript. Prefer the source's own words; cite the section, page or timestamp that decided it.
2. Where the brief is silent, take the **contract default**: Q6 → the product type's stack bundle in `dev-flow` §Stack decisions; Q7 → `"shadcn"`; Q8 → `"tanstack-form"`; Q9 → `null`; locales `["en", "it"]`. Where there is no default — audience, problem, wedge, success criteria — write `<TBD — needs user input>` exactly as the constraint below says, never a plausible guess.
3. Record every derived or defaulted answer in **`PRD.md` §Open questions** as `Assumed: <answer> — because <source | contract default>`, and in the `history` entry as `inputs.assumptions`. That list *is* the interview, deferred: the user reviews it instead of answering live.
4. **No measurement without an explicit request.** If the brief does not ask to measure usage, leave `## Measurement` out and `stack.analytics` unset; do not record it as an open question.
5. **Never derive the topology shape** when Q9 is `eve` (single app / monorepo / agent-only): write `needs a human: shape`, draft everything in the PRD that does not depend on it, and hand off.

### Step 4 — Draft the documents

🔴 **Everything in these documents is either something the user said, or an assumption. There is no
third kind — and the second one is marked.**

Measured 2026-11-18 on a real interactive run (`ops-config`): the PRD arrived complete — five MVP
stories, a filled §Agent authority table with its sentences — and the user's reaction was *"BUT I
TOLD IT NOTHING."* They were right. `grep Assumed:` over that PRD returned **zero**. §Open questions
listed six things the agent did not know, which was good, and nothing at all about the much larger
set of things it had **decided on the user's behalf**.

The cause: until now the `Assumed:` rule lived only inside §Autonomous runs. A run in `interactive`
mode never reads that section, so the rule did not exist where it was needed. It is unconditional now.

- **Ask the PRD's own questions before drafting its sections.** User stories, out of scope, the
  evidence rule, technical constraints — and §Agent authority when `stack.ui` is `"ui-sdk"`. Drafting
  them from the PROJECT.md interview is authoring, not recording.
- **What you author anyway is marked where it sits**, not only in a list at the end: a line
  `> Assumed: <what> — because <why>` immediately under the heading or the table it applies to. A
  reader reads the section; an appendix is read by nobody, and a month later an unmarked assumption is
  indistinguishable from a decision the team took.
- **§Open questions keeps its job** — what is *unknown* — and gains nothing here. "I don't know" and
  "I decided for you" are different failures and are recorded differently.
- The `history` entry records both: `inputs.decisions` for what the user said, `inputs.assumptions`
  for what you wrote.

A document that is 90% authored and unmarked is worse than an empty one: the empty one gets filled in,
the full one gets approved.



#### `PROJECT.md` template

```markdown
# <Project Name>

## Overview

<2–4 sentences capturing what this is, in plain English. Pretend the reader is a smart non-technical
stakeholder seeing the project for the first time.>

## Audience

<Who is this for? Be specific. If there are multiple personas, list each as a sub-bullet with their
role, context, and what they're trying to do.>

## Problem & current alternatives

<The pain point. What do they do today? What hurts about that?>

## Value proposition

<The wedge — the one thing this product does that nothing else does, or does better. One sentence,
then optionally a paragraph elaborating.>

## Success criteria (6 months)

- <Measurable signal #1>
- <Measurable signal #2>
- <Optional: leading indicators>

## Out of scope

<Optional — things the project deliberately won't do, to set expectations.>
```

#### `PRD.md` template

```markdown
# <Project Name> — PRD

## Problem

<Restated from PROJECT.md but with more detail. What specifically goes wrong for the user
without this product? Use a concrete scenario.>

## Solution overview

<How the product solves it. 2–4 paragraphs. Mention key flows but not implementation details.>

## User stories (MVP)

- **US-1.** As a <persona>, I want to <action>, so that <outcome>.
  - Acceptance: <bullet list — what must be true for this story to be done?>
- **US-2.** …
- **US-3.** …

(3–5 stories. If the user listed more, mark the rest as "Post-MVP" in a separate section.)

## Measurement

<Only if the user chose to measure; otherwise leave the whole section out.>

Decided before launch, not after. Levels: traffic, product.

- **Activation event**: `<event_name>` — <what the user has done when they first get the value> (within 7 days of signup)
- **Retention targets**: D7 ≥ <n> % · D30 ≥ <n> % of activated users (back on day 7 / day 30)
- **False positives to watch**: <e.g. sign-ups without activation; revenue without retention>
- **Events to instrument**: `<event_name>` (where it fires) · …

## Agent authority

<Only when an agent will operate this product's own interface — `stack.ui = "ui-sdk"` with the agent
bridge, see `design-md-to-app/references/ui-sdk-mapping.md`. Leave the section out otherwise.>

🔴 **When to ask, because getting this wrong is what it looked like the first time.** This section is
filled **after question 7 has settled `stack.ui` on `"ui-sdk"`** — never before. It is **not** one of
the seven opening questions, and *"who is the agent and where does it run?"* asked while the user is
still describing the product reads as an interrogation about a decision nobody has taken yet.

Once `stack.ui` is `"ui-sdk"`, ask **in one batch**, not one at a time: whose agent (ours only, or the
visitor's browser through WebMCP — the default is ours only), then the rows below. If `stack.ui` is
anything else, **ask nothing and leave the section out**: the bridge does not exist on that topology,
so the questions have no answer to record.

🔴 **These are product decisions, not attributes.** "Deleting a project needs a person" is a line of
PRD; `data-agent-confirm` is only how it gets written down. Decided here, the markup follows. Decided
while building, it gets decided by whoever typed the component — which in practice means not decided.

One row per action an agent can reach. The **sentence** matters as much as the verdict: it is what the
person will be shown when they are asked, so write it for them, from app state, and make it say the
consequence.

| Action | An agent may | The sentence a person sees |
|---|---|---|
| change a project's name | alone | — |
| invite a member | **ask first** | "Invites <email> as an editor. They get access immediately." |
| delete the project | **ask first** | "Deletes the project and all its files. This cannot be undone." |
| read the recovery codes | **never** — hidden from the agent | — |
| fill the tax ID | fill, never read | — |

Three verdicts and nothing in between: **alone**, **ask first**, **never**. "Probably fine" is
`ask first`; the cheap mistake is a question too many, not a deletion too few.

**And one question above the table: whose agent?** Ours only, or also the one built into the
visitor's browser (WebMCP). They are different decisions with different consequences — the second
sends what is on screen to a model we do not run — and the default answer is **ours only**. If the
product wants the browser's agent too, say so here and read
`design-md-to-app/references/ui-sdk-mapping.md` §WebMCP: it is an explicit call with a second
approval callback, and on a product handling personal data it is a sub-processor question
(`compliance-audit` R3 and R8).

⚠️ **A sentence is not optional on an `ask first` row.** The person is asked with it and nothing else.
"Are you sure?" tells them nothing, and an agent that reached that control already thought it was the
right one.

## Non-goals

<What the MVP explicitly does not include. Be opinionated.>

## Scope rules

- **A new feature enters the MVP when**: <the evidence, e.g. "three test users hit the same wall", "a story cannot be completed without it">
- **Not before launch, whatever the evidence**: <e.g. "a second payment provider", "an admin panel">
- **Who decides**: <the user, or the named owner>

## Technical constraints

<Anything that constrains the engineering choices: required tech, compliance, integration deadlines.
If none, say so.>

## Open questions

<Things the user couldn't answer or that need stakeholder input. Ask the user to flag these to whoever
needs to decide.>
```

### Step 5 — Write files and update state

Write `PROJECT.md` and/or `PRD.md` into `<root>/.workflow/`.

**Then check the scope rules before going on**: `python3 <skills>/prd-from-idea/scripts/scope.py check <root>`. It
must print `Scope rules complete.`. A missing line or a placeholder left in `## Scope rules` is filled now, from the
user's answer to question 7b or, without one, with your proposal marked as such — never handed off empty, or every
later scope check runs without a rule. In revise mode, a PRD that predates the section gets it here.

Update `meta.json`:
- bump `phase` to `idea_captured` (after `PROJECT.md`) or `prd_drafted` (after `PRD.md`) — see the contract for monotonicity rules
- update `updated_at` to ISO-8601 UTC now
- append to `history`:
  ```json
  {
    "skill": "prd-from-idea",
    "ran_at": "<now>",
    "outputs": ["PROJECT.md", "PRD.md"],
    "phase_before": "<old>",
    "phase_after": "<new>"
  }
  ```

### Step 6 — Hand off

Tell the user:
- which files were written (relative paths)
- what the new phase is
- what the orchestrator would propose next: usually `figma-to-design-md` if they have a Figma, or `design-md-to-app` if they're going to write the DESIGN.md by hand or already have one

Do **not** silently invoke the next skill. The user (or the orchestrator) decides.

## Important constraints

- **Don't invent.** If the user can't answer "who is this for", you ask again or write `<TBD — needs user input>` rather than imagine an audience.
- **Don't pad.** The PRD's value is being decision-forcing, not exhaustive. A 2-page PRD that names the wedge clearly is better than a 10-page PRD full of platitudes.
- **One h1 only.** The h1 is the project name. Sub-sections are h2.
- **Don't number user stories with backend IDs** (no `JIRA-123`-style). Use `US-1, US-2, ...` so they survive renaming.
- **Scope is decided, not drifted into.** A story added or removed after the PRD exists passes the scope check and is recorded with `scripts/scope.py record`: see `references/scope-check.md`.

## Reference files

- `references/scope-check.md` — the check a new request passes, its four outcomes, descope, the founder path.
- `scripts/scope.py` — `check` the PRD's `## Scope rules`, `record` a decision in `## Scope changes`.
- `references/contracts.md` — the `.workflow/` dev-flow contract (vendored).
