> Sources: <https://www.scaleway.com/en/docs/> · <https://www.scaleway.com/en/docs/serverless-containers/> ·
> <https://www.scaleway.com/en/docs/generative-apis/quickstart/> ·
> <https://www.scaleway.com/en/docs/generative-apis/reference-content/data-privacy/> ·
> eve's own `docs/agent-config.md` (shipped with the package) for the direct-provider path.
> Checked **2026-09-12**. Console flags and product names move: `[VERIFY]` before running anything.

# Scaleway — what it adds to an eve product, and what it must never take away

## The picture at runtime — who calls whom

```
        ┌──────────────── Vercel ────────────────┐
        │                                        │
        │   apps/web  (Next)                     │
        │      │                                 │
        │      └──> eve agent                    │
        │             │                          │
        │             ├── model   ──> AI Gateway ┼──> Anthropic / OpenAI / …
        │             ├── sandbox ──> Vercel Sandbox
        │             └── tools                  │
        │                  │                     │
        └──────────────────┼─────────────────────┘
                           │  HTTPS — one tool, like any other
                           ▼
                 ┌──── Scaleway ────┐
                 │  apps/ml         │   ← SAM 3 / OCR / YOLO, on a GPU
                 │  Jobs            │   ← the 40-minute batch
                 │  Object Storage  │   ← the files, when they must stay in the EU
                 └──────────────────┘
```

**Read it for what does *not* change.** The model stays on the Gateway. The sandbox stays Vercel's.
The deploy stays Vercel. The bill stays one. **Scaleway appears nowhere inside eve** — it is a
destination a tool calls, the same way a tool calls Stripe or Resend. To the agent, `apps/ml` is
indistinguishable from any other HTTP API, and it neither knows nor needs to know where it runs.

That is the whole answer to "how does it integrate with eve": **through a tool, never through
configuration.** Configuration swaps a component out and you pay in whatever that component was
giving you. A tool adds a capability and takes nothing.

## Where it enters the flow

Never as a question about eve. Only as the answer to a question about the **product**, at one point:

```
prd_drafted → design_extracted → scaffolded → page_generated → module_added → feature_complete
                                                  ▲
                              here, and only if the PRD asks for one of three things
```

| The PRD says | The skill that answers | What happens |
|---|---|---|
| "it recognises what is in the photo" | `monorepo-add-python-service` (`--variant ml`) | creates `apps/ml`, which needs a GPU. Scaleway is *where you deploy it*, decided at `feature_complete` |
| "it reprocesses the whole archive nightly" | the same `apps/ml` image + **Serverless Jobs** | Scaleway's cron runs it — **eve is not the trigger** — and the agent is woken by a webhook when it is done (§2) |
| "patient data does not leave the EU" | `module-add` (`db` / `storage`) + `compliance-audit` | the corpus stays in the EU, tools read it, only the extract reaches the model |

**If the PRD says none of the three, Scaleway is never mentioned.** In most projects it never
appears at all, and that is the correct outcome — not a gap.

## A worked example, end to end

A product where you upload photos of a building site and ask questions about what is in them.

1. **`monorepo-bootstrap`** → `apps/web` (Next) + `packages/`.
2. **`eve-agent`** → `apps/agent`. Model: a Gateway id. Untouched from here on.
3. The PRD asks for segmentation → **`monorepo-add-python-service --variant ml`** → `apps/ml`,
   FastAPI, SAM 3.
4. **One eve tool**, twelve lines:

```ts title="agent/tools/segment.ts"
export default defineTool({
  description: "Segment a construction-site photo. Returns masks + model_version.",
  inputSchema: z.object({ imageUrl: z.string().url(), prompt: z.string() }),
  async execute({ imageUrl, prompt }) {
    const res = await fetch(`${process.env.ML_SERVICE_URL}/segment`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ imageUrl, prompt }),
    });
    return fence("segment-result", await res.json());   // §11 — it is not your text
  },
});
```

5. **`vercel-deploy`** ships `apps/web` + the agent to Vercel. `apps/ml` goes to a Scaleway GPU
   Instance. The only thing joining them is `ML_SERVICE_URL`.

A user asks *"how many pipes are in this photo?"* and the agent: reasons (Gateway) → calls `segment`
(Scaleway) → gets masks plus `model_version` → answers (Gateway).

