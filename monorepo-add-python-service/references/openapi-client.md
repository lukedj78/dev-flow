> Sources: <https://fastapi.tiangolo.com/how-to/extending-openapi/> (`app.openapi()`) ·
> <https://openapi-ts.dev/> (openapi-typescript, openapi-fetch) ·
> <https://turborepo.dev/docs/reference/configuration#dependson>.
> Verified **2026-09-11**: `openapi-typescript@7.13.0`, `openapi-fetch@0.17.0`, both MIT; the
> `createClient<Paths>(clientOptions?)` signature read from the shipped `dist/index.d.ts`.

# From FastAPI to a client `apps/web` cannot get wrong

The seam has one job: **a change to a Pydantic model must fail `apps/web`'s typecheck.** Not
fail at runtime, not return a 422 nobody reads — fail the build, in CI, before merge.

Three steps, each owned by one package.

## 1. Export the schema without starting a server

`app.openapi()` returns the schema as a dict; FastAPI documents it under *Extending OpenAPI*.
Starting uvicorn and curling `/openapi.json` works too and is worse — it needs a free port and a
readiness wait in CI.

```python
# apps/<name>/scripts/export_openapi.py
"""Dump the OpenAPI schema to openapi.json. No server, no port."""

import json
from pathlib import Path

from <name>.main import app

out = Path(__file__).resolve().parents[1] / "openapi.json"
out.write_text(json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(f"wrote {out}")
```

`sort_keys=True` is not cosmetic: without it the key order can move between runs, the file
changes, and every downstream cache entry is invalidated for no reason.

Commit `openapi.json`. It is generated, and it is also the diff that shows a reviewer the API
changed — which is exactly what you want in a pull request.

## 2. Generate types and the client in `packages/api`

```bash
pnpm --filter @<slug>/api add -D openapi-typescript
pnpm --filter @<slug>/api add openapi-fetch
```

`openapi-typescript` ships a CLI (`bin` in its package.json) and emits **types only** — no
runtime. `openapi-fetch` is the ~6 kB fetch wrapper that consumes them.

```json
// packages/api/package.json
{
  "scripts": {
    "build": "openapi-typescript ../../apps/<name>/openapi.json -o src/<name>/schema.d.ts"
  },
  "dependencies": { "openapi-fetch": "^0.17.0" },
  "devDependencies": {
    "openapi-typescript": "^7.13.0",
    "@<slug>/<name>": "workspace:*"
  }
}
```

That last line is the ordering edge, not a code dependency — see `turbo-integration.md`.

```ts
// packages/api/src/<name>/index.ts
import createClient from "openapi-fetch";

import type { paths } from "./schema";

/** The <name> service client. `baseUrl` comes from the caller, never from a literal. */
export function create<Name>Client(baseUrl: string) {
  return createClient<paths>({ baseUrl });
}

export type { paths as <Name>Paths } from "./schema";
```

**Why these two and not an alternative.** The field has three shapes: a types-only generator
plus a thin runtime (this), a full SDK generator (`openapi-generator`, `orval` —
hundreds of generated files, a build step that outgrows the service), or hand-written `fetch`
(no gate at all). The middle option is the one that makes a schema change a compile error
without adding a code generator to your review surface: `schema.d.ts` is one file, it contains
no logic, and a reviewer can read its diff. `[VERIFY]` on every pass — if something emits the
same guarantee with less, take it; the seam is what matters, not the library.

## 3. Consume it in `apps/web`, and nowhere else

```ts
// apps/web/lib/<name>.ts
import { create<Name>Client } from "@<slug>/api/<name>";

/** Resolve the client per request, not at module scope. */
export function <name>() {
  const baseUrl = process.env.<NAME>_SERVICE_URL;
  if (!baseUrl) throw new Error("<NAME>_SERVICE_URL is not set");
  return create<Name>Client(baseUrl);
}
```

⚠️ **Do not read the variable at module scope**, and do not export a ready-made client. It is the
obvious shape and it breaks the build: `next build` evaluates page modules while collecting page
data, so a top-level `throw` on a missing variable fails the build rather than the request —

```
Error: Failed to collect page data for /
```

— on any machine where the service URL is not set, CI included. A function defers the read to the
request that actually needs it. (Observed 2026-09-11 on Next 16.3.4 while running this skill's
acceptance test; the module-scope version was what this file said first.)

```ts
// in a Server Component or a Route Handler
const { data, error } = await <name>().POST("/echo", { body: { text: "hello" } });
if (error) { /* typed error shape */ }
// data is typed from the Pydantic model. Rename a field in Python and this stops compiling.
```

`openapi-fetch` returns `{ data, error }` rather than throwing — the error is part of the type,
so the handler is checked too.

**The service is called server-side.** `<NAME>_SERVICE_URL` is a server variable, not
`NEXT_PUBLIC_*`: a browser calling the Python service directly means CORS, a public endpoint and
a second authentication surface. If a page genuinely needs it from the client, proxy through a
Route Handler.

## Making the typecheck the gate

The generated `schema.d.ts` is the only thing standing between a renamed Pydantic field and a
green build, so it must be **regenerated before the typecheck, in CI, every time**.

```jsonc
// turbo.json
{
  "tasks": {
    "typecheck": { "dependsOn": ["^build"] }
  }
}
```

The chain is already complete once the edges exist: `apps/web` depends on `@<slug>/api`, whose
`build` depends on `^openapi`, which is `apps/<name>`'s export. So `turbo typecheck` runs
export → generate → typecheck, in that order, and a schema change that breaks the web app breaks
it **in CI, on the branch**.

Verify the gate the only way that means anything: rename a field in `schemas.py`, run
`pnpm turbo typecheck`, and watch `apps/web` fail. If it passes, one of the edges is missing —
almost always the `workspace:*` line in `packages/api`.

## Common mistakes

| Mistake | What happens |
|---|---|
| `fetch("http://localhost:8000/…")` in a component | the gate does not exist; drift surfaces as a runtime 422 in production |
| `NEXT_PUBLIC_<NAME>_SERVICE_URL` | the service is now public, and CORS is your problem |
| `openapi.json` gitignored | reviewers cannot see the API change, and CI regenerates it from a different environment |
| No `workspace:*` edge in `packages/api` | the client is generated from the previous schema; everything compiles and is wrong |
| Reading `<NAME>_SERVICE_URL` at module scope | `next build` evaluates page modules to collect page data, so a missing variable fails the **build**, not the request |
| Editing `schema.d.ts` by hand | overwritten on the next build, and the edit was a workaround for a Pydantic model that should have changed |
