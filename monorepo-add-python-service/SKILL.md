---
name: monorepo-add-python-service
description: 'Add a Python service (FastAPI, managed by uv) as an app of a turborepo scaffolded by `monorepo-bootstrap`, wired into pnpm workspaces and the turbo task graph, with a generated TypeScript client so `apps/web` never hand-writes a `fetch`. Two variants: `generic` (any HTTP service) and `ml` (vision/OCR models — one model resident at a time, `model_version` on every response, Metal locally and CUDA in production). Requires `stack.framework="monorepo"` and `phase` in {scaffolded, page_generated, module_added}; records `stack.monorepo.services`; never bumps `phase`. Triggers: "aggiungi un servizio python", "aggiungi un microservizio FastAPI", "apps/ml", "servizio di inferenza", "add a fastapi service to the monorepo", "python app in the monorepo", "expose a model to the web app". Not for: scaffolding the monorepo itself (`monorepo-bootstrap`), a shared TS package (`monorepo-add-shared-package`), backend modules inside the Next app (`module-add`), or an eve agent (`eve-agent`).'
---

# monorepo-add-python-service — a Python app in a JS monorepo, joined at the task graph

Some work does not belong in Node: a vision model, an OCR pipeline, anything whose ecosystem
is Python. The instinct is a second repository, and it costs you the thing a monorepo is for —
one install, one task graph, one CI, one version of the contract between the two sides.

This skill puts a **FastAPI service in `apps/<name>/`**, managed by `uv`, joined to the
monorepo through two seams and no others:

1. a minimal `package.json` whose scripts shell out to `uv run` — turbo runs scripts and does
   not care what is behind them;
2. a **generated TypeScript client** in `packages/api/src/<name>/`, so a schema change breaks
   `apps/web`'s typecheck instead of its users.

> **Versions verified 2026-09-11** — `uv@0.12.13`, `fastapi@0.141.1`, `uvicorn@0.52.4`,
> `pydantic@2.13.5`, `pytest@9.1.1`, `ruff@0.16.7`, `turbo@2.10.12`,
> `openapi-typescript@7.13.0`, `openapi-fetch@0.17.0`. Every reference cites its source next
> to the instruction. `[VERIFY]` marks the surfaces that move.

## Why a `package.json` bridge and not turbo's native Python support

Turborepo **does** discover uv workspace members natively — and it is behind a future flag,
and its own documentation says: *"uv support is experimental and can change at any time. We
encourage you to try it out in side projects, proof-of-concepts, and other environments where
stability is not essential."* ([Python (Experimental)](https://turborepo.dev/docs/guides/tools/python))

It also requires the **repository root** to become a uv workspace — a root `pyproject.toml`,
a root `uv.lock`, `[tool.turbo].name` — which changes what `monorepo-bootstrap` writes, for
every project, to serve one app.

So this skill takes the stable path: the Python app stays a plain pnpm workspace member with a
scripts-only `package.json`, and everything Python-shaped stays inside `apps/<name>/`. Revisit
when the flag graduates — `references/turbo-integration.md` carries the migration note.

## Contract

See `references/contracts.md` (vendored from `dev-flow`). Key facts:

