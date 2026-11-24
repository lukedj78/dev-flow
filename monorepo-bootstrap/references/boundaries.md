# Package boundaries — topology `"web-agent-inapp"`

One web app, the eve agent inside it (`apps/web/agent/`), and a set of domain packages whose
boundaries are the reason the repo is a monorepo at all. The boundaries are enforced by **what each
package declares**, checked on every `pnpm lint`, not by a review someone may skip.

## `boundaries.json` — the one source

At the repo root, committed. It says which packages exist and who may use whom; `scaffold_packages.py`
creates them from it and `check_boundaries.py` enforces it, so the two can never disagree.

```json
{
  "scope": "@acme",
  "packages": {
    "packages/db":       { "purpose": "schema, migrations, repositories", "may_depend_on": ["config"] },
    "packages/services": { "purpose": "the only domain door", "may_depend_on": ["platform", "auth"] },
    "capabilities/*":    { "purpose": "one capability = one eve extension", "may_depend_on": ["contracts", "services"] },
    "apps/web":          { "purpose": "the Next.js app", "may_depend_on": ["*"] }
  },
  "paths": {
    "apps/web/agent": { "may_import": ["contracts", "services", "capability-*"] }
  }
}
```

- Names are workspace packages **without the scope** (`db` = `@acme/db`); `*` is every workspace
  package; a trailing `*` is a prefix (`capability-*`).
- `paths` exists because the agent and the app are **one package**: `package.json` cannot stop
  `apps/web/agent/tools/x.ts` from importing `@acme/db`, so a path rule does. Keeping the agent on
  services and contracts is what lets it move to its own `apps/agent` later as a move, not a rewrite.
- The starting table for this topology is `boundaries-web-agent-inapp.json`. Change it when the
  product needs it, with a reason the team can read (an ADR in projects that keep them). Adding a
  package means adding it here first; `pnpm lint` then fails until the code agrees.

## The four checks (`scripts/check_boundaries.py`)

The project runs **its own copy** (`init-monorepo.sh` puts it in `scripts/`), so CI needs no skill. The `set-phase scaffolded` gate runs **the skill's** copy instead: a check the repository controls cannot be the one that guards the repository.

| Check | Refuses |
|---|---|
| Declared | a workspace package (from `pnpm-workspace.yaml`) that `boundaries.json` does not list — no rule means refused, not allowed |
| Dependencies | a `@scope/*` entry in `dependencies` / `devDependencies` / `peerDependencies` that `may_depend_on` does not allow |
| Undeclared imports | an import of a workspace package the file's `package.json` does not declare |
| Internals | `@scope/pkg/some/file` unless `pkg`'s `exports` declares that subpath — a package's public surface is what it exports |
| Paths | from a `paths` folder: a workspace package not in `may_import`, an alias (`@/`, `~/`, `#…`, or any `paths` key of the nearest `tsconfig.json`), or a relative path that leaves the folder |

Comments are removed by a scanner that leaves strings alone (a URL or a glob in a string no longer hides the import after it); `.vue`, `.svelte` and `.astro` files are read too, as are `import(`…`)` with a backtick and `vi.mock`/`jest.mock`. An import built at runtime cannot be read and is not policed. Only workspace packages are policed: npm dependencies
are each package's own business. `--self-test` builds a throwaway monorepo with one violation of each
kind and proves every one is refused and the legal imports are not — run it after editing the script.

**Measured on a scaffold of this topology (2026-11-24):** with a capability depending on `db`, an
import of `@demo/services/src/index` and an agent tool importing `@demo/db`, `pnpm lint` exits 1 with
exactly those three; clean, it exits 0, and `pnpm typecheck` / `pnpm test` pass across all packages.

## Tooling that comes with the topology

- **Biome** for lint and format of the code (`biome check .` in the root `lint`). The shared rules are
  `packages/config/biome.base.json`, extended by the root `biome.json`. Not `biome.json`: Biome 2
  treats a second `biome.json` below the root as a nested root configuration and refuses to run.
- **One `packages/config`** — `tsconfig/{base,library,nextjs}.json`, `biome.base.json`, `src/env.ts`.
  Packages extend `../config/tsconfig/library.json` by relative path, so nothing depends on `config`
  just to compile and the table stays about code.
- **ESLint only for the design lint** (`@shadcn/lint` is an ESLint plugin), only in `apps/web` and
  `packages/ui`, and only where the UI is styled with Tailwind.
- `turbo.json` keeps `build.dependsOn: ["^build"]`: a capability that depends on `contracts` must build
  after it, or `eve extension build` produces a package with no tools.
