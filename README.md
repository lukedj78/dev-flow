# dev-flow

> **A filesystem contract for agent-driven SDLC.**
> One folder (`.workflow/`), one state file (`meta.json`), and **33 skills (13 web + 15 mobile + 3 monorepo + 2 refactor)** that read/write it. The contract is the product — the skills are durable, replaceable consumers.
>
> The web family now includes **`eve-agent`** — scaffold and grow an [eve](https://eve.dev) agent (`apps/agent`) as the AI engine behind a Next.js app, opted into via `stack.agent`. See [docs/example-full-walkthrough.md](./docs/example-full-walkthrough.md) and the autonomous-loop runbook [docs/loop-engineering.md](./docs/loop-engineering.md).

```
                      ┌────────────────────────┐
                      │  .workflow/meta.json   │ ◄─── single source of truth
                      │  (phase + stack +      │      every skill reads
                      │   history + artifacts) │      every skill writes
                      └─────────┬──────────────┘
                                │
              ┌─────────────────┴─────────────────┐
              │                                   │
              ▼ stack.framework="next"            ▼ stack.framework="expo-rn"
              │                                   │
              │   WEB FAMILY (13 skills)           MOBILE FAMILY (15 skills)
              │                                   │
   ┌──────────┼──────────┐               ┌────────┼─────────┐
   │          │          │               │        │         │
   ▼          ▼          ▼               ▼        ▼         ▼
 prd-from-  design-md-  module-add      rn-       rn-       rn-
 idea       to-app      (auth, db,      bootstrap add-      module-add
 prd-to-    screenshot- payments,        rn-      screen    (auth, db,
 tasks      to-page     email, ci, …)   styling   rn-       storage,
 figma-to-  write-tests                  rn-      write-    realtime,
 design-md                                expo-    tests     push,
 image-to-                                router   …         payments)
 design-md                                                  rn-eas-deploy
              │                                   │
              └─────────────────┬─────────────────┘
                                │
                                ▼
                        Codebase at <project-root>/
                        (Next.js app or Expo app)
```

The skills are **interchangeable consumers** of the contract. Tomorrow you could rewrite any of them in TypeScript, swap one out for a Cursor-flavored variant, or extend with your own — as long as they read `meta.json` and respect the phase semantics, they compose.

**Three stacks today, one contract.** The web stack ships Next.js (or Astro/Vite) + shadcn/Base UI/MUI apps; the mobile stack ships Expo + React Native + NativeWind apps with EAS publishing to the App Store + Play Store; the **monorepo** stack ships both in one turborepo (with `apps/web/` + `apps/mobile/` + shared `packages/`). `dev-flow` (the orchestrator) reads `meta.json#stack.framework` and routes to the correct family — `prd-from-idea` and `prd-to-tasks` are stack-agnostic and used by all three.

---

## Why a contract, not just skills

Most "AI agent toolkits" hardcode orchestration in prompts. That works until the conversation drops context — then the agent forgets which step you were on, what design tokens it picked, which modules it wired.

dev-flow fixes that the way distributed systems fix it: **state lives on disk, not in the agent's head.** Every skill is independently re-runnable from `.workflow/meta.json`. Resume a build the next morning, hand it off to a different agent, run two skills in parallel — the contract holds.

The skill count is an implementation detail. The contract is the moat.

---

## What the contract gives you

- **Resumability.** The agent forgets, the filesystem doesn't. `meta.json` records where you are; any skill can pick up.
- **Composability.** Skills don't call each other — they read/write the same state. New skills slot in by declaring which `phase` they consume and produce.
- **Portability.** The contract is just JSON + Markdown + folders. It survives a model swap, a tooling pivot, even a rewrite of the skills in another language.
- **Auditability.** Every skill run appends to `meta.json#history` with inputs, outputs, phase delta. You always know who wrote what when.
- **Idempotency.** Re-running a skill is safe — it sees its own previous output and skips/updates instead of duplicating.
- **Drift detection.** Every contract file is content-addressed. When the user edits `DESIGN.md` by hand, the system knows that `registry.json` and `/showcase` (which were derived from it) are now stale — and it knows transitively, so a chain of derivations propagates.

The contract is also published as a standalone Python package, [`dev-flow-contract`](./contract-package), so any future tool — a Cursor plugin, a CLI, a different LLM agent — can read/write `.workflow/` without depending on Claude Code. The skills are interchangeable consumers; the package is the durable surface.

---

## Quick start (5 minutes)

### 1. Install the skills

Pick whichever fits your setup — they all end up at `~/.claude/skills/<name>/` :

#### Option A — bundled `install.sh` (recommended for this repo)

```bash
git clone git@github.com:lukedj78/dev-flow.git
cd dev-flow
./install.sh                          # defaults to Claude Code
./install.sh --platform codex         # or Codex CLI / Copilot / Gemini / Cursor
./install.sh --list-platforms         # see all supported runtimes
```

The script copies all 33 skill folders into the platform-appropriate location (e.g. `~/.claude/skills/`, `~/.codex/dev-flow-skills/`, `~/.gemini/skills/`), drops in the right bootstrap file (`AGENTS.md`, `GEMINI.md`, `.cursorrules`) when needed, and backs up any pre-existing version with the same name to `<skill>.bak`. To uninstall + restore backups: `./uninstall.sh --platform <same>`.

**Portability**: dev-flow's skills are designed to be runtime-portable. See [Cross-platform support](#cross-platform-support) below.

#### Option B — Claude Code `/plugin add` (interactive)

If you have the repo cloned locally:

```
/plugin add /path/to/dev-flow/dev-flow
/plugin add /path/to/dev-flow/prd-from-idea
…
```

Run once per skill folder. Useful if you only want to install a subset.

#### Option C — `gh skill install` (GitHub CLI extension)

```bash
gh extension install <ext-author>/gh-skill          # one-time
gh skill install lukedj78/dev-flow                   # private repo, requires auth
# OR for a specific subset
gh skill install lukedj78/dev-flow dev-flow design-md-to-app
```

This works with the same `gh auth` you already use to clone private repos.

#### Option D — drag-and-drop the `.skill` files

The `dist/` folder contains packaged `.skill` archives. Drag them into your Claude Code window one at a time — useful when you don't have shell access on the target machine. (`dist/` is regenerated periodically; the newest skills — e.g. `eve-agent` — may ship source-only until repackaged, so prefer `install.sh` for the full set.)

#### Verify

```bash
ls ~/.claude/skills/ | wc -l
# Should print 33. Restart Claude Code if you don't see them in /skills.
```

The **core happy-path** skills (the web flow most projects start with):

| Skill | What it does |
|---|---|
| **`dev-flow`** | The orchestrator — reads `.workflow/meta.json` and proposes what to do next |
| `prd-from-idea` | Idea paragraph → `PROJECT.md` + `PRD.md` |
| `prd-to-tasks` | `PRD.md` → `tasks.md` (importable into beads / Linear / GitHub Issues) |
| `linear-scrum` | Take a project into Linear and run it with agile scrum — cycles, estimates, sprint planning, velocity reports; Linear as source of truth |
| `figma-to-design-md` | Figma URL → `DESIGN.md` (Google design.md spec) + screenshots |
| `image-to-design-md` | 1+ raster images → `DESIGN.md` + screenshots |
| `design-md-to-app` | `DESIGN.md` → scaffolded Next.js + shadcn app with theme + showcase + folder convention |
| `coss-ui` | Coss/UI (Cal.com design system on Base UI) via the shadcn `@coss/*` registry — Init/Add modes, DESIGN.md token reconciliation; requires Tailwind v4, mixed MIT/AGPLv3 license |
| `screenshot-to-page` | One screenshot → one route, with pixel-perfect verification loop |
| `module-add` | Wire `auth` / `db` / `payments` / `email` / `test` / `ci` / `motion` / `voice` / `realtime` / `storage` / `deploy` modules |
| `write-tests` | One source file (server action / page / component / query) → its Vitest or Playwright test, following the project's existing patterns |

`install.sh` installs **all 33 skills**, not just these. Beyond the core flow above: the web discipline skills (`forms`, `data-fetching`, `state-discipline`), the agent engine (`eve-agent`), the 2 refactor skills (`promote-component`, `composition-patterns-guide`), the 15 mobile `rn-*` skills, and the 3 monorepo skills. Full breakdown in [The 33 skills, in detail](#the-33-skills-in-detail).

### 2. Create a project

```bash
mkdir -p ~/projects/my-app && cd ~/projects/my-app
```

### 3. Open Claude Code in that directory and say:

> *"I want to build a CRM for veterinary clinics. Customer records, vaccination history, appointment scheduling, document archive."*

The orchestrator (`dev-flow`) will:
1. Create `.workflow/meta.json`.
2. Invoke `prd-from-idea` → `PROJECT.md` + `PRD.md`.
3. Ask if you have a Figma / images / want to write the DESIGN.md by hand.
4. Invoke the right design-extraction skill → `.workflow/DESIGN.md`.
5. Ask for stack choice (Next + shadcn is the default).
6. Invoke `design-md-to-app` → fully scaffolded codebase + showcase.
7. Optionally invoke `screenshot-to-page` for routes from your screenshots.
8. Optionally invoke `module-add` for db / auth / etc.

By the end you have a runnable Next.js app at the project root, with a `.workflow/` folder that documents every decision.

---

## Use cases

Seven concrete recipes — what to type, what to expect. Pick the one that matches your situation and start there. The sections below assume you've installed the skills (see Quick start).

### 1. Greenfield project — idea to running app

**Situation**: empty directory, you have an idea, no design assets yet.

```bash
mkdir -p ~/projects/vet-crm && cd ~/projects/vet-crm
```

In Claude Code, say:

> *"I want to build a CRM for veterinary clinics. Customer records, vaccination history, appointment scheduling."*

The orchestrator routes through phases:

```
1. dev-flow            → init_workflow .  (creates .workflow/meta.json, phase=empty)
2. prd-from-idea       → PROJECT.md + PRD.md  (phase=prd_drafted)
3. prd-to-tasks        → tasks.md  (phase=tasks_split)
4. image-to-design-md  → DESIGN.md  (asks for reference screenshots)
   OR figma-to-design-md if you have a Figma URL
5. design-md-to-app    → full scaffold + /showcase  (phase=scaffolded)
6. screenshot-to-page  → /clients, /appointments, …  (phase=page_generated)
7. module-add db       → Drizzle + Neon
8. module-add auth     → better-auth
```

Check progress at any time:

```bash
$ python3 ~/.claude/skills/dev-flow/scripts/show_state.py .
Project:  'Vet CRM'  ('vet-crm')
Phase:    scaffolded
Stack:    framework=next, ui=shadcn
Skill runs: 4
  - prd-from-idea         → phase=prd_drafted
  - image-to-design-md    → phase=design_extracted
  - design-md-to-app      → phase=scaffolded
Next step proposal: screenshot-to-page  OR  module-add
```

**End-to-end time**: ~25 minutes if Neon credentials are ready, ~10 minutes with placeholder env values.

---

### 2. You already have a `DESIGN.md` — skip straight to scaffold

**Situation**: you wrote a DESIGN.md by hand (or copied from another project) and want to scaffold immediately.

```bash
mkdir my-app && cd my-app
mkdir .workflow
cat > .workflow/DESIGN.md << 'EOF'
# My App Design System
## Color Palette
- primary: #0066cc
- background: #ffffff
- on-surface: #111827
## Typography
- display: Inter, 48px, 600
- body: Inter, 16px, 400
...
EOF
```

In Claude Code:

> *"Use this DESIGN.md to scaffold the app. Next + shadcn."*

`design-md-to-app` starts directly from `phase=design_extracted`, skips PRD/tasks (the DESIGN is already there), and produces:

- `package.json`, `app/`, `components/site/`, `lib/server/`, `lib/queries/`
- `registry.json` (token-first shadcn install)
- `app/showcase/page.tsx` with 9 sections
- `app/error.tsx`, `app/loading.tsx`, `lib/env.ts` (Zod-validated), `next.config.ts` (security headers)
- Theme provider + mode-toggle (D-key shortcut, with rich-editor exclusion)
- Folder skeleton ready for `screenshot-to-page` and `module-add`

---

### 3. Figma → DESIGN.md (3 access paths, picked automatically)

**Situation**: you have a Figma URL and want to extract the design system.

```bash
mkdir ~/projects/aether && cd ~/projects/aether
```

In Claude Code:

> *"Extract the design system from this Figma file: `https://www.figma.com/design/<file-key>/Aetherfield`"*

`figma-to-design-md` picks the first available access path:

| Path | When it fires | Quality |
|---|---|---|
| **A — Figma Dev Mode MCP** | A `mcp__figma*` tool is exposed in this session | High — uses real variables + styles |
| **B — Figma REST API** | `FIGMA_ACCESS_TOKEN` is set, OR you provide a personal access token when asked | Medium-high — variables + styles via `/v1/files/<key>` |
| **C-bis — Playwright-assisted** | Browser MCP available but no Figma access — opens the file in a headless browser, screenshots key frames, runs k-means on the pixels | Medium — palette inferred, typography from rendered text |
| **C — Manual export** | Nothing else available — guides you to export PNGs + (optional) Tokens Studio JSON | Lower, but always works |

The skill **tells you explicitly** which path it's using:

```
$ "Using Path A — Figma MCP, found mcp__figma__get_file"
$ "Using Path B — REST API with token from env"
$ "No Figma access. Falling back to Path C-bis with Playwright."
```

**Path B example** (most common — you have a token but no MCP):

```bash
export FIGMA_ACCESS_TOKEN=figd_xxx
```

> *"Extract design from `https://www.figma.com/design/<file-key>/MyProject`"*

The extraction produces:
- `.workflow/DESIGN.md` (Google design.md spec)
- `.workflow/screenshots/<frame-name>.png` (2–3 reference frames)
- `.workflow/_design-md-mapping.json` recording which path was used + any fallbacks

If Path A/B couldn't read typography (rare), the skill **stops and asks** instead of inventing weights — typography is non-negotiable.

---

### 4. Screenshot → page (two-mode pixel verification)

**Situation**: you have a screenshot of a UI and want it as a real route.

Drop the screenshot in `.workflow/screenshots/dashboard.png`, then:

> *"Turn `dashboard.png` into `/dashboard`."*

`screenshot-to-page` picks the verification mode based on the **kind of route**:

| Route shape | Mode | Target | Iter cap |
|---|---|---|---|
| `/dashboard`, `/settings`, `/clients/<id>`, anything CRUD | **`structure-first`** (default) | ≤ 8% delta, token-correct | 3 |
| `/`, `/pricing`, `/about`, `/sign-up`, marketing/landing | **`pixel-tight`** (opt-in) | ≤ 2% delta | 8 |

Why two modes: pixel-tight on dashboards produces rigid HTML that imitates pixels instead of respecting tokens. The next developer can't tell which spacing was a design choice and which was an LLM matching one pixel. For brand-critical surfaces (heros, pricing), the inverse is true — fidelity IS the value.

The skill states the chosen mode in its hand-off:

> *"Iterated in `structure-first` mode (3 passes, final delta 6.4%) — token-correct, semantically clean. Switch to pixel-tight if you want closer fidelity for production."*

---

### 5. Retroactive edit to DESIGN.md (drift detection)

**Situation**: you edited `.workflow/DESIGN.md` by hand (changed primary from blue to purple) after the app was already scaffolded.

```bash
$ python3 ~/.claude/skills/dev-flow/scripts/check_drift.py . --plan
  ✗ .workflow/DESIGN.md    image-to-design-md  self-drift
  ⚠ registry.json          design-md-to-app    upstream-stale
  ⚠ app/showcase/page.tsx  design-md-to-app    upstream-stale  (transitively via registry.json)

Migration plan (re-run these skills, in order):
  image-to-design-md:
    ✗ .workflow/DESIGN.md  (self-drift)
  design-md-to-app:
    ⚠ registry.json
    ⚠ app/showcase/page.tsx

Run the skills in the order shown — each one's outputs will refresh
the artifacts and clear the drift downstream.
```

You know **exactly** what to re-run and in what order. Drift propagates transitively through `derived_from` chains.

This is the use case the linear phase enum could not handle — the system now models the actual iterative workflow of product development.

---

### 6. Add a module to an existing scaffold

**Situation**: scaffold is running. You want a database, then auth, then payments.

> *"Add a database."*

`module-add` checks prerequisites, picks the default (Drizzle + Neon), installs:
- `drizzle-orm`, `@neondatabase/serverless`, `drizzle-kit`
- `lib/db/schema.ts` with tenant-scoped indexes, `uniqueIndex`, soft-delete `archivedAt` convention, RLS docs
- `drizzle.config.ts`, `lib/db/index.ts`
- `pnpm db:push` / `db:migrate` / `db:studio` scripts in `package.json`
- `DATABASE_URL` in `.env.local.example`

> *"Add auth."*

Detects `stack.db = neon-drizzle`, picks better-auth as the default:
- `lib/auth.ts`, `lib/auth-client.ts`, `app/api/auth/[...all]/route.ts`
- **`lib/auth-server.ts`** with `getCurrentUserId()` / `getCurrentTenantId()` helpers — replaces the stubs in `lib/server/<domain>.ts`
- Auth tables appended to `lib/db/schema.ts`
- `BETTER_AUTH_SECRET`, `BETTER_AUTH_URL` env vars

> *"Add payments."*

Stripe with subscriptions + one-time:
- `lib/stripe.ts` (server SDK with pinned `apiVersion`), `lib/stripe-client.ts` (memoized loader)
- `app/api/stripe/webhook/route.ts` (signed receiver, idempotent handler) + `/portal` redirect
- `app/billing/page.tsx` reference UI
- `subscriptions` table in Drizzle schema
- Instructions for `stripe listen --forward-to localhost:3000/api/stripe/webhook` during dev

Same shape for `module-add email` (Resend + React Email), `module-add test` (Vitest + Playwright), `module-add ci` (husky + GH Actions). Re-running is **idempotent** — the skill detects existing installs and skips.

---

### 7. Use the contract outside Claude Code

**Situation**: you want to build your own tool — a CLI, a Cursor extension, a different LLM agent — that reads/writes `.workflow/`.

```bash
pip install -e ./contract-package    # while not on PyPI yet
```

```python
from pathlib import Path
from dev_flow_contract import (
    init_workflow, record_artifact, set_phase, append_history,
    check_drift, Phase
)

root = Path("./my-project")
init_workflow(root, name="My Project")

# After your tool writes a file:
(root / ".workflow" / "DESIGN.md").write_text("# Design")
record_artifact(root, ".workflow/DESIGN.md", produced_by="my-extractor")

# Bump the phase + record the run:
set_phase(root, Phase.DESIGN_EXTRACTED)
append_history(
    root,
    skill="my-extractor",
    inputs={"source_url": "https://..."},
    outputs=["DESIGN.md"],
    phase_after=Phase.DESIGN_EXTRACTED,
)

# Later, check what's stale:
report = check_drift(root)
if report.has_drift:
    for row in report.rows:
        if row.status != "fresh":
            print(f"{row.path}: {row.status}")
```

The dev-flow Claude Code skills are **interchangeable consumers** of this package. Tomorrow you can rewrite any of them in TypeScript, swap one for a Cursor variant, or extend with your own — as long as your tool reads/writes the contract correctly, it composes.

---

## Cross-platform support

dev-flow is designed to be **runtime-portable**. The contract (`.workflow/`) is just JSON + Markdown + folders, the helper scripts are pure Python, and the skill bodies are tool-name-agnostic prose. The only Claude Code-specific bit is the discovery mechanism — and that's solved per-runtime by a small bootstrap file.

### Support matrix

| Runtime | Install path | Bootstrap | Status |
|---|---|---|---|
| **Claude Code** | `~/.claude/skills/` | none — auto-discovered | ✅ fully tested |
| **Codex CLI** (OpenAI) | `~/.codex/dev-flow-skills/` | `AGENTS.md` (auto-copied) | 🧪 scaffolded, not yet validated end-to-end |
| **Copilot CLI** (GitHub) | `~/.config/gh-copilot/skills/` | none — `skill` tool auto-discovers | 🧪 scaffolded |
| **Gemini CLI** (Google) | `~/.gemini/skills/` | `GEMINI.md` (auto-copied) | 🧪 scaffolded |
| **Cursor** | `~/.dev-flow-skills/` | `.cursorrules` (auto-copied) | 🧪 scaffolded |
| **Generic** (any LLM agent) | `~/.dev-flow-skills/` | `system-prompt.md` (manual integration) | 🧪 scaffolded |

`🧪 scaffolded` means: the install path + bootstrap file are wired and tested for shape (`./install.sh --platform codex` produces the right tree), but full end-to-end runs against the real runtime haven't been validated yet. If you try one and hit issues, please [file an issue](https://github.com/lukedj78/dev-flow/issues) — happy to iterate.

### What makes it portable

1. **Tool-name mapping** — the skill bodies use Claude Code names (`Bash`, `Read`, `Edit`, `Glob`, `Grep`). The `bootstrap/tool-mappings.md` reference (installed alongside the skills) is the canonical Claude → Codex → Copilot → Gemini → Cursor equivalence table. The LLM reads it once at session start and translates as it goes.

2. **Bootstrap files** for runtimes that don't auto-discover skills:
   - `bootstrap/templates/AGENTS.md` — Codex CLI entry point
   - `bootstrap/templates/GEMINI.md` — Gemini CLI entry point
   - `bootstrap/templates/.cursorrules` — Cursor entry point
   - `bootstrap/templates/system-prompt.md` — generic system-prompt fallback for custom agents

3. **`dev-flow-contract` Python package** — the runtime-independent core. Any Python-capable agent can read/write `.workflow/` correctly without depending on any specific runtime:
   ```python
   from dev_flow_contract import init_workflow, record_artifact, check_drift
   ```

4. **Agent-agnostic helper scripts** — `init_workflow.py`, `update_meta.py`, `check_drift.py`. They're invoked by shell, so every runtime can use them via whatever shell tool it has.

### Per-runtime usage guide

Six recipes — install once, then per-project. Same skill content, same `.workflow/` contract, different loading mechanism.

#### Claude Code (native)

Install once:
```bash
git clone https://github.com/lukedj78/dev-flow.git
cd dev-flow
./install.sh
```

Use it on any project:
```bash
mkdir ~/projects/my-app && cd ~/projects/my-app
claude            # open Claude Code here
```

Then say:
> *"I want to build a CRM for veterinary clinics."*

Auto-discovery picks the skills from `~/.claude/skills/`, `dev-flow` orchestrator routes. Nothing to configure per project.

#### Codex CLI (OpenAI)

Install once:
```bash
./install.sh --platform codex
# → ~/.codex/dev-flow-skills/ + ~/.codex/dev-flow-skills/AGENTS.md
```

Per project:
```bash
mkdir ~/projects/my-app && cd ~/projects/my-app
cp ~/.codex/dev-flow-skills/AGENTS.md .
codex
```

Codex reads `AGENTS.md` at session start. The template tells it where the skills live, how to translate Claude tool names to Codex equivalents (`Bash` → `shell`, `Edit` → `apply_patch`), and how to update `meta.json` after each step.

> *"I want to build a CRM for veterinary clinics."*

**Minimal variant** (if you don't want to copy AGENTS.md to every project):
```bash
echo "Load instructions from ~/.codex/dev-flow-skills/AGENTS.md" > AGENTS.md
```

#### Copilot CLI (GitHub)

Install once:
```bash
./install.sh --platform copilot
# → ~/.config/gh-copilot/skills/
```

No per-project bootstrap — Copilot CLI auto-discovers skills like Claude Code.

```bash
cd ~/projects/my-app
gh copilot suggest "I want to build a CRM for veterinary clinics"
```

Verify the install:
```bash
gh copilot skills list | grep dev-flow
```

#### Gemini CLI (Google)

Install once:
```bash
./install.sh --platform gemini
# → ~/.gemini/skills/ + ~/.gemini/skills/GEMINI.md
```

Per project:
```bash
mkdir ~/projects/my-app && cd ~/projects/my-app
cp ~/.gemini/skills/GEMINI.md .
gemini
```

Gemini reads `GEMINI.md` at session start. Skills are activated via `activate_skill` when a trigger pattern matches.

> *"I want to build a CRM for veterinary clinics."*

#### Cursor

Install once:
```bash
./install.sh --platform cursor
# → ~/.dev-flow-skills/ + ~/.dev-flow-skills/.cursorrules
```

Per project:
```bash
mkdir ~/projects/my-app && cd ~/projects/my-app
cp ~/.dev-flow-skills/.cursorrules .
cursor .
```

Open Cursor's chat (`Cmd+L`) and say:
> *"I want to build a CRM for veterinary clinics."*

**Honesty caveat**: Cursor doesn't have a native skills system. The skills become *prompt augmentation* loaded via `.cursorrules` — not auto-routing. Quality depends on how well Cursor follows the rules; on long sessions it can drop references. Works better if you guide explicitly: *"Use the prd-from-idea skill to draft a PRD."*

#### Custom agent (LangChain, OpenAI Assistants, raw API)

Install once:
```bash
./install.sh --platform generic
# → ~/.dev-flow-skills/ + ~/.dev-flow-skills/system-prompt.md
```

Prepend `system-prompt.md` to your agent's system prompt. Examples:

**LangChain**
```python
from langchain.prompts import SystemMessagePromptTemplate

with open("/Users/you/.dev-flow-skills/system-prompt.md") as f:
    dev_flow_prompt = f.read()

system_msg = SystemMessagePromptTemplate.from_template(
    dev_flow_prompt + "\n\nYou are a coding assistant…"
)
```

**OpenAI Assistants API**
```python
from openai import OpenAI
client = OpenAI()

assistant = client.beta.assistants.create(
    name="My Dev Agent",
    instructions=open("/Users/you/.dev-flow-skills/system-prompt.md").read(),
    tools=[{"type": "code_interpreter"}],
    model="gpt-4o",
)
```

The agent **must** have:
- Filesystem read/write to `~/.dev-flow-skills/` (so it can read SKILL.md files).
- Shell execution (so it can call the Python helpers: `init_workflow.py`, `update_meta.py`, `check_drift.py`).

Without both, the contract operations don't work.

### Universal commands (any runtime)

These are runtime-agnostic — every platform calls them via shell:

```bash
# Show project state
python3 ~/.<platform>/<skills-dir>/dev-flow/scripts/show_state.py .

# Detect drift after manual edits to contract files
python3 ~/.<platform>/<skills-dir>/dev-flow/scripts/check_drift.py . --plan
```

Or, from any Python runtime that installed the contract package:

```bash
pip install -e ~/dev-flow/contract-package
```

```python
from dev_flow_contract import init_workflow, check_drift, record_artifact
```

### Picking the right runtime

| If… | Use | Why |
|---|---|---|
| You want zero-config + best auto-routing | **Claude Code** | The skills were designed for it; matching is unambiguous |
| You're already on the OpenAI CLI / prefer OpenAI models | **Codex CLI** | Solid `AGENTS.md` support, but you'll need to validate (not e2e tested) |
| You work in GitHub repos and want everything via `gh` | **Copilot CLI** | Auto-discovery + natural fit with git/PR workflows |
| You want Google models / huge context windows | **Gemini CLI** | 1M+ token context useful on big projects |
| Your IDE is Cursor and you don't want to switch tools | **Cursor** | No tool-switch, but routing is weaker — you'll be more explicit |
| You're building a custom agent | **Generic** | `system-prompt.md` is the smallest possible starting point |

**Honest disclaimer**: today only Claude Code has been tested end-to-end. The other 5 are scaffolded — install paths and bootstraps are wired, but full project runs haven't been validated. If you try one and it works, [open an issue](https://github.com/lukedj78/dev-flow/issues) so the support matrix can be updated; if it doesn't work, **also** open one — fixes come from feedback.

### Porting to a runtime not listed

If your agent runtime isn't in the matrix:

1. Create a bootstrap file mirroring the structure of `bootstrap/templates/system-prompt.md`.
2. Add your runtime's tool names to `bootstrap/tool-mappings.md` (PRs welcome).
3. Add a case to `install.sh`'s platform switch.

The skill bodies and the contract don't need to change — only the bootstrap layer.

---

## Documentation

- 📐 **[Architecture](./docs/architecture.md)** — the `.workflow/` contract, the `meta.json` schema, the phase enum, file conventions.
- 🛠 **[Conventions](./docs/conventions.md)** — folder layout (`components/site/` vs `app/<route>/_components/`), server actions in `lib/server/<domain>`, theme system with keyboard shortcut, showcase template.
- 📚 **[Case studies](./docs/case-studies.md)** — three projects built with the suite (Aetherfield editorial, Notarius CRM, Wisely fintech). Each shows which skills were used and what was generated.
- 🤖 **[Full walkthrough](./docs/example-full-walkthrough.md)** — one product ("Helmsman" AI support desk) exercising all 33 skills, phase by phase: core → design → monorepo → web → mobile → agent (eve) → voice/realtime → deploy.
- 🔁 **[Loop engineering](./docs/loop-engineering.md)** — runbook for an autonomous Linear → Claude Code → PR loop on a Hetzner server (the harness that *repeats* one dev-flow iteration). Project-agnostic; eve is one optional payload.

---

## The 33 skills, in detail

> `dev-flow`, `prd-from-idea`, and `prd-to-tasks` are **stack-agnostic** — all three stacks use them. The 13 web-stack skills assume `meta.json#stack.framework="next"` (and `stack.nextjs_version="16"` — Pages Router and pre-16 are refused); the 15 mobile-stack skills assume `"expo-rn"`; the 3 monorepo-stack skills assume `"monorepo"`. The 2 refactor skills (`promote-component`, `composition-patterns-guide`) are stack-agnostic and work across all three. `dev-flow` reads that key and routes.

### Web stack (Next.js + shadcn/ui)

### `dev-flow` — the orchestrator

**When to use it:** when you want to *not* think about which skill comes next. Paste an idea / a Figma URL / images, and `dev-flow` figures out the right specialist to invoke based on `phase` in `meta.json`.

```
phase=empty            → prd-from-idea
phase=idea_captured    → prd-from-idea (expand)
phase=prd_drafted      → branches by stack.framework:
                         "next"    → prd-to-tasks  OR  figma-to-design-md  OR
                                     image-to-design-md  OR  design-md-to-app
                         "expo-rn" → rn-bootstrap (mobile scaffold)
phase=tasks_split      → figma-to-design-md  OR  image-to-design-md  OR  design-md-to-app
phase=design_extracted → "next"    → design-md-to-app
                         "expo-rn" → rn-bootstrap
phase=scaffolded       → "next"    → screenshot-to-page  OR  module-add
                         "expo-rn" → rn-add-screen  OR  rn-module-add  OR  rn-write-tests
phase=page_generated   → module-add (next)  OR  rn-module-add (expo-rn)  OR  more screen-gen
phase=module-added     → write-tests / rn-write-tests  OR  iterate
                         (expo-rn) → eventually  rn-eas-deploy  once feature-complete
phase=feature_complete → (expo-rn only) rn-eas-deploy
phase=deployed         → (expo-rn only) maintenance loop: rn-add-screen for new features,
                         rn-eas-build-submit-update for OTA hotfixes
```

`dev-flow` does not do specialist work itself — it **only routes** and updates state. If you find it doing PRD drafting or scaffolding directly, that's a bug.

**Bundled scripts:**
- `scripts/init_workflow.py <project-root> [--name "Project Name"]` — creates `.workflow/` with a fresh `meta.json`.
- `scripts/show_state.py <project-root>` — prints current phase, files present, proposed next step.

### `prd-from-idea` — paragraph → PRD

**Input**: a paragraph or two describing what you want to build.
**Output**:
- `.workflow/PROJECT.md` — strategic brief (audience, problem, value prop, success criteria).
- `.workflow/PRD.md` — product requirements (user stories, acceptance criteria, non-goals, open questions).

**How it works**: the skill asks you 5–8 high-leverage questions, parses your answer, fills the templates. It refuses to invent: if you can't answer "who is this for", it writes `<TBD — needs user input>` rather than guess.

### `prd-to-tasks` — PRD → executable checklist

**Input**: `.workflow/PRD.md` (and `.workflow/PROJECT.md` for context).
**Output**: `.workflow/tasks.md` with 1 task per `- [ ]` checkbox. Compatible with **beads**, **GitHub Issues import**, **Linear CSV**, **ralph-tui**.

**Sizing**: each task ≈ 2–8 hours of focused work. If a task is bigger, the skill splits it. If smaller, it merges with a sibling. Output ≤ ~15 tasks for an MVP.

### `linear-scrum` — Linear + agile scrum for a dev-flow project

**Input**: `.workflow/meta.json` (+ `.workflow/tasks.md` for first setup) and a connected Linear MCP.
**Output**: a Linear Project with issues (estimates, `area:web`/`area:agent` labels, milestones) and cycles, plus the `linear`/`scrum` blocks in `meta.json`. Linear is treated as the source of truth: sync only pushes new tasks, pulls status/velocity, plans the active sprint up to the velocity target, and reports — it never bumps `phase`.

**Modes**: Setup (new project), Adopt (existing Linear project), Sync (ongoing — push new tasks, pull status/velocity, plan sprint, report).

### `figma-to-design-md` — Figma → DESIGN.md

**Input**: a Figma URL (`figma.com/file/`, `/design/`, `/proto/`, `/board/`, `/site/`).
**Output**: `.workflow/DESIGN.md` (Google design.md spec) + `.workflow/screenshots/` (HD captures).

**3 access paths, picked automatically**:
- **A — Figma Dev Mode MCP**, if a `mcp__figma*` tool is exposed.
- **B — Figma REST API**, if a `FIGMA_ACCESS_TOKEN` env var is set.
- **C — Manual / Playwright-assisted**, if a browser tool is available; falls back to asking the user for screenshots.

The skill validates the output against the Google spec before writing (frontmatter delimited correctly, `colors.primary` defined, no duplicate sections, dimensions in `px/em/rem` only, all `{path.to.token}` references resolve).

### `image-to-design-md` — 1+ raster images → DESIGN.md

**Input**: 1 or more PNG / JPG / WebP images (screenshots of competitor apps, Pinterest pins, Dribbble shots, Figma exports).
**Output**: `.workflow/DESIGN.md` + `.workflow/screenshots/<slug>.png` for each image.

**How it works**:
- **Palette**: k-means quantization on the cropped pixels (`scripts/quantize_palette.py`); when there are multiple images, `scripts/aggregate_palettes.py` merges near-duplicates and rewards colors that recur across screens.
- **Typography**: vision-LLM identifies font lookalike + estimates sizes / weights / line-heights from pixel measurements. Proprietary fonts (Söhne, Wise Sans, Cera Pro) are recognized AND mapped to a Google Fonts open-source fallback that the DESIGN.md emits as `fontFamily`.
- **Components**: vision-LLM detects buttons / cards / inputs / nav / badges; emits the `components` block with the variants seen.
- **Layout / shapes / elevation**: inferred from corners + spacing + shadow patterns visible in the images.

The skill is explicit about confidence: every guess is flagged in the prose. A 1-image input where text isn't visible produces a stub `typography:` block + a prominent note ("typography pending — supply a second image with visible text").

### `design-md-to-app` — DESIGN.md → working app

**Input**: `.workflow/DESIGN.md` + `.workflow/meta.json#stack`.
**Output**: a fully scaffolded codebase at the project root (NOT inside `.workflow/`), with:

- Framework installed (Next.js + Tailwind v4 by default; Vite + React, Remix, Astro variants supported via `references/<framework>-<ui>.md`).
- shadcn/ui via the **token-first registry approach**: emits `<root>/registry.json` from DESIGN.md, runs `pnpm dlx shadcn@latest init ./registry.json --yes`, then `pnpm dlx shadcn@latest add --all --yes`. Every primitive lands in `components/ui/` pre-themed.
- **shadcn CLI v4 awareness**: picks the primitive base via `stack.ui_base` (`radix` default | `base` for Base UI — `shadcn create --base`), plus icon library / CSS variables / RTL. If you built a config on [ui.shadcn.com/create](https://ui.shadcn.com/create), pass the **preset code** as `stack.shadcn_preset` and the skill scaffolds with `--preset` instead of the DESIGN.md token install (preset XOR DESIGN.md-tokens). A **confirmation gate** prints the full resolved config and waits for your OK before scaffolding.
- **Theme system**: `next-themes` + `<ThemeProvider>` + a `<ModeToggle>` button with a global `D` keyboard shortcut (excluded when typing in inputs).
- **Folder skeleton**: `components/<group>/` for cross-route shared, `app/<route>/_components/` for page-scoped, `lib/server/<domain>.ts` for server actions, `lib/queries/<domain>.ts` for reads, `hooks/`.
- **Site-shell components**: `SiteTopNav`, `WordmarkFooter`, `MarketingShell` for public pages; `AppShell` for authenticated routes; `Eyebrow` helper.
- **`/showcase` route**: a 9-section design-system documentation page (Color tokens, Typography ladder, Buttons, Cards, Inputs, Badges, Radius, Spacing, Do's/Don'ts) — non-skippable in dev-flow mode.
- **Placeholder routes** for every nav item declared in DESIGN.md / screenshots / PRD, so no link goes to `/_not-found`.
- **Server actions stub**: at least one `lib/server/<domain>.ts` with Zod schemas + `ActionResult<T>` discriminated union + `flattenZod` helper, as a referenceable pattern.

The structure is mandatory in dev-flow mode — see [docs/conventions.md](./docs/conventions.md).

### `screenshot-to-page` — screenshot → working route

**Input**: one image from `.workflow/screenshots/` + `DESIGN.md` + `meta.json#stack`.
**Output**: a real route in the codebase (`app/<route>/page.tsx`) with extracted reusable components.

**Workflow**:
1. **Pattern detection**: scan the screenshot for repeated visual patterns (3 cards same shape → extract one `<Card>` + map; 5 nav items → extract `<NavItem>`).
2. **Map to design system**: every color / radius / spacing must reference a DESIGN.md token. If you need a value that doesn't exist, the skill asks before adding.
3. **Pixel-perfect loop** (when a browser tool is available): build → take screenshot at the same viewport → diff vs. reference (`scripts/visual_diff.py`) → fix the worst region → repeat until delta < 2% (or 8 iterations).
4. Imagery is left as `bg-muted` placeholders with `{/* TODO: replace */}` comments — the skill doesn't fabricate photography.

### `module-add` — wire backend / infra modules

**Input**: a module name from the supported list.
**Output**: dependencies installed, config files written, a reference implementation at the canonical path, `meta.json#stack` updated, schema additions applied.

| Module | Tech | Status |
|---|---|---|
| `auth` | better-auth (email/password + magic link) | ✅ shipped |
| `db` | Drizzle ORM + Neon Postgres | ✅ shipped |
| `payments` | Stripe (subscriptions + one-time + webhook + portal) | ✅ shipped |
| `email` | Resend + React Email | ✅ shipped |
| `test` | Vitest + Testing Library + Playwright | ✅ shipped |
| `ci` | husky + lint-staged + GitHub Actions | ✅ shipped |
| `motion` | Motion (rebranded framer-motion) + opinionated wrappers (FadeIn, StaggerList, MagneticButton) | ✅ shipped |
| `voice` | Realtime voice over the Vercel AI Gateway (`@ai-sdk/gateway` + `experimental_useRealtime`); STT → agent → TTS topology | ✅ shipped (experimental API) |
| `realtime` | App-level WebSockets (Vercel Functions `experimental_upgradeWebSocket`); presence / chat / collab, external store for shared state | ✅ shipped (experimental API) |
| `storage` | UploadThing / S3 | 🚧 planned |
| `deploy` | Vercel / Fly / Cloudflare Pages | 🚧 planned |

The skill is **idempotent**: re-running `module-add db` on a project that already has it detects the install and skips, instead of double-installing. Cross-module dependencies are resolved automatically (`auth` requires `db`; `payments` requires both — the skill prompts before chaining).

### `write-tests` — generate a test for one source file

**Input**: one source file path (`lib/server/clienti.ts`, `app/clienti/page.tsx`, `components/site/site-top-nav.tsx`, `lib/queries/scadenze.ts`).
**Output**: the corresponding test file, written next to the source or in `e2e/`, following the project's existing mocking conventions and test framework (Vitest / Playwright).

**Trigger phrases**: "scrivi i test per X", "test per la server action Y", "e2e per /clienti", "unit test per il componente Z".

| File pattern | Test type | Path |
|---|---|---|
| `lib/server/<domain>.ts` | Vitest unit (server action) | `lib/server/__tests__/<name>.test.ts` |
| `lib/queries/<domain>.ts` | Vitest unit (query) | `lib/queries/__tests__/<name>.test.ts` |
| `app/<route>/page.tsx` | Playwright e2e | `e2e/<route-slug>.spec.ts` |
| `components/<group>/<name>.tsx` | Vitest + RTL | co-located `.test.tsx` |

**Prerequisite**: `module-add test` has been run (Vitest + Playwright are wired). If not, the skill stops and routes there. **Idempotent**: existing test files are never silently overwritten — the user is asked whether to regenerate, append missing cases, or abort.

**What it does NOT do**: install test packages, run a full suite, fix failing tests. A failing test is a signal — the skill surfaces it, the user decides whether to fix the test or the source.

### `eve-agent` — scaffold + grow the AI agent engine (`apps/agent`)

**Input**: a monorepo with `stack.agent = "eve"` (opted into at stack-decision time, or added on demand).
**Output**: an [eve](https://eve.dev) agent at `apps/agent` (Vercel's filesystem-first agent framework) that the web app consumes as its engine — or one new capability added to an existing agent.

The agent counterpart to `design-md-to-app` + `module-add`: where those build/grow the Next.js app, `eve-agent` builds/grows the agent. **Two modes**, one logical operation per run (idempotent):
- **Scaffold mode** (no `apps/agent` yet): `agent.ts` + `instructions.md`, the default HTTP channel, a baseline eval, and `packages/types` (re-exported eve session/event types). The web app consumes it via the official `withEve()` + `useEveAgent()` integration.
- **Capability mode** (agent exists): add ONE file — a tool (`agent/tools/<name>.ts`), skill, channel, connection (MCP/OpenAPI), schedule, subagent, or hook — plus its eval.

**The one rule**: never guess the eve API — the source of truth is the bundled docs at `node_modules/eve/docs/`. Non-idempotent tools (payments, deletes, external writes) are approval-gated, because eve replays durable steps. It sits **outside** the `phase` line (its own capability cadence, often Linear-driven), recording only `stack.agent` + `history`. References: `eve-conventions.md`, `eve-scaffold.md`, `eve-capabilities.md`, `eve-web-integration.md`; script `check_eve_state.py`.

> Voice and realtime pair naturally: `module-add voice` puts a voice surface **over** the eve agent (STT → agent → TTS — eve stays the brain, voice is I/O), and `module-add realtime` covers user-to-user realtime that the agent doesn't own. Never run two competing control loops.

### `forms` — one toolkit for every form (Next.js 16 App Router)

**Input**: a form to scaffold or edit (edit panel, create dialog, settings page).
**Output**: a Client Component leaf that goes through `lib/forms/` — `useEditForm` / `useCreateForm` + `<FormProvider>` + `<FormField>` + `<FormActions>` + `mapFormError` — with explicit Save button gated by dirty + valid state, baseline reset on success, AbortController, and discriminated-union error mapping.

**Two library backends, identical consumer code**, picked at scaffold via `meta.json#stack.forms`:
- `"tanstack-form"` (default, recommended) — `@tanstack/react-form` + Zod v4 underneath.
- `"react-hook-form"` (opt-in) — `react-hook-form` + `@hookform/resolvers/zod` underneath.

Hook names, render layer, error contract, and dirty semantics are identical across both. The choice is invisible to consumers — only `lib/forms/` knows which library it wraps. The skill **refuses to apply** if `stack.framework ∉ {"next", "monorepo"}` or `stack.nextjs_version != "16"`.

**Bans** (lint + skill-enforced): `useState` for field values, raw `useForm` outside `lib/forms/`, auto-save / save-on-blur / debounce, inline `toast.success`/`toast.error` from form components, hand-rolled dirty tracking, `<form onSubmit>` that calls `fetch` directly.

**Audit mode**: "audit my codebase against the forms skill" runs 10 ripgrep checks (A–J), produces a severity-sorted report, offers fixes in order (toolkit first, mixed-library second, raw `useForm` + inline toasts third, missing dirty-gating fourth, etc.).

Derived from `lusentis/next-skills/nextjs-forms` (MIT) — see `forms/SKILL.md` Sources section.

### `data-fetching` — read in Server Components, mutate via Server Actions

**Input**: a data read in a Next.js 16 App Router app.
**Output**: the read landed in the correct place per the four-rung ladder:
1. **Async Server Component** (default, ~90% of cases) — `await listX()` at the top.
2. **URL `searchParams`** — filter / tab / range state moves to the URL; page stays a Server Component.
3. **`Promise<T>` + `use()` + `<Suspense>`** — when a Client Component genuinely needs server data as props at mount (charting libs, third-party widgets).
4. **Route Handler + SWR / React Query** — last resort, narrow scope: polling, focus refetch, third-party-mutated data.

Server Actions are for **mutations only** — never reads. After mutating, call `revalidatePath` / `revalidateTag` / `refresh()` and let the Server Component re-render. Never `useState + useEffect + fetch` in a Client Component. Never `useEffect` driving a Server Action call.

**Why**: Server Actions are queued sequentially. Reading via action in `useEffect` costs SSR, streaming, request deduping, caching, parallelism — and produces no error to warn you. The bug is silent.

**Refuses to apply** if `stack.framework ∉ {"next", "monorepo"}` or `stack.nextjs_version != "16"` (Pages Router has a different mental model entirely).

**Audit mode**: 7 violation kinds (A–G), greps for each, severity-sorted report, fix order with toolkit-first prioritization.

Derived from `lusentis/next-skills/nextjs-data-fetching` (MIT).

### `state-discipline` — eight-rung ladder before reaching for `useState`

**Input**: a `useState + useEffect` pair, a bare `useEffect`, or a "should I `useState` here?" question.
**Output**: refactor applied at the right rung of an 8-step ladder:
1. **Derive** during render (don't store-and-sync).
2. **URL state** for shareable / back-button-correct state.
3. **Lift** state to the nearest common parent (don't mirror).
4. **Server state** belongs on the server (route to `data-fetching`) — or in a query library if it must be client.
5. **Side effect after user click** → event handler, not `useEffect`.
6. **Reset on identity change** → `key={prop}`, not `useEffect`.
7. **One-time external sync** (DOM API, third-party widget, focus management) → `useMountEffect` (project's explicit-intent escape hatch with a single localized `eslint-disable`).
8. **Honest local UI state** (hover, dropdown-open, animation flag) → `useState` is fine. Move on.

**Bans bare `useEffect`** via lint:
```json
{ "selector": "CallExpression[callee.name='useEffect']",
  "message": "Bare useEffect is banned. Use useMountEffect or walk the ladder." }
```

Covers also `useOptimistic` (over hand-rolled optimistic UI), `useTransition` (non-blocking heavy updates), `key`-based reset, and the explicit `useMountEffect` helper.

**Refuses to apply** outside Next.js 16 / App Router. The principles transfer to other React 19 setups, but the URL/Server-Component rungs do not.

**Audit mode**: 8 violation kinds (A–H), report with prioritized fix order.

Derived from `lusentis/next-skills/nextjs-usestate` (MIT) — renamed `state-discipline` because the rules cover all state-shaped decisions, not only `useState`.

### Mobile stack (Expo + React Native)

The 15 mobile skills mirror the web stack philosophy: opinionated defaults, idempotent operations, contract-driven state. Activate by saying "mobile" / "iOS" / "Android" at the target-platform question in `prd-from-idea` — that sets `meta.json#stack.framework="expo-rn"`.

**Stack opinions baked in** (Wave 1–3):

- Expo SDK ultimo stabile + **TypeScript** + **New Architecture ON** + **npm** (not yarn/pnpm).
- **Expo Router** for navigation (file-based + typed routes).
- **NativeWind v4** for styling (Tailwind 3.4.x pinned — TW 4 incompatible today).
- **Zustand** for global state, **TanStack Query v5** for server state.
- **Reanimated 4 + Gesture Handler 2** for animations and gestures.
- **`expo-image`** instead of RN's `Image`, **`@shopify/flash-list`** for any list > 20 items.
- **`expo-secure-store`** for tokens (never AsyncStorage).
- **EAS** for cloud build, submit, and OTA updates.
- **RevenueCat** for IAP (Apple 3.1.1 enforcement), Stripe only for non-digital.
- **Jest + React Native Testing Library** for unit/integration, **Maestro** for e2e (Detox banned).

**Knowledge skills (10)** — guardrails that auto-activate when the agent enters that domain:

| Skill | When it triggers |
|---|---|
| `rn-fundamentals` | Start of any RN/Expo task; choices about managed vs bare, SDK, New Architecture. |
| `rn-styling` | NativeWind setup, Flexbox in RN, safe-area, dark mode, design tokens. |
| `rn-expo-router` | File-based routing, layouts, typed routes, deep linking, modals. |
| `rn-components-apis` | Which RN primitive to use (`Pressable`, `expo-image`, `FlashList`, `KeyboardAvoidingView`, `Linking`, `Platform.select`). |
| `rn-data-fetching` | TanStack Query queries/mutations/optimistic/infinite scroll. Bans `fetch + useEffect` for production data. |
| `rn-animations-gestures` | Reanimated worklets, layout animations, pan/pinch/scroll-linked. |
| `rn-push-notifications` | `expo-notifications`, permission timing, 3 entry paths, deep linking from payload. |
| `rn-backend` | **Provider-agnostic**: client-auth patterns (secure-store, Zustand auth, refresh-on-401, auth gate). Sub-references for **Supabase** (default) / **Firebase** / **custom REST** / **tRPC**. |
| `rn-eas-build-submit-update` | EAS Build profiles, credentials, EAS Submit, OTA via EAS Update + channels, EAS Workflows CI. |
| `rn-publishing-payments` | App Store + Play Store metadata, RevenueCat IAP, store assets, review-rejection patterns. |

**Operative skills (5)** — invoked by `dev-flow` when the orchestrator routes to mobile:

| Skill | Phase | What it does |
|---|---|---|
| `rn-bootstrap` | `prd_drafted` → `scaffolded` | Scaffolds a new Expo app from PRD + DESIGN.md. 4-script chain (init → install → wire-NativeWind → verify). Idempotent. |
| `rn-add-screen` | `scaffolded` → `page_generated` | Adds a route to `app/` via 5 canonical templates (list / detail / form / modal / auth-gated). Wires data layer if needed. |
| `rn-module-add` | `scaffolded` → `module-added` | Wires `auth` / `db` / `storage` / `realtime` / `push` / `payments` modules. Provider-agnostic (Supabase, Firebase, custom REST, tRPC, RevenueCat). |
| `rn-write-tests` | any | Jest + RNTL + Maestro setup + tests for one source file. Mirrors `write-tests` for RN. |
| `rn-eas-deploy` | `feature_complete` → `deployed` | End-to-end deploy: pre-submission checklist → preview build → smoke → production build → EAS Submit → channels. Refuses incomplete checklist. |
| `rn-upgrade` | any (maintenance) | Upgrades an Expo/RN project's SDK: `expo install --fix` → `expo-doctor` → cache clear → prebuild (CNG vs bare) → breaking-changes checklist. Defers per-version detail to Expo docs/MCP. |

**Use case — idea to App Store**:

```
1. paste idea → prd-from-idea ("target: mobile") → sets stack.framework="expo-rn"
2. dev-flow proposes Mobile bundle (Supabase + RevenueCat + EAS) → user confirms
3. rn-bootstrap → app scaffold (10 min)
4. rn-module-add auth → Supabase wired
5. rn-add-screen "login form" → app/(auth)/sign-in.tsx generated
6. rn-add-screen "feed" → app/(app)/feed.tsx with TanStack Query + FlashList
7. rn-module-add payments → RevenueCat paywall
8. rn-write-tests → Jest covers feed + auth
9. rn-eas-deploy → preview → production → submit to both stores
```

Typical timeline: 12–16 hours of focused work from PRD to live submission.

**Single-source canonical reference**: [`dev-flow/references/stack-expo-rn.md`](./dev-flow/references/stack-expo-rn.md) — what `stack.framework="expo-rn"` means, which skill for which phase, what keys live under `meta.json#stack`, which web skills are NEVER invoked on this stack (`design-md-to-app`, `module-add`, `screenshot-to-page`, etc. are web-only).

### Monorepo stack (turborepo: web + mobile + shared packages)

The 3 monorepo skills compose a single repo where both a Next.js web app AND an Expo + RN mobile app live side-by-side, sharing types, design tokens, and the backend client. Activated by answering "both / monorepo" at the target-platform question in `prd-from-idea` (sets `meta.json#stack.framework="monorepo"`).

**Stack opinions baked in**:

- **pnpm workspaces + turborepo** (only — no yarn/nx/lerna).
- **One `.workflow/`** in repo root, shared by both apps (one PRD, one DESIGN.md).
- **3 mandatory packages**: `packages/shared/` (types + Zod + business logic), `packages/design/` (DESIGN.md → Tailwind + NativeWind presets), `packages/api/` (backend client + queries).
- **No cross-platform UI library** — web uses shadcn/Base UI/MUI, mobile uses NativeWind. Components stay platform-specific.
- **Backend shared, payment split**: auth/db/storage shared via `packages/api/`; web payments via Stripe, mobile via RevenueCat (Apple 3.1.1 mandate).
- **Deploy split**: web on Vercel, mobile on EAS — two pipelines in parallel.

**The 3 monorepo skills**:

| Skill | When it triggers |
|---|---|
| `monorepo-bootstrap` | Phase `prd_drafted` + `stack.framework="monorepo"`. Scaffolds root configs (pnpm-workspace.yaml, turbo.json, tsconfig.base.json), invokes `design-md-to-app` in `apps/web/`, invokes `rn-bootstrap` in `apps/mobile/`, generates the 3 shared package skeletons, patches Metro config for the workspace topology. Idempotent. |
| `monorepo-add-shared-package` | "Estrai questa logica in shared", "crea un package @<slug>/forms condiviso". Creates a new package OR extracts files from an app into an existing/new shared package, updates path aliases in `tsconfig.base.json`, adds the package as `workspace:*` to both apps. Two modes: create-empty and extract-from-app. |
| `monorepo-sync-types` | "Rigenera i tipi da Supabase", "sync DB schema". Provider-aware: Supabase → `supabase gen types typescript`, tRPC → TS inference re-export, Firebase → manual + Zod runtime validation, custom REST → Zod/OpenAPI/manual. Always writes into `packages/shared/src/types/`. |

**Use case — idea to two-platform launch**:

```
1. paste idea → prd-from-idea ("target: both/monorepo") → stack.framework="monorepo"
                + stack.monorepo.web.ui="shadcn" + stack.monorepo.mobile.ui="nativewind"
2. dev-flow → monorepo-bootstrap → root configs + apps/web + apps/mobile + packages/
3. module-add db --supabase → installs in packages/api/, both apps consume @<slug>/api
4. monorepo-sync-types → packages/shared/src/types/database.ts generated
5. screenshot-to-page (web) + rn-add-screen (mobile) → screens for both
6. rn-module-add payments revenuecat (apps/mobile/) + module-add payments stripe (apps/web/)
7. monorepo-add-shared-package forms → shared form validators between apps
8. setup-deploy → Vercel for apps/web/; rn-eas-deploy → EAS for apps/mobile/
9. (live!) one PRD, one DESIGN, two apps in production, shared backend + types.
```

**Single-source canonical reference**: [`dev-flow/references/stack-monorepo.md`](./dev-flow/references/stack-monorepo.md) — what `stack.framework="monorepo"` means, the full `stack.monorepo` object shape, phase routing including the new `monorepo_initialized` phase, monorepo-aware patches required across the other skills.

---

### Refactor skills (stack-agnostic)

Two skills that work across all three stacks (web, mobile, monorepo), focused on **keeping component architecture clean as projects grow**:

| Skill | When it triggers |
|---|---|
| `promote-component` | "Scan promotion candidates" / "Promovi PostCard". Implements the **Rule of Three** (Sandi Metz "The Wrong Abstraction"): components stay at L0 until the 3rd use, then promote to L1 (`app/(group)/_components/`) or L2 (`components/shared/<dominio>/`). Two modes: scan (analyze codebase + report markdown table) and promote (move file + rewrite all imports + tsc verify + atomic commit). Monorepo-aware. |
| `composition-patterns-guide` | "Refactor this component" / "too many boolean props" / "compound component". Codifies the **7 Vercel composition-patterns rules** (avoid boolean prop proliferation, compound components with shared context, context interface `{state, actions, meta}`, lift state into providers, children over render props, explicit variants, React 19 no-forwardRef) plus our colocation rules. Knowledge skill — provides the thinking framework. |

The canonical model for shared components is the **3-level hierarchy** documented in `docs/superpowers/specs/2026-06-06-folder-structure-refactor.md`:

```
L0  app/<route>/_components/<Name>.tsx       page-private (default)
L1  app/(group)/_components/<Name>.tsx       route-group shared
L2  components/shared/<dominio>/<Name>.tsx   globally shared
```

Plus 2 special folders that don't follow promotion: `components/ui/` (shadcn/Base UI/MUI primitives) and `components/theme/` (ThemeProvider, ModeToggle).

---

## How the skills compose

A typical "from scratch to running app" session uses the skills in this order:

```
1. dev-flow             → init `.workflow/` + ask the user what they want to build
2. prd-from-idea        → PROJECT.md + PRD.md
3. prd-to-tasks         → tasks.md (optional)
4. figma-to-design-md   → DESIGN.md + screenshots/
   OR
   image-to-design-md   → DESIGN.md + screenshots/
   OR
   manual               → user pastes their own DESIGN.md
5. design-md-to-app     → scaffolded codebase + theme + showcase + placeholder routes
6. screenshot-to-page   → for each screenshot, generate a real route (loop)
7. module-add db        → Drizzle + Neon
8. module-add auth      → better-auth
9. module-add (others)  → payments / email / storage / deploy as needed
```

Or in one sentence:

> **An idea → a working, themed, branded Next.js app with theme toggle, server actions, db, auth, and 12 routes — all driven by 8 small skills sharing one `.workflow/` folder.**

---

## Anatomy of `.workflow/`

```
<project-root>/                   ← codebase root (Next/Vite/Remix)
├── .workflow/                    ← planning + design metadata
│   ├── meta.json                 ← single source of truth
│   ├── PROJECT.md                ← high-level brief
│   ├── PRD.md                    ← requirements
│   ├── tasks.md                  ← task breakdown
│   ├── DESIGN.md                 ← Google design.md spec
│   └── screenshots/              ← raw / annotated UI references
├── package.json                  ← codebase at root
├── app/, components/, lib/       ← framework conventions
├── registry.json                 ← shadcn token registry
└── …
```

`meta.json` schema (excerpt):

```json
{
  "project_slug": "wisely",
  "project_name": "Wisely",
  "phase": "module-added",
  "stack": {
    "framework": "next",
    "ui": "shadcn",
    "auth": "better-auth",
    "db": "neon-drizzle"
  },
  "history": [
    { "skill": "prd-from-idea", "phase_after": "prd_drafted", "ran_at": "..." },
    { "skill": "image-to-design-md", "phase_after": "design_extracted", "ran_at": "..." },
    { "skill": "design-md-to-app", "phase_after": "scaffolded", "ran_at": "..." },
    { "skill": "module-add", "phase_after": "module-added", "inputs": { "module": "db" } },
    { "skill": "module-add", "phase_after": "module-added", "inputs": { "module": "auth" } }
  ]
}
```

The full schema is in [docs/architecture.md](./docs/architecture.md).

---

## When you'd skip a skill

| You have | Skip |
|---|---|
| A DESIGN.md already written | `figma-to-design-md` + `image-to-design-md`. Just `cp` your file into `.workflow/`. |
| A Figma file | `image-to-design-md`. Use Figma path B (REST API with token) for highest precision. |
| Only inspiration images | `figma-to-design-md`. Use `image-to-design-md` instead. |
| A scaffold already running | `design-md-to-app`. Theme-only mode applies a DESIGN.md to existing code. |
| No screenshots | `screenshot-to-page`. Hand-write the routes. |
| No backend yet | `module-add`. Stays empty until the user wants persistence. |

---

## What's intentionally NOT in dev-flow

- A code-generation tool that writes business logic for you. The skills generate **structure + conventions + first-pass UI**. Business logic stays human.
- A CMS. Content layer is project-specific.
- Hosting. `module-add deploy` produces config; the actual deploy is your call.
- Analytics / observability. Too project-specific to template.

---

## What comes next — when dev-flow hands you the keys

When the skills are done, you have:

- A scaffolded app with routing, theme system, dark/light toggle, server-action conventions.
- A `/showcase` page proving the design system landed.
- (Optionally) auth, db, tests, CI wired up via `module-add`.
- A `lib/server/<domain>.ts` reference action that you can copy-evolve.

What dev-flow does **not** do — these are your work as the developer:

1. **Real business logic.** The server-action template returns mock data. You write the actual mutations (`db.insert(...)`, `db.update(...)`) for your domain.
2. **Real forms wired to the actions.** The scaffold ships one stub form per declared route. You bind real inputs, real Zod schemas, real `useFormState` (or React 19's `useActionState`) per page.
3. **Production env vars.** `.env.local.example` is a checklist — fill `.env.local` with real values from your Neon/Vercel/Stripe dashboards.
4. **Migrations to a real DB.** Switch from `pnpm db:push` to `pnpm db:generate` + commit + `pnpm db:migrate` once you have data that matters.
5. **Tightening the CSP.** `next.config.ts` ships a permissive default Content-Security-Policy. Tighten it as you remove inline scripts/styles.
6. **Real photography / iconography.** Image placeholders are `bg-muted` divs with `TODO` comments. Replace with `next/image` + your CDN.
7. **Test coverage.** `module-add test` ships smoke tests. Real coverage (unit + integration + E2E for critical flows) is yours.
8. **A11y audit.** The scaffold passes basic checks (semantic landmarks, focus rings, reduced-motion). Run axe-core or Lighthouse on every shipped page before launch.

If any of these feel too big to tackle alone, dev-flow's siblings ([screenshot-to-page](./screenshot-to-page) for new pages, `module-add` for new infra) keep working — call them again whenever you need a fresh page or a new module.

---

## Contributing

The skills are **plain folders** with a `SKILL.md` + `references/` + optional `scripts/`. To add a new skill or modify an existing one, follow the [skill-creator](https://github.com/anthropics/skills) conventions and contribute via PR.

To add a new module variant to `module-add` (e.g., Clerk auth, Supabase db), drop a new `references/module-<name>.md` following the same pattern as `module-auth.md` / `module-db.md`. The orchestrator picks it up automatically.

### Maintenance scripts

The repo ships three top-level scripts (in `scripts/`) you can run anytime:

```bash
# Sanity-check every skill (frontmatter YAML, portable paths, snake_case phases,
# sibling cross-references, installer coverage)
python3 scripts/lint_skills.py

# Regenerate skills.json (the machine-readable registry of all 33 skills)
python3 scripts/build_skills_registry.py

# Repackage the dist/<name>.skill bundles from source (keeps dist/ in sync; run
# after editing any SKILL.md / references / scripts / assets)
python3 scripts/build_skill_bundles.py          # all 33
python3 scripts/build_skill_bundles.py dev-flow # or just one

# Check for npm version drift in the RN/Expo stack-defaults pin set
./scripts/refresh-stack-defaults.sh          # dry-run, print diff
./scripts/refresh-stack-defaults.sh --apply  # rewrite the stack-defaults.md files
```

CI runs `lint_skills.py` + `build_skills_registry.py` on every PR (see `.github/workflows/lint-skills.yml`); a missing or stale `skills.json` will fail the workflow.

---

## License

MIT — see [LICENSE](./LICENSE).
