#!/usr/bin/env bash
# scaffold_python_service.sh — create apps/<name>/, a FastAPI service managed by uv,
# as a member of an existing pnpm + turborepo workspace.
#
# Idempotent by construction: every file is written only when absent, and each path is
# reported as `created` or `exists`. Re-running changes nothing and says so — the caller
# needs to be able to run this twice without reading the diff to find out what happened.
#
# It does NOT patch turbo.json, package.json of other packages, or meta.json. Those are
# decisions with context (see the skill's Step 4–7); a script that edits shared files
# silently is how a scaffold becomes something you have to undo.
#
# Usage:
#   scaffold_python_service.sh <project-root> [--name ml] [--port 8000] [--variant generic|ml]

set -euo pipefail

ROOT="${1:-}"; shift || true
NAME="ml"; PORT="8000"; VARIANT="generic"

while [ $# -gt 0 ]; do
  case "$1" in
    --name)    NAME="${2:-}"; shift 2 ;;
    --port)    PORT="${2:-}"; shift 2 ;;
    --variant) VARIANT="${2:-}"; shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

[ -n "$ROOT" ] || { echo "usage: $0 <project-root> [--name ml] [--port 8000] [--variant generic|ml]" >&2; exit 2; }
[ -d "$ROOT" ] || { echo "not a directory: $ROOT" >&2; exit 2; }

case "$VARIANT" in generic|ml) ;; *) echo "--variant must be generic or ml (got: $VARIANT)" >&2; exit 2 ;; esac
printf '%s' "$NAME" | grep -qE '^[a-z][a-z0-9-]*$' || { echo "--name must be kebab-case (got: $NAME)" >&2; exit 2; }
case "$NAME" in web|mobile|agent|root) echo "--name '$NAME' collides with a reserved app name" >&2; exit 2 ;; esac
printf '%s' "$PORT" | grep -qE '^[0-9]{2,5}$' || { echo "--port must be numeric (got: $PORT)" >&2; exit 2; }

# --- preconditions the script can check on its own -------------------------
[ -f "$ROOT/pnpm-workspace.yaml" ] || { echo "no pnpm-workspace.yaml at $ROOT — not a pnpm workspace" >&2; exit 1; }
[ -f "$ROOT/turbo.json" ]          || { echo "no turbo.json at $ROOT — not a turborepo" >&2; exit 1; }
grep -qE "^\s*-\s*['\"]?apps/\*" "$ROOT/pnpm-workspace.yaml" || {
  echo "pnpm-workspace.yaml does not glob apps/* — the service would be invisible to pnpm" >&2; exit 1; }

# Namespace: meta.json#project_slug when present, else the directory name.
SLUG="$(basename "$ROOT")"
if [ -f "$ROOT/.workflow/meta.json" ]; then
  SLUG="$(python3 -c "
import json,sys
try: print(json.load(open('$ROOT/.workflow/meta.json')).get('project_slug') or '$SLUG')
except Exception: print('$SLUG')
")"
fi

APP="$ROOT/apps/$NAME"
# Python identifiers cannot contain '-'
MOD="$(printf '%s' "$NAME" | tr '-' '_')"
ENVP="$(printf '%s' "$NAME" | tr '[:lower:]-' '[:upper:]_')"

created=0; existed=0
write() {  # write <relative-path> <<'EOF' … EOF
  local rel="$1" path="$APP/$1"
  mkdir -p "$(dirname "$path")"
  if [ -e "$path" ]; then
    echo "  exists   apps/$NAME/$rel"; existed=$((existed+1)); cat >/dev/null
  else
    cat >"$path"; echo "  created  apps/$NAME/$rel"; created=$((created+1))
  fi
}

echo "[scaffold] apps/$NAME  (package @$SLUG/$NAME · module $MOD · port $PORT · variant $VARIANT)"

write package.json <<EOF
{
  "name": "@$SLUG/$NAME",
  "version": "0.0.0",
  "private": true,
  "scripts": {
    "dev": "uv run uvicorn $MOD.main:app --reload --port $PORT",
    "test": "uv run pytest -q",
    "lint": "uv run ruff check .",
    "typecheck": "uv run ruff check --select F .",
    "build": "uv sync --locked",
    "openapi": "uv run python scripts/export_openapi.py"
  }
}
EOF

if [ "$VARIANT" = "ml" ]; then
  ML_EXTRA='
[project.optional-dependencies]
# Model dependencies: `uv sync --extra ml` on the GPU host, plain `uv sync` everywhere else.
# Pin each against the model card before trusting it — see references/variant-ml.md.
ml = [
  "torch>=2.5",
  "transformers>=4.57",
  "pillow>=11",
]
'
else
  ML_EXTRA=''
fi

