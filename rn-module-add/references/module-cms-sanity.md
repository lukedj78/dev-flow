# rn-module-add → `cms` (Sanity — default)

Wire **Sanity** as the content layer of an Expo + RN app: a hosted **Sanity Studio is the admin panel**
(no admin UI to build, no admin users in your database), and the app reads the catalogue with GROQ over
Sanity's **HTTP Query API** — plain `fetch`, no SDK in the bundle, nothing for Metro to mis-resolve.

**What belongs here and what does not.** Content that a non-developer edits and the app only *reads*
— catalogue, articles, FAQs, pricing tables, marketing copy — goes in the CMS. Anything a *user* of
the app creates or owns — accounts, bookings, orders, messages — stays in the transactional backend
(`auth` / `db` modules: Supabase by default). The split is the whole point: the Studio gives editors
CRUD on content for free, RLS protects user data in Postgres, and neither has to know about the other.

> **Versions checked 2026-09-08** — `sanity@6.13.0` and `@sanity/vision@6.13.0` (npm `latest`;
> `engines.node >=22.12`), `@sanity/client@8.6.1`. Sanity's own Next.js template still pins
> `sanity@^5.31.1`; both majors export `sanity/structure` and `sanity/cli`, so the config below works on
> either — `[VERIFY]` the peer ranges on a bump. Docs: <https://www.sanity.io/docs/http-query>,
> <https://www.sanity.io/docs/api-versioning>, <https://www.sanity.io/docs/keeping-your-data-safe>,
> <https://www.sanity.io/docs/studio/deployment>, <https://www.sanity.io/docs/studio/configuration>,
> template <https://github.com/sanity-io/sanity-template-nextjs-clean> (schema/config idioms).

## Idempotency check

1. `<project-root>/cms/sanity.config.ts` exists.
2. `<project-root>/lib/cms.ts` exists.
3. `<project-root>/.env.example` contains `EXPO_PUBLIC_SANITY_PROJECT_ID`.
4. `meta.json#stack.cms == "sanity"`.

All four → "already wired"; offer to add a schema type or a query instead. Otherwise proceed.

## Out-of-band setup (the user does this — it needs an account)

1. **Create the project** at <https://www.sanity.io/manage> (or `npx sanity@latest init` inside
   `cms/` once scaffolded). Note the **project id**; the default dataset is `production`.
2. **Decide public vs private dataset.** Per the docs, in a public dataset *"everyone can query for
   content in the dataset without being authorized"*; in a private one *"only authenticated users or
   requests with authorization tokens can read"*. **For a catalogue the app shows to everyone, keep the
   dataset public and ship no token.** An `EXPO_PUBLIC_*` variable is compiled into the JS bundle, and
   the docs are explicit: *"Never add an access token to JavaScript that is bundled for client-side use
   and served publicly unless you take extra precautions."* If the content genuinely must be private,
   read it through your backend (a Supabase Edge Function or the web app), not from the phone.
3. **Create one Editor token for the seed/import scripts** — manage.sanity.io → project → API →
   Tokens. It lives in `cms/.env` only. It never enters the app's `.env`, `app.json` or `eas.json`.

## Step A — scaffold `cms/` (the Studio, its own package)

`cms/` is a separate npm package inside the repo: one clone, one commit history, one README, and the
Studio deploys independently of the app. Metro must not crawl it — see Step C.

```
cms/
├── package.json
├── sanity.config.ts        # defineConfig + structureTool + visionTool + schema types
├── sanity.cli.ts           # defineCliConfig: api.projectId/dataset, studioHost
├── schemaTypes/
│   ├── index.ts            # export const schemaTypes = [...]
│   └── <type>.ts           # one defineType per document type
├── scripts/
│   └── seed.mjs            # @sanity/client transaction, deterministic _id → idempotent
├── .env.example            # SANITY_STUDIO_PROJECT_ID, SANITY_STUDIO_DATASET, SANITY_SEED_TOKEN
├── .gitignore              # node_modules, dist, .sanity, .env
└── README.md
```

