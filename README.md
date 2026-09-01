# dev-flow

![dev-flow v1.0.0 — map of the 45 skills: phase pipeline (Plan · Design · Build · Ship), web/mobile/agent tracks, eve agent engine, cross-cutting layers and pre-deploy gates, the three rules every skill is held to plus the ecosystem-first library defaults, plugin install, full index](./docs/assets/dev-flow-map-v1-r12.png)

**📖 [Browse the 44 skills →](https://lukedj78.github.io/dev-flow/)** — one page per skill: what it does, when it applies, what it deliberately doesn't, and the references it ships. Generated from `skills.json`, so it can't drift from the suite.

<sub>The poster above is the interactive map (dark/light): [`docs/dev-flow-skill-map.html`](./docs/dev-flow-skill-map.html)</sub>

> **A filesystem contract for agent-driven SDLC.**
> One folder (`.workflow/`), one state file (`meta.json`), and **45 skills (6 core + 16 web + 2 agent + 16 mobile + 3 monorepo + 2 refactor)** that read/write it. The contract is the product — the skills are durable, replaceable consumers.
>
> **v1.0.0** — install as a Claude Code plugin: `/plugin marketplace add lukedj78/dev-flow` then `/plugin install dev-flow@dev-flow`. Other runtimes (Codex · Copilot · Gemini · Cursor) use [`install.sh`](#1-install-the-skills). See the [CHANGELOG](./CHANGELOG.md).
>
> The web family now includes **`eve-agent`** — scaffold and grow an [eve](https://eve.dev) agent as the AI engine behind a Next.js app, opted into via `stack.agent`. It lives inside the app, in `apps/agent`, or **alone at the repo root** when the product has no UI at all ([three topologies](#eve-agent--scaffold--grow-the-ai-agent-engine)). See [docs/example-full-walkthrough.md](./docs/example-full-walkthrough.md) and the autonomous-loop runbook [docs/loop-engineering.md](./docs/loop-engineering.md).
>
> **Rule zero — doc-grounded, never invent.** The skills are a second brain: when one says *"use library X"*, it ships the **how** from X's official docs, prefers the **version-matched** source the tool itself ships (`next dev` maintains an `AGENTS.md` block pointing at bundled docs; eve ships `node_modules/eve/docs`), marks fast-moving identifiers `[VERIFY]`, and gets re-verified on a cadence — logged in [docs/vercel-changelog-watch.md](./docs/vercel-changelog-watch.md). The map of every how-to is **[docs/knowledge-index.md](./docs/knowledge-index.md)**.
>
> **Golden rules** (enforced on every project, see the contract): **① code is written in English** (identifiers, constants, comments — independent of the conversation language); **② every frontend ships i18n from day one** — web via [next-intl](https://next-intl.dev/), mobile via the RN i18n stack, minimum locales **English + Italian**, no hardcoded user-facing copy.

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
              │   WEB FAMILY (15 skills)           MOBILE FAMILY (16 skills)
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
 design-md              vercel-deploy                       rn-eas-deploy
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

Two ways in, two philosophies. The **plugin** subscribes you to the suite as a managed bundle that updates when we ship. **`install.sh`** copies the skill files so you can fork and hack on them — and it's the route for Codex / Copilot / Gemini / Cursor. Pick one; installing both leaves you with every skill twice.

#### Option A — Claude Code plugin (recommended)

```bash
/plugin marketplace add lukedj78/dev-flow
/plugin install dev-flow@dev-flow
```

All 44 skills arrive namespaced (`dev-flow:forms`, `dev-flow:rn-bootstrap`, …), and `/plugin marketplace update` pulls new releases. The shipped set is generated from the canonical taxonomy, so what you install always matches [`skills.json`](./skills.json) and the [CHANGELOG](./CHANGELOG.md).

#### Option B — bundled `install.sh` (editable copies, all runtimes)

```bash
git clone git@github.com:lukedj78/dev-flow.git
cd dev-flow
./install.sh                          # defaults to Claude Code
./install.sh --platform codex         # or Codex CLI / Copilot / Gemini / Cursor
./install.sh --list-platforms         # see all supported runtimes
```

The script copies all 45 skill folders into the platform-appropriate location (e.g. `~/.claude/skills/`, `~/.codex/dev-flow-skills/`, `~/.gemini/skills/`), drops in the right bootstrap file (`AGENTS.md`, `GEMINI.md`, `.cursorrules`) when needed, and backs up any pre-existing version with the same name to `<skill>.bak`. To uninstall + restore backups: `./uninstall.sh --platform <same>`.

**Portability**: dev-flow's skills are designed to be runtime-portable. See [Cross-platform support](#cross-platform-support) below.

#### Option C — `/plugin add` a single skill (local development)

If you have the repo cloned locally:

```
/plugin add /path/to/dev-flow/dev-flow
/plugin add /path/to/dev-flow/prd-from-idea
…
```

Run once per skill folder. Useful if you only want to install a subset.

#### Option D — `gh skill install` (GitHub CLI extension)

```bash
gh extension install <ext-author>/gh-skill          # one-time
gh skill install lukedj78/dev-flow                   # private repo, requires auth
# OR for a specific subset
gh skill install lukedj78/dev-flow dev-flow design-md-to-app
```

This works with the same `gh auth` you already use to clone private repos.

#### Option E — drag-and-drop the `.skill` files

The `dist/` folder contains packaged `.skill` archives. Drag them into your Claude Code window one at a time — useful when you don't have shell access on the target machine. (`dist/` is regenerated periodically; the newest skills — e.g. `eve-agent` — may ship source-only until repackaged, so prefer `install.sh` for the full set.)

#### Verify

```bash
ls ~/.claude/skills/ | wc -l
# Should print 45. Restart Claude Code if you don't see them in /skills.
```

The **core happy-path** skills (the web flow most projects start with):

| Skill | What it does |
|---|---|
| **`dev-flow`** | The orchestrator — reads `.workflow/meta.json` and proposes what to do next |
| `prd-from-idea` | Idea paragraph → `PROJECT.md` + `PRD.md` |
| `prd-to-tasks` | `PRD.md` → `tasks.md` (importable into beads / Linear / GitHub Issues) |
| `linear-scrum` | Take a project into Linear and run it with agile scrum — cycles, estimates, sprint planning, velocity reports; Linear as source of truth |
| `compliance-audit` | GDPR + EU AI Act audit of an existing project (10-point risk register) + safe auto-remediation; flags legal decisions. Horizontal; proposed as a pre-deploy gate |
| `spec-review` | Review a diff on two axes — does it match `PRD.md`/`tasks.md`, and does it obey the contract it was built under? Parallel sub-agents, reported side by side, never merged |
| `figma-to-design-md` | Figma URL → `DESIGN.md` (Google design.md spec) + screenshots |
| `image-to-design-md` | 1+ raster images → `DESIGN.md` + screenshots |
| `design-md-to-app` | `DESIGN.md` → scaffolded Next.js + shadcn app with theme + showcase + folder convention |
| `coss-ui` | Coss/UI (Cal.com design system on Base UI) via the shadcn `@coss/*` registry — Init/Add modes, DESIGN.md token reconciliation; requires Tailwind v4, mixed MIT/AGPLv3 license |
| `screenshot-to-page` | One screenshot → one route, with pixel-perfect verification loop |
| `module-add` | Wire `auth` / `db` / `payments` / `email` / `test` / `ci` / `motion` / `voice` / `realtime` / `storage` / `deploy` modules |
| `write-tests` | One source file (server action / page / component / query) → its Vitest or Playwright test, following the project's existing patterns |
| `vercel-deploy` | Ship the web app: preview → smoke → staged production → promote → domains + DNS, with a rollback runbook. The only skill that sets `phase = "deployed"` for web |

`install.sh` installs **all 45 skills**, not just these. Beyond the core flow above: the `compliance-audit` capability, the web discipline skills (`forms`, `data-fetching`, `state-discipline`, `transitions`), the web add-ons (`heroicons-animated` animated icons, `vercel-doctor` cost/perf and `shadscan` UI-quality pre-deploy gates, `vercel-deploy` the ship step), the agent engine (`eve-agent`, `eve-registry-porting`), the 2 refactor skills (`promote-component`, `composition-patterns-guide`), the 16 mobile `rn-*` skills, and the 3 monorepo skills. Full breakdown in [The 45 skills, in detail](#the-44-skills-in-detail).

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

### 8. Load one skill from a URL, without installing anything

**Situation**: an agent that is not Claude Code — v0, Codex, an eve agent in Slack, a hosted
assistant — needs one of these skills for a single job, and cannot run `./install.sh`.

Every `SKILL.md` here is a conforming Agent Skill and this repository is public, so each one already
has a stable raw URL:

```
https://raw.githubusercontent.com/lukedj78/dev-flow/main/<skill>/SKILL.md
```

Point the agent at that and it has the skill. Vercel does the same thing with
[`vercel.com/design.md`](https://vercel.com/design.md) — a single public file their agents load to
produce on-brand pages from tools that have no access to the repository.

Two limits worth knowing before relying on it:

- **`references/` do not come along.** A `SKILL.md` that says "see `references/contracts.md`" is
  giving the agent a relative path it cannot resolve from a raw URL. Either fetch the reference
  explicitly at its own raw URL, or use the packaged `dist/<skill>.skill` bundle, which carries
  every file.
- **`main` is a moving target.** For anything you want to be reproducible, pin the URL to a commit
  SHA instead of `main` — the same reason a lockfile exists.

The counterpart pattern from the same Vercel piece is worth taking too: **judgement in prose, the
mechanics in an artefact the agent never reads.** Their skill carries the design reasoning; the
published stylesheet carries the class names and tokens and loads in the browser, and the skill
explicitly forbids reading its implementation into context. The agent cannot drift what it never
sees. Our equivalent is the generated theme layer — once `design-md-to-app` has written it, the
downstream skills consume its names and must not invent new ones.

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

- 🌐 **[lukedj78.github.io/dev-flow](https://lukedj78.github.io/dev-flow/)** — the browsable index, one page per skill. Generated from the taxonomy by `scripts/build_site.py`; `--check` keeps it from going stale.

- 📐 **[Architecture](./docs/architecture.md)** — the `.workflow/` contract, the `meta.json` schema, the phase enum, file conventions.
- 🛠 **[Conventions](./docs/conventions.md)** — folder layout (`components/site/` vs `app/<route>/_components/`), server actions in `lib/server/<domain>`, theme system with keyboard shortcut, showcase template.
- 📚 **[Case studies](./docs/case-studies.md)** — three projects built with the suite (Aetherfield editorial, Notarius CRM, Wisely fintech). Each shows which skills were used and what was generated.
- 🤖 **[Full walkthrough](./docs/example-full-walkthrough.md)** — one product ("Helmsman" AI support desk) exercising all 45 skills, phase by phase: core → design → monorepo → web → mobile → agent (eve) → voice/realtime → deploy.
- 🔁 **[Loop engineering](./docs/loop-engineering.md)** — runbook for an autonomous Linear → Claude Code → PR loop on a Hetzner server (the harness that *repeats* one dev-flow iteration). Project-agnostic; eve is one optional payload.
- 📇 **[Knowledge index](./docs/knowledge-index.md)** — the map of every doc-grounded how-to: which domain, which reference, which upstream to re-verify. Start here when wiring a library or running a knowledge refresh.
- 🧠 **[Obsidian](./docs/OBSIDIAN.md)** — this repo is also an Obsidian vault (config committed): graph view over skills → references, backlinks, full-text search across all 45 skills.
- 🔤 **[CONTEXT.md](./CONTEXT.md)** — the ubiquitous language: what *skill*, *family*, *phase*, *reference*, *gate*, *module* mean here, and the words to avoid (three different things are called "registry" — always qualify it).
- 📋 **[CHANGELOG.md](./CHANGELOG.md)** — semver on the suite as a whole; what a major/minor/patch bump means for the contract.
- 🚫 **[.out-of-scope/](./.out-of-scope/)** — decisions *not* to build, each with what would change our mind. Read before proposing something that was already evaluated.

---

## Repository layout

```
<skill-name>/                45 skill folders, FLAT at the root
├── SKILL.md                 the skill (frontmatter: name + description)
├── references/*.md          its doc-grounded how-tos, recipes, vendored contract
└── scripts/*                its executable helpers + tests
docs/                        cross-cutting docs, knowledge index, assets
scripts/                     repo tooling (registry + manifest + bundle builders, linter)
dist/                        generated <skill>.skill bundles (one per skill)
.claude-plugin/              plugin.json (generated) + marketplace.json — plugin distribution
.out-of-scope/               decisions not to build, with what would change our mind
.obsidian/                   committed vault config (see docs/OBSIDIAN.md)
bootstrap/ contract-package/ evals/   templates, the contract as a package, eval fixtures
README.md · CONTEXT.md (glossary) · CHANGELOG.md · install.sh · uninstall.sh · skills.json
```

**Why the skill folders are flat, not nested by family.** The root mirrors the install target (`~/.claude/skills/<name>/`) one-to-one, keeps ~385 cross-skill reference paths valid, and matches what Claude Code / Codex / Gemini expect. The six-family grouping is **logical, not physical**: it lives in the `TAXONOMY` map in [`scripts/build_skills_registry.py`](./scripts/build_skills_registry.py) and is published in `skills.json`. That map is the single source of truth for family + role — a skill missing from it is a **build error**, never a silent default, so the counts here and in `install.sh` can't drift out of sync again.

---

## The 45 skills, in detail

> 6 skills are **stack-agnostic core**: `dev-flow`, `prd-from-idea`, `prd-to-tasks`, `linear-scrum`, `compliance-audit`, and `spec-review` — all three stacks use them. The 15 web-stack skills assume `meta.json#stack.framework="next"` (and `stack.nextjs_version="16"` — Pages Router and pre-16 are refused); the 2 agent-engine skills (`eve-agent`, `eve-registry-porting`) assume `stack.agent="eve"`; the 16 mobile-stack skills assume `"expo-rn"`; the 3 monorepo-stack skills assume `"monorepo"`. The 2 refactor skills (`promote-component`, `composition-patterns-guide`) are stack-agnostic and work across all three. `dev-flow` reads that key and routes.

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
                         → eventually the stack's deploy skill, once feature-complete
phase=feature_complete → gates (any stack): compliance-audit  +  vercel-doctor (web on Vercel)
                         "next"    → vercel-deploy
                         "expo-rn" → rn-eas-deploy
                         eve agent → eve deploy
phase=deployed         → "next"    → maintenance loop: screenshot-to-page / module-add,
                                     re-run the gates after material changes
                         "expo-rn" → maintenance loop: rn-add-screen for new features,
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

### `compliance-audit` — GDPR + EU AI Act audit & remediation

**Input**: an **existing** dev-flow project (any stack — Next.js web, Expo mobile, or an eve agent) + `.workflow/meta.json#stack`.
**Output**: `docs/compliance/audit-report.md` (findings with severity · GDPR/AI-Act article · `file:line` evidence · fix), a `meta.json#compliance` block, and — in Remediate mode — the safe mitigations applied as reviewable diffs (DSAR export/erasure endpoints, cookie-consent banner + privacy pages, AI-transparency disclosure, PII-scrubbing logger + retention policy, a sub-processor register generated from `stack`) plus `TODO(compliance)` flags for the legal decisions.

**How it works**: scores the codebase against a fixed **10-point risk register** (R1 DSAR · R2 consent/cookies · R3 EU data residency & transfers · R4 retention/TTL & PII-scrubbing · R5 AI-transparency Art. 50 · R6 high-risk Annex III/DPIA · R7 PII in logs · R8 sub-processors · R9 special-category data · R10 memory/manipulation). `scripts/scan.py` is a fast first-pass signal; every hit is verified in code before it lands in the report. **Auto-applies only the safe, mechanical fixes and flags every decision** (which EU region, legal basis, whether high-risk) — it never decides law for you. Horizontal capability: run it any time; dev-flow proposes it as a **pre-deploy gate** at `feature_complete` and re-runs it in the `deployed` maintenance loop. Records `meta.json#compliance`, never bumps `phase`. **Not legal advice** — it produces engineering findings + a DPIA template; a DPO/counsel confirms.

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
- **shadcn CLI v4 awareness**: picks the primitive base via `stack.ui_base` (**`base` default** — Base UI, shadcn's own default since 2026-07 | `radix` | `aria` for React Aria — `shadcn create --base`), plus icon library / CSS variables / RTL. If you built a config on [ui.shadcn.com/create](https://ui.shadcn.com/create), pass the **preset code** as `stack.shadcn_preset` and the skill scaffolds with `--preset` instead of the DESIGN.md token install (preset XOR DESIGN.md-tokens). A **confirmation gate** prints the full resolved config and waits for your OK before scaffolding.
- **Theme system**: `next-themes` + `<ThemeProvider>` + a `<ModeToggle>` button with a global `D` keyboard shortcut (excluded when typing in inputs).
- **Folder skeleton**: `components/<group>/` for cross-route shared, `app/<route>/_components/` for page-scoped, `lib/server/<domain>.ts` for server actions, `lib/queries/<domain>.ts` for reads, `hooks/`.
- **Site-shell components**: `SiteTopNav`, `WordmarkFooter`, `MarketingShell` for public pages; `AppShell` for authenticated routes; `Eyebrow` helper.
- **`/showcase` route**: a 9-section design-system documentation page (Color tokens, Typography ladder, Buttons, Cards, Inputs, Badges, Radius, Spacing, Do's/Don'ts) — non-skippable in dev-flow mode.
- **Placeholder routes** for every nav item declared in DESIGN.md / screenshots / PRD, so no link goes to `/_not-found`.
- **Server actions stub**: at least one `lib/server/<domain>.ts` with Zod schemas + `ActionResult<T>` discriminated union + `flattenZod` helper, as a referenceable pattern.

- **i18n from day one** (golden rule 2): next-intl wired at scaffold — `[locale]` routing, `messages/{en,it}.json`, provider — so no copy is ever hardcoded. How-to: `references/i18n-next-intl.md`.
- **Visual defaults, opt-in**: maps via [mapcn](https://mapcn.dev/) (`references/maps-mapcn.md`) and illustrations via [Koboyo](https://koboyo.com/icons) (`references/illustrations.md`) — the latter deliberately sparing: `stack.illustrations` defaults to `null`, and hand-drawn art is added only when DESIGN.md's visual language admits it, at emotional moments (first empty state, onboarding, 404), a handful per product.

- **Conversational surfaces are a standard, not a suggestion** (`references/chat-and-typeset.md`): any chat, inbox, comment thread or agent console composes the official shadcn primitives — `MessageScroller`, `Message`, `Bubble`, `InputGroup` — and any rendered markdown goes through **typeset**, never `whitespace-pre-wrap`. The reference implementation is shadcn's own MIT [`chatbot-template`](https://github.com/shadcn-ui/chatbot-template); read it rather than inferring how the pieces fit.

  It also carries the **three human-in-the-loop mechanisms**, which are easy to cross and produce a UI nobody is listening to. *Ask* — a tool with an `outputSchema` and **no `execute`** parks on the client, renders a `<Questionnaire />` (the same component `forms` owns) and returns the human's answer as the tool output. *Approval* — `needsApproval` + `addToolApprovalResponse`. *eve* — `input.requested` on the agent's event stream, answered with `respond()`, and **not** interchangeable with the first two.

The structure is mandatory in dev-flow mode — see [docs/conventions.md](./docs/conventions.md).

### `coss-ui` — Coss/UI, the Cal.com design system on Base UI

**Input**: a project that wants the Cal.com aesthetic, or `meta.json#stack.ui = "coss"`.
**Output**: components installed from the namespaced `@coss/*` shadcn registry, with DESIGN.md tokens reconciled on top.

**How it works**: two modes — **Init** (`shadcn init @coss/style` on a new or empty project: components, the neutral colour system, sidebar variables, base styles, Inter + Geist Mono) and **Add** (pull `@coss/ui`, a single `@coss/<name>`, or particles into a project that already exists). Because Coss ships **the same CSS variable names as shadcn/ui**, the DESIGN.md → tokens pipeline works unchanged: your tokens override theirs in `globals.css`, no bridging layer.

It is a deliberate fourth choice inside the shadcn/Base-UI family, not a default, and it carries two caveats worth stating before you pick it: **Tailwind CSS v4 is required**, and the licence is **mixed MIT / AGPLv3** (`references/deps-and-license.md`). Offer it when someone wants the Cal.com look or an AI-first Base UI kit; `design-md-to-app` still owns the generic scaffold, this skill owns the Coss-specific install and token reconciliation.

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
| `storage` | Vercel Blob (default: server + client uploads, auth-gated, `files` table); UploadThing / S3 + presigned URLs as alternatives | ✅ shipped |
| `deploy` | Vercel project config (link, `vercel.json`, per-environment env vars, EU region, monorepo root directory); `vercel-deploy` does the actual shipping | ✅ shipped |

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

### `eve-agent` — scaffold + grow the AI agent engine

**Input**: a project with `stack.agent = "eve"` (opted into at stack-decision time, or added on demand).
**Output**: an [eve](https://eve.dev) agent (Vercel's filesystem-first agent framework) that the product runs on — or one new capability added to an existing agent.

**Three topologies, and the project picks — `dev-flow` §Topology policy proposes them in this order:**

| | Shape | Choose it when |
|---|---|---|
| **①** | **Single web app**, agent inside it | The product **is** the interface. One deploy, no workspace overhead — the ordinary case |
| **②** | **Monorepo** `apps/web` + `apps/agent` | The agent has its own deploy cadence, channels beyond the web UI, or a second consumer (mobile) that shares types |
| **③** | **Agent only** (`stack.framework = "agent"`) | Every surface is elsewhere — Slack, email, GitHub, Linear — and **nothing needs rendering**. `agent/` sits at the repo root |

Shape ③ is not theoretical: Vercel Labs' [`kody-eve-template`](https://github.com/vercel-labs/kody-eve-template) is exactly that. In it `eve-agent` owns the whole repo and is the **bootstrap** skill, so it bumps `phase` to `scaffolded` — the only topology where it touches phase at all. The web skills correctly refuse an agent-only project: there is no frontend for `forms`, `data-fetching` or `shadscan` to work on.

**Starting at ① costs nothing** — `monorepo-bootstrap` promotes later, and moving `agent/` into `apps/agent/` is a directory move, not a rewrite. Choosing ② up front costs workspace overhead on every command for a second app that may never ship, so the question that settles it is *what is the second consumer?* No answer means ①.

The agent counterpart to `design-md-to-app` + `module-add`: where those build/grow the Next.js app, `eve-agent` builds/grows the agent. **Two modes**, one logical operation per run (idempotent):
- **Scaffold mode** (no `apps/agent` yet): `agent.ts` + `instructions.md`, the default HTTP channel, a baseline eval, and `packages/types` (re-exported eve session/event types). The web app consumes it via the official `withEve()` + `useEveAgent()` integration.
- **Capability mode** (agent exists): add ONE file — a tool (`agent/tools/<name>.ts`), skill, channel, connection (MCP/OpenAPI), schedule, subagent, or hook — plus its eval.

**The one rule**: never guess the eve API — the source of truth is the bundled docs at `node_modules/eve/docs/`. **Ecosystem-first:** it installs from eve's registry (`eve registry search <cap>` → `eve add <kind>/<name>`; third-party shadcn-format sources via `eve registry add`) — the prebuilt [integrations](https://eve.dev/integrations) catalog (50+ MCP/OpenAPI connections, 11+ channels, official extensions) — before hand-rolling. Non-idempotent tools (payments, deletes, external writes) are approval-gated, because eve replays durable steps. It sits **outside** the `phase` line (its own capability cadence, often Linear-driven), recording only `stack.agent` + `history`. For **multi-tenant SaaS** agents it also codifies eve's composed recipes — tenant auth, per-tenant approvals, tenant-scoped long-term memory, runtime/tenant-owned dynamic scheduling, a durable **audit-hook** (Art. 12 traceability), the **read-vs-egress data boundary**, and the **multi-agent team** architecture (lead routes depth-1 to non-overlapping specialists; handoff artifacts travel by id so documents never enter the lead's context) — under one rule: derive tenant/user from the verified session, never from model input. The skill mirrors the **entire eve docs surface** — a `eve-docs-coverage.md` map ties every eve.dev/docs page to a reference. References: `eve-conventions.md`, `eve-scaffold.md`, `eve-capabilities.md`, `eve-web-integration.md`, `eve-patterns.md` (multi-tenant, dynamic, governance, traceability & multi-agent-team recipes), `eve-evals.md` (full eval API), `eve-concepts.md` (agent.ts/compaction, context control, default harness, sandbox, durability, sessions/streaming, HITL, state, dynamic capabilities & workflows, responsible use), `eve-docs-coverage.md` (docs coverage map); script `check_eve_state.py`.

**Ten composed recipes** in `references/eve-patterns.md`, distilled from the docs, from three MIT Vercel Labs templates and from Vercel's own SRE-agent guide. The first four are the multi-tenant backbone (tenant auth · per-tenant approvals · tenant-scoped memory · dynamic scheduling); then traceability and the read-vs-egress boundary; then **three shapes an agent can take** — §7 a **team** (a lead routing to non-overlapping specialists), §8 a **pipeline** (declared stations, and what a run with *nobody watching* may do), §9 an **investigation** (an agent that concludes rather than builds); and §10 the **cross-channel notification**, where `to()` is a handoff and a notification wants the platform API plus an app-owned outbox.

Read §8 the moment anything triggers the agent without a human in the room — a webhook, a label, a schedule — because that is when "park for approval" silently becomes "hang forever". Its counter-intuitive core: **deny an unattended run, don't gate it** (a card needs somebody to answer it); **disable eve's built-in `agent` tool** once you have stations, or the orchestrator delegates to a clone of itself and bypasses them; **take a tool's target from auth, not from model input**, so text injected into an issue body can't redirect the write; and for what should never happen, **remove the capability instead of gating it** — a gate is one prompt away from being argued with.

**§9's rule is the one to carry out of here even if you never build an SRE agent**: *a finding may not be deleted because it inconveniences a hypothesis.* An agent may add evidence and may abandon a hypothesis; it may not tidy away the fact that contradicted one. Anything under pressure to conclude converges quietly otherwise — and the resulting report reads **better** than an honest one, because nothing in it disagrees. The same discipline `shadscan` needs and `spec-review` enforces by refusing to merge its two axes.

> Voice and realtime pair naturally: `module-add voice` puts a voice surface **over** the eve agent (STT → agent → TTS — eve stays the brain, voice is I/O), and `module-add realtime` covers user-to-user realtime that the agent doesn't own. Never run two competing control loops.

### `eve-registry-porting` — port components from public eve registries, tenant-safe

Ports a tool, connection, or skill from a public eve/Flue agent registry (atomeve.dev, evex.sh, agentcn, eveagents.dev) into a multi-tenant eve app without adopting the registry's standalone-agent runtime model — enforcing the conformance checklist (tenant from the verified session, `companyId` in every query, per-tenant encrypted secrets, verified deps only, sensitive actions gated) that keeps third-party registry code tenant-safe. It's the **third** sourcing choice — after eve's official [integrations](https://eve.dev/integrations) and extension packages, before hand-writing — for source you need to own/modify that has no maintained package.

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
2. **URL `searchParams`** — filter / tab / range state moves to the URL; page stays a Server Component (server reads the `searchParams` prop, client writes it with type-safe `nuqs`).
3. **`Promise<T>` + `use()` + `<Suspense>`** — when a Client Component genuinely needs server data as props at mount (charting libs, third-party widgets).
4. **Route Handler + SWR / React Query** — last resort, narrow scope: polling, focus refetch, third-party-mutated data.

Server Actions are for **mutations only** — never reads. After mutating, call `revalidatePath` / `revalidateTag` / `refresh()` and let the Server Component re-render. Never `useState + useEffect + fetch` in a Client Component. Never `useEffect` driving a Server Action call.

**Next 16.3 — Instant Navigation** (stable, opt-in via `cacheComponents` + `partialPrefetching`): the skill covers the Stream / Cache / **Block** levers, the static-shell-vs-App-Shell distinction that explains why a page can be instant on load and blocking on navigation, `use cache: private|remote`, and how Partial Prefetching changes `<Link>` (one reusable shell per route, not one request per link). Adoption routes to Vercel's official migration guide and Skills — we don't hand-roll it.

**Why**: Server Actions are queued sequentially. Reading via action in `useEffect` costs SSR, streaming, request deduping, caching, parallelism — and produces no error to warn you. The bug is silent.

**Refuses to apply** if `stack.framework ∉ {"next", "monorepo"}` or `stack.nextjs_version != "16"` (Pages Router has a different mental model entirely).

**Audit mode**: 7 violation kinds (A–G), greps for each, severity-sorted report, fix order with toolkit-first prioritization.

Derived from `lusentis/next-skills/nextjs-data-fetching` (MIT).

### `state-discipline` — eight-rung ladder before reaching for `useState`

**Input**: a `useState + useEffect` pair, a bare `useEffect`, or a "should I `useState` here?" question.
**Output**: refactor applied at the right rung of an 8-step ladder:
1. **Derive** during render (don't store-and-sync).
2. **URL state** for shareable / back-button-correct state (written client-side with type-safe `nuqs`, not hand-rolled `router.replace`).
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

### `transitions` — one tokenized motion system

**Input**: "add a transition / animation", "animate this", "page transition", "stagger these cards", or a request to **audit** the motion in a codebase.
**Output**: motion routed through one token layer (`lib/motion/tokens.ts` + a CSS-var bridge) and a curated, tokenized library (`lib/motion/transitions.ts`) — entrance/exit, stagger, toggles (modal/dropdown/panel/toast/accordion), hover (lift/tilt/avatar-group), feedback (success check, error shake, number pop, skeleton shimmer), layout, and route/page transitions.

**How it works**: governs motion the way `state-discipline` governs state — reach for the **cheapest technique tier first** (Tailwind + `tw-animate-css` → CSS keyframes → View Transitions API → Motion runtime), always ship a `prefers-reduced-motion` fallback, animate only `transform`/`opacity`, and use tokens instead of magic-number durations/easings. Four modes: **Setup** (scaffold `lib/motion/` from the DESIGN.md motion block), **Apply** (best-fit transition at the lowest viable tier), **Audit** (`scripts/scan_motion.py` first-pass → verified findings), **Refine** (swap hardcoded values → tokens). Sits **above** `module-add motion` (which installs the Motion runtime) and reuses `tw-animate-css`; routes to `module-add motion` only when a spring/layout/gesture effect genuinely needs JS. Records `meta.json#stack.motion`, never bumps `phase`. Web-only — the mobile counterpart is `rn-animations-gestures`.

Inspired by the **[transitions.dev](https://transitions.dev/)** motion library (Jakub Antalík) — this is our token-driven, stack-native take on the idea, not a fork or an install of their package.

### `heroicons-animated` — Motion-animated Heroicons via the shadcn registry

**Input**: "animated icon" / "animate this icon" / "make the bell shake on a new notification".
**Output**: one Motion-animated Heroicon added from the [`@heroicons-animated/*`](https://www.heroicons-animated.com/) shadcn registry (316 icons, MIT) — `shadcn add @heroicons-animated/<name>` — wired with the **accessibility guard the raw components lack**.

**How it works**: each icon is a `registry:ui` `.tsx` built on `motion` that animates on hover and exposes an imperative ref handle (`<Name>IconHandle.startAnimation()/stopAnimation()`) for event-driven control. The skill owns the registry install and enforces two things the library omits: a **`prefers-reduced-motion` guard** (the components animate unconditionally) and timing **aligned to `lib/motion/tokens.ts`**. Ecosystem-first for icons — don't hand-animate an SVG. Sits alongside `transitions` (motion discipline) and `module-add motion` (the runtime it depends on); same namespaced-registry mechanism as `coss-ui`. Web only; no phase bump. RN counterpart: `rn-animations-gestures`.

### `spec-review` — did we build what the PRD asked, the way the contract says?

**Input**: a fixed point to diff against (`main`, a SHA, a tag) in a project with a `.workflow/`.
**Output**: two reports side by side — **Spec** and **Standards** — never merged, with the worst issue *within each axis*.

**How it works**: two parallel sub-agents, one per axis. **Spec** asks whether the diff implements what `.workflow/PRD.md` + `tasks.md` asked for — missing requirements, scope creep, things that look done but are wrong, each quoting the spec line. **Standards** asks whether it obeys the contract the project was built under: the golden rules (English identifiers, i18n from day one), the declared `meta.json#stack` (a diff reaching for a library the project didn't declare is a finding), the discipline skills, and a **Fowler smell baseline** as the floor — with the repo's own docs overriding all of it.

**Why two axes and never one verdict**: a change can follow every convention and implement the wrong feature (Standards pass, Spec fail), or do exactly what the PRD asked while ignoring the declared stack (Spec pass, Standards fail). Merging them lets either hide behind the other.

**Not Claude Code's built-in `/code-review`** — that reviews code generically and knows nothing about `.workflow/`. This one reads the change against *this project's* spec and contract, which is precisely the half a generic reviewer has to guess at. Without a `.workflow/` it refuses and points you there. Proposed when a chunk of work lands (`page_generated`, `module_added`), not only before shipping — a spec finding is cheapest while the branch is still open. Records `meta.json#spec_review`; no phase bump; never blocks. Adapted from [Matt Pocock's `code-review`](https://github.com/mattpocock/skills) (MIT) — the two-axis split and the smell baseline are his.

### `vercel-doctor` — cost & performance pre-deploy gate

**Input**: "my Vercel bill is high" / "optimize for Vercel" / a pre-deploy check on a Next.js-on-Vercel project.
**Output**: a `docs/vercel/doctor-report.md` (health score + findings), the **safe fixes applied**, and the judgment calls **routed to the owning skill**.

**How it works**: wraps the third-party [vercel-doctor](https://www.vercel-doctor.com/) CLI, which scans a Next.js codebase for costly Vercel patterns across six areas — caching that defeats the CDN, dead code, function duration, image waste, excessive invocations, config. The skill applies the mechanical fixes (dead-code removal with `tsc` green, config/image tweaks) and routes the rest to the skill that owns it: caching + invocations → `data-fetching` (Next 16 `"use cache"` / Server-Component reads), images → `design-md-to-app`. The **cost/perf sibling of `compliance-audit`** (legal-risk gate) — both are `feature_complete` pre-deploy gates, both record to `meta.json`, both never bump `phase` or block deploy. Third-party tool, `[VERIFY]` the invocation + license. Refuses for non-Vercel/non-Next targets.

### `shadscan` — UI-quality & accessibility pre-deploy gate

**Input**: "audit my UI" / "check accessibility" / "is this accessible" / a pre-deploy check on a React + shadcn app.
**Output**: `docs/ui/shadscan.json` (score out of 100 + per-category breakdown + file:line evidence), the **confirmed defects fixed**, the **product decisions surfaced** to you, and the rest **routed to the owning skill**.

**How it works**: wraps the third-party [shadscan](https://www.shadscan.com/) CLI — a *deterministic, read-only* static audit (it does not start the app, edit files, call an LLM, upload source, or need secrets) that scores six categories: Foundation, Interaction, States, Accessibility, Forms, Production Polish. The skill reads the `--json` report's `agentHandoff` block, where every actionable carries a **`disposition`** (`fix` / `decide` / `verify`) and a **`confidence`**, plus machine-checkable acceptance criteria. It **opens every `fix` item in the source before touching anything**, treats `decide` items as **product questions for you** (never invents an answer), verifies the advisories in code, and routes the real corrections to whoever owns them — `forms`, `transitions`, `data-fetching`, `design-md-to-app`, `composition-patterns-guide`.

**Why that reading step is the skill.** On the first real run, **only 2 of 9 `fix` items survived it.** shadscan invents nothing — every string it quoted was really in the file it named — but it cannot follow a prop across a component boundary, climb to a wrapper, see through a `render` prop, or know that a subtree renders to WebGL instead of the DOM. A suppressed focus ring whose wrapper carries `focus-within:ring`, a pending state lifted into the parent, a `fallback={null}` inside a `<Canvas>` — all reported, none defects. **The better-composed the codebase, the more false positives it produces.** The skill encodes which rule kinds to trust: *does this file exist?* is reliable, *is this component semantically complete?* is not.

This is the **third pre-deploy gate**, and the one that closes a real hole: `compliance-audit` reads the legal surface and `vercel-doctor` the cost surface, but until now **nothing mechanically verified that the UI we prescribe actually got built**. Two of shadscan's rules are verbatim our own contract — `animations-respect-reduced-motion` is the core rule of `transitions`, and the label/error-association rules are what `forms` specifies.

**The discipline: never optimise for the score.** shadscan says this itself — *do not add unused infrastructure solely to increase the audit score*. A command menu nobody asked for is a regression that scores well. Web only (DOM/React rules); no phase bump; never blocks the deploy on its own.

### `vercel-deploy` — ship the web app to production

**Input**: "deploy" / "ship it" / "manda in produzione", on a project at `feature_complete`.
**Output**: the app live on its production domain, `meta.json#phase = "deployed"`, and a rollback runbook in the user's hands.

**How it works**: the web counterpart of `rn-eas-deploy`, and the **only** skill that moves a web project to `deployed`. It ships; it does not configure — `vercel.json`, the region and the env-var matrix belong to `module-add deploy`, and if they're missing it routes there instead of improvising. The shape is dictated by two documented Vercel behaviours: *the first deployment of a new project is always a production deployment* (so "preview first" doesn't exist on day one, and the skill branches), and a production deploy can be **staged** — `vercel --prod --skip-domain` builds with production env vars while serving no traffic, then `vercel promote` makes it Current without a rebuild. That triad (`--skip-domain` → `promote` → `rollback`) is what Vercel's own docs name as the preferred production commands, over `vercel alias`. Then domains + DNS (apex A record, project-specific CNAME for `www`, never hardcoded), and a rollback runbook that leads with the trap: **after a rollback Vercel turns off auto-assignment of production domains**, so pushes to `main` stop going live until someone promotes. Sets `phase = "deployed"` only once the production domain actually serves the deployment.

### `vgpu-shaders` — should this project reach for WebGPU, and what does it cost?

**Input**: "shader" / "WGSL" / "WebGPU" / "vgpu" / "aggiungi uno shader", or an animated hero that a CSS tier can't express.
**Output**: a grounded *decision* first; then, only if it survives, the `vgpu` wiring — `.wgsl` loader, a `"use client"` canvas, a reduced-motion path, a CI render snapshot, and `meta.json#stack.shaders`.

**How it works**: [`vgpu`](https://vgpu.sh) is Vercel Labs' WebGPU library (MIT), and it ships a **first-party skill generated from its own source docs** — 258 symbols, stamped with `vgpuVersion` + `gitSha`. So this skill **deliberately does not restate the API**: it installs alongside theirs (`npx skills add vercel-labs/vgpu`) and owns the half nobody generates. That half is: vgpu is `transitions`' **Tier 4**, above Motion — a GPU device, a compile step, a render loop and a battery — so don't skip rungs; and vgpu's docs never mention `prefers-reduced-motion`, which this repo requires of *every* transition. The fix is theirs, unconnected: `advance(0)` freezes the clock while frames still render, so reduced motion is **hold the first frame**, not hide the canvas. Plus the CI trap worth knowing before you trust a green build — headless Chrome captures a WebGPU canvas as **black**, so `agent-browser --webgpu --headed` is not optional.

It also covers the uses that are **not** a hero, because WebGPU is a compute API of which rendering is one case: `compute()` + storage ping-pong for simulation (the GPU wins on parallel arithmetic and loses on transfer — a dashboard aggregation belongs in a Web Worker); **`pixelDiff`** as a visual-regression primitive, with `maxByte <= 2` documented as driver noise; **`gpuFrameTime`** as a CI performance gate; headless image generation from data; and `vgpu/scene` for a configurator. Two gaps it names rather than papers over: the compute docs' examples import from `vgpu/mock`, and the landing page advertises MP4 while the shipped docs mention video **nowhere**.

### Mobile stack (Expo + React Native)

The 16 mobile skills mirror the web stack philosophy: opinionated defaults, idempotent operations, contract-driven state. Activate by saying "mobile" / "iOS" / "Android" at the target-platform question in `prd-from-idea` — that sets `meta.json#stack.framework="expo-rn"`.

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
8. vercel-deploy → Vercel for apps/web/; rn-eas-deploy → EAS for apps/mobile/
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

### The rule that closes the loop: install after every edit

**A skill edit is not done until it is installed.** Editing here changes nothing for the agent — it
loads `~/.claude/skills`. That gap is invisible by construction: the lint passes (the repo is correct),
the skill fires (a copy exists), and it is simply the wrong text. It is how 25 corrected skills spent a
day being ignored.

```bash
./install.sh                      # every skill change ends here
python3 scripts/lint_skills.py    # check 12 reports any remaining divergence
```

⚠️ **Don't reach for `skill-doctor` right after an edit** — it grades *past conversations*, so a re-run
immediately after a change returns identical numbers by construction: the sessions it reads used the
old text. Verified, not assumed: the run before and after `./install.sh` matched on every count.

The cadence that works is **install on every edit, `skill-doctor` periodically** — once the edited
skills have been used enough to have a history worth grading. The linter judges an edit; the doctor
judges a habit.

### Two axes of skill rot — and which tool owns which

A skill decays in two independent directions, and catching one tells you nothing about the other.

| Axis | Question | Caught by |
|---|---|---|
| **Is it still true?** | the upstream moved: a module path, a CLI flag, a deprecation, a dead link | a **verification pass** — `npm pack` the package and read its `.d.ts`, `curl` every cited URL, diff the shipped docs |
| **Is it working?** | the skill exists and is accurate, but it never fires, or it fires and the agent still flails | **[`skill-doctor`](https://github.com/warpdotdev/common-skills/blob/main/.agents/skills/skill-doctor/SKILL.md)** (Warp, MIT) |

`skill-doctor` reads **local agent conversation transcripts** — Claude Code's project-history JSONL
among them — scores them against two published rubrics (**efficiency**: rework, cost to the human,
redundant reads, batching, flailing, verification timing; **code quality**: design, correctness,
conventions, tests), then drafts the skill edits the failed conversations justify, as a full proposed
`SKILL.md` plus a unified diff. Everything runs locally; it writes to a scratch directory, never into
the repo.

```bash
npx skills@latest add warpdotdev/common-skills --skill skill-doctor
```

⚠️ **Check the installed copies before trusting any verdict.** The first real run here found **25 of
43 installed skills diverging from the repo** — every one of them a skill corrected that same day. The
grader reads what the agent actually loads, so a stale install makes every finding about the wrong
text. Run `./install.sh` first, then measure — and since `2026-08-28` the linter's twelfth check
tells you when you have not.

⚠️ **It cannot see this repo's skills without being told where they are.** Its collector probes the
conventional roots (`~/.claude/skills`, `~/.agents/skills`, `~/.codex/skills`) and globs `*/SKILL.md`
under each. Our layout is 45 flat folders at the repo root — a valid skills root, just not one it
probes. First run here reported **`skills found: 0`** — a perfectly formed, completely empty report
from which you would conclude that no skill is ever used.

Both traps are closed by [`scripts/skill-doctor.sh`](./scripts/skill-doctor.sh), which passes
`--skills-dir` and **omits `--include-global-skills`**, then refuses to hand back an empty report:

```bash
scripts/skill-doctor.sh ~/src/common-skills
```

The omitted flag is the second trap. Global roots are added *only* under `--include-global-skills`
(`collect_sessions.py:124`), and the collector skips names it has already seen — so with the flag on,
it reads the **installed** copy of every skill and drafts its edits against that. With it off,
`--skills-dir` wins: verified by running it, **45 of 47 skills resolve inside `~/my-skills`** and none
in `~/.claude/skills`. Before, 3 of 368. The price is deliberate — without the global roots the report
cannot see plugin or third-party skills, which is exactly right when auditing our own.

The script reads `skills found:` back out of the collector's summary and **exits `1` when it is zero**,
because a silent zero reads as a finding. Verified by pointing it at a collector that prints zero.

It also warns when transcripts go missing. The collector keys sampled sessions by the `sessionId` inside
the `.jsonl` but writes each transcript to `<harness>-<id>.md`, and a **resumed conversation keeps its
sessionId across two files** — so both records are marked sampled and the second write clobbers the
first. Sessions are ordered newest-first, so the survivor is the older, usually smaller fragment: the
richer transcript is the one that disappears. A real 90-day run marked **13 sampled and wrote 12 files**,
losing a 674-call session to a 13-call one. `sessions_sampled` in the summary counts the deduplicated
keys, so it reports 12 and looks correct.

And read the **`repeated` tool-call count with suspicion in this repo**: it keys on tool + argument
prefix, so `update_meta.py <project> set-phase …` and `update_meta.py <project> record-artifact …`
count as a repeat of each other, as do successive `Edit`s building up one file. A dev-flow session
that advances four phases looks wasteful and is not.

**Install it; don't wrap it.** It is already a maintained MIT skill, so this repo does not ship a copy
— the same call made for `anydoc` and for `vgpu`'s generated API skill. `scripts/skill-doctor.sh` is
not a wrapper around the tool: it vendors nothing and asks you for the path to your own checkout. It
only fixes the two flags and turns one silent failure loud.

**The findings from the first full run** — 54 sessions over 90 days — are written up in
[`docs/skill-doctor-referto.html`](./docs/skill-doctor-referto.html) (in Italian). It is a dated
snapshot, not living documentation: its figures are true as of 28 August 2026 and are deliberately
never re-aligned, the same distinction drawn under `[VERIFY]` between an open question and a dated
stamp.

⚠️ **But a proposal is not a merge, and this repo is unusual: the skills under test *are* the repo.**
An edit that reads well as prose can still be unmergeable here, because the invariants live outside the
file it changed. Before accepting one:

1. **`python3 scripts/lint_skills.py`** — 14 checks. The description cap in particular: over 1024
   characters a conforming client **skips the skill**, so a "clearer" description that grew is a
   regression, not an improvement.
2. **Regenerate in dependency order** — `build_skills_registry.py` **before** `build_site.py`, then
   `build_plugin_manifest.py --check`.
3. **A new skill touches six other places**: the taxonomy row, both installers, the README catalogue,
   and every stated count. Check 11 finds them; it will not write them.
4. **`references/contracts.md` is vendored byte-identically into every skill.** Editing one copy is
   always wrong.

So the useful division is: **skill-doctor proposes from evidence this repo cannot see, and the linter
decides what is mergeable.** Neither replaces reading the diff.

### Writing the `description`

The description is the **only** thing a skill is selected on — the body is never read until it loads. Five rules, all learned the hard way and all enforced by the linter:

1. **It must fit in 1024 characters.** Over the cap a conforming client **skips the skill entirely** — it does not truncate. Seven descriptions once sat within 40 characters of that line; one added sentence would have made a skill silently cease to exist.
2. **Triggers are load-bearing; explanation is not.** Keep every phrase somebody would actually type — in both languages where it matters (`"questionnaire"` *and* `"questionario"`) — and let the body carry the how. Every shortening in this repo came out of duplicated explanation, never out of a trigger.
3. **Anything the body promises, the description must name.** A capability documented in a section whose words never appear here is unreachable: the skill won't load for the request that needs it. Check 8 enforces this; `<Questionnaire />` shipped that way before it existed.
4. **Prefer a folded block — `description: >-`.** An apostrophe inside a single-quoted YAML scalar closes it and breaks the frontmatter, which means the skill fails to load at all. A folded block needs no escaping, so Italian prose (`"crea l'app dal DESIGN.md"`) is safe in it.
5. **Don't list sibling skills.** `dev-flow` enumerated sixteen of them and the list was wrong within weeks. Describe the shape; let the body name names.

### Maintenance scripts

The repo ships eight scripts (in `scripts/`) you can run anytime — four of them are what CI enforces:

```bash
# Sanity-check every skill — 14 checks (frontmatter YAML + the 1024-char
# description cap, portable paths, snake_case phases, sibling cross-references,
# installer coverage, capability reachability, README catalogue coverage,
# every skill count stated in prose, the skill map's per-skill meta, the number of
# checks itself, and whether what is installed still matches this repo)
python3 scripts/lint_skills.py

# Regenerate skills.json (the machine-readable registry of all 45 skills)
python3 scripts/build_skills_registry.py

# Repackage the dist/<name>.skill bundles from source (keeps dist/ in sync; run
# after editing any SKILL.md / references / scripts / assets)
python3 scripts/build_skill_bundles.py          # all 43
python3 scripts/build_skill_bundles.py dev-flow # or just one

# Regenerate the browsable site (docs/index.html + docs/skills/, from skills.json)
python3 scripts/build_site.py           # write
python3 scripts/build_site.py --check   # CI: fail if stale

# Regenerate the plugin manifest (skills allowlist comes from the taxonomy)
python3 scripts/build_plugin_manifest.py
python3 scripts/build_plugin_manifest.py --check   # CI: fail if stale

# Validate the plugin + marketplace manifests with the real Claude Code CLI
claude plugin validate .claude-plugin/plugin.json --strict
claude plugin validate . --strict                  # the marketplace entry

# Check for npm version drift in the RN/Expo stack-defaults pin set
./scripts/refresh-stack-defaults.sh          # dry-run, print diff
./scripts/refresh-stack-defaults.sh --apply  # rewrite the stack-defaults.md files
```

CI runs `lint_skills.py`, `build_skills_registry.py`, `build_agent_plugin.py --check` and `build_site.py --check` on every PR (see `.github/workflows/lint-skills.yml`). A stale `skills.json`, an out-of-date plugin manifest, or a site that wasn't regenerated all fail the workflow.

⚠️ **Run the generators in dependency order: `build_skills_registry.py` *before* `build_site.py`.** The site pages embed values that come from `skills.json` (each skill's line count, among others), so `build_site.py --check` run *first* compares the site against the **old** registry and passes — then regenerating `skills.json` makes the site stale behind your back. A locally-green check followed by a red CI is this ordering, not a flaky runner.

**Six of the fourteen checks exist because the same thing kept happening: the content held and the metadata rotted.** Check 8 catches a capability documented in a skill body but missing from its `description` — the skill would never load for the request that needs it. Check 10 catches a skill that exists but is absent from the README catalogue. Check 11 catches a skill count stated in prose that no longer matches reality — it found six on its first run, four of them in phrasings that a grep for the obvious form ("N skills") never matched — a bare count after "There are", one inside "packaging of all N", and both installers' header comments. It gained a thirteenth pattern later, for the skill map's metric card — a bare `<div class="v">44</div>` with no adjacent word for any prose pattern to catch, which is exactly why it sat wrong through a release. **Check 12** compares what is installed against what is here, and reports rather than fails: a divergence is a fact about your machine, not about the commit. **Check 13** compares the skill map's per-skill meta — the bare `1122·9r·2s` beside each name — against `skills.json`; nothing writes those numbers and no prose pattern can reach them, and on its first run **9 of the 15 rows were wrong**. **Check 14** guards the count in this very sentence, because the commit that added checks 13 and 14 first wrote "13" in three places.

**Regenerating the skill map.** Edit [`docs/dev-flow-skill-map.html`](./docs/dev-flow-skill-map.html), then re-shoot the hero PNG at 1300px wide (the page's own `scrollHeight`, device scale 1.5) into `docs/assets/`. ⚠️ **Force reduced motion when you shoot it** — the sections are `.reveal` (opacity 0 until an IntersectionObserver adds `.in`), so a headless capture renders them blank; the `prefers-reduced-motion` rule is the escape hatch:

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --disable-gpu --hide-scrollbars \
  --force-prefers-reduced-motion --force-device-scale-factor=1.5 --window-size=1300,<scrollHeight> \
  --screenshot=docs/assets/dev-flow-map-v1-r<n>.png file://$PWD/docs/dev-flow-skill-map.html
```

And shoot at **1300 CSS px**, not at whatever width gives 1950 output pixels — 975×2 lands on the same pixel width but a narrower breakpoint, and the layout differs. **Give the file a new name every time** — `dev-flow-map-<version>-r<n>.png` — and update the `README` image path: GitHub's camo proxy caches by URL, so overwriting in place leaves everyone looking at the previous image.

---

## License

MIT — see [LICENSE](./LICENSE).
