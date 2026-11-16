# The moves, bucket by bucket

Read the section of the bucket `ci_audit.py` named. Each move is a candidate: measure it side by
side (SKILL.md Step 3) before it stays. Third-party tools and plans move fast: re-check a tool's
current docs before relying on a flag named here.

## Waiting — under 10 seconds

- **A runner that is there when the job is.** A 5-second job that queues 10 minutes is a 10-minute
  job. Hosted alternatives to GitHub's runners (Blacksmith is the default to try) usually start in
  seconds; check the regions and the data terms first (SKILL.md, Data residency).
- **Cancel the superseded run.** A new commit on a branch cancels its run in progress:

  ```yaml
  concurrency:
    group: ci-${{ github.ref }}
    cancel-in-progress: ${{ github.ref != 'refs/heads/main' }}
  ```

  `main` keeps every run: its runs are the record.

## Setup — under 30 seconds

- **Cache hits above 95% on pull requests**: seed the caches from `main` (a run on every push to
  `main` saves them; pull requests restore with `main`'s key as the fallback). Count the hit rate
  from the runs, not from a single try.
- **Cache `node_modules` itself**, keyed on the lockfile and the toolchain's version, not only the
  package manager's store: restoring a folder beats relinking thousands of packages.
- **A blobless clone**: `actions/checkout` with `filter: blob:none` keeps the history and fetches
  file contents on demand; a shallow clone breaks `--affected` and any tool that reads history.
- **The package manager**: bun installs fastest on many repositories. On a pnpm workspace with
  turbo, switching is a migration (lockfile, workspace protocol, scripts): one PR of its own, after
  a side-by-side install and a full green suite.

## Running

### Lint — under 5 seconds

oxlint for every rule it covers, with every rule turned on that the code passes or that is worth
fixing. A project's own rules (custom plugins, a design-system lint with its cap) stay in ESLint
until oxlint runs them; then ESLint runs only those, and the side-by-side list says which.

### Typecheck — under 5 seconds

`bun check` (Bun 1.4.3 and later) reports the errors TypeScript 7 reports, on all cores. When it
cannot check this repository, TypeScript 7's native compiler is the fallback. Keep the project's
own `tsconfig` as the one source of what is checked.

### Format

oxfmt in place of Prettier, once the side-by-side run shows the same output on the repository (or
the difference is accepted in one formatting PR of its own).

### Tests — under 60 seconds per shard

- **Stop reloading the app per test file**: Vitest `isolate: false`, with state reset after every
  file. Write the reset rules into `AGENTS.md` (what a test must clean: mocks, timers, globals,
  the database rows it made), so the next test written follows them.
- **Random order** (Vitest `sequence.shuffle`) flushes out tests that pass only after another one.
  A test that fails in some orders has a leak: fix the leak.
- **Shard by measured duration**, onto 8-core machines, each shard with its own database. Buy
  cores before shards, and match the test concurrency to the cores. Splitting by file count leaves
  one shard with every slow file: split on the durations the last runs recorded.

## Shape

- Lint, typecheck, build and tests run as parallel jobs, each in its budget.
- Migration checks and the other apps' tests leave the slowest job for jobs of their own.
- **Locally, under 9 seconds**: a pre-push hook runs format, lint and typecheck on the changed
  files. A hook, because a line in `AGENTS.md` is a step an agent can skip.
- **Every job has its budget as `timeout-minutes`**, so a stage that slows down goes red instead of
  quietly costing a minute more.