`cms/package.json` (Node 22+, ESM so the seed script can `import`):

```json
{
  "name": "<slug>-cms",
  "private": true,
  "type": "module",
  "engines": { "node": ">=22.12" },
  "scripts": {
    "dev": "sanity dev",
    "build": "sanity build",
    "deploy": "sanity deploy",
    "seed": "node --env-file=.env scripts/seed.mjs"
  },
  "dependencies": {
    "@sanity/client": "^8.6.1",
    "@sanity/vision": "^6.13.0",
    "react": "^19.2.2",
    "react-dom": "^19.2.2",
    "sanity": "^6.13.0",
    "styled-components": "^6.1.15"
  },
  "devDependencies": { "typescript": "^5.9.0" }
}
```

`cms/sanity.config.ts` — the shape the docs give (`defineConfig`, `structureTool` from
`sanity/structure`, `schema: { types }`), reading `SANITY_STUDIO_*` at build time as the official
template does:

```ts
import { defineConfig } from "sanity";
import { structureTool } from "sanity/structure";
import { visionTool } from "@sanity/vision";
import { schemaTypes } from "./schemaTypes";

const projectId = process.env.SANITY_STUDIO_PROJECT_ID ?? "";
const dataset = process.env.SANITY_STUDIO_DATASET ?? "production";

export default defineConfig({
  name: "<slug>-admin",
  title: "<Project name> — Admin",
  projectId,
  dataset,
  plugins: [structureTool(), visionTool()],
  schema: { types: schemaTypes },
});
```

`cms/sanity.cli.ts` — `studioHost` is what `sanity deploy` asks for the first time; pinning it here
makes the deploy non-interactive. Hostnames *"can only contain letters, numbers, and hyphens"* and
*"start and end with a letter or a number"*:

```ts
import { defineCliConfig } from "sanity/cli";

export default defineCliConfig({
  api: {
    projectId: process.env.SANITY_STUDIO_PROJECT_ID,
    dataset: process.env.SANITY_STUDIO_DATASET ?? "production",
  },
  studioHost: process.env.SANITY_STUDIO_STUDIO_HOST || "<slug>", // → https://<slug>.sanity.studio
});
```

