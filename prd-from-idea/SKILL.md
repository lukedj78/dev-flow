---
name: prd-from-idea
description: 'Turn a raw product idea (a paragraph, a Notion dump, a half-formed thought) into a structured PROJECT.md (high-level brief) and PRD.md (product requirements document) inside a project''s `.workflow/` folder, following the dev-flow contract. Use when the user pastes a product idea and says "let''s plan this", "draft a PRD", "what would this look like as a project", or starts a new project from scratch. Also use when a `.workflow/` exists at phase `empty` or `idea_captured` and the orchestrator routes here. Not for: writing code, designing UI, or producing task lists (those are downstream skills).'
---

# prd-from-idea — idea → PROJECT.md + PRD.md

This skill turns an unstructured product idea into two artifacts that downstream skills depend on:

1. **`PROJECT.md`** — the strategic brief. One page. Audience, problem, value proposition, success criteria. The piece other humans read.
2. **`PRD.md`** — the product requirements doc. Several pages. User stories, acceptance criteria, non-goals, open questions. The piece engineers and downstream skills consume.

The skill is interactive — it asks the user a small number of high-leverage questions and turns the answers into the docs. It does **not** invent PRD content from nothing.

## When this skill applies

- A user pastes a product idea ("I want to build a dashboard for X") and asks to start.
- Orchestrator (`dev-flow`) routes here when `phase` is `empty` or `idea_captured`.
- A `PROJECT.md` exists but `PRD.md` doesn't — the skill expands the brief into requirements.

If a `PRD.md` already exists, the skill enters **revise mode**: it reads the current PRD, asks what's wrong, and edits in place. It does not silently overwrite.

## Contract

This skill follows the dev-flow contract — see `references/contracts.md` (vendored copy) for the canonical schema. Key facts:
- Output goes into `<project-root>/.workflow/`.
- Set `phase = "idea_captured"` after writing `PROJECT.md`; set `phase = "prd_drafted"` after writing `PRD.md`.
- Append a `history` entry to `meta.json` for every run.

## Workflow

### Step 1 — Locate the project root + read state

If invoked by the orchestrator, the project root is given. Otherwise ask the user.

Read `.workflow/meta.json`. If absent, ask the user whether to initialize the project here (run `dev-flow`'s `init_workflow.py`). Don't guess.

### Step 2 — Determine which artifact to produce

| State | Action |
|---|---|
| `PROJECT.md` missing | Produce `PROJECT.md` first, then ask if user wants to continue to PRD |
| `PROJECT.md` exists, `PRD.md` missing | Read `PROJECT.md`, produce `PRD.md` building on it |
| Both exist | Ask user which to revise (don't overwrite blindly) |

### Step 3 — Interview the user (the high-leverage questions)

#### Q: target platform

Ask: "What's the primary target — web, mobile (iOS+Android), or desktop?"

Map the user's answer → `meta.json#stack.framework`:
- "web" / "web app" / no answer → `stack.framework: "next"` (current default for web)
- "mobile" / "iOS" / "Android" / "mobile app" / "native app" → `stack.framework: "expo-rn"`
- "desktop" → out of scope for this skill set — refuse politely and refer the user to Tauri/Electron docs.

Write `stack.framework` into `meta.json` immediately so downstream skills (`prd-to-tasks`, `dev-flow` routing) see it. Other `stack.*` keys (`ui`, `auth`, `db`, `payments`, `deploy`) remain `null` at this stage — they get filled in by `rn-bootstrap` / `design-md-to-app` / `module-add` / `rn-module-add` later.

---

For `PROJECT.md`, ask **at most 5 questions**, in this order. Skip any the user already answered in their initial paste.

1. **Who is this for?** (target audience — be specific: not "B2B" but "Series A SaaS founders running 10–30 person teams")
2. **What's the problem they have right now?** (in their own words, not yours)
3. **How do they solve it today?** (status quo / competitors)
4. **What's the wedge?** (the one thing this product does better than the status quo — be ruthless, one sentence)
5. **What does success look like in 6 months?** (one or two measurable signals — MAU, revenue, retention, qualitative quotes)

For `PRD.md`, after `PROJECT.md` is in place, ask:

6. **What are the 3–5 user stories that define an MVP?** (in `As a … I want … so that …` form; if user gives more, ask which 3–5 are non-negotiable)
7. **What is explicitly out of scope?** (forces clarity)
8. **What technical constraints exist?** (must use Postgres, must be GDPR-compliant, must integrate with X, etc. — `null` is a fine answer)

If the user pastes a long brief, parse it and ask only the unanswered questions. Don't make them re-state things they already wrote.

### Step 4 — Draft the documents

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

## Non-goals

<What the MVP explicitly does not include. Be opinionated.>

## Technical constraints

<Anything that constrains the engineering choices: required tech, compliance, integration deadlines.
If none, say so.>

## Open questions

<Things the user couldn't answer or that need stakeholder input. Ask the user to flag these to whoever
needs to decide.>
```

### Step 5 — Write files and update state

Write `PROJECT.md` and/or `PRD.md` into `<root>/.workflow/`.

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
