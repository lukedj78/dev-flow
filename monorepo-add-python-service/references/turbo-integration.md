> Sources: <https://turborepo.dev/docs/reference/configuration> (`inputs`, `outputs`, `persistent`, `dependsOn`, `$TURBO_DEFAULT$`, `$TURBO_ROOT$`) ·
> <https://turborepo.dev/docs/guides/multi-language> · <https://turborepo.dev/docs/guides/tools/python> · <https://pnpm.io/workspaces>.
> Verified **2026-09-11** against `turbo@2.10.12`.

# The Python app in the task graph

## What turbo actually needs

Nothing Python-aware. Turborepo runs the `scripts` of a workspace member; the member is a
directory with a `package.json` under a `pnpm-workspace.yaml` glob. `apps/*` is already a glob
in every monorepo `monorepo-bootstrap` writes, so **the app joins the workspace by existing**.

Run `pnpm install` once after scaffolding so pnpm records the new member.

## Root `turbo.json`

`monorepo-bootstrap` writes `build` / `dev` / `lint` / `typecheck` / `test`. The Python app
reuses them and adds `openapi`. The tasks below are the complete diff:

```jsonc
{
  "$schema": "https://turborepo.dev/schema.json",
  "tasks": {
    // …build / lint / typecheck / test as scaffolded…

    "dev": {
      "cache": false,
      "persistent": true
    },

    // FastAPI → apps/<name>/openapi.json. Cacheable: same sources, same schema.
    "openapi": {
      "inputs": ["$TURBO_DEFAULT$", "src/**/*.py", "pyproject.toml", "uv.lock"],
      "outputs": ["openapi.json"]
    }
  }
}
```

And in `packages/api/turbo.json` (or the root, scoped) the step that consumes it:

```jsonc
{
  "extends": ["//"],
  "tasks": {
    "build": {
      "dependsOn": ["^openapi"],
      "outputs": ["src/**/schema.d.ts", "dist/**"]
    }
  }
}
```

`^openapi` means *"the `openapi` task of this package's dependencies"*. Adding
`"@<slug>/<name>": "workspace:*"` to `packages/api`'s `devDependencies` is what creates that
edge — the dependency is not for code, it is for **ordering**. Without it turbo has no reason
to run the export before the generation, and you get a client built from yesterday's schema.

## The `inputs` trap, which is the reason this file exists

From the configuration reference, verbatim:

> Using the `inputs` key opts you out of `turbo`'s default behavior of considering
> `.gitignore`. You must reconstruct the globs from `.gitignore` as desired or use
> `$TURBO_DEFAULT$` to build off of the default behavior.

A Python package is exactly where this bites. The moment you write `inputs` without
`$TURBO_DEFAULT$`, turbo starts hashing everything in the directory — including
`__pycache__/`, `.venv/`, `.pytest_cache/` and `.ruff_cache/`, all of which change on **every
run**. The task then never hits the cache again, and the symptom is "turbo is slow", which
nobody traces back to a glob.

So: **`$TURBO_DEFAULT$` first, then narrow.** The default is already "files checked into source
control", which is right for Python; the extra globs are there to be explicit about what
matters, not to replace it.

Three files are always inputs no matter what you write, per the same reference: `package.json`,
`turbo.json`, and the package manager lockfile.

## `dev` must stay persistent

`"persistent": true` tells turbo the task never exits, and turbo then **refuses** to let another
task depend on it — which is the point: a task depending on a dev server would wait forever.
`"cache": false` because there is no output to cache.

`turbo dev` then starts Next and the service together:

```
$ pnpm turbo dev
• Packages in scope: @acme/api, @acme/ml, @acme/web
• Running dev in 3 packages

@acme/web:dev:  ▲ Next.js 16.3.4
@acme/web:dev:  - Local:  http://localhost:3000
@acme/ml:dev:   INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
@acme/ml:dev:   INFO:     Application startup complete.
```

## `test` and `lint` pick it up for free

They are the same task names, so `pnpm turbo test` runs Vitest in `apps/web` and pytest in
`apps/<name>`, in parallel, with per-package caching:

```
@acme/web:test: ✓ 12 passed
@acme/ml:test:  2 passed in 0.41s
@acme/ml:lint:  All checks passed!
```

Nothing about this is Python-specific. That is the design: **the bridge is the whole
integration**, so a reader of `turbo.json` does not need to know what language is behind a task.

## Outputs may leave the package, and should not here

The reference says outputs must resolve *inside the repository root* — not inside the package —
and `$TURBO_ROOT$` exists for repo-root-relative paths. So `apps/<name>` could write the client
straight into `packages/api/` and cache it.

Do not. Two packages writing the same files means neither owns them, and the first `turbo prune`
or partial-graph run that restores one without the other leaves a half-generated client. Keep
the schema in `apps/<name>/openapi.json` and let `packages/api` generate from it: one writer per
directory, and the `^openapi` edge does the ordering.

## `[VERIFY]` — native uv workspaces, when the flag graduates

Turborepo can discover uv workspace members natively: set
`futureFlags.experimentalPythonWorkspaces` in the root `turbo.json`, give the repository root a
`pyproject.toml` with a uv workspace, a `uv.lock` and a `[tool.turbo].name`. Turbo then registers
`build` / `format` / `check` / `lint` / `test` from the tools it detects (Ruff, Black, mypy,
pytest) and hashes `uv.lock`, `.python-version` and the tool configs automatically.

It is behind a flag and documented as *"experimental and can change at any time"*, and it
requires changing the repository root for every dev-flow monorepo, not just those with a Python
app. Re-check this on each pass: if it graduates, the migration is to delete the bridge
`package.json`, move the app into the root uv workspace, and drop the explicit `inputs` — the
native path hashes the right things without them. The RFC is
<https://github.com/vercel/turborepo/discussions/13625>.
