> Sources: <https://www.scaleway.com/en/docs/> · <https://www.scaleway.com/en/docs/serverless-containers/> ·
> <https://www.scaleway.com/en/docs/generative-apis/quickstart/> ·
> <https://www.scaleway.com/en/docs/generative-apis/reference-content/data-privacy/> ·
> eve's own `docs/agent-config.md` (shipped with the package) for the direct-provider path.
> Checked **2026-09-12**. Console flags and product names move: `[VERIFY]` before running anything.

# Scaleway — what it adds to an eve product, and what it must never take away

**It is not a skill, and it should not become one.** A skill per cloud vendor is how a repo ends up
with sixty skills that all say "install their CLI and log in".

**And it is not a replacement for anything.** The first version of this file asked the wrong
question — *"what would you swap out?"* — and produced a list of things you lose. The right question
is the opposite: **what does eve not do, that Scaleway does, and how does eve reach it?**

The answer to *how* is one sentence, and it is the whole architecture:

> **eve reaches Scaleway through a tool, not through configuration.**

Configuration swaps a component out — a different model provider, a different database — and you pay
for it in what that component was giving you. **A tool adds a capability and takes nothing**: the
agent keeps its Gateway, its Sandbox, its observability and its one bill, and gains something it
could not do at all.

Read §1–§5 as additions. §6 is the honest list of swaps, kept because someone will eventually have a
residency requirement that forces one — but a swap is a last resort here, not the plan.

## The argument that decides it: the data stays in the EU

Everything else here has an equivalent elsewhere. This does not:

> *"Your personal data may be stored in the following region: Paris, France."*
> *"Your data is not used for training, retraining, or improving the base models."*
> — Scaleway, Generative APIs data privacy

Scaleway is a French company operating EU regions. For a project where `compliance-audit` raises
**R3 (transfers outside the EEA)** and the client's answer is "it must not leave", that turns a
paragraph of justification into a sentence. That is the whole case; reach for Scaleway when the case
applies, and use the default stack when it does not.

Two limits, stated so the sentence stays honest: they retain *aggregated and anonymised* API usage
data for up to **6 months**, and incident data for up to **two weeks**, *"only to reproduce,
investigate, and fix the underlying issue"*.

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

**Serverless Jobs** is: batch runs, multiple cron triggers per job, automatic retries. The agent
starts the job and the result arrives later, which is precisely the shape `eve-patterns.md` §10
already describes — *record the intent before attempting delivery, and post through the destination's
API rather than `to()`, which would start a turn you did not want*.

Again additive: the Sandbox stays for what it is good at, and the long job stops being something the
agent has to pretend it can hold.

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
`monorepo-add-python-service/references/deploy-container.md`). **Serverless Containers** scales to zero and bills per request;
A GPU means **GPU Instances** (`/docs/gpu/`), a machine you run — *not* a serverless
runtime. `[VERIFY]`: "Serverless GPU" is not a documented Scaleway product; the serverless family is
Containers, Functions and Jobs.

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
