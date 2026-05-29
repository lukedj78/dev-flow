---
name: write-tests
description: 'Write Vitest unit/integration tests OR Playwright e2e tests for an existing source file (server action, page, component, query). Reads the project''s wired test framework from `.workflow/meta.json#stack.test`, follows the mocking patterns already present in `vitest.setup.ts` and any sibling test files. Use when the user says "scrivi i test per X", "test per la server action Y", "e2e per /clienti", "unit test per il componente Z", "add tests for <file>", or after `screenshot-to-page` / `module-add` runs and the user wants coverage. Not for: scaffolding the test infrastructure (`module-add test`), running QA on a deployed site (`qa`), or methodology guidance (`superpowers:test-driven-development`).'
---

# write-tests — generate tests for one file at a time

This skill writes the test file that should sit next to a piece of source code. One invocation = one source file → one test file. It does **not** install test infrastructure (that's `module-add test`), does **not** debug failing tests (that's `superpowers:systematic-debugging`), and does **not** run an HTTP-based QA pass (that's `qa`).

The unit of work is **deliberately small** because tests rot when they're auto-generated in bulk. A single file at a time forces the user to read what was written and accept it before moving to the next.

## When this skill applies

- The user names a source file: "scrivi i test per `lib/server/clienti.ts`", "test per `app/checkout/page.tsx`", "e2e per /scadenze".
- The orchestrator routes here from `module_added` (test infrastructure exists) when the user wants per-feature coverage.
- The project has a wired test stack — `meta.json#stack.test` is set, OR `vitest.config.ts` + `playwright.config.ts` exist at the root.

## Contract

This skill follows the dev-flow contract — see `references/contracts.md`. Key facts:
- Reads `<root>/.workflow/meta.json#stack.test` to confirm the test framework is wired.
- Reads the project's existing `vitest.setup.ts`, `vitest.config.ts`, `playwright.config.ts`, and any sibling test files to learn the mocking style — **does not re-prescribe** patterns from scratch.
- Writes a single test file alongside the source (`__tests__/<name>.test.ts` for unit, `e2e/<name>.spec.ts` for e2e).
- Does NOT bump `phase` — tests are continuous work, not a phase transition.
- Appends to `meta.json#history` with the source file path, the test path, and the test type.
- **Idempotent**: if the test file already exists, ask the user — either regenerate, append missing cases, or abort. Never silently overwrite.

## Workflow

### Step 1 — Verify prerequisites

Read `<project-root>/.workflow/meta.json`:

- `stack.test` must be set (e.g., `"vitest+playwright"`). If `null`, stop and tell the user: *"Test infrastructure not wired. Run `module-add test` first, then come back."*
- `phase` should be `module_added` or later. If earlier, the project might not have anything testable yet — warn and ask whether to proceed.

If `stack.test` is unset but `vitest.config.ts` exists at the project root, the user installed Vitest manually outside the contract. Proceed, but log this in the user-facing summary so they can re-run `module-add test` to formalize.

### Step 2 — Identify the source file + classify it

The user names a file. Classify it by path + content:

| Pattern | Classification | Reference |
|---|---|---|
| `lib/server/<domain>.ts` (contains `"use server"` or exported async functions returning `ActionResult`) | **Server action** | `references/test-server-action.md` |
| `lib/queries/<domain>.ts` (async functions reading from `@/lib/db`) | **Query** | `references/test-query.md` |
| `app/<route>/page.tsx` or `app/<route>/[...slug]/page.tsx` | **Page (e2e)** | `references/test-page-e2e.md` |
| `components/**/*.tsx` containing `"use client"` and interactive logic | **Component (RTL)** | `references/test-component.md` |
| `components/ui/*.tsx` (shadcn primitives) | **Skip** — primitives are tested upstream | — |
| Anything else | **Ask the user** what kind of test they want | — |

If the file matches multiple patterns (e.g., a server action that internally uses a query), test as **server action** — the action is the public surface, the query is implementation detail.

### Step 3 — Read the project's existing test patterns

Before writing anything, read **at least one existing test file of the same type** in the project. The mocking style, the import order (mocks before imports), the naming convention, and the assertion library are already pinned by what's there. Copy the style. Don't introduce a new pattern.

If no test of that type exists yet:
- For server actions: read `references/test-server-action.md` for the canonical pattern.
- For pages e2e: read `references/test-page-e2e.md`.
- For components: read `references/test-component.md`.
- For queries: read `references/test-query.md`.

Also read `vitest.setup.ts` to see what's globally mocked (typically `next/navigation`, `next/cache`). Don't re-mock those in individual tests.

### Step 4 — Read the source file

Read the source file end-to-end. Identify:

- **For server actions**: the action's input schema (Zod), the success path, every business-error branch (what does it return `{ ok: false }` for?), every system-error branch (what does it `throw`?), and the auth dependencies (`getCurrentTenantId`, `getCurrentUserId`).
- **For queries**: the input arguments, the SQL/Drizzle calls, the shape of the return, the not-found / empty-result handling.
- **For pages**: the rendered structure (which sections, which interactive elements, which links), the data dependencies (what `getX()` queries fire), the URL params if dynamic.
- **For components**: the prop surface, the interactive states (`useState`, event handlers), the conditional rendering branches.

Make a list of test cases **before writing the test**. The list is the spec — the test file is just the encoding.

### Step 5 — Check for existing test file

Look for:
- Server actions: `lib/server/__tests__/<name>.test.ts`
- Queries: `lib/queries/__tests__/<name>.test.ts`
- Components: `components/<group>/__tests__/<name>.test.tsx` (or co-located: `components/<group>/<name>.test.tsx`)
- Pages: `e2e/<route-slug>.spec.ts`

If exists:
- **Ask** the user: regenerate from scratch, add only the missing cases, or abort?
- **Default**: add only the missing cases. Open the existing file, run the spec list against the existing `it("...")` blocks, and append the gaps.
- **Never silently overwrite**.

### Step 6 — Write the test

Apply the relevant reference template (from `references/`), filling in the project-specific values:

- Real source paths (resolved from `meta.json` or by reading the project tree).
- Real mock shapes (read from existing tests if any).
- Real assertion patterns (match what's already there for consistency).

The reference templates show the **canonical shape** for each test type. Adapt — don't paste verbatim.

### Step 7 — Run the new test in isolation

After writing:

```bash
pnpm vitest run <test-file>          # for unit tests
pnpm playwright test <test-file>     # for e2e
```

If it fails, read the error:
- **Mock missing**: a dependency wasn't mocked. Add the mock at the top of the file, re-run.
- **Schema drift**: the source file's signature doesn't match what the test assumed. Re-read source, re-write the relevant `it()` block.
- **Test passes but coverage is wrong**: this skill doesn't gate on coverage — leave a comment if a branch wasn't hit and tell the user.

If the failure is in the **source code** (e.g., the action throws unexpectedly), stop. Tests revealing real bugs is the point — surface the bug to the user, don't paper over it.

### Step 8 — Update state and report

Update `.workflow/meta.json`:

- **Don't bump phase**. Tests are continuous.
- Append history:
  ```json
  {
    "skill": "write-tests",
    "ran_at": "<now>",
    "inputs": {"source": "lib/server/clienti.ts", "type": "server-action"},
    "outputs": ["lib/server/__tests__/clienti.test.ts"],
    "phase_before": "<unchanged>",
    "phase_after": "<unchanged>"
  }
  ```

Tell the user:
- The test file path.
- The list of cases covered (one bullet per `it("...")`).
- The list of cases **deliberately not covered** (e.g., "auth-mocking pattern requires `module-add auth` to have run; one test marked `it.todo`") so they know the gap.
- The command to run it: `pnpm vitest run <path>` or `pnpm playwright test <path>`.

## Important constraints

- **One source file per invocation.** "Scrivi i test per tutto" is N runs — keep history clean and let the user accept each.
- **Read existing tests first.** If `lib/server/__tests__/practices.test.ts` already exists with a specific mocking style, the new `clienti.test.ts` matches that style. Consistency over canonical-template-from-this-skill.
- **Don't introduce new test deps.** If the project has Vitest + Playwright, work with those. Don't suggest `jest`, `mocha`, `cypress`, `vitest-mock-extended`, etc.
- **Don't fix the source code.** If a test reveals a bug, surface it. Don't silently rewrite the source to make the test pass.
- **Real assertions, not snapshots by default.** Snapshot tests rot. Prefer specific assertions (`expect(result.ok).toBe(false)`, `expect(page.locator("h1")).toContainText("...")`). Snapshots only when the user explicitly asks.
- **Skip what's not testable cheaply.** Pages with WebGL canvases, third-party iframes, or external API calls without a mock surface — write a `test.skip` with a comment explaining why instead of writing a brittle test. Honesty over coverage theater.

## Cross-skill dependencies

- **Requires** `module-add test` to have run (the test infrastructure has to exist).
- **Plays nice with** `module-add db`, `module-add auth` — the smoke tests in `module-add test` mock these; this skill follows the same pattern.
- **Pre-`module-add ci`**: tests written by this skill run in CI once `module-add ci` runs (the GHA workflow added there picks up `pnpm test:run` and `pnpm test:e2e`).

## What this skill does NOT do

- **Does not install test packages.** That's `module-add test`. If `vitest` isn't in `package.json`, this skill stops and routes there.
- **Does not run a full test suite.** It runs only the new test in isolation to verify it passes. Full suite runs are CI's job.
- **Does not fix failing tests.** A failing test is a signal, not a problem. Surface it to the user; the user decides whether to fix the test or fix the source.
- **Does not generate coverage reports.** Coverage is a separate concern; the user can wire `vitest --coverage` themselves once they have enough tests.
- **Does not write tests for shadcn primitives or third-party libs.** Test the project's own logic, not the dependencies.