write pyproject.toml <<EOF
[project]
name = "$MOD"
version = "0.0.0"
requires-python = ">=3.12"
dependencies = [
  "fastapi>=0.141.1",
  "uvicorn[standard]>=0.52.4",
  "pydantic>=2.13.5",
]
$ML_EXTRA
[dependency-groups]
dev = [
  "pytest>=9.1.1",
  "ruff>=0.16.7",
  # starlette 1.6 moved TestClient onto httpx2; without it the API tests fail at
  # COLLECTION with "The starlette.testclient module requires httpx2 to be installed".
  # Found by running the scaffold, not by reading the docs (verified 2026-09-11).
  "httpx2>=2.12.0",
]

[tool.ruff]
target-version = "py312"

[tool.pytest.ini_options]
testpaths = ["tests"]

[build-system]
requires = ["uv_build>=0.12,<0.13"]
build-backend = "uv_build"
EOF

write .python-version <<'EOF'
3.12
EOF

write "src/$MOD/__init__.py" <<EOF
"""$NAME service."""

__all__ = ["app"]

from .main import app
EOF

write "src/$MOD/schemas.py" <<'EOF'
"""Pydantic models. These ARE the OpenAPI schema, and therefore the TypeScript client:
rename a field here and apps/web stops compiling. That is the point."""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(description="Always 'ok' when the process is serving.")
    service: str
    version: str


class EchoRequest(BaseModel):
    text: str = Field(min_length=1, description="Any non-empty string.")


class EchoResponse(BaseModel):
    text: str
    length: int
EOF

write "src/$MOD/main.py" <<EOF
"""FastAPI entrypoint. Stateless: input in, JSON out — see references/service-layout.md."""

from fastapi import FastAPI

from .schemas import EchoRequest, EchoResponse, HealthResponse

app = FastAPI(title="$NAME service", version="0.0.0", openapi_url="/openapi.json")


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="$NAME", version=app.version)


@app.post("/echo", response_model=EchoResponse)
def echo(request: EchoRequest) -> EchoResponse:
    """Example endpoint — replace it. It exists so the generated client has a request
    body to type; a schema with only GET /health teaches the next endpoint nothing."""
    return EchoResponse(text=request.text, length=len(request.text))
EOF

write "tests/test_api.py" <<EOF
"""API tests. They must not need a model, a GPU or a network — that is what keeps
\`turbo test\` fast enough to run on every commit."""

from fastapi.testclient import TestClient

from $MOD.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_echo_round_trip() -> None:
    response = client.post("/echo", json={"text": "hello"})
    assert response.status_code == 200
    assert response.json() == {"text": "hello", "length": 5}


def test_echo_rejects_empty() -> None:
    assert client.post("/echo", json={"text": ""}).status_code == 422
EOF

write "scripts/export_openapi.py" <<'EOF'
"""Dump the OpenAPI schema to openapi.json. No server, no port.

sort_keys=True on purpose: without it the key order can move between runs, the file
changes for no reason, and every downstream cache entry is invalidated with it.
"""

import json
from pathlib import Path

from __MOD__.main import app