Schema types use `defineType` / `defineField` from `sanity` (the template's idiom). Derive them from
the PRD's domain — **never** from a generic "post/author" example. One document type per file:

```ts
// cms/schemaTypes/flight.ts — example from a flight-booking PRD
import { defineField, defineType } from "sanity";

export const flight = defineType({
  name: "flight",
  title: "Flight",
  type: "document",
  fields: [
    defineField({ name: "flightNumber", type: "string", validation: (rule) => rule.required() }),
    defineField({ name: "airline", type: "reference", to: [{ type: "airline" }], validation: (rule) => rule.required() }),
    defineField({ name: "route", type: "reference", to: [{ type: "route" }], validation: (rule) => rule.required() }),
    defineField({ name: "departureTime", type: "datetime", validation: (rule) => rule.required() }),
    defineField({ name: "price", type: "number", validation: (rule) => rule.required().positive() }),
    defineField({ name: "currency", type: "string", options: { list: ["USD", "EUR", "GBP"] }, initialValue: "USD" }),
    defineField({ name: "status", type: "string", options: { list: ["scheduled", "boarding", "delayed", "cancelled"] }, initialValue: "scheduled" }),
  ],
  preview: { select: { title: "flightNumber", subtitle: "status" } },
});
```

```ts
// cms/schemaTypes/index.ts
import { airline } from "./airline";
import { route } from "./route";
import { flight } from "./flight";
export const schemaTypes = [airline, route, flight];
```

Then, in `cms/`: `npm install && npm run dev` → <http://localhost:3333>. The Studio *is* the admin
panel: create, edit, duplicate, delete, publish — nothing to build.

## Step B — the app reads over the HTTP Query API (`lib/cms.ts`)

The endpoint, from the docs:

```
GET https://{projectId}.apicdn.sanity.io/v{YYYY-MM-DD}/data/query/{dataset}?query=<GROQ>&$name=<JSON>
GET https://{projectId}.api.sanity.io/v{YYYY-MM-DD}/data/query/{dataset}      ← uncached; needed with a token
```

- **Parameters** are `$`-prefixed in the GROQ and sent as query-string params. Send **JSON-encoded**
  values (`$origin="lagos"` with the quotes) so strings, numbers and booleans keep their type.
- **Response**: `{ ms, query, result, syncTags }` — the data is under `result`.
- **GET is capped at 11 KB** (*"we've put the max limit on GET queries at 11 KB"*); longer queries go
  by POST with `{ query, params }`, and *"queries sent using the POST method will also be cached on the
  CDN"*.
- **API version is a fixed date.** *"Any past or present date is valid"*, and *"computing it at runtime
  (for example from `new Date()`) means your API version changes every day"* — hardcode `2026-09-01`
  (or the day you start) and bump deliberately.
- A token forces the `api.` host (CDN responses are not authenticated) — one more reason to keep the
  catalogue dataset public.

```ts
// lib/cms.ts — Sanity read access over plain fetch
const projectId = process.env.EXPO_PUBLIC_SANITY_PROJECT_ID;
const dataset = process.env.EXPO_PUBLIC_SANITY_DATASET ?? "production";
const apiVersion = "2026-09-01"; // static on purpose — see api-versioning

if (!projectId) console.warn("[cms] EXPO_PUBLIC_SANITY_PROJECT_ID is not set — copy .env.example to .env");

export class CmsError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "CmsError";
  }
}

export async function cmsFetch<T>(query: string, params: Record<string, unknown> = {}, signal?: AbortSignal): Promise<T> {
  const url = new URL(`https://${projectId}.apicdn.sanity.io/v${apiVersion}/data/query/${dataset}`);
  url.searchParams.set("query", query);
  for (const [key, value] of Object.entries(params)) url.searchParams.set(`$${key}`, JSON.stringify(value));
  if (url.toString().length > 11_000) throw new CmsError(414, "GROQ query over the 11 KB GET limit — switch this call to POST");
  const response = await fetch(url.toString(), { signal });
  if (!response.ok) throw new CmsError(response.status, (await response.text()) || response.statusText);
  return ((await response.json()) as { result: T }).result;
}
```

Queries live in `lib/queries/` as TanStack Query hooks (`rn-data-fetching` patterns), with keys under
`lib/query-keys.ts`:

```ts
// lib/queries/use-flight-search.ts
export function useFlightSearch(params: SearchParams, enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.flights.search(params),
    queryFn: ({ signal }) =>
      cmsFetch<Flight[]>(
        `*[_type == "flight" && status != "cancelled"
          && lower(route->originCity) == $origin
          && lower(route->destinationCity) == $destination
          && departureTime >= $from && departureTime < $to]
          | order(departureTime asc)
          { _id, flightNumber, departureTime, price, currency,
            airline->{ name, code, "logoUrl": logo.asset->url },
            route->{ originCity, originAirportCode, destinationCity, destinationAirportCode } }`,
        { origin: params.origin.toLowerCase(), destination: params.destination.toLowerCase(), from, to },
        signal,
      ),
    enabled, // run on the user's tap, not on every keystroke
    staleTime: 60_000,
  });
}
```

**The dereference rule.** A `reference` field holds `{_ref}`; comparing `originCity` on the flight
itself matches nothing. Filter and project through the arrow — `route->originCity`,
`airline->{name}`, `logo.asset->url`. This exact bug cost three prompt rounds in the tutorial that
motivated this module; write the `->` the first time.

## Step C — keep `cms/` out of the Metro graph

`cms/node_modules` holds React, `sanity` and `styled-components` versions the app must never resolve.
Block the folder in `metro.config.js` (keep the NativeWind wrapper `rn-bootstrap` generated):

```js
const path = require("node:path");
config.resolver.blockList = [
  new RegExp(`${path.resolve(__dirname, "cms").replace(/[/\\]/g, "[/\\\\]")}[/\\\\].*`),
];
```

And exclude it from the app's TypeScript program: `"exclude": ["node_modules", "cms"]` in
`tsconfig.json` (the Studio has its own `cms/tsconfig.json`).

## Step D — seed and bulk import (`cms/scripts/seed.mjs`)

Editors will not type 30 rows by hand. Seed with `@sanity/client` in a **transaction** using
**deterministic `_id`s**, so re-running updates instead of duplicating — `createOrReplace` *"overwrites
existing documents if they have an `_id`"*:

```js
import { createClient } from "@sanity/client";

