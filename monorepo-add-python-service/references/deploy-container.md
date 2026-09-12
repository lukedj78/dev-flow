> Sources: <https://docs.astral.sh/uv/guides/integration/docker/> (base image, cache mounts, `UV_COMPILE_BYTECODE`, `UV_LINK_MODE`) ·
> <https://hub.docker.com/_/python> · <https://vercel.com/docs/projects/environment-variables> ·
> <https://www.scaleway.com/en/docs/serverless-containers/> · <https://www.scaleway.com/en/docs/gpu/> · <https://www.scaleway.com/en/docs/serverless-jobs/>.
> Verified **2026-09-11** for the Dockerfile; the provider steps are marked `[VERIFY]` — consoles move faster than docs.

# Two deploy targets, because there are two runtimes

`apps/web` goes to Vercel. `apps/<name>` is a container: Vercel does not run long-lived Python
processes, and the `ml` variant wants a GPU Vercel does not sell. Two targets is not a
complication to engineer away — it is the shape of the thing.

## The Dockerfile

uv's own Docker guide recommends `python:3.x-slim-trixie` as the base with the uv binary copied
in from the distroless image. That is what this uses, verbatim in structure:

```dockerfile
FROM python:3.12-slim-trixie
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Byte-compile on install: slower build, faster cold start. Worth it for a service that
# scales to zero. `copy` avoids the hardlink warning when the cache is a mount.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Dependencies first, in their own layer: they change far less often than the source,
# so a code edit does not re-resolve the world.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE <port>
CMD ["uvicorn", "<name>.main:app", "--host", "0.0.0.0", "--port", "<port>"]
```

Four things that are load-bearing:

- **`--locked`** fails if `uv.lock` disagrees with `pyproject.toml` instead of quietly
  resolving something else. An image that installs different versions than your laptop is the
  bug this flag exists to prevent.
- **`--no-dev`** leaves pytest and ruff out — they are a `[dependency-groups] dev` entry
  (`service-layout.md`), so this works without listing anything.
- **`--host 0.0.0.0`**. The default binds loopback, and a container that binds loopback answers
  nothing from outside. It is the single most common reason a working image "does not respond".
- **`ENV PATH=/app/.venv/bin:$PATH`** so `CMD` runs the venv's uvicorn without `uv run`.

Pin `ghcr.io/astral-sh/uv:latest` to a version for a production build: `:0.12.13` today.
`latest` in a Dockerfile is a build that changes when you did not.

### Build context

Build from **the app directory**, not the repo root:

```bash
docker build -t <name>:local apps/<name>
docker run --rm -p <port>:<port> --env-file apps/<name>/.env <name>:local
curl -s localhost:<port>/health
```

The service has no workspace dependencies — that is why the bridge `package.json` carries no
`dependencies`. Nothing from `packages/` needs to be in the image, so the context stays small
and the build stays fast.

## Registry and runtime

`[VERIFY]` — consoles and CLI flags move; check the provider's own quickstart before running.

**Scaleway Serverless Containers** (the main example: scales to zero, per-request billing,
EU-hosted, which matters when `compliance-audit` asks where the data goes):

1. Create a **Container Registry** namespace.
2. `docker login` against the registry with your Scaleway credentials.
3. Tag and push: `docker tag <name>:local rg.<region>.scw.cloud/<namespace>/<name>:<tag>` then
   `docker push …`.
4. Deploy the container from the pushed image, console or `scw` CLI, and **set the port
   parameter to the port the image exposes** — a mismatch there is the other reason a working
   image answers nothing.

<https://www.scaleway.com/en/docs/serverless-containers/quickstart/>

For the `ml` variant, a GPU means **GPU Instances** (`https://www.scaleway.com/en/docs/gpu/`) — a
machine you run, with Docker or Kubernetes on it, not a serverless runtime. Same image shape, a CUDA
base instead of `python:3.12-slim-trixie` (`variant-ml.md`).

⚠️ **Correction, 2026-09-12.** This file first said "Scaleway Serverless GPU" and linked
`/docs/serverless-gpu/`. That URL **404s** and no such product is documented: the serverless family is
Containers, Functions and Jobs, and GPUs are Instances. Written from a summary instead of a checked
URL — the repo's own rule is `curl -o /dev/null -w '%{http_code}'` over every URL a skill cites.

**Alternatives**, same container, different trade:

| Runtime | Why you would |
|---|---|
| Google Cloud Run | scale-to-zero, generous free tier, GPU in some regions |
| AWS App Runner / ECS Fargate | you are already on AWS and the VPC matters |
| Fly.io | simple, close to the edge, straightforward GPUs |
| Modal / Replicate / Hugging Face Inference Endpoints | the `ml` variant when you would rather rent the GPU than run it |
| A plain VM with the image | one machine, one model, predictable bill — often the right answer |

None of these is a dev-flow default. The service is a container; where it runs is the user's
decision and their bill.

## Environment variables, both sides

**On the service** — whatever `.env.example` lists, plus the port the runtime expects.

**On Vercel, for `apps/web`** — one variable, the service URL:

```
<NAME>_SERVICE_URL = https://<name>.<something>.scw.cloud
```

Two rules that are not optional:

- Set it in **every environment that runs the app**, Preview included. A variable that exists
  only in Production is the classic "works locally and in prod, the PR preview 500s" — the same
  trap `vercel-deploy` documents for every other variable.
- **Not `NEXT_PUBLIC_`.** That would ship the service URL to the browser and invite direct
  calls; the service is reached server-side (`openapi-client.md`).

If the service is not public, put it behind whatever the runtime offers — a private network, an
IP allowlist, or a shared secret header that `apps/web` sends and the service checks. Decide
this before the first deploy, not after the endpoint has been indexed.

## What this skill does not do

It does not push an image, create a registry namespace, or hold a credential. It writes the
Dockerfile, names the targets, and lists the variables. The steps that need your account are
yours — this skill never enters a credential on your behalf.
