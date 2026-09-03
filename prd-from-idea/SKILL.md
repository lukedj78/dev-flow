---
name: prd-from-idea
description: 'Turn a raw product idea — a paragraph, a Notion dump, a half-formed thought, or a brief that arrived as a **file** (`.docx`, `.pdf`, `.pptx`, `.xlsx`: an RFP, a client deck, a Word spec — converted to Markdown first with `anydoc`) — into a structured PROJECT.md (high-level brief) and PRD.md (product requirements document) inside a project''s `.workflow/` folder, following the dev-flow contract. Use when the user pastes a product idea and says "let''s plan this", "draft a PRD", "what would this look like as a project", "fammi il PRD da questo PDF", "PRD da questo documento/RFP", or starts a new project from scratch. Also use when a `.workflow/` exists at phase `empty` or `idea_captured` and the orchestrator routes here. Not for: writing code, designing UI, or producing task lists (those are downstream skills).'
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

### Step 2 — Determine which artifact to produce

| State | Action |
|---|---|
| `PROJECT.md` missing | Produce `PROJECT.md` first, then ask if user wants to continue to PRD |
| `PROJECT.md` exists, `PRD.md` missing | Read `PROJECT.md`, produce `PRD.md` building on it |
| Both exist | Ask user which to revise (don't overwrite blindly) |

### Step 3 — Interview the user (the high-leverage questions)

For `PROJECT.md`, ask **at most 7 questions**, in this order. Skip any the user already answered in their initial paste.

1. **Who is this for?** (target audience — be specific: not "B2B" but "Series A SaaS founders running 10–30 person teams")
2. **What's the problem they have right now?** (in their own words, not yours)
3. **How do they solve it today?** (status quo / competitors)
4. **What's the wedge?** (the one thing this product does better than the status quo — be ruthless, one sentence)
5. **What does success look like in 6 months?** (one or two measurable signals — MAU, revenue, retention, qualitative quotes)
6. **What's the primary target — web, mobile (iOS+Android), both (monorepo), or desktop?** (forces a stack decision early). Map the answer → `meta.json#stack.framework`:
   - "web" / "web app" / no answer → `stack.framework: "next"` (current default for web)
   - "mobile" / "iOS" / "Android" / "mobile app" / "native app" → `stack.framework: "expo-rn"`
   - "both" / "monorepo" / "web + mobile" / "stesso prodotto su entrambi" → `stack.framework: "monorepo"`
   - "desktop" → out of scope for this skill set — refuse politely and refer the user to Tauri/Electron docs.
7. **(Web only OR monorepo: ask for the web side)** **Which UI library — shadcn/ui, Base UI, MUI, or Coss/UI?** Map the answer → `meta.json#stack.ui` (for `framework="next"`) or `meta.json#stack.monorepo.web.ui` (for `framework="monorepo"`):
   - "shadcn" / "shadcn/ui" / "i want to own the source" → `"shadcn"`
   - "base ui" / "base-ui" / "headless library no CLI" → `"base-ui"`
   - "mui" / "material ui" / "material design" / "internal tool with lots of tables" → `"mui"`
   - "coss" / "coss/ui" / "cal.com design system" / "cal.com style" → `"coss"` (Coss/UI, the Cal.com design system built on Base UI — requires Tailwind v4)
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
