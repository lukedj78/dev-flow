# EU data sovereignty — deciding where the data lives, before the stack is wired

> **Engineering guidance, not legal advice.** A DPO or qualified counsel confirms legal basis, transfer
> assessments and DPIAs. Every vendor fact below was read on the vendor's own page and every legal fact
> on a primary source (EUR-Lex, curia, EDPB, Garante, Gazzetta Ufficiale / Normattiva, govinfo.gov) on
> **2026-09-15**. "not verified" means no primary source was found — treat it as unknown, not as "no".
> The two claims that change the picture most (Regulation (EU) 2026/1744, the Garante note of
> 29 April 2026) were re-read on the primary source a second time before being written here.

**Why this exists.** On a project handling identity documents, tax data and filings to authorities,
where the data lived was decided service by service — Vercel Blob, then Scaleway after a search — and
sub-processors and US transfers were found afterwards. `compliance-audit` checks at `feature_complete`;
by then a Blob store's region, a Neon project's region and a Linear workspace's region can no longer be
changed. The decision belongs at the stack decision, and every module applies it.

**The rule in one line.** Primary: the EU. A service with no EU option is **flagged and recorded, never a
blocker** — the only thing the phase gate refuses is not having decided.

---

## 1. The four questions (asked once, at the stack decision)

| # | Question | Why it matters |
|---|---|---|
| a | Does the product process personal data of people in the EU? | GDPR scope (Art. 3). No → `"none"` is the honest answer. |
| b | Which sensitive categories? identity documents, tax, health, biometrics, minors, financial, criminal, location | Art. 9 / Art. 10, Art. 30(5) (records needed whatever the size), Art. 35 (large-scale Art. 9/10 data → DPIA) |
| c | Do customers or sectors impose residency? (public administration, healthcare, finance, a contract clause) | Turns "prefer EU" into "must be EU", and often into "EU-controlled vendor" |
| d | Must exposure to the US CLOUD Act be avoided? | Region does not answer it — control of the vendor does (§2) |

Record them — never in prose only:

```bash
python3 dev-flow/scripts/data_residency.py decide <root> \
  --eu-subjects yes --categories identity-documents,tax,contact \
  --residency-obligations no --avoid-cloud-act yes [--residency eu --reason "…"]
```

It writes `stack.data_residency`, `compliance.data_categories` and `stack_config.data_residency_answers`,
and renders `docs/compliance/subprocessors.md`. Suggestion: (a) no → `none`; (c) or (d) yes →
`eu-sovereign`; otherwise → `eu`. A choice different from the suggestion is recorded with its reason.

## 2. What the three values mean

- **`eu`** — every service in an **EU member-state region** where the vendor offers one. London and Zurich
  are *adequacy* locations, not EU (the UK decision runs to 27 Dec 2031, Decision (EU) 2025/2574; Switzerland
  2000/518/EC) — record them as such.