**Nothing was replaced. The agent gained a sense it did not have.**

## The argument that decides it: the data stays in the EU

Everything else here has an equivalent elsewhere. This does not:

> *"Your personal data may be stored in the following region: Paris, France."*
> *"Your data is not used for training, retraining, or improving the base models."*
> — Scaleway, Generative APIs data privacy

Scaleway is a French company operating EU regions. For a project where `compliance-audit` raises
**R3 (transfers outside the EEA)** and the client's answer is "it must not leave", that turns a
paragraph of justification into a sentence.

Two limits, stated so the sentence stays honest: they retain *aggregated and anonymised* API usage
data for up to **6 months**, and incident data for up to **two weeks**, *"only to reproduce,
investigate, and fix the underlying issue"*.

---

# The three reasons, in detail

Sections 1–5 are the additions above, spelled out. **§6 is a separate thing**: swaps that *replace*
part of the default stack. Those are a last resort someone's legal requirement forces on you, never
the plan — and this file is not a skill, because a skill per cloud vendor is how a repo ends up with
sixty skills that all say "install their CLI and log in".

## 1. Your own models — the thing eve structurally cannot do

eve calls **hosted** models through the AI Gateway. It cannot run *your* model: SAM 3 segmentation,
DeepSeek-OCR, a YOLO detector, a fine-tuned classifier, bulk embeddings over a private corpus. Those
need a GPU you control, and no amount of Gateway configuration produces one.

**GPU Instances** (`/docs/gpu/` — a machine with Docker or Kubernetes on it, *not* a serverless
runtime) run exactly that. And the container already exists: `monorepo-add-python-service`'s `ml`
variant is the FastAPI service, with one resident model, `model_version` on every response and a
CUDA image for production.

eve then calls it as a tool:

```ts title="agent/tools/segment.ts"
export default defineTool({
  description: "Segment an image. Returns masks and the model version that produced them.",
  inputSchema: z.object({ imageUrl: z.string().url(), prompt: z.string() }),
  async execute({ imageUrl, prompt }) {
    const res = await fetch(`${process.env.ML_SERVICE_URL}/segment`, { … });
    return fence("segment-result", await res.json());   // §11: it is not your text
  },
});
```

**Nothing was replaced.** The Gateway still does the reasoning — "which of these regions is the
product?" — and Scaleway does the pixels. The agent gained a sense it did not have.

## 2. Work that outlives a turn

eve's Sandbox is for agent-driven execution *inside* a session, with a timeout. Re-OCR'ing 100k
documents, re-embedding a corpus after a model change, transcoding a video library — that is not a
sandbox, and holding a turn open for forty minutes is not a design.

**Serverless Jobs** is: batch runs, multiple cron triggers per job, automatic retries, injected
environment variables. A **job definition** is *"a template… including the container image used, the
resources allocated, and the command to execute"*; a **job run** is one execution of it.

### The trick that makes this cheap: it is the same image

You do not build a second artifact. `apps/ml` is already a container; a Job is **that image with a
different command**. One Dockerfile, one registry entry, one set of dependencies that are guaranteed
to match the ones the API is serving with — which is the actual reason this is worth doing rather
than writing a separate batch service that drifts.

```python
# apps/ml/src/ml/jobs/reindex.py — a module, not a server. Same package, same models.
def main() -> None:
    for batch in iter_documents_missing_embeddings(size=256):
        write_embeddings(embed(batch), model_version=current_version())
    notify_done(processed=..., model_version=current_version())
```

The job definition points at the same image and overrides the entrypoint:

```
image:            rg.<region>.scw.cloud/<namespace>/ml:<tag>
startup_command:  python
args:             ["-m", "ml.jobs.reindex"]
cron:             0 3 * * *
```

⚠️ `[VERIFY]` the field names against the API version you are on: `command` is **deprecated in
v1alpha1** in favour of **`startup_command` + `args` in v1alpha2**. A job definition written from an
old example fails at run time, when nobody is watching — which is 03:00.

### Worked example — the nightly re-embedding

The archive is 400k documents. The embedding model changes, and everything has to be re-embedded.

