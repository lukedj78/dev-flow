# module-add → `ci` (husky + lint-staged + GitHub Actions)

Wire a **continuous-integration scaffold**: pre-commit hooks (husky + lint-staged) and a GitHub Actions workflow that runs typecheck + lint + unit tests + build on every PR.

The aim is to fail fast locally (so CI doesn't waste minutes catching what husky could have caught in seconds) and to give the user a clean green check on every PR.

Checked 2026-08-12: `actions/checkout`, `actions/setup-node`, `actions/upload-artifact` bumped to their current major (`v7`; were pinned at `v4`, three majors behind) — pure orchestration actions with no compatibility trade-off, safe to track current. `node-version` bumped `20` → `24`: Node 20 is past end-of-life (only 22-maintenance and 24-active are current supported lines), and `24` matches the `engines.node >= 24` floor `monorepo-bootstrap` sets elsewhere in this repo. **`pnpm/action-setup@v4` + `version: 9` deliberately left alone** — pnpm's own docs say `action-setup` supports installing pnpm v10 and older only; v11+ requires switching to the newer `pnpm/setup` action. Bumping just this file's pin to a newer pnpm major would silently diverge from `monorepo-bootstrap/references/structure.md`'s root `packageManager: "pnpm@9.0.0"`, which is what actually governs lockfile format for a scaffolded project — a coordinated version bump across both, not a doc typo fix.

## Idempotency check

Before doing anything:

1. `<project-root>/package.json` contains `"husky"` in devDependencies.
2. `<project-root>/.husky/pre-commit` exists.
3. `<project-root>/.github/workflows/ci.yml` exists.

If all three: tell the user it's installed, offer to update the workflow (e.g., add e2e step, change Node version). Don't double-install.

## Prerequisites

- The project must be a git repo (`git init` already done — every scaffold should have this).
- Recommended after `module-add test` so the workflow has tests to run. If `stack.test` is null, the workflow skips the test step but still runs typecheck + lint + build.

## Install

```bash
cd <project-root>
pnpm add -D husky lint-staged
pnpm exec husky init
```

`husky init` creates `.husky/pre-commit` with a default `pnpm test` line — we'll overwrite it.

## Files to write

### `.husky/pre-commit`

```bash
pnpm lint-staged
```

Keep it minimal. The pre-commit hook is for **fast** checks only — formatting + lint on staged files. Heavier checks (typecheck, full test suite) run in CI, not locally on every commit.

### `package.json` additions

Append:

```json
{
  "lint-staged": {
    "*.{ts,tsx,js,jsx}": [
      "eslint --fix",
      "prettier --write"
    ],
    "*.{json,md,css}": [
      "prettier --write"
    ]
  }
}
```

If the project doesn't use Prettier yet, drop the `prettier --write` lines or run `pnpm add -D prettier` first. ESLint is assumed (Next ships it by default).

### `.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  ci:
    runs-on: ubuntu-latest
    timeout-minutes: 10

    steps:
      - uses: actions/checkout@v7

      - uses: pnpm/action-setup@v4
        with:
          version: 9

      - uses: actions/setup-node@v7
        with:
          node-version: 24
          cache: pnpm

      - name: Install dependencies
        run: pnpm install --frozen-lockfile

      - name: Typecheck
        run: pnpm typecheck

      - name: Lint
        run: pnpm lint

      - name: Unit tests
        run: pnpm test:run
        # Only runs if module-add test has wired Vitest. Safe to leave —
        # if the script is missing, the step fails fast with a clear error.

      - name: Build
        run: pnpm build
        env:
          # Placeholders so `next build` doesn't fail at module-eval time.
          # The actual values are set per-environment in Vercel/your host.
          DATABASE_URL: postgresql://placeholder:placeholder@placeholder.neon.tech/db
          BETTER_AUTH_SECRET: placeholder-secret-32-chars-minimum-aaaaaaaaaaaa
          BETTER_AUTH_URL: http://localhost:3000
          NEXT_PUBLIC_APP_URL: http://localhost:3000
```

The placeholder env vars match the `.env.local.example` shape from `module-auth` and `module-db`. They let the build resolve without leaking secrets — actual production values come from Vercel/host env config.

### Optional: `.github/workflows/e2e.yml`

If `stack.test = "vitest+playwright"`, also write the e2e workflow:

```yaml
name: E2E

on:
  pull_request:

jobs:
  e2e:
    runs-on: ubuntu-latest
    timeout-minutes: 20

    steps:
      - uses: actions/checkout@v7
      - uses: pnpm/action-setup@v4
        with:
          version: 9
      - uses: actions/setup-node@v7
        with:
          node-version: 24
          cache: pnpm

      - run: pnpm install --frozen-lockfile
      - run: pnpm exec playwright install --with-deps chromium

      - name: Build
        run: pnpm build
        env:
          DATABASE_URL: postgresql://placeholder:placeholder@placeholder.neon.tech/db
          BETTER_AUTH_SECRET: placeholder-secret-32-chars-minimum-aaaaaaaaaaaa
          BETTER_AUTH_URL: http://localhost:3000
          NEXT_PUBLIC_APP_URL: http://localhost:3000

      - name: Run Playwright tests
        run: pnpm test:e2e
        env:
          DATABASE_URL: postgresql://placeholder:placeholder@placeholder.neon.tech/db
          BETTER_AUTH_SECRET: placeholder-secret-32-chars-minimum-aaaaaaaaaaaa
          BETTER_AUTH_URL: http://localhost:3000
          NEXT_PUBLIC_APP_URL: http://localhost:3000

      - uses: actions/upload-artifact@v7
        if: always()
        with:
          name: playwright-report
          path: playwright-report/
          retention-days: 7
```

Note: the e2e workflow uses `pnpm build && pnpm start` implicitly via Playwright's `webServer` config — but the config currently runs `pnpm dev`. For CI speed, edit `playwright.config.ts` so `webServer.command` becomes `pnpm start` and add a separate build step (already done above). Leave a comment in the playwright config so the user can flip it if they prefer dev mode locally.

### `package.json` script additions

Make sure these exist (some may already be there from prior modules):

```json
{
  "typecheck": "tsc --noEmit",
  "lint": "next lint",
  "format": "prettier --write ."
}
```

If `tsc` isn't installed yet (e.g., a JS-only scaffold — rare), skip the typecheck script and remove the matching CI step.

## Update meta.json

```json
{
  "stack": {
    "ci": "husky+gh-actions"
  }
}
```

## Known caveats

- **Husky requires `prepare` script in package.json**: `"prepare": "husky"`. `husky init` adds this automatically — don't remove it, or hooks won't install on `pnpm install`.
- **CI `pnpm install --frozen-lockfile` fails if lockfile is out of sync**. If a teammate updated `package.json` without committing the new lockfile, CI breaks. The fix is always to commit the lockfile, never to drop `--frozen-lockfile`.
- **Build env vars in CI are placeholders**, not real secrets. Production secrets live in the host (Vercel/Fly/etc.). Don't be tempted to add real `DATABASE_URL` to GitHub secrets unless you actually want CI to hit prod data — that's almost never the right move.
- **Pre-commit hooks slow down rapid commits**. If a teammate pushes back hard, suggest `git commit --no-verify` for emergencies and consider moving heavy linting to CI only. Don't widen the hook scope by default.
- **The e2e workflow is opt-in**: only write `e2e.yml` if `stack.test = "vitest+playwright"`. For lighter projects, the unit-test step in `ci.yml` is enough.