const client = createClient({
  projectId: process.env.SANITY_STUDIO_PROJECT_ID,
  dataset: process.env.SANITY_STUDIO_DATASET ?? "production",
  token: process.env.SANITY_SEED_TOKEN,   // Editor token — scripts only, never the app
  apiVersion: "2026-09-01",
  useCdn: false,                          // writes and token reads bypass the CDN
});

let tx = client.transaction();
for (const airline of airlines) tx = tx.createOrReplace({ _id: `airline-${airline.code.toLowerCase()}`, _type: "airline", ...airline });
await tx.commit();
```

References between seeded documents are `{ _type: "reference", _ref: "<the deterministic _id>" }`.
A CSV importer follows the same shape (`csv-parse` + one `createOrReplace` per row); ship a template
CSV next to it so editors know the columns.

## Step E — deploy the Studio

```bash
cd cms && npm run deploy        # = npx sanity deploy → https://<studioHost>.sanity.studio
```

The first run prompts for the hostname unless `studioHost` is set (Step A). In CI, `sanity deploy`
authenticates with `SANITY_AUTH_TOKEN`. The deployed Studio is the URL you hand to the content team.

## `.env.example` additions (app root)

```
# Sanity — public read of a PUBLIC dataset. No token here: EXPO_PUBLIC_* ships in the bundle.
EXPO_PUBLIC_SANITY_PROJECT_ID=
EXPO_PUBLIC_SANITY_DATASET=production
```

`cms/.env.example`:

```
SANITY_STUDIO_PROJECT_ID=
SANITY_STUDIO_DATASET=production
SANITY_STUDIO_STUDIO_HOST=
# Editor token for scripts/seed.mjs only — never ship it in the app
SANITY_SEED_TOKEN=
```

## meta.json

- `stack.cms = "sanity"`; `history` entry `{ module: "cms", provider: "sanity" }`; phase →
  `module_added` if earlier.
- `compliance-audit`: Sanity is a **sub-processor** for whatever the Studio stores; if editors put
  personal data in content (author names, testimonials), it enters the register. `[VERIFY]` dataset
  region options on the current Sanity plan before promising EU residency.

## Anti-patterns (NEVER do)

- ❌ Editor / write token in `EXPO_PUBLIC_*`, `app.json` `extra`, or `eas.json` — it is in the bundle.
- ❌ Private dataset + Viewer token in the app "because it's only read" — same bundle, same exposure.
- ❌ `apiVersion: new Date().toISOString().slice(0, 10)` — behaviour changes without a deploy.
- ❌ `@sanity/client` inside the RN app — `fetch` covers reads; keep the SDK in `cms/scripts`.
- ❌ Comparing a reference field's sub-property without `->`.
- ❌ Admin users in Supabase to "manage flights" — that is the Studio's job; RLS stays user-only.
- ❌ A `studio/` folder beside the repo — the agent working in the app cannot see the schema.

## Alternatives (not implemented — refuse and offer)

Payload, Contentful, Strapi, Directus. Same shape (schema → hosted or self-hosted admin → read API);
a new variant is a contract change: copy this file as the structural template and ground every
identifier in the vendor's docs before running.
