---
name: dev-flow
description: 'Orchestrate an end-to-end product-development workflow built on atomic skills. Reads `.workflow/meta.json` in a project directory, figures out what phase the user is in (idea → PRD → tasks → design → scaffolded → pages → modules), and delegates to the right specialist skill: `prd-from-idea`, `prd-to-tasks`, `figma-to-design-md`, `image-to-design-md`, `design-md-to-app`, `screenshot-to-page`, `module-add`. Use when the user wants to "start a new project end-to-end", "advance my project to the next stage", "what should I do next on this project", or pastes a brand-new product idea / Figma URL / inspiration images with a request to "build the app". Not for: deeply-specialized work inside one stage (in that case, invoke the specialist skill directly).'
---

# dev-flow — workflow orchestrator

`dev-flow` does not do the work itself. It is a **router**: it inspects the project's `.workflow/` folder, decides what's next, and tells the user which specialist skill to invoke (or invokes it).

The whole point of this skill is that the user can say *"continue building this thing"* without remembering which step comes next. The orchestrator reads `meta.json`, looks at what's already there, and proposes the next move.

## When this skill applies

- The user pastes a Figma URL, a product idea, or a vague "let's build X" request and wants the entire pipeline.
- The user opens a project directory and asks "what's next" / "continue".
- The user is unsure which of the dev-flow specialist skills to use.

If the user is clearly inside one phase (e.g., "improve the auth module", "regenerate the pricing page from this screenshot"), call the relevant specialist skill directly — don't route through the orchestrator.

## The contract

`.workflow/` is the load-bearing convention. Read **`references/contracts.md`** before doing anything — it defines the folder layout, the `meta.json` schema, the `phase` enum, and which skill owns which file. **Do not improvise.** If a skill behaves in a way the contract doesn't describe, fix the contract or fix the skill — never silently diverge.

## Workflow

### Step 1 — Locate or create the project root

Ask the user for the project's absolute path. If they don't have one, propose `~/projects/<slug>/` where slug is derived from the project name (see contract for derivation rules).

If `<root>/.workflow/` does not exist, create it and write a minimal `meta.json`:

```json
{
  "project_slug": "<slug>",
  "project_name": "<name>",
  "created_at": "<ISO-8601 UTC now>",
  "updated_at": "<same>",
  "phase": "empty",
  "stack": {
    "framework": null, "ui": null, "auth": null, "db": null,
    "payments": null, "deploy": null
  },
  "history": []
}
```

Skills downstream require `meta.json` to exist — never skip this.

### Step 2 — Read state and decide the next move

Read `.workflow/meta.json`. Branch on `phase`:

| Current `phase` | Next move (in priority order) |
|---|---|
| `empty` | `prd-from-idea` (capture idea + draft PRD). If the user already has a Figma URL handy, can also detour via `figma-to-design-md` first — but PRD usually comes first for clarity. |
| `idea_captured` | `prd-from-idea` (expand `PROJECT.md` into a `PRD.md`). |
| `prd_drafted` | `prd-to-tasks` if user wants explicit task breakdown; OR `figma-to-design-md` if user has a Figma; OR `image-to-design-md` if user has 1+ raster images (PNG/JPG screenshots, mockups, Pinterest pins); OR jump to `design-md-to-app` if simple project + DESIGN.md will be hand-written. |
| `tasks_split` | `figma-to-design-md` or `image-to-design-md` or `design-md-to-app`. |
| `design_extracted` | `design-md-to-app` (this is the natural next step — DESIGN.md exists, time to scaffold). |
| `scaffolded` | `screenshot-to-page` if `screenshots/` has unmapped images; `module-add` to wire auth/db/etc.; iterate. |
| `page_generated` | `module-add` or more `screenshot-to-page` runs. |
| `module-added` | Iterate — there's no terminal state. Ask the user what's next. |
| anything else | Treat as `empty` (forward-compatible). |

The orchestrator must propose, not impose. After deciding, **tell the user the proposed next step in one sentence**, and ask for confirmation before invoking. Example: *"You're at `design_extracted` (DESIGN.md + 6 screenshots in place). I propose running `design-md-to-app` to scaffold a Next.js + shadcn project. OK to proceed, or do you want to add modules / change stack first?"*

### Step 3 — Invoke the right skill

When the user confirms, invoke the specialist skill with explicit input:

- the project root path
- relevant `meta.json` fields (e.g., `stack` for `design-md-to-app`)
- any user-supplied input (Figma URL, screenshot path, brand brief)

The specialist skill writes its outputs into `.workflow/`, updates `phase` and appends to `history` in `meta.json`.

After the specialist returns, **read `meta.json` again** to confirm the phase advanced. If it didn't, the specialist either errored or the user aborted — propose the next move accordingly.

### Step 4 — Loop

Most projects need multiple specialists in sequence. The orchestrator's job is to keep going: after one specialist finishes, immediately re-evaluate state and propose the next step. Keep looping until the user says "stop" or `phase` reaches `module-added` and the user has nothing more to add.

## Stack decisions

When transitioning out of `prd_drafted` and into scaffolding, the user has to choose a stack. The orchestrator should ask once and persist in `meta.json#stack`. Sensible default-bundle suggestions:

| Profile | framework | ui | auth | db | payments |
|---|---|---|---|---|---|
| **SaaS B2B** | next | shadcn | better-auth | neon-drizzle | stripe |
| **B2C consumer** | next | shadcn | clerk | supabase | stripe |
| **Marketing site** | astro | shadcn-astro | null | null | null |
| **Internal tool** | vite-react | shadcn | better-auth | neon-drizzle | null |

Ask the user the project type, propose the bundle, let them override individual choices. Don't ask 6 separate questions when one ("what kind of app?") plus a confirmation gets you there.

## What dev-flow does NOT do

- **Doesn't do specialist work itself.** No PRD writing, no DESIGN.md generation, no scaffolding. If you find yourself doing actual work (other than reading state and routing), stop — call the right specialist.
- **Doesn't edit `app/`.** That's owned by `design-md-to-app` and friends.
- **Doesn't make stack decisions silently.** Always ask the user, even if a default is obvious.
- **Doesn't skip phases.** If the user tries to jump from `empty` straight to `design-md-to-app`, gently push back: at minimum `PROJECT.md` should exist so the design-to-app skill knows the brand voice.

## Bundled scripts

- `scripts/init_workflow.py <project-root> [--name "Project Name"]` — creates `.workflow/` with a fresh `meta.json`. Use when the user opts into the orchestrator on an empty directory.
- `scripts/show_state.py <project-root>` — prints the current `phase`, the files present, and the proposed next step. Use early in every conversation when the user asks "what's next".

Both scripts are simple JSON readers/writers; running them doesn't make decisions for the user.
