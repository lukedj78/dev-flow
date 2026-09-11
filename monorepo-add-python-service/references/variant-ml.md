> Sources: <https://docs.astral.sh/uv/concepts/projects/dependencies/> (extras) ·
> <https://docs.docker.com/desktop/features/gpu/> (GPU passthrough is Linux/CUDA only) ·
> <https://huggingface.co/docs/huggingface_hub/guides/manage-cache> (`HF_HOME`) ·
> <https://pytorch.org/docs/stable/notes/mps.html> (Metal backend).
> Model repositories checked on the Hub **2026-09-11**: `facebook/sam3`, `deepseek-ai/DeepSeek-OCR`,
> `Ultralytics/YOLO26` all resolve. Everything about *how* a model is called is `[VERIFY]` — read
> the model card, not this file.

# The `ml` variant — a service that holds models

Everything in `service-layout.md` still applies. This adds four constraints that come from the
models being large, slow to load, and tied to the machine's GPU. **It adds no inference code**:
the skill scaffolds the contract and the extension points, because a model integration that was
written from memory rather than from the model card is worse than none.

The first real case: a service exposing `facebook/sam3` (segmentation), `deepseek-ai/DeepSeek-OCR`
(OCR) and `Ultralytics/YOLO26` (detection) to `apps/web`.

## 1. Model dependencies are an extra, never the base

```toml
[project]
dependencies = ["fastapi>=0.141.1", "uvicorn[standard]>=0.52.4", "pydantic>=2.13.5"]

[project.optional-dependencies]
ml = [
  # `[VERIFY]` each against the model card before pinning — these are the heavy ones
  # and the versions that work together move.
  "torch>=2.5",
  "transformers>=4.57",
  "pillow>=11",
]
```

`uv sync` gives a working API in seconds. `uv sync --extra ml` gives one that can run a model,
and downloads gigabytes. Keep them apart and **every laptop, every CI job and every `turbo
test` stays fast** — CI runs the API tests, not the models.

Why an extra and not a dependency group: uv's docs call `[dependency-groups]` *"local
dependencies for development"* and `[project.optional-dependencies]` published optional
dependencies. Model deps are neither dev nor mandatory — they are an optional **runtime**
feature, on the GPU host and nowhere else. That is what an extra means.

## 2. One model resident at a time, with explicit unloading

The constraint is a 16 GB laptop. SAM 3 and DeepSeek-OCR do not coexist there, and the failure
is not a clean error — it is the machine swapping until something is killed.

So the service holds **one** model, and switching unloads the previous one. The scaffold gives
you the registry and the seam; you fill in `_load`:

```python
# src/<name>/models.py — the contract. Inference belongs to whoever reads the model card.
from dataclasses import dataclass
from typing import Any, Protocol


class Model(Protocol):
    version: str
    def unload(self) -> None: ...


@dataclass
class _Slot:
    name: str | None = None
    model: Any = None


_slot = _Slot()


def get(name: str) -> Any:
    """Return the named model, evicting whatever else was resident.

    One slot on purpose: two vision models do not fit in 16 GB, and the symptom of
    trying is the OS killing the process, not an exception you can catch.
    """
    if _slot.name == name:
        return _slot.model
    release()
    _slot.name, _slot.model = name, _load(name)
    return _slot.model


def release() -> None:
    if _slot.model is None:
        return
    _slot.model.unload()          # model-specific; the card says how
    _slot.name, _slot.model = None, None
    _free_accelerator_cache()     # torch.cuda.empty_cache() / torch.mps.empty_cache()
```

Two things this buys beyond not crashing: the first request after a switch is honestly slow —
expose that, do not hide it behind a timeout — and `release()` gives you a `POST /models/release`
endpoint, which is how you get your laptop's memory back without restarting the service.

⚠️ **Loading is not thread-safe and uvicorn is concurrent.** Guard `get()` with a lock, or run
the loader in a single worker. Two requests for two different models arriving together, with no
lock, will load both — which is the exact thing this design exists to prevent.

## 3. `model_version` on every response

Every response carries which weights produced it:

```python
class Prediction(BaseModel):
    model_version: str   # e.g. "facebook/sam3@<commit-sha>" or sha256 of the weights file
    ...
```

Not decoration. A model is swapped, or a Hub repository moves its `main`, and suddenly the
outputs are different — with `model_version` in the payload that is a one-line diff in a log; without
it, it is a week of "did something change?". Use the **Hub revision SHA**, not the tag: a tag is
mutable, which is the whole problem.

Pin the revision when loading, too. `main` is not a version.

## 4. Metal locally, CUDA in production — and Docker sits out the first half

**Docker Desktop on macOS does not pass the GPU through.** There is no Metal in the container;
a model that ran at 40 ms on the host runs on CPU inside it, or not at all. This is a platform
fact, not a configuration to find.

So:

| | Local (macOS) | Production |
|---|---|---|
| How it runs | **native** — `uv sync --extra ml && uv run uvicorn …` | container |
| Device | `mps` (Apple Metal) | `cuda` |
| Base image | — | a CUDA image, **not** `python:3.12-slim-trixie` |

`turbo dev` runs the native process, so the local loop is unchanged — that is the point of the
bridge. `docker build` is for the thing you ship.

Resolve the device once, at startup, and log it:

```python
device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
```

A service silently on `cpu` because `mps` was unavailable is the performance bug that gets
blamed on the model.

`deploy-container.md`'s Dockerfile is the CPU/API shape. For the GPU image, swap the base for
the CUDA one the framework's own docs recommend — `[VERIFY]` per framework and per CUDA
generation, and keep `uv sync --locked --no-dev --extra ml`.

## 5. Weights live outside the repository

```bash
# .env.example
HF_HOME=~/.cache/huggingface        # the Hub's own cache variable
<NAME>_MODEL_CACHE=~/.cache/<slug>-models
```

And in `.gitignore`, defensively, because one `HF_HOME=./models` in a hurry is all it takes:

```gitignore
models/
*.safetensors
*.onnx
*.pt
```

Weights are hundreds of megabytes to tens of gigabytes. A repository that ate one is a
repository every clone pays for, forever — git does not forget. In the container, mount the
cache as a volume so a cold start does not re-download.

## What belongs in the service, and what does not

**In**: the HTTP contract, the Pydantic models, one slot with explicit eviction, the device
resolution, `model_version`, the endpoint per capability (`/segment`, `/ocr`, `/detect`).

**Out**: preprocessing that belongs to the model card, post-processing the web app can do,
business rules, anything stateful. The service answers *"what does this model see in this
image"*. If it starts deciding what to do about it, that logic wanted to be in `apps/web`.
