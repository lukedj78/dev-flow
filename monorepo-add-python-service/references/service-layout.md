> Sources: <https://docs.astral.sh/uv/concepts/projects/> · <https://docs.astral.sh/uv/concepts/projects/dependencies/> ·
> <https://fastapi.tiangolo.com/> · <https://pnpm.io/workspaces> · internal opinion for the seams.
> Versions verified **2026-09-11**: uv 0.12.13, fastapi 0.141.1, uvicorn 0.52.4, pydantic 2.13.5, pytest 9.1.1, ruff 0.16.7.

# `apps/<name>/` — what lands there, and why each file exists

```
apps/<name>/
├── package.json          ← the bridge: scripts only, no dependencies
├── pyproject.toml        ← the real manifest, managed by uv
├── uv.lock               ← committed; the lockfile IS the reproducibility
├── .python-version       ← 3.12, so `uv run` never picks the system Python
├── .env.example          ← committed; .env is not
├── Dockerfile            ← production only (see deploy-container.md)
├── README.md             ← how to run it WITHOUT Docker, which is how you will run it
├── src/<name>/
│   ├── __init__.py
│   ├── main.py           ← FastAPI app, /health, one typed example endpoint
│   └── schemas.py        ← Pydantic models — the source of the OpenAPI schema
├── tests/
│   └── test_api.py       ← pytest over /health and the example endpoint
└── scripts/
    └── export_openapi.py ← dumps the schema without starting a server
```

## `package.json` — a member with no dependencies

pnpm treats any directory with a `package.json` under a workspace glob as a member; there is no
requirement that it declare dependencies (<https://pnpm.io/workspaces>). That is the whole trick:
turbo runs **scripts**, and a script can be anything.

```json
{
  "name": "@<slug>/<name>",
  "version": "0.0.0",
  "private": true,
  "scripts": {
    "dev": "uv run uvicorn <name>.main:app --reload --port <port>",
    "test": "uv run pytest -q",
    "lint": "uv run ruff check .",
    "typecheck": "uv run ruff check --select F .",
    "build": "uv sync --locked",
    "openapi": "uv run python scripts/export_openapi.py"
  }
}
```

Three deliberate choices:

- **`typecheck` is not mypy.** A type checker is a decision with a cost (annotating a codebase
  that mostly moves tensors around), and turbo needs the task to exist so the graph is uniform.
  Ruff's `F` rules catch the undefined name and the unused import, which is the failure this
  task is actually guarding in a scaffolded service. Swap in `mypy` or `ty` when the service
  earns it — the script name stays.
- **`build` is `uv sync --locked`.** `--locked` fails if `uv.lock` is out of date rather than
  silently resolving something else; it is the CI-safe form (uv docs, *Locking and syncing*).
- **No `dependencies` key at all.** Adding one would make pnpm try to install npm packages for
  a Python app.

## `pyproject.toml`

```toml
[project]
name = "<name>"
version = "0.0.0"
requires-python = ">=3.12"
dependencies = [
  "fastapi>=0.141.1",
  "uvicorn[standard]>=0.52.4",
  "pydantic>=2.13.5",
]

[project.optional-dependencies]
# `ml` variant only — see variant-ml.md. Never in [project.dependencies].
# ml = ["torch>=…", "transformers>=…", …]

[dependency-groups]
# httpx2 is not optional: starlette 1.6 moved TestClient onto it, and without it the
# API tests fail at *collection* with "The starlette.testclient module requires httpx2
# to be installed". Found by running the scaffold (2026-09-11), not by reading a page.
dev = ["pytest>=9.1.1", "ruff>=0.16.7", "httpx2>=2.12.0"]

[tool.ruff]
target-version = "py312"

[build-system]
requires = ["uv_build>=0.12,<0.13"]
build-backend = "uv_build"
```

**Why extras and not a dependency group for the model deps.** uv documents the split plainly:
`[project.optional-dependencies]` are *"published optional dependencies"* and `[dependency-groups]`
(PEP 735) are *"local dependencies for development"*
(<https://docs.astral.sh/uv/concepts/projects/dependencies/>). Model weights are neither dev nor
mandatory — they are an **optional runtime feature**, installed on the GPU host and skipped on a
laptop. That is what an extra is. `uv sync` gets you a working API; `uv sync --extra ml` gets you
one that can run a model.

`dev` as a dependency group is the other half: pytest and ruff are development-only by
definition, and `uv sync --no-dev` in the production image leaves them out.

## `.python-version`

One line: `3.12`. Without it `uv run` resolves against whatever Python it finds, and the service
that works on your machine picks a different interpreter in CI. `uv python pin 3.12` writes it.

## `src/<name>/main.py`

```python
"""FastAPI entrypoint. Stateless: input in, JSON out."""

from fastapi import FastAPI

from .schemas import EchoRequest, EchoResponse, HealthResponse

app = FastAPI(
    title="<name> service",
    version="0.0.0",
    # OpenAPI is on by default at /openapi.json; naming it here is documentation,
    # and the export script reads app.openapi() rather than hitting the server.
    openapi_url="/openapi.json",
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="<name>", version=app.version)


@app.post("/echo", response_model=EchoResponse)
def echo(request: EchoRequest) -> EchoResponse:
    """Example endpoint — replace it. It exists so the generated client has
    something with a request body to type."""
    return EchoResponse(text=request.text, length=len(request.text))
```

The example endpoint is not decoration: a schema with only a `GET /health` generates a client
with no request types, and the first real endpoint then has nothing to copy from.

## `.env.example`

Committed. `.env` is not — `monorepo-bootstrap` already gitignores it.

```bash
# Port uvicorn binds. Must match the port in package.json's dev script.
<NAME>_PORT=<port>
# Comma-separated origins allowed to call this service directly in the browser.
# Empty in the normal setup: apps/web calls it server-side and nothing reaches it from a page.
<NAME>_CORS_ORIGINS=
```

## Stateless by default — and the exception, with its price

The service **does not get the database**. It receives input and returns JSON. Three reasons,
in order of how much they hurt when ignored:

1. **Two owners of one schema.** The moment the Python service reads a table, a Drizzle
   migration in `apps/web` can break it, and nothing in the type system says so. The
   TypeScript client makes the HTTP contract checkable; there is no equivalent for a shared
   Postgres schema across two languages.
2. **Two connection pools** against one database, sized independently, discovered under load.
3. **Deploy coupling.** A stateless service scales to zero and starts cold without ceremony.
   One holding connections does not.

The exception is real: a job that must stream a million rows through a model would spend more
on HTTP than on inference. If you take it, take it deliberately —

- give the service its **own read-only credential**, never the app's;
- mark the tables it reads in `module-add`'s notes, so a migration knows it has a second reader;
- write down that `stack.monorepo.services[].reads_db = true`, so the next person sees it.

A service that quietly acquired the connection string because it was convenient is the version
of this that costs a weekend.

## `README.md` inside the app

It answers one question, because it is the question every time: **how do I run this without
Docker?**

```bash
cd apps/<name>
uv sync                 # + `--extra ml` for the model variant
uv run uvicorn <name>.main:app --reload --port <port>
```

The Dockerfile is for production. Nobody should need Docker to change a line and see it reload.
