# module-add → `cms` (Sanity via `next-sanity` — default)

Wire **Sanity** as the content layer of a Next.js 16 App Router app. Editors get a hosted **Sanity
Studio** as their admin panel; the app reads content in **Server Components** through
`sanityFetch` from `next-sanity/live`, which keeps pages fresh on publish without a cache-invalidation
layer of your own.

**Scope.** Content a non-developer edits and the app only reads — pages, posts, catalogue, FAQs,
pricing copy. User-owned data (accounts, orders, messages) stays in `db` / `auth`. The two never
overlap: the Studio is CRUD for content, Postgres + RLS is CRUD for users.

> **Versions checked 2026-09-08** — `next-sanity@13.3.4` (peers `next ^16.0.0-0`, `react ^19.2.3`,
> `sanity ^5.29.0 || ^6.0.0`, `@sanity/client ^7.26.2 || ^8.0.0`, `styled-components ^6.1`);
> `sanity@6.13.0` (`engines.node >=22.12`). Sources: the `next-sanity` README
> (<https://github.com/sanity-io/next-sanity>), the official template
> <https://github.com/sanity-io/sanity-template-nextjs-clean> (`frontend/sanity/lib/*`, `studio/*` —
> committed 2026-08-03, pins `next-sanity ^13.0.8` / `sanity ^5.31.1`),
> <https://www.sanity.io/docs/api-versioning>, <https://www.sanity.io/docs/keeping-your-data-safe>,
> <https://www.sanity.io/docs/studio/deployment>.

## Idempotency check

1. `package.json` has `next-sanity` in `dependencies`.
2. `sanity/lib/client.ts` and `sanity/lib/live.ts` exist.
3. `.env.local.example` contains `NEXT_PUBLIC_SANITY_PROJECT_ID`.
4. `meta.json#stack.cms == "sanity"`.

All four → installed; offer a new schema type or a new query instead.

## Prerequisites

- Next.js 16 App Router (`stack.nextjs_version = "16"`). `sanityFetch` is a **server read** — it sits
  on rung 1 of `data-fetching`'s ladder (async Server Component). Never fetch Sanity from a Client
  Component with `useEffect`; never through a Server Action (actions are for mutations).
- Node ≥ 22.12 for the Studio package.

## Out-of-band setup (the user)

1. Create the project at <https://www.sanity.io/manage>; dataset `production`.
2. Create a **Viewer** token for the app's *server* — `SANITY_API_READ_TOKEN`. It is read in a
   `server-only` module (below) and never reaches the browser bundle. The docs: *"Never add an access
   token to JavaScript that is bundled for client-side use and served publicly."*
3. Optionally an **Editor** token for seed scripts, kept in `cms/.env` only.

## Where the Studio lives — two shapes

| Shape | When | Cost |
|---|---|---|
| **`cms/` package in the repo** *(default — same as the mobile module, and what the official template does with `studio/`)* | one codebase, editors get `https://<host>.sanity.studio`, the web bundle carries no Studio code | a second `package.json` |
| **Embedded route** `app/studio/[[...tool]]/page.tsx` via `next-sanity/studio` | the Studio must sit under the app's own domain/auth | `sanity` + `styled-components` in the web app; `[VERIFY]` the current embedded-Studio guide linked from the next-sanity README before writing the route — its code is not quoted here |

Default to the package: in a monorepo it is the same `cms/` the mobile app uses, one schema for both.
The `cms/` package layout, `sanity.config.ts`, `sanity.cli.ts`, schema idioms, seed script and
`sanity deploy` are documented once, in `rn-module-add/references/module-cms-sanity.md` §A, §D, §E —
follow them verbatim; nothing differs for web.

## Install (app)

```bash
cd <project-root>
pnpm add next-sanity @sanity/image-url
```

## Files (from the official template, trimmed)