1. **Nobody wakes the agent.** Scaleway's cron fires the job at 03:00. eve is not involved, and that
   is the design, not an omission — see the decision below.
2. The job re-embeds in batches, writing straight to the database. Every row carries the
   `model_version` that produced it, so a half-finished run is **resumable and auditable** rather
   than a mystery.
3. When it finishes it POSTs to eve's **webhook channel** — `agent/channels/webhook.ts`, the shape
   `eve-patterns.md` §9e already describes: verify a shared secret, start the session under
   `waitUntil`, return an ack immediately because nobody is reading the reply.
4. The agent, awake for the first time in this story, does one turn: post "re-embedded 400k
   documents, model `<sha>`, 12 failures" to the channel the team reads.
5. Meanwhile a `job_status` tool lets anyone ask *"how is the reindex going?"* mid-run. The agent
   **reads** the status; it does not hold the job.

⚠️ The notification goes through the **platform's API**, not `ctx.to()`. `to()` starts or resumes an
agent session — a turn and a model call to say "the batch finished". `eve-patterns.md` §10 is that
mistake written down.

### eve `schedules` or Scaleway cron? — the decision

eve has its own scheduler (`defineSchedule({ cron, markdown | run })`), so the question is real:

| Use | When |
|---|---|
| **eve `schedules`** | the **agent** must do something on a cadence — read yesterday's tickets and summarise, review open PRs, decide whether to escalate. The work *is* reasoning |
| **Scaleway cron on a Job** | **infrastructure** must chew through data — re-embed, re-OCR, transcode, rebuild an index. The work is compute, and a language model adds nothing to it |

The failure mode worth naming: putting the nightly batch on an eve schedule makes an LLM turn the
trigger for a four-hour compute job. You pay for a model call to start it, the turn's timeout has no
relationship to the job's duration, and a retry means a second *conversation* rather than a second
run. **Don't wake a language model to press start.**

Additive throughout: the Sandbox stays for what it is good at, eve's schedules stay for reasoning on
a clock, and the long job stops being something the agent has to pretend it can hold.

## 3. The data stays in the EU without the model moving

This is the nuance the first version missed, and it is the one that matters most.

You do **not** have to move inference to keep data in the EU. Keep the *data* in Scaleway — Managed
PostgreSQL, Object Storage — and let the agent's tools read it, sending the model only what the answer
needs. That is `eve-patterns.md` §6's **read-vs-egress boundary** made concrete: the corpus never
leaves; a few hundred tokens of context do, and you chose which.

A residency requirement almost never says "no model may see any derived text". It says the records
stay put. Design for the sentence that was actually written.

## 4. The artifact store, S3-compatible

`eve-patterns.md` §7d: handoff artifacts travel **by id**, written to blob storage — a long audit, a
research dump, a plan the next specialist needs and no human wants pasted in a thread. That needs a
blob store, and Vercel Blob is the default.

Scaleway **Object Storage** is S3-compatible, so it slots in by changing an endpoint and credentials.
The pattern does not change at all. Worth it when the artifacts themselves are personal data.

## 5. A second model endpoint **in addition**, per turn — not instead

**Generative APIs** is an OpenAI-compatible endpoint:

```
base URL:  https://api.scaleway.ai/v1
auth:      api_key = <SCW_SECRET_KEY>     (a Scaleway API secret key)
```

The mistake would be to set it as *the* model. Don't. eve's `model` accepts
**`defineDynamic({ events })`**, and each handler returns the concrete model for its scope — so the
default stays the Gateway and specific turns route elsewhere:

```ts title="agent/agent.ts"
import { defineAgent, defineDynamic } from "eve";
import { createOpenAICompatible } from "@ai-sdk/openai-compatible";

const scaleway = createOpenAICompatible({
  name: "scaleway",
  baseURL: "https://api.scaleway.ai/v1",
  apiKey: process.env.SCW_SECRET_KEY,
});

export default defineAgent({
  model: defineDynamic({
    events: {
      "turn.started": (ctx) =>
        handlesRestrictedData(ctx) ? scaleway("<model-id>") : "openai/gpt-5.4",
    },
  }),
});
```

`npm install @ai-sdk/openai-compatible` (3.0.48, Apache-2.0, checked 2026-09-12). Model ids: the
open-weight families — Llama, Mistral, Qwen, Gemma, DeepSeek — `[VERIFY]` against the supported-models
page, the list moves weekly.