- **`eu-sovereign`** — `eu`, **and** where a European alternative exists, a vendor **not under US control**.
  The CLOUD Act (18 U.S.C. § 2713) obliges a provider to disclose data in its *"possession, custody, or
  control, regardless of whether such communication, record, or other information is located within or
  outside of the United States"*
  ([govinfo](https://www.govinfo.gov/content/pkg/USCODE-2023-title18/html/USCODE-2023-title18-partI-chap121-sec2713.htm)).
  An EU region of a US-controlled vendor therefore meets `eu`, not `eu-sovereign`. Answering such an order
  from the EU is itself a transfer (EDPB Guidelines 02/2024).
- **`none`** — no EU constraint. The register is still kept: Art. 28 does not depend on residency.

**Certifications are per offer, not per company.** SecNumCloud (ANSSI) is the strictest EU-sovereignty
qualification; checked 2026-09-15 it is **not** held company-wide by any vendor below — OVHcloud has it on
specific offers, Clever Cloud through partner Cloud Temple's zones, Scaleway is *"undergoing"* it. C5 (BSI)
and HDS (French health data) answer other questions. Never write "sovereign" from a logo — write the offer.

## 3. Operating rules

1. **Set the EU region explicitly on every service.** Vendor defaults are usually US (Vercel `iad1`,
   Firebase Cloud Functions `us-central1`). Several regions are **fixed at creation**: Vercel Blob store,
   Neon project, Supabase project, Sentry org, Grafana stack, Linear workspace, Axiom dataset, OpenAI project.
2. **Every module updates the register** (`data_residency.py add … --by module-add`): name, service,
   personal data it receives, region, transfer basis (`none` / `adequacy` / `dpf` / `scc` / …), DPA link,
   EU alternative. EDPB Opinion 22/2024: the identity of **every processor and sub-processor down the chain**
   should be *"readily available at all times"*.
3. **Extra-EU transfers: name the basis and minimise the data.** The EU-US DPF (Decision (EU) 2023/1795)
   covers only organisations on the DPF list; the General Court upheld it in *Latombe* (T-553/23, 3 Sep
   2025) and the **appeal C-703/25 P is pending** — keep SCCs (Decision (EU) 2021/914, Module 3 for
   processor → sub-processor) in the DPA as the fallback. Remote access from a third country is a transfer
   (EDPB Rec. 01/2020); when a processor needs data in the clear, no technical measure fixes an inadequate
   destination (Use Case 6).
4. **Deletion is applicative; lifecycle rules are a safety net.** Every object-storage lifecycle engine
   checked works in **days** (OVHcloud: *"best-effort … most rules are applied within 24 hours"*); Vercel
   Blob has no lifecycle rules and deletes *"may take up to 60 seconds to propagate"* with CDN caching up to a
   month by default. Erasure calls DELETE on the object with the record; declare for each data category where
   it lives and how it is deleted (`compliance-audit` R4). Old backups keep erased users until they expire —
   say so in the privacy notice.
5. **Keys: the KEK leaves the environment variables before the first external customer.** An EU KMS (§4.10)
   or a self-hosted OpenBao; the app holds data keys, never the key-encryption key.
6. **AI: EU processing, no training, no personal data in prompts unless the step needs it.** Pass an id and
   let a tool read the record. Chatbots and generated content: AI Act Art. 50 applies **from 2 Aug 2026**
   (§5.3) — `compliance-audit` R5.
7. **Payment providers are often independent controllers** (Stripe partly, Mollie mostly, Adyen for
   acquiring) — a DPA does not cover everything they do; list them anyway.

---

## 4. Service table

Legend: **Default** = what dev-flow wires today · **EU of default** = how to keep the default in the EU ·
**EU alternative** = European-headquartered option. "US control" states corporate facts only.
All rows verified **2026-09-15**; the sources column is the page the cell was read on.

### 4.1 Hosting / serverless compute

| Option | Role | US control | EU region & setting | Notes (cost · DX · lock-in · what stays out) | Source |
|---|---|---|---|---|---|
| Vercel | Default | Vercel Inc., Delaware | `fra1`, `cdg1`, `dub1`, `arn1` via `vercel.json` `regions` (default `iad1`; `lhr1` is UK) | Pinning moves **functions and ISR cache only**: 126 edge PoPs, Routing Middleware (*"all regions by default"*), logs and account data stay global. Build region undocumented (a 2024 staff forum reply says US — build in EU CI and deploy `--prebuilt` if it matters). DPA relies on SCCs; Vercel states DPF. | [regions](https://vercel.com/docs/regions) · [function region](https://vercel.com/docs/functions/configuring-functions/region) · [DPA](https://vercel.com/legal/dpa) |
| Scaleway Serverless Containers | EU alternative | Scaleway SAS, iliad group (FR) | `fr-par`, `nl-ams`, `pl-waw`, `it-mil` | Container target (Next standalone + Dockerfile), low lock-in. ISO 27001, HDS; SecNumCloud in progress. | [API](https://www.scaleway.com/en/developers/api/serverless-containers) · [compliance](https://www.scaleway.com/en/security-and-compliance/) |
| Clever Cloud | EU alternative (PaaS) | Clever Cloud SAS, Nantes (FR); ownership not verified | zones `par`, `parhds`, `scw`, `grahds`, `rbx`, `rbxhds`, `wsw` (`ldn` is UK) | git-push PaaS; some zones run on OVHcloud/Scaleway/IONOS hardware. ISO 27001, HDS zones; SecNumCloud via Cloud Temple zones. | [CLI regions](https://www.clever.cloud/developers/doc/manage/cli/applications/) · [security](https://www.clever.cloud/security/) |
| OVHcloud | EU alternative (IaaS) | OVH Groupe SA, Roubaix (FR) | `EU-WEST-PAR`, `GRA`, `SBG`, `RBX`, `DE`, `WAW`, `EU-SOUTH-MIL` | Broad, lower-level DX. SecNumCloud **per offer** (Bare Metal Pod, SNC VMware, SNC Cloud Platform) — standard Public Cloud is not. | [regions](https://www.ovhcloud.com/en/public-cloud/regions-availability/) · [SecNumCloud](https://www.ovhcloud.com/en/bare-metal/secnumcloud/) |
| Hetzner | EU alternative (VMs) | Hetzner Online GmbH (DE) | `fsn1`, `nbg1`, `hel1` | Cheapest compute, you run ops. ISO 27001 over all hosting services; customer master data stays in the EU. | [locations](https://docs.hetzner.com/cloud/general/locations/) · [cert](https://www.hetzner.com/unternehmen/zertifizierung/) |
| IONOS Cloud | EU alternative (IaaS) | IONOS SE (DE); a US PE firm held a minority stake at the 2023 IPO — current holding not verified | `de/fra`, `de/txl`, `es/vit`, `fr/par` | C5 Type 1 (28 May 2026); ISO 27001 on IT-Grundschutz for German cloud products. | [certificates](https://cloud.ionos.de/zertifikate) |

### 4.2 Database (Postgres)

| Option | Role | US control | EU region & setting | Notes | Source |
|---|---|---|---|---|---|
| Neon | Default (`neon-drizzle`) | Neon, LLC — parent **Databricks, Inc.** (US), the contracting party | **`aws-eu-central-1` only** (`aws-eu-west-2` is London); fixed per project | Serverless, branching. Control plane / account metadata location not documented. Databricks states DPF. | [regions](https://neon.com/docs/introduction/regions) · [DPA](https://neon.com/dpa) |
| Supabase | Default (mobile, some web) | Contracting: Supabase Pte. Ltd. (SG); controller in privacy notice: Supabase, Inc.; account data in the US | `eu-west-1`, `eu-west-3`, `eu-central-1`, `eu-north-1` — pick a **specific** one: the generic "Europe" includes London and Zurich; fixed per project | Postgres + Auth + Storage in region; backups exclude Storage objects; Supabase itself warns backups, logs, exports and Edge Functions can affect residency. DPF not verified (DPA uses SCCs). | [regions](https://supabase.com/docs/guides/platform/regions) · [GDPR](https://supabase.com/docs/guides/security/gdpr-compliance) |
| Scaleway Managed PostgreSQL / Serverless SQL | EU alternative | Scaleway (FR) | Managed: `fr-par`, `nl-ams`, `pl-waw`; Serverless SQL (closest to Neon, PG16, scale-to-zero): `fr-par` only | Backup region selectable via API. | [managed](https://www.scaleway.com/en/developers/api/managed-database-postgre-mysql/) · [serverless](https://www.scaleway.com/en/developers/api/serverless-sql-databases/) |
| Aiven for PostgreSQL | EU alternative | Aiven Oy, Helsinki (FI) | choose a European underlying cloud: UpCloud (`upcloud-de-fra`, `upcloud-fi-hel`, …) or OVH (`avn-ovh-par`, `avn-ovh-waw1`, …) | The underlying cloud is the residency lever. ISO 27001/27017/27018/27701. | [clouds](https://aiven.io/docs/platform/reference/list_of_clouds) · [DPA](https://aiven.io/dpa) |
| OVHcloud / Clever Cloud PostgreSQL | EU alternative | FR | OVHcloud EU regions as §4.1 (off-site backup region configurable); Clever Cloud "in France" | Clever Cloud PITR not documented. | [OVH](https://docs.ovhcloud.com/en/guides/public-cloud/databases/postgresql-capabilities) · [Clever](https://www.clever.cloud/product/postgresql/) |

### 4.3 Object storage

| Option | Role | US control | EU region & setting | Lifecycle / deletion | Source |
|---|---|---|---|---|---|
| Vercel Blob | Default | Vercel Inc. | `fra1`/`cdg1`/`dub1`/`arn1`, **fixed at store creation** | No lifecycle rules; delete propagation up to 60 s, CDN cache up to 1 month by default — keep sensitive files in a private store behind a Function | [Blob](https://vercel.com/docs/vercel-blob) |
| Scaleway Object Storage | EU alternative | FR | `fr-par`, `nl-ams`, `pl-waw`, `it-mil` | expiry after N days | [lifecycle](https://www.scaleway.com/en/docs/object-storage/how-to/manage-lifecycle-rules/) |
| OVHcloud Object Storage | EU alternative | FR | EU regions §4.1 | `Days` ≥ 1 or `Date`, best effort within ~24 h | [lifecycle](https://docs.ovhcloud.com/en/guides/storage-and-backup/object-storage/s3-bucket-lifecycle) |
| Hetzner Object Storage | EU alternative | DE | `fsn1`, `nbg1`, `hel1` | `Days`; object lock documented | [overview](https://docs.hetzner.com/storage/object-storage/overview/) |
| IONOS Object Storage | EU alternative | DE | `eu-central-4` (FRA), `eu-central-3` (BER), `de`, `eu-central-2`, `eu-south-2` | days after creation or date | [endpoints](https://docs.ionos.com/cloud/backup-and-storage/ionos-object-storage/endpoints.md) |

### 4.4 Backup

| Option | Built-in | Off-site EU copy | Source |
|---|---|---|---|
| Neon | history window: Launch ≤ 7 days, Scale ≤ 30 days; backup storage location not documented | `pg_dump` scheduled job → a **different vendor's** EU bucket (Neon documents the pattern with S3; swap the endpoint) | [history](https://neon.com/docs/postgres/backup-restore/history-window) · [automate](https://neon.com/docs/manage/backup-pg-dump-automate) |
| Supabase | daily 7/14/30 days by plan; PITR add-on 7/14/28 days; **Storage objects excluded** | `supabase db dump` + copy buckets separately | [backups](https://supabase.com/docs/guides/platform/backups) |
| OVHcloud / Scaleway / Aiven managed DBs | OVHcloud replicates backups to a second, configurable region; Scaleway backup region set via API; Aiven PITR by plan | set the second region to another EU region | [OVH backups](https://docs.ovhcloud.com/en/guides/public-cloud/databases/backups) · [Aiven](https://aiven.io/docs/products/postgresql/concepts/pg-backups) |

### 4.5 CDN

| Option | Role | EU restriction | Processes | Source |
|---|---|---|---|---|
| Vercel CDN | Default | **none documented** — 126 PoPs worldwide; the WAF can deny countries, which is not the same | visitor IP, path, headers, geolocation at every PoP | [how the CDN works](https://vercel.com/docs/how-vercel-cdn-works) |
| Bunny.net | EU alternative (BunnyWay d.o.o., SI) | Routing Filters serve *"exclusively from our 24 Points of Presence (PoPs) within Europe"* | logs anonymise IPs by default (/24, /64), kept 3 days | [routing filters](https://bunny.net/blog/introducing-routing-filters-gdpr-friendly-eu-only-cdn-routing/) · [GDPR](https://bunny.net/gdpr/) |
| Scaleway Edge Services | EU alternative | PoP locations not verified; fronts Scaleway buckets and load balancers | — | [Edge Services](https://www.scaleway.com/en/edge-services/) |

Never put personal data in URLs; never cache authenticated responses at the edge.

### 4.6 Transactional email

| Option | Role | US control | EU setting | What stays out | Source |
|---|---|---|---|---|---|
| Resend | Default | Plus Five Five, Inc. (SF) | sending region `eu-west-1` **per domain** | **account data, email metadata, logs and API records stay in the US whatever the sending region** (Resend's GDPR page); no ISO 27001; DPF "Active – re-certification under review" | [regions](https://resend.com/docs/dashboard/domains/regions) · [GDPR](https://resend.com/security/gdpr) |
| Lettermint | EU alternative | Lettermint B.V. (NL), founder-owned, no parent | EU only, own AS and IPs | ISO 27001; from €10/month; inbound + broadcasts | [EU email](https://lettermint.co/european-email) · [sub-processors](https://lettermint.co/subprocessors) |
| Scaleway TEM | EU alternative | FR | `fr-par` only | API still `v1alpha1`; no inbound, no marketing | [TEM](https://www.scaleway.com/en/transactional-email-tem/) |
| Brevo | EU alternative | Sendinblue SAS (FR); US subsidiary for support | EU by default (OVH France, GCP Belgium) | ISO 27001 | [terms/DPA](https://www.brevo.com/legal/termsofuse/) |
| Mailjet | EU alternative | Sinch group (SE), which includes US companies | GCP Frankfurt + Belgium | ISO 27001 as stated | [security](https://www.mailjet.com/legal/security-privacy/) |

### 4.7 Authentication

| Option | Role | US control | EU setting | Notes | Source |
|---|---|---|---|---|---|
| better-auth | Default | library, MIT | none needed — users live in **your** database | no sub-processor, **unless** the optional paid "Better Auth Infrastructure" add-on is enabled (operator and hosting not verified — treat as a new sub-processor) | [intro](https://www.better-auth.com/docs/introduction) · [infrastructure](https://better-auth.com/docs/infrastructure/introduction) |
| Clerk | Default (managed) | Clerk, Inc. (SF) | **no EU region** — *"US-based only"*, regional residency *"Not offered"* | DPF active; flag and record if chosen | [security](https://clerk.com/security) |
| Supabase Auth | Default (mobile) | see §4.2 | users in the project's Postgres → project region | Supabase's own account data: US/SG | [users](https://supabase.com/docs/guides/auth/users) |
| Keycloak (self-hosted) | EU alternative | CNCF project, Apache-2.0 | wherever you run it | you own upgrades and HA | [keycloak.org](https://www.keycloak.org/) |
| ZITADEL | alternative — **US parent** | ZITADEL Inc. (SF) parent, contracts via CAOS AG (CH, adequacy) | Cloud `europe-west3` (Frankfurt) or self-host (AGPL) | *"cannot guarantee that data in transit will stay exclusively within the selected region"* | [GDPR](https://zitadel.com/gdpr) |
| Ory | alternative — **US HQ** | Ory Corp (AZ), German GmbH as EEA representative | Ory Network personal-data location "EU", fixed; self-host Kratos | operational data globally replicated | [data location](https://www.ory.com/docs/security-compliance/personal-data-location) |

For an EU-controlled auth stack: better-auth in an EU database, or self-hosted Keycloak / ZITADEL / Ory Kratos.

### 4.8 Payments

| Option | Role | Controller role & location | Source |
|---|---|---|---|
| Stripe | Default | EEA contracts with Stripe Payments Europe, Ltd (IE); DPA says data is transferred *"globally"* incl. Stripe, LLC (US); Stripe is processor **and** controller (fraud, risk, compliance); DPF active | [DPA](https://stripe.com/legal/dpa) |
| Polar | Default (merchant of record) | Polar Software, Inc. (DE, USA); seller of record; hosting and DPA not published (not verified) | [privacy](https://polar.sh/legal/privacy) |
| RevenueCat | Default (mobile) | US; AWS and Snowflake in the **USA**; SCCs in the DPA; **no EU option** — flag and record | [DPA](https://www.revenuecat.com/dpa/) |
| Mollie | EU alternative | Mollie B.V. (NL, DNB-licensed); controller for most processing; hosting location not verified | [privacy](https://www.mollie.com/privacy) |
| Adyen | EU alternative | Adyen N.V. (NL, bank); controller for acquiring; hosting not stated | [privacy](https://www.adyen.com/policies-and-disclaimer/privacy-policy) |

### 4.9 Product analytics · logging and observability

| Option | Role | US control | EU setting | Notes | Source |
|---|---|---|---|---|---|
| PostHog Cloud EU | Default | PostHog, Inc. (SF) | sign up at `eu.posthog.com` (AWS Frankfurt), separate account per region | EU sub-processors are US companies | [data storage](https://posthog.com/docs/privacy/data-storage) |
| Umami (self-hosted) | Default | MIT | wherever you run it | documented cookieless | [docs](https://docs.umami.is/docs/) |
| Plausible | EU alternative | Estonian entity, bootstrapped | Hetzner Falkenstein, EU by default | cookieless | [data policy](https://plausible.io/data-policy) |
| Pirsch | EU alternative | Emvi Software GmbH (DE) | Hetzner (DE) | cookie-free, hashed IPs | [privacy](https://pirsch.io/privacy) |
| Matomo | alternative (NZ company, adequacy) | InnoCraft (NZ) | Cloud in Frankfurt, or self-host | ISO 27001 | [cloud](https://matomo.org/matomo-cloud/) |
| Sentry EU | Default | Functional Software, Inc. (SF) | pick EU (Frankfurt, `de.sentry.io`) **at org creation**, not changeable | **user accounts, org settings, tokens, audit logs, integration metadata stay in the US** | [data storage location](https://docs.sentry.io/organization/data-storage-location/) |
| Axiom | Default (logs) | US | EU edge `eu-central-1.aws.edge.axiom.co`, per dataset, fixed | account management through US infrastructure | [regions](https://axiom.co/docs/reference/regions) |
| Better Stack | Default (logs) | Better Stack, Inc. (DE, USA) | `data_region: germany` per source | independent controller for account data | [create source](https://betterstack.com/docs/logs/api/create-a-source/) |
| GlitchTip / Bugsink | EU alternative (Sentry-SDK compatible) | GlitchTip MIT; Bugsink B.V. (NL, source-available PolyForm Shield) | self-host; Bugsink hosted *"within the European Union"* | switch the DSN | [Bugsink](https://www.bugsink.com/privacy-policy/) · [GlitchTip](https://glitchtip.com/) |
| Scaleway Cockpit | EU alternative | FR | regional push endpoints (e.g. `fr-par`) | metrics/logs/traces, not an error tracker | [Cockpit](https://www.scaleway.com/en/docs/cockpit/) |

### 4.10 AI / LLM inference

| Option | Role | EU processing & setting | Retention / training | Source |
|---|---|---|---|---|
| Vercel AI Gateway | Default | per request `providerOptions.gateway.inferenceRegion = { scope: 'zone', geoRegion: 'eu' }` — fails closed with HTTP 400; assert `providerMetadata…inferenceEndpoint.geoRegion`. **Gap stated in the docs:** the gateway hop itself *"can terminate and be processed in any Vercel region"* | gateway keeps nothing; `zeroDataRetention: true` (Pro/Enterprise per request; team-wide $0.10 / 1,000 requests) routes only to ZDR providers; EU pin passes provider regional pricing (e.g. +10%) | [regional inference](https://vercel.com/docs/ai-gateway/security-and-compliance/regional-inference) · [ZDR](https://vercel.com/docs/ai-gateway/security-and-compliance/zdr) |
| Anthropic API (direct) | Default (via gateway) | **no EU option** — `inference_geo` is `global` or `us` only; for EU use Vertex `eu`, a Bedrock EU profile or Foundry | not used for training by default | [data residency](https://platform.claude.com/docs/en/manage-claude/data-residency) |
| Claude on Vertex AI | EU of default | multi-region endpoint `eu` (`aiplatform.eu.rep.googleapis.com`); Global endpoint gives *"no data residency guarantees"* | no training without permission; +10% | [Claude on Vertex](https://platform.claude.com/docs/en/build-with-claude/claude-on-vertex-ai) |
| Claude on Amazon Bedrock | EU of default | EU geo cross-Region inference profile (destination list *"will never change"*) | providers have no access to prompts; explicit no-training wording not verified | [inference profiles](https://docs.aws.amazon.com/bedrock/latest/userguide/inference-profiles-support.html) |
| OpenAI API | EU of default | new project with region Europe; **needs sales approval** (abuse monitoring controls + Modified Retention amendment); fixed per project | no training since 1 Mar 2023 unless opted in; +10% for models released from 2026-03-05 | [your data](https://developers.openai.com/api/docs/guides/your-data) |
| Azure OpenAI / Foundry | EU of default | `DataZoneStandard` on an EU resource → EU Data Boundary; `GlobalStandard` may process anywhere | not used to train; not available to OpenAI | [deployment types](https://learn.microsoft.com/en-us/azure/ai-foundry/foundry-models/concepts/deployment-types) |
| Mistral AI | EU alternative (FR, no US parent) | EU by default; US endpoint only if chosen | API data not used for training — but **Labs models may train regardless of opt-out**; check the privacy toggle; ZDR on Scale plan by request | [data location](https://help.mistral.ai/en/articles/347629-where-do-you-store-my-data-or-my-organization-s-data) · [controls](https://docs.mistral.ai/admin/monitor-comply/privacy-data-controls) |
| Scaleway Generative APIs | EU alternative | Paris; open models on Scaleway infrastructure | ZDR by default (misuse/500 investigation up to 2 weeks); no training | [data privacy](https://www.scaleway.com/en/docs/generative-apis/reference-content/data-privacy/) |
| OVHcloud AI Endpoints | EU alternative | Gravelines (FR) | *"never be used to train"*; zero retention except billing | [capabilities](https://docs.ovhcloud.com/en/guides/public-cloud/ai-machine-learning/ai-endpoints-capabilities) |

The model call is the transfer that matters: self-hosting the eve runtime does not move inference.

### 4.11 Queues, background jobs, workflows

| Option | Role | EU setting | Caveat | Source |
|---|---|---|---|---|
| Vercel Queues (beta) | Default | queue region `fra1`/`cdg1`/`dub1`/`arn1` | during an outage messages may be stored in a neighbouring region — *"Strict data residency… is not supported yet"*; consumer functions default to `iad1` | [concepts](https://vercel.com/docs/queues/concepts) |
| Vercel Workflows | Default | `start(wf, args, { region: 'fra1' })`, workflow ≥ 5.0.0-beta.33 | **4.x runs always live in `iad1`** | [workflow](https://vercel.com/docs/workflow) |
| Inngest Cloud | seen in projects | **no EU region** (AWS US) — self-host, or encrypt payloads with the SDK middleware | flag and record | [security](https://www.inngest.com/docs/learn/security) |
| Upstash QStash / Redis | seen | QStash default is EU (`eu-central-1`); Redis primary region at creation, no non-EU replicas | US company (Upstash, Inc.) | [QStash regions](https://upstash.com/docs/qstash/howto/multi-region) |
| Trigger.dev | seen | worker region `eu-central-1` | DPA: data stored in **AWS US-East-1** — EU execution, not EU storage | [DPA](https://trigger.dev/legal/dpa) |
| Scaleway Queues + Serverless Jobs | EU alternative | Queues `fr-par`, `nl-ams` (SQS-compatible); Jobs Paris, Amsterdam | no durable-step SDK | [Queues](https://www.scaleway.com/en/docs/queues/concepts/) · [Jobs](https://www.scaleway.com/en/docs/serverless-jobs/) |

### 4.12 Key management

| Option | Role | EU setting | Notes | Source |
|---|---|---|---|---|
| AWS KMS | EU of a hyperscaler | `eu-central-1`, `eu-west-1`, `eu-west-3`, `eu-south-1`, `eu-south-2`, `eu-north-1` (`eu-west-2` London, `eu-central-2` Zurich are not EU) | FIPS 140-3 L3 HSMs; US parent | [KMS](https://docs.aws.amazon.com/kms/latest/developerguide/overview.html) |
| Google Cloud KMS | EU of a hyperscaler | multi-region `europe` or a single EU region; **avoid `eur5`–`eur8`** (include London or Zurich) | location fixed per key ring | [locations](https://docs.cloud.google.com/kms/docs/locations) |
| Scaleway Key Manager | EU alternative | `fr-par`, `nl-ams`, `pl-waw` | `generate-data-key` for envelope encryption; API `v1alpha1` | [Key Manager](https://www.scaleway.com/en/docs/key-manager/) |
| OVHcloud KMS (OKMS) | EU alternative | region-bound domain, KMIP + REST | **backups replicated to two other regions** — check the mapping | [architecture](https://docs.ovhcloud.com/en/guides/manage-and-operate/kms/architecture-overview) |
| OpenBao (self-hosted) | EU alternative | wherever you run it | OSI-licensed Vault fork (Linux Foundation); Vault itself is BSL and IBM-owned | [openbao.org](https://openbao.org/) |

### 4.13 Mobile backend and project tooling

| Option | Role | EU setting | What stays out | Source |
|---|---|---|---|---|
| Supabase | Default | specific EU region at project creation | as §4.2 | [regions](https://supabase.com/docs/guides/platform/regions) |
| Firebase | alternative | Firestore / Storage / RTDB location per resource; **set Cloud Functions region** (default `us-central1`) | **Firebase Authentication runs only in US data centres**; services without location selection may process anywhere | [locations](https://firebase.google.com/docs/projects/locations) · [privacy](https://firebase.google.com/support/privacy) |
| Expo Push Service | Default | **no EU option** (GCP US) | stores push tokens, not content; `getDevicePushTokenAsync` sends to FCM/APNs directly and skips Expo | [push FAQ](https://docs.expo.dev/push-notifications/faq/) |
| RevenueCat | Default | **no EU option** | as §4.8 | [DPA](https://www.revenuecat.com/dpa/) |
| Linear (`linear-scrum`) | Default | choose **European Union at workspace creation** — not self-serve to change | workspace info, **all user accounts and API keys**, notification emails and usage data stay in the US | [security](https://linear.app/docs/security) · [EU hosting](https://linear.app/changelog/2024-05-23-european-union-data-hosting) |

---

## 5. Regulations — primary links and re-verification cadence

| Instrument | What matters for engineering choices | Primary source | Re-verify |
|---|---|---|---|
| **GDPR** (EU) 2016/679 | Art. 9 special categories (biometric identification = Art. 9) · 10 criminal data · 25 by design and default (retention is a default, not a setting) · **28** processors and sub-processor authorisation · **30** records (the under-250 exemption does not apply with Art. 9/10 data) · **32** security incl. encryption · 33–34 breach within 72 h · **35** DPIA (large-scale Art. 9/10 data) · **44–49** transfers — Art. 49 derogations are not a basis for routine hosting | [EUR-Lex](https://eur-lex.europa.eu/eli/reg/2016/679/oj/eng) | quarterly; at once if the Data Omnibus is adopted |
| **EU-US DPF** Decision (EU) 2023/1795 | covers only listed organisations; *Latombe* T-553/23 dismissed 3 Sep 2025; **appeal C-703/25 P pending** | [EUR-Lex](https://eur-lex.europa.eu/eli/dec_impl/2023/1795/oj/eng) · [appeal notice](https://eur-lex.europa.eu/eli/C/2025/6610/oj/eng) | monthly while C-703/25 P is pending |
| **SCCs** Decision (EU) 2021/914 | Module 3 (P2P) for processor → sub-processor; Clause 14 = transfer impact assessment | [EUR-Lex](https://eur-lex.europa.eu/eli/dec_impl/2021/914/oj/eng) | annually |
| **EDPB** | Rec. 01/2020 (remote access is a transfer; Use Case 6) · Guidelines 07/2020 controller/processor · 05/2021 what a transfer is · **Opinion 22/2024** (identity of the whole sub-processor chain) · 02/2024 Art. 48 (answering a foreign order is a transfer) · 9/2022 and 01/2021 breach | [EDPB documents](https://www.edpb.europa.eu/our-work-tools/our-documents_en) | every EDPB plenary release |
| **AI Act** (EU) 2024/1689, amended by **(EU) 2026/1744** (in force 27 Jul 2026) | Art. 5 prohibitions from 2 Feb 2025 · GPAI obligations from 2 Aug 2025 · **Art. 50 transparency from 2 Aug 2026** (legacy generative systems: Art. 50(2) marking by 2 Dec 2026) · **Annex III high-risk moved to 2 Dec 2027**, Annex I to 2 Aug 2028 · Annex III 1(a) excludes 1:1 biometric *verification* (our reading for selfie-to-ID check-in — confirm with counsel) | [AI Act](https://eur-lex.europa.eu/eli/reg/2024/1689/oj/eng) · [2026/1744](https://eur-lex.europa.eu/eli/reg/2026/1744/oj/eng) | quarterly; on each Commission guideline under Arts. 6, 50, 96 |
| **Data Omnibus** COM(2025) 837 | **a proposal, not law** — its GDPR, ePrivacy, Data Act and NIS2 changes do not apply | [procedure 2025/0360/COD](https://eur-lex.europa.eu/legal-content/EN/HIS/?uri=CELEX:52025PC0837) | monthly |
| **NIS2** Dir. (EU) 2022/2555 · Italy **D.lgs. 138/2024** | in scope if medium-sized or larger and of a listed type (cloud, data centre, CDN, managed services, marketplaces); Art. 21(2)(d) supply-chain duties reach vendors of covered customers; Italy: ACN registration 1 Jan–28 Feb each year | [NIS2](https://eur-lex.europa.eu/eli/dir/2022/2555/oj/eng) · [D.lgs. 138/2024](https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:decreto.legislativo:2024-09-04;138) · [ACN](https://www.acn.gov.it/portale/nis) | before each registration window |
| **Data Act** (EU) 2023/2854 | applies from 12 Sep 2025; cloud switching: notice ≤ 2 months, transition ≤ 30 days; **no switching charges from 12 Jan 2027**; Art. 28 — providers publish the jurisdiction of their infrastructure (a documented answer per vendor) | [EUR-Lex](https://eur-lex.europa.eu/eli/reg/2023/2854/oj/eng) | semi-annually; 12 Jan 2027 |
| **eIDAS 2** (EU) 2024/1183 | Member States provide an EU Digital Identity Wallet within 24 months of the Dec 2024 implementing acts (≈ late 2026 — our computation); selective disclosure could replace ID photo capture | [EUR-Lex](https://eur-lex.europa.eu/eli/reg/2024/1183/oj/eng) | quarterly until national wallets launch |
| **CLOUD Act** 18 U.S.C. § 2713 | disclosure duty for data in a provider's control regardless of location | [govinfo](https://www.govinfo.gov/content/pkg/USCODE-2023-title18/html/USCODE-2023-title18-partI-chap121-sec2713.htm) · [DOJ](https://www.justice.gov/criminal/cloud-act-resources) | annually |

### 5.1 Italy

| Instrument | What matters | Primary source | Re-verify |
|---|---|---|---|
| Codice privacy, D.lgs. 196/2003 as amended by D.lgs. 101/2018 | art. 2-octies: criminal data; read the current text on Normattiva | [Normattiva](https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:decreto.legislativo:2003-06-30;196) | semi-annually |
| Garante, provv. 364 of 6 Jun 2024 (email metadata) | email metadata and logs *"non dovrebbe comunque superare i 21 giorni"* without further safeguards | [doc. web 10026277](https://www.garanteprivacy.it/home/docweb/-/docweb-display/docweb/10026277) | Garante newsletter, monthly |
| Garante, 9 Jun 2022 (Google Analytics) | encryption with keys held by the US provider is not a supplementary measure — the key-control reasoning still applies | [doc. web 9782890](https://www.garanteprivacy.it/home/docweb/-/docweb-display/docweb/9782890) | — |
| **Guest registration** — TULPS art. 109 + D.M. 7 Jan 2013 as amended by **D.M. 16 Sep 2021** | send guest data within 24 h of arrival (6 h for stays ≤ 24 h), leases < 30 days included; **delete the transmitted data as soon as the Alloggiati Web receipt exists, keep only the receipt for 5 years** (art. 4-bis(2)) | [TULPS art. 109](https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:regio.decreto:1931-06-18;773~art109) · [D.M. 2021](https://www.gazzettaufficiale.it/eli/id/2021/10/14/21A06000/sg) | semi-annually |
| **Garante note, 29 Apr 2026** — guests' identity documents | no copies required; delete digital copies and destroy paper copies once the receipt exists; **no photos on mobile devices or messaging apps**; providers governed by Art. 28 | [doc. web 10244289](https://www.garanteprivacy.it/home/docweb/-/docweb-display/docweb/10244289) | monthly |

For a product in that domain the engineering rule follows directly: **no persistent ID-image storage** —
extract the fields, transmit, keep the receipt, purge; and a DPIA before any biometric matching.

---

## 6. Where each skill applies this

| Skill | What it does with the decision |
|---|---|
| `dev-flow` §Stack decisions | asks §1, records with `data_residency.py decide`, walks the bundle through §4 proposing EU region and European alternative per service |
| `module-add` Step 1b · `rn-module-add` Step 2b | reads the decision, sets the EU region in the config it writes, records the provider with `data_residency.py add`; a provider with no EU option is flagged, not refused |
| `eve-agent` §Where the agent's data goes | model route from §4.10, EU Sandbox region, bounded session and event-log retention, ids instead of sensitive data in payloads |
| `compliance-audit` | `data_residency.py check --json` is the baseline for R3, R8, R9: register vs. code, configured regions vs. decision, transfer bases on flagged rows |
| `vercel-doctor` | surfaces non-EU `regions` in `vercel.json` under an EU decision, routes the change to `module-add deploy` |
| `update_meta.py set-phase` / `show_state.py` | refuses `scaffolded` while `stack.data_residency` is `null`; shows flags without blocking |

## 7. Keeping it current

Re-run the vendor rows **every quarter** and whenever a default changes; the regulation rows on the cadence
in §5. Update the date at the top only for rows actually re-read, and record each pass in
`docs/vercel-changelog-watch.md`. Open questions from 2026-09-15 that a pass should try to close: DPF
registry status for vendors whose listing could not be read (Supabase, Neon's listing under Databricks,
RevenueCat), Vercel's build region in the docs, the operator of Better Auth Infrastructure, hosting
locations of Mollie, Adyen and Polar, the C-703/25 P procedural stage, and whether a vertical SaaS is a
"data processing service" under the Data Act.
