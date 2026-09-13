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

## 6. The narrowest interface, so a model is one argument

A model you cannot swap is a model you cannot evaluate, and you will want to swap one: a better
checkpoint appears, or the one you picked turns out to be wrong for your documents. Give it the
**smallest interface the caller actually needs**, not the model's own API:

```python
class NerModel(Protocol):
    version: str
    def persons(self, text: str) -> list[tuple[int, int, str, float]]: ...
```

Two methods. A second model is then an adapter, an A/B is one argument, and the integration *is*
the adapter you already wrote to run the comparison.

**Prefer a union to a replacement when the models fail on different inputs.** A composite that
satisfies the same Protocol and merges the answers needs no change in the caller at all:

```python
class EnsembleNer:
    def persons(self, text):
        return merge([s for m in self.models for s in m.persons(text)])
```

Decide the merge policy explicitly and write down why. Overlapping spans merging into their union
extent, for a redactor, because *a name half redacted is a name in the clear* — while a confidence
threshold governs whether a candidate is admitted at all, not whether half of an admitted one is
kept. Touching-but-not-overlapping spans stay apart: a comma between two names is a boundary.

## 7. Deciding whether to swap: a differential bench, not a score

You will not have labelled data. You do not need it to answer *"is this model better for us"* —
run both over the same documents and look at where they **disagree**. Agreement is not accuracy,
and the bench should say so on every run.

What made the difference between a bench that answered and one that misled:

- **Three arms, including a floor.** Rules alone, rules+A, rules+B. A span the rules already found
  is credited to neither model, so what separates A from B is the thing only a model can do.
- **Distinct values, not span counts.** A first run reported "370 spans only B found". They were
  **16 distinct strings**, one of them counted 325 times because it was a running page header.
  Print both numbers side by side or the aggregate will lie.
- **Per document, not only totals.** One long document carried 93% of that corpus by words and
  every finding. The per-document row is what separates *"B is better"* from *"B is better on one
  document type"* — a much narrower and much more useful claim.
- **Measure the pipeline separately from the model.** An arm reproducing the shipped path exactly
  (there: no chunking, whole document into a 512-token encoder) answers *what would fixing the
  plumbing buy, with the same model*. A pipeline fix and a model swap must never be credited to
  each other. Here the prediction was that chunking explained the gap; it explained **two spans**.
- **The corpus ships empty and the output is gitignored.** Real documents are neither shareable
  nor committable, and the disagreement file carries the values the models found.
- **A document that produces no text is dropped and counted, never entered as an empty string** —
  it would score as a perfect agreement on a document nobody read.

## 8. A token limit is a wall the pipeline walks through

The trap that cost the most here. A 512-position encoder handed a longer document does **not**
raise: the `transformers` pipeline truncates, warns on stderr and returns. So the service answers
`200` having examined the first page, and for anything safety-adjacent — redaction, screening,
classification — that is the worst available failure: success reported, the rest never looked at.

Window the input, and size the windows **against the tokenizer**, not against a guessed character
count: propose a window by characters, cut it at a sentence boundary, halve it until the tokenizer
agrees it fits. Overlap consecutive windows by more than the longest entity you expect, so
something split by a seam is whole in the next one, and map the spans back to global offsets.

Inject the budget as a callable — `fits(piece) -> bool` — and the windowing is testable without
loading the weights: every window fits, every offset points where it claims, **every character is
covered** (a gap between windows is an entity nobody looks at), and the thing at the very end
survives.

## What belongs in the service, and what does not

**In**: the HTTP contract, the Pydantic models, one slot with explicit eviction, the device
resolution, `model_version`, the endpoint per capability (`/segment`, `/ocr`, `/detect`).

**Out**: preprocessing that belongs to the model card, post-processing the web app can do,
business rules, anything stateful. The service answers *"what does this model see in this
image"*. If it starts deciding what to do about it, that logic wanted to be in `apps/web`.
