> Sources: <https://www.scaleway.com/en/docs/> · <https://www.scaleway.com/en/docs/serverless-containers/> ·
> <https://www.scaleway.com/en/docs/generative-apis/quickstart/> ·
> <https://www.scaleway.com/en/docs/generative-apis/reference-content/data-privacy/> ·
> eve's own `docs/agent-config.md` (shipped with the package) for the direct-provider path.
> Checked **2026-09-12**. Console flags and product names move: `[VERIFY]` before running anything.

# Scaleway — where it fits, and where it does not

**It is not a skill, and it should not become one.** Scaleway is a *provider choice* for capabilities
dev-flow already models: a deploy target, a database, object storage, and — the interesting one — a
model endpoint. A skill per cloud vendor is how a repo ends up with sixty skills that all say
"install their CLI and log in".

So this file is the decision layer: four slots where Scaleway is a legitimate answer, the one
argument that actually decides it, and the cases where it is the wrong call.

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

## Slot 1 — `deploy` for a container that is not the Next app

Already the documented target for `monorepo-add-python-service` (see
`monorepo-add-python-service/references/deploy-container.md`). **Serverless Containers** scales to zero and bills per request;
**Serverless GPU** is the same image shape for the `ml` variant.

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

## Slot 4 — the model endpoint, and this is the eve one

**Generative APIs** is an **OpenAI-compatible** endpoint:

```
base URL:  https://api.scaleway.ai/v1
auth:      api_key = <SCW_SECRET_KEY>     (a Scaleway API secret key)
```

Models are the open-weight families — Llama, Mistral, Qwen, Gemma, DeepSeek and others; check the
supported-models page rather than this file, the list moves weekly.

### Wiring it into eve

eve's own `docs/agent-config.md` says `model` accepts **either** a Gateway model id string **or a
direct-provider AI SDK `LanguageModel`**, with provider packages as ordinary project dependencies.
So the path exists and is supported, not a hack:

```bash
npm install @ai-sdk/openai-compatible    # 3.0.48, Apache-2.0 (checked 2026-09-12)
```

```ts title="agent/agent.ts"
import { createOpenAICompatible } from "@ai-sdk/openai-compatible";

const scaleway = createOpenAICompatible({
  name: "scaleway",
  baseURL: "https://api.scaleway.ai/v1",
  apiKey: process.env.SCW_SECRET_KEY,
});

export default defineAgent({
  model: scaleway("<model-id>"),   // [VERIFY] the id against the supported-models page
});
```

⚠️ **Know what you are giving up, because it is not nothing.** eve's default is the **Vercel AI
Gateway**, and going direct costs you all of it at once:

- **routing and failover** across providers, which the Gateway does and a single endpoint cannot;
- **one bill** — model spend stops being a Vercel line item and becomes a second invoice;
- the Gateway's **observability**, which `eve-agent`'s cost and tracing guidance assumes;
- eve's own caveat, quoted from `agent-config.md`: a config with a **direct-provider
  `LanguageModel` stays a runtime entry** rather than compile-only, unlike a static Gateway id.

And one thing you are *not* giving up: eve's Sandbox stays Vercel's. There is no Scaleway sandbox
backend — the subpaths are `eve/sandbox/{vercel,docker,just-bash,microsandbox}` (0.54.3). A Scaleway
box could host the `docker()` backend, but that is a self-hosting project, not a configuration.

**So: take slot 4 only when the residency requirement reaches the model calls themselves.** That is
a real requirement — a health or legal product whose prompts carry personal data — and it is also a
requirement people claim before checking whether it applies. Ask what the prompts actually contain
before trading the Gateway away.

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