```ts
// sanity/lib/api.ts — keep lean: imported by both server and client code
function assertValue<T>(v: T | undefined, message: string): T {
  if (v === undefined) throw new Error(message);
  return v;
}
export const projectId = assertValue(process.env.NEXT_PUBLIC_SANITY_PROJECT_ID, "Missing NEXT_PUBLIC_SANITY_PROJECT_ID");
export const dataset = assertValue(process.env.NEXT_PUBLIC_SANITY_DATASET, "Missing NEXT_PUBLIC_SANITY_DATASET");
// A static date — see https://www.sanity.io/docs/api-versioning ("today's date … written as a static string")
export const apiVersion = process.env.NEXT_PUBLIC_SANITY_API_VERSION || "2026-09-01";
export const studioUrl = process.env.NEXT_PUBLIC_SANITY_STUDIO_URL || "http://localhost:3333";
```

```ts
// sanity/lib/token.ts
import "server-only";
export const token = process.env.SANITY_API_READ_TOKEN;
if (!token) throw new Error("Missing SANITY_API_READ_TOKEN");
```

```ts
// sanity/lib/client.ts
import { createClient } from "next-sanity";
import { apiVersion, dataset, projectId, studioUrl } from "@/sanity/lib/api";
import { token } from "@/sanity/lib/token";

export const client = createClient({
  projectId,
  dataset,
  apiVersion,
  useCdn: true,
  perspective: "published",
  token, // required for a private dataset; server-only via token.ts
  stega: { studioUrl },
});
```

```ts
// sanity/lib/live.ts
import { defineLive } from "next-sanity/live";
import { client } from "@/sanity/lib/client";
import { token } from "@/sanity/lib/token";

export const { sanityFetch, SanityLive } = defineLive({
  client,
  serverToken: token,   // drafts in Presentation / Draft Mode
  browserToken: token,  // shared with the browser ONLY inside a valid Next.js Draft Mode session
});
```

`<SanityLive />` is rendered once, in `app/[locale]/layout.tsx` (the template's comment: *"responsible
for making all sanityFetch calls in your application live, so should always be rendered"*).

```tsx
// app/[locale]/(marketing)/posts/[slug]/page.tsx — a Server Component read
import { sanityFetch } from "@/sanity/lib/live";
import { postQuery } from "@/sanity/lib/queries";

export default async function PostPage(props: { params: Promise<{ slug: string }> }) {
  const params = await props.params;
  const { data: post } = await sanityFetch({ query: postQuery, params });
  if (!post?._id) notFound();
  return <Article post={post} />;
}
```

GROQ lives in `sanity/lib/queries.ts` as `defineQuery` strings; dereference references with `->`
(`author->{name}`, `image.asset->url`). Run `npx sanity typegen generate` from `cms/` (the template's
`sanity.cli.ts` `typegen` block) to get typed results.

## `.env.local.example`

```
NEXT_PUBLIC_SANITY_PROJECT_ID=
NEXT_PUBLIC_SANITY_DATASET=production
NEXT_PUBLIC_SANITY_API_VERSION=2026-09-01
NEXT_PUBLIC_SANITY_STUDIO_URL=http://localhost:3333
# Viewer token, server-only (sanity/lib/token.ts imports "server-only")
SANITY_API_READ_TOKEN=
```

## Verify

`pnpm build` with placeholder env values (`token.ts` throws on a missing token — set the placeholder).
Do not connect: the user sets real values in `.env.local`.

## meta.json

`stack.cms = "sanity"`, phase → `module_added` if earlier, history `{ module: "cms", tech: "sanity" }`.
`compliance-audit`: Sanity becomes a sub-processor; content with personal data (author bios,
testimonials) enters the register. `[VERIFY]` dataset region options before promising EU residency.

## Anti-patterns (NEVER do)

- ❌ `SANITY_API_READ_TOKEN` without the `server-only` import, or any token under `NEXT_PUBLIC_*`.
- ❌ Fetching Sanity in a Client Component (`useEffect` + `client.fetch`) — rung 4 of the ladder for a
  rung-1 problem.
- ❌ Reading content through a Server Action.
- ❌ A computed `apiVersion`.
- ❌ Two Studios (embedded + package) pointing at one dataset with diverging schemas.

## Alternatives (not implemented — refuse and offer)

Payload (self-hosted, Postgres, Next-native), Contentful, Strapi. Same structural template; ground
every identifier in the vendor's docs before running.