out = Path(__file__).resolve().parents[1] / "openapi.json"
out.write_text(json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(f"wrote {out}")
EOF
# the heredoc above is quoted so nothing expands; substitute the module name after the fact
if [ -f "$APP/scripts/export_openapi.py" ]; then
  python3 - "$APP/scripts/export_openapi.py" "$MOD" <<'PY'
import sys, pathlib
p, mod = pathlib.Path(sys.argv[1]), sys.argv[2]
t = p.read_text(encoding="utf-8")
if "__MOD__" in t:
    p.write_text(t.replace("__MOD__", mod), encoding="utf-8")
PY
fi

if [ "$VARIANT" = "ml" ]; then
write "src/$MOD/models.py" <<'EOF'
"""One resident model at a time, with explicit eviction.

The constraint is a 16 GB machine: two vision models do not fit, and the symptom of
trying is the OS killing the process, not an exception you can catch. See
references/variant-ml.md — including the lock this needs before it meets concurrency.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class _Slot:
    name: str | None = None
    model: Any = None
    version: str | None = None


_slot = _Slot()


def _load(name: str) -> tuple[Any, str]:
    """Load `name`, returning (model, version).

    EXTENSION POINT — deliberately unimplemented. Read the model card; pin the Hub
    REVISION SHA, never a mutable tag, and return it as the version.
    """
    raise NotImplementedError(f"no loader registered for {name!r}")


def _free_accelerator_cache() -> None:
    """torch.cuda.empty_cache() / torch.mps.empty_cache() once torch is a dependency."""


def get(name: str) -> Any:
    if _slot.name == name:
        return _slot.model
    release()
    _slot.model, _slot.version = _load(name)
    _slot.name = name
    return _slot.model


def current_version() -> str:
    """Goes into every response as `model_version`. Without it, 'did something change?'
    is a week of work instead of a one-line diff."""
    if _slot.version is None:
        raise RuntimeError("no model loaded")
    return _slot.version


def release() -> None:
    if _slot.model is None:
        return
    unload = getattr(_slot.model, "unload", None)
    if callable(unload):
        unload()
    _slot.name = _slot.model = _slot.version = None
    _free_accelerator_cache()
EOF

write "src/$MOD/device.py" <<'EOF'
"""Resolve the accelerator once, at startup, and log it.

Docker Desktop on macOS does not pass Metal through, so the local loop runs native and
the container is for production. A service silently on `cpu` because `mps` was
unavailable is the performance bug that gets blamed on the model.
"""


def resolve() -> str:
    try:
        import torch
    except ImportError:
        return "cpu"  # base install: no model extra, no accelerator
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"
EOF
fi

write .env.example <<EOF
# Port uvicorn binds. Must match the dev script in package.json.
${ENVP}_PORT=$PORT
# Comma-separated origins allowed to call this service from a browser.
# Empty in the normal setup: apps/web calls it server-side, nothing reaches it from a page.
${ENVP}_CORS_ORIGINS=
$( [ "$VARIANT" = "ml" ] && cat <<MLENV
# Weights live OUTSIDE the repository. A repo that ate a checkpoint pays for it forever.
HF_HOME=~/.cache/huggingface
${ENVP}_MODEL_CACHE=~/.cache/$SLUG-models
MLENV
)
EOF

write .gitignore <<EOF
__pycache__/
*.py[cod]
.venv/
.pytest_cache/
.ruff_cache/
.env
$( [ "$VARIANT" = "ml" ] && printf 'models/\n*.safetensors\n*.onnx\n*.pt\n' )
EOF

write Dockerfile <<EOF
# Production image. Locally you run this natively — see README.md.
# Base + uv copy + cache mounts follow https://docs.astral.sh/uv/guides/integration/docker/
FROM python:3.12-slim-trixie
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \\
    UV_LINK_MODE=copy

WORKDIR /app

# Dependencies in their own layer: they change far less often than the source.
RUN --mount=type=cache,target=/root/.cache/uv \\
    --mount=type=bind,source=uv.lock,target=uv.lock \\
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \\
    uv sync --locked --no-install-project --no-dev

COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \\
    uv sync --locked --no-dev

ENV PATH="/app/.venv/bin:\$PATH"
EXPOSE $PORT
# --host 0.0.0.0: the default binds loopback, and a container that binds loopback
# answers nothing from outside. Most common reason a working image "does not respond".
CMD ["uvicorn", "$MOD.main:app", "--host", "0.0.0.0", "--port", "$PORT"]
EOF

write README.md <<EOF
# @$SLUG/$NAME

FastAPI service, managed by [uv](https://docs.astral.sh/uv/). Part of the turborepo: turbo runs
the scripts in \`package.json\`, which shell out to \`uv run\`.

## Run it locally — no Docker

\`\`\`bash
cd apps/$NAME
uv sync$( [ "$VARIANT" = "ml" ] && printf ' --extra ml' )
uv run uvicorn $MOD.main:app --reload --port $PORT
curl -s localhost:$PORT/health
\`\`\`

Or from the repository root, alongside the web app:

\`\`\`bash
pnpm turbo dev
\`\`\`

The Dockerfile is for production only.$( [ "$VARIANT" = "ml" ] && printf ' Docker Desktop on macOS does not expose Metal, so model work runs natively here and in a CUDA container in production.' )

## Tests and lint

\`\`\`bash
uv run pytest -q
uv run ruff check .
\`\`\`

## The TypeScript client

\`pnpm --filter @$SLUG/$NAME run openapi\` writes \`openapi.json\`; \`packages/api\` turns it into a
typed client. \`apps/web\` calls the service **only** through that client, with the base URL in
\`${ENVP}_SERVICE_URL\`. A hand-written \`fetch\` skips the gate that makes a schema change a
compile error.
EOF

echo "[scaffold] $created created, $existed already present"
if [ "$created" -eq 0 ]; then
  echo "[scaffold] nothing to do — apps/$NAME is already scaffolded"
else
  cat <<EOF
[scaffold] next:
  1. cd $ROOT && pnpm install            # register the new workspace member
  2. cd apps/$NAME && uv sync$( [ "$VARIANT" = "ml" ] && printf ' --extra ml' ) && uv lock   # commit uv.lock
  3. add the \`openapi\` task to turbo.json  (references/turbo-integration.md)
  4. generate the client                  (references/openapi-client.md)
EOF
fi