- Reads `<project-root>/.workflow/meta.json#stack.framework` — must be `"monorepo"`.
- Requires `phase` in `{scaffolded, page_generated, module_added}`.
- Records the service in **`stack.monorepo.services`** (array; see the contract's `stack` section).
- Appends `history`. **Does not modify `phase`** — same policy as `monorepo-add-shared-package`:
  this skill adds a capability, it does not advance the build. Never regress `phase`.
- **Golden rule 1** (code in English) applies to everything generated here.
- **Golden rule 2 (i18n) does not apply**: the service has no UI. It returns JSON. Nothing here
  is user-facing text, so there are no locales to add — state this rather than leaving a reader
  to wonder, the way `eve-agent` does for the agent app.

## The ownership pact

`apps/<name>/` belongs to this skill, the way `apps/agent/` belongs to `eve-agent`. Concretely:

- **`design-md-to-app`, `screenshot-to-page`, `forms`, `transitions`, `shadscan`, `coss-ui` and
  the other web skills must never be proposed for this app.** They target a Next.js app with a
  UI; this app has neither. dev-flow's routing table says so — if something proposes them here,
  that is the bug.
- `module-add` operates in `apps/web/`. It does not reach into `apps/<name>/`.
- The two sides meet at exactly two places: the generated client in `packages/api/src/<name>/`
  and the `<NAME>_SERVICE_URL` environment variable. Nothing else crosses.

## When this skill applies

- "aggiungi un servizio python" / "add a fastapi service to the monorepo" / "apps/ml".
- A PRD needs work the JS ecosystem does not do well: vision, OCR, classical ML, scientific
  computing, a library that only exists in Python.
- dev-flow may route here from `scaffolded` / `page_generated` / `module_added` when
  `stack.monorepo.services` is empty and the PRD names such work. It is **proposed, never
  imposed** — a Python service is a stack decision and a second runtime to deploy.

## Knowledge dependencies

- `monorepo-bootstrap/references/structure.md` — the canonical `apps/` + `packages/` layout.
- `dev-flow/references/stack-monorepo.md` — the `stack.monorepo.*` sub-keys.
- `references/service-layout.md` — what lands in `apps/<name>/` and why each file is there.
- `references/turbo-integration.md` — the task graph, and the caching trap that eats a day.
- `references/openapi-client.md` — FastAPI → `packages/api` → a typecheck that fails on drift.
- `references/deploy-container.md` — the Dockerfile, the registry, the runtime, both env sides.
- `references/variant-ml.md` — the model variant: memory, `model_version`, Metal vs CUDA.

## Workflow

### Step 1 — Verify preconditions

Refuse, with the reason and the fix, if any of these is false:

| Check | Message when it fails |
|---|---|
| `.workflow/meta.json` exists | "No dev-flow project here. Run `dev-flow` first." |
| `stack.framework == "monorepo"` | "This skill is monorepo-only. A single Next app has no `apps/` to add to — put the service in its own repo, or run `monorepo-bootstrap` first." |
| `phase` ∈ {scaffolded, page_generated, module_added} | "Need a scaffolded monorepo. Current phase: `<phase>`." |
| `pnpm-workspace.yaml` exists and its globs cover `apps/*` | "`apps/*` is not a workspace glob — the service would be invisible to pnpm." |
| `turbo.json` exists | "No turbo.json at the root: this is not a turborepo." |
| `uv` on `PATH` | "uv is required. Install it: `curl -LsSf https://astral.sh/uv/install.sh \| sh` (macOS/Linux) — see <https://docs.astral.sh/uv/getting-started/installation/>." |

Read `meta.json#project_slug` for the package namespace.

### Step 2 — Collect the inputs

One round-trip, with defaults, and **say the variant out loud** because it changes the
dependency tree and the deploy target:

- **name** — default `ml`. kebab-case. Rejected: `web`, `mobile`, `agent`, `root`, and any
  existing entry in `apps/`.
- **port** — default `8000`. Must not collide with `apps/web` (3000) or an existing service.
- **variant** — `generic` (default for anything else) or `ml`. The `ml` variant adds an
  optional dependency group, a model registry with explicit unloading, and a different
  production image. It does **not** add any inference code.

### Step 3 — Scaffold

```bash
bash <skill>/scripts/scaffold_python_service.sh <project-root> --name <name> --port <port> --variant <generic|ml>
```

Idempotent by construction: every file is written only if absent, and the script reports
`created` / `exists` per path. Re-running it is a no-op that prints what it found. See
`references/service-layout.md` for what each file is and why.

### Step 4 — Register the tasks

Patch the root `turbo.json` — `references/turbo-integration.md` has the exact JSON and the
reason for every key. The one that is not obvious and costs a day if missed:

> `inputs` opts you **out** of turbo's `.gitignore` awareness. A Python package without
> `$TURBO_DEFAULT$` in its `inputs` hashes `__pycache__/`, `.venv/` and `.pytest_cache/`, and
> the cache never hits again. ([Configuring turbo.json → `inputs`](https://turborepo.dev/docs/reference/configuration#inputs))

### Step 5 — Generate the client

```bash
pnpm --filter @<slug>/<name> run openapi     # FastAPI → apps/<name>/openapi.json
pnpm --filter @<slug>/api run build          # openapi.json → packages/api/src/<name>/
```

`apps/web` imports the client and reads `<NAME>_SERVICE_URL` from the environment. A hand-written
`fetch` to the service is the anti-pattern this whole seam exists to prevent — see
`references/openapi-client.md`, which also shows how to make the typecheck the gate.

### Step 6 — Verify, and say what actually ran

```bash
python3 <skill>/scripts/check_python_service.py <project-root> --name <name>
```

It reports **signals**, never a verdict: uv present and its version, the Python version the
service pins, whether the turbo tasks are registered, whether the client exists and is newer
than the schema. Read them and decide; do not paste them as a pass.

Then the real thing, because a signal is not a run:

```bash
pnpm turbo dev --filter @<slug>/<name>     # then: curl -s localhost:<port>/health
pnpm turbo test lint --filter @<slug>/<name>
```

### Step 7 — Record it

`meta.json#stack.monorepo.services` gains one entry, and `history` gains one line:

```bash
python3 <dev-flow>/scripts/update_meta.py <project-root> append-history \
  --skill 'monorepo-add-python-service' \
  --inputs '{"name":"<name>","port":<port>,"variant":"<variant>"}' \
  --outputs '{"app":"apps/<name>","client":"packages/api/src/<name>"}'
```

`phase` is untouched, before and after.

## Common anti-patterns (NEVER do)

- ❌ `fetch("http://localhost:8000/…")` in `apps/web`. The generated client exists so that a
  schema change is a **compile error**, not a runtime 422 nobody sees until production.
- ❌ A hardcoded service URL. `<NAME>_SERVICE_URL`, both locally and on Vercel.
- ❌ `inputs` without `$TURBO_DEFAULT$` — see Step 4.
- ❌ Giving the service the database. It is stateless: input in, JSON out. The exception and
  its cost are in `references/service-layout.md`; taking it without reading that is how two
  services end up owning one schema.
- ❌ Model dependencies in the base dependency set. `torch` in the base install means every
  `uv sync` on every laptop and every CI job pulls gigabytes. `references/variant-ml.md`.
- ❌ Running the `ml` variant in Docker on macOS expecting the GPU. Docker Desktop does not
  expose Metal. Native locally, CUDA container in production.
- ❌ Committing model weights, or caching them inside the repo.

## What this skill does NOT do

- **No inference code.** It scaffolds the contract and the extension points. Which model, how
  it is called, what it returns — product work.
- **No second scaffold.** One service per run. Run it again for another.
- **No deploy.** It writes the Dockerfile and documents the target; pushing the image and
  creating the runtime is the user's move, with credentials this skill never handles.
- **No UI.** Golden rule 2 does not apply here; see Contract.