Two things to know before using it, neither of which is a reason not to:

- eve's own note: a config containing a **dynamic model or a direct-provider `LanguageModel` stays a
  runtime entry** rather than compile-only.
- The turns routed to Scaleway are outside the Gateway, so they are outside its routing, failover and
  observability *for those turns*. The default path keeps all three. That is the difference between
  an addition and a swap, and it is the reason to write it as `defineDynamic` rather than as `model:`.

**And the Sandbox stays Vercel's regardless.** There is no Scaleway backend — the subpaths are
`eve/sandbox/{vercel,docker,just-bash,microsandbox}` (0.54.3). A Scaleway machine could host the
`docker()` backend, but that is a self-hosting project, not a configuration.

---

# 6. The swaps — last resort, not the plan

Everything above adds. What follows *replaces*, and each row costs something real. Reach for these
only when a residency requirement leaves no alternative, and say the cost out loud when you do.

## Slot 1 — `deploy` for a container that is not the Next app

Already the documented target for `monorepo-add-python-service` (see
`monorepo-add-python-service/references/deploy-container.md`). **Serverless Containers** scales to
zero and bills per request, with a request timeout up to one hour.

For a GPU it is **GPU Instances** (`/docs/gpu/`) — a machine you run, with Docker or Kubernetes on
it, *not* a serverless runtime. `[VERIFY]`: "Serverless GPU" is **not** a documented Scaleway
product; the serverless family is Containers, Functions and Jobs.

This is the least controversial slot, because `apps/web` stays on Vercel and only the container
moves. Nothing about the Next app changes.

`stack.deploy` stays `"vercel"` for the web app: a container runtime is recorded on the service
entry (`stack.monorepo.services[]`), not as the project's deploy target. One project can have both.

## Slot 2 — `db`, when Neon is refused for residency

Scaleway ships **Managed PostgreSQL** (plus MySQL, Redis, MongoDB, OpenSearch, ClickHouse).

Drizzle does not care: it speaks Postgres over a connection string, so `module-add db`'s schema,
migrations and client are unchanged. What changes is what you give up —

| | Neon (our default) | Scaleway Managed Postgres |
|---|---|---|
| Scale to zero | yes — a sleeping branch costs nothing | no, an instance runs |
| Branching per PR | first-class, and `module-add db` uses it | not the model |
| Serverless driver | `@neondatabase/serverless` over HTTP, which is what makes it work on edge/serverless | a normal TCP pool, so **connection pooling becomes yours to think about** |

That third row is the one that bites. A Next app on Vercel opening TCP connections per invocation
needs a pooler in front; on Neon the HTTP driver sidesteps the question. Do not swap the provider
without answering it.

Take this slot when residency requires it. Not for price, and not for "we might need MySQL later".

## Slot 3 — `storage`, S3-compatible

**Object Storage** is S3-compatible, so the `s3` variant `module-add storage` already documents
works by changing the endpoint and credentials. No new code path.

Worth it when the files are personal data and must stay in the EU; otherwise `vercel-blob` remains
the default precisely because it adds no vendor and no sub-processor.

## When Scaleway is the wrong answer

- **The Next app.** `vercel-deploy` exists, Vercel builds Next, and the two are the same company's
  product. Moving `apps/web` to a container to "own the infrastructure" costs you ISR, the image
  pipeline, preview deployments and the `vercel-doctor` cost analysis, and buys a Dockerfile.
- **"It is cheaper."** Sometimes true, and it is not a reason on its own. `vercel-doctor` measures
  the bill; move when it says so, with the number.
- **"It is European."** Not by itself either. `compliance-audit` says whether residency is a
  *requirement*; if it is not, the default stack stays.

## Recording the choice

Whatever slot is taken, it goes in `meta.json#stack` with the same key as any other provider, and
the reason goes in `history`:

```json
{ "db": "scaleway-postgres", "storage": "s3", "deploy": "vercel" }
```

⚠️ `stack.db` does not have a Scaleway value in the contract's enum today, and the enum ends in
`| string` for exactly this case. If a project actually takes slot 2, add the value to the contract
rather than leaving a bare string nobody can grep for.
