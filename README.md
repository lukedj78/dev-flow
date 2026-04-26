# dev-flow

> **A filesystem contract for agent-driven SDLC.**
> One folder (`.workflow/`), one state file (`meta.json`), and a small set of skills that read/write it. The contract is the product — the skills are durable, replaceable consumers.

```
                      ┌────────────────────────┐
                      │  .workflow/meta.json   │ ◄─── single source of truth
                      │  (phase + stack +      │      every skill reads
                      │   history + artifacts) │      every skill writes
                      └─────────┬──────────────┘
                                │
            ┌───────────────────┼───────────────────┐
            │                   │                   │
            ▼                   ▼                   ▼
     prd-from-idea       design-md-to-app     module-add
     prd-to-tasks        screenshot-to-page   (auth, db,
     figma-to-design-md                        payments,
     image-to-design-md                        email, ci, …)
            │                   │                   │
            └───────────────────┼───────────────────┘
                                │
                                ▼
                        Codebase at <project-root>/
```

The skills are **interchangeable consumers** of the contract. Tomorrow you could rewrite any of them in TypeScript, swap one out for a Cursor-flavored variant, or extend with your own — as long as they read `meta.json` and respect the phase semantics, they compose.

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

The script copies the 8 skill folders into the platform-appropriate location (e.g. `~/.claude/skills/`, `~/.codex/dev-flow-skills/`, `~/.gemini/skills/`), drops in the right bootstrap file (`AGENTS.md`, `GEMINI.md`, `.cursorrules`) when needed, and backs up any pre-existing version with the same name to `<skill>.bak`. To uninstall + restore backups: `./uninstall.sh --platform <same>`.

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

The `dist/` folder contains all 8 packaged `.skill` archives. Drag them into your Claude Code window one at a time — useful when you don't have shell access on the target machine.

#### Verify

```bash
ls ~/.claude/skills/ | grep -E "dev-flow|prd-|figma-|image-|design-|screenshot-|module-"
# Should print 8 entries. Restart Claude Code if you don't see them in /skills.
```

The 8 skills are:

| Skill | What it does |
|---|---|
| **`dev-flow`** | The orchestrator — reads `.workflow/meta.json` and proposes what to do next |
| `prd-from-idea` | Idea paragraph → `PROJECT.md` + `PRD.md` |
| `prd-to-tasks` | `PRD.md` → `tasks.md` (importable into beads / Linear / GitHub Issues) |
| `figma-to-design-md` | Figma URL → `DESIGN.md` (Google design.md spec) + screenshots |
| `image-to-design-md` | 1+ raster images → `DESIGN.md` + screenshots |
| `design-md-to-app` | `DESIGN.md` → scaffolded Next.js + shadcn app with theme + showcase + folder convention |
| `screenshot-to-page` | One screenshot → one route, with pixel-perfect verification loop |
| `module-add` | Wire `auth` / `db` / `payments` / `email` / `storage` / `deploy` modules |

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

---

## The 8 skills, in detail

### `dev-flow` — the orchestrator

**When to use it:** when you want to *not* think about which skill comes next. Paste an idea / a Figma URL / images, and `dev-flow` figures out the right specialist to invoke based on `phase` in `meta.json`.

```
phase=empty            → prd-from-idea
phase=idea_captured    → prd-from-idea (expand)
phase=prd_drafted      → prd-to-tasks  OR  figma-to-design-md  OR  image-to-design-md  OR  design-md-to-app
phase=tasks_split      → figma-to-design-md  OR  image-to-design-md  OR  design-md-to-app
phase=design_extracted → design-md-to-app
phase=scaffolded       → screenshot-to-page  OR  module-add
phase=page_generated   → module-add  OR  more screenshot-to-page
phase=module-added     → iterate
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
| `storage` | UploadThing / S3 | 🚧 planned |
| `deploy` | Vercel / Fly / Cloudflare Pages | 🚧 planned |

The skill is **idempotent**: re-running `module-add db` on a project that already has it detects the install and skips, instead of double-installing. Cross-module dependencies are resolved automatically (`auth` requires `db`; `payments` requires both — the skill prompts before chaining).

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

---

## License

MIT — see [LICENSE](./LICENSE).
