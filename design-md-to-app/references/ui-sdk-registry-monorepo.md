# UI SDK from a design-system registry, in a monorepo (`stack.ui_registry`)

For a project with `stack.ui = "ui-sdk"` (or `stack.monorepo.web.ui = "ui-sdk"`) **and** `stack.ui_registry`
set: the components are not written by hand, they come from the project's design-system registry and live
in `packages/ui`, the shadcn monorepo shape. `ui-sdk-mapping.md` stays the reference for UI SDK itself; this
file is the install. Agentic Factory's `ui-agent` is the case it was measured on.

**Measured, not assumed.** On 2026-11-26 ui-agent's registry (981 items, `@ui-sdk/*@0.1.0-beta.17`) was
installed into a shadcn monorepo converted to pnpm and `moduleResolution: Bundler`: base, 14 primitives,
`login-01` and `chat-01`. It built and rendered — after **seven** fixes that nobody had predicted. Each one is
a rule below, and `scripts/check_ui_registry.py` checks it: an earlier plan (G1) had guessed five rules and
got two of them wrong against the real registry.

## Steps

### 1. Read the registry before installing anything

```bash
python3 <skill>/scripts/check_ui_registry.py items <registry-url>/r/ base button <the items> --version <ui_sdk_version>
```

It follows every `registryDependencies` and reports, per item:

| Code | Level | What it means | Whose fix |
|---|---|---|---|
| U1 | stop | `@ui-sdk/core` / `@ui-sdk/react` not at `ui_sdk_version` exactly | regenerate the registry |
| U2 | stop | a second behaviour library (`@shadcn/react`, `radix-ui`, `@radix-ui/*`, `@base-ui/react`) — golden rule 3. Measured: `message-scroller` and `questionnaire` depend on `@shadcn/react` | the registry, or an exception the user records in `stack_config.primitive_exceptions` |
| U3 | warn | a `.css` file outside a `registry:theme` item — tokens belong in `globals.css`; themes may ship CSS | the registry |
| U4 | warn | a dependency with no version, or a range | the registry |
| U5 | stop | a file typed `registry:file` that imports `@/components/ui/…` or `@/lib/…`: shadcn copies `registry:file` **as is**, without rewriting imports, so in a monorepo the import points nowhere. Measured on every block. `registry:ui` and `registry:lib` files are rewritten correctly | type block files `registry:component` |
| U6 | stop | `registryDependencies` on `localhost`: the registry was built for a local origin | rebuild with the public origin |
| U7 | warn | a `.tsx` with handlers or hooks and no `'use client'`: it breaks a server page's prerender. Measured: `login-01/login-form.tsx` | the registry |

**Done when** it exits 0, or every stop has been fixed in the registry or recorded by the user as an
exception. The fixes on the registry's side are its owner's: name them, don't patch the copy you install.

### 2. Shape the monorepo

Start from the shadcn monorepo (`shadcn init -t next --monorepo`), then make it the project's:

- **pnpm**, not the npm the template writes: `pnpm-workspace.yaml`, `"workspace:*"` for internal packages.
- **`moduleResolution: "Bundler"`** in the TypeScript config, not the template's `NodeNext`, under which
  re-exports without an extension (Phosphor's, for one) do not resolve: 225 errors measured.
- **`apps/web/components.json` → `"aliases": { "lib": "@<ui-package>/lib" }`**. With the template's `@/lib`,
  `registry:lib` items (`cn`, `render`, the fonts) land in `apps/web/lib` while the components in
  `packages/ui` import them from `@<ui-package>/lib`: broken imports.
- `registries: { "<namespace>": "<url>" }` in both `components.json`, from `stack.ui_registry`.
- **`registry_intake.py setup <root>`**: it records `stack.ui_registry.namespace` as `trust: "live"`.

**Done when** `pnpm install` passes and `apps/web/components.json` names the UI package's `lib`.

### 3. Install

From `apps/web` (the shadcn monorepo rule: it routes `registry:ui` to `packages/ui`):

```bash
pnpm dlx shadcn@<pinned> add <namespace>/base <namespace>/<item> …
```

Then:

- **The layer order goes first in `packages/ui`'s `globals.css`**, before `@import "tailwindcss"`:
  `@layer ui-sdk, theme, base, components, utilities;` — the registry's own app declares it, but its `base`
  item does not carry it, so the merged file has `@layer ui-sdk { … }` *after* Tailwind's layers and a
  utility can no longer override a component. Nothing looks wrong until one should.
- **Import the fonts once**, in the root layout: `import "@<ui-package>/lib/<fonts file>"`.
- **Dependencies of files that land in the app** (`registry:file` with a target such as
  `@components/agent/…`) are installed into `packages/ui` only. With pnpm the app cannot see them: add them to
  `apps/web/package.json` too (measured: `@ui-sdk/react` for `components/agent/bridge.ts`).
- **`pnpm.overrides`** for `@ui-sdk/core` at `ui_sdk_version`: one copy.

**Done when** `check_ui_registry.py project <root>` exits 0:

| Code | What |
|---|---|
| P1 | `apps/web`'s `lib` alias is the UI package's |
| P2 | the layer order line comes before `@import "tailwindcss"` |
| P3 | one `@ui-sdk/core` in `pnpm-lock.yaml` |
| P4 | every package an app file imports is a dependency of the app (or of the workspace root) |
| P5 | no `@/components/ui/…` or `@/lib/…` import left in the app (U5, installed anyway) |

### 4. Prove it

`tsc --noEmit` in `packages/ui` and `apps/web`, `next build`, and the page **looked at** in a browser, not
only built: the registry's entry animations start at opacity 0, so an early screenshot shows empty cards.

**Done when** the build passes and the blocks render with the design system's type, spacing and colour.

## Two settings the registry and the project disagree on

- **`noUncheckedIndexedAccess`**: a project with it on (Agentic Factory's) rejects registry code written
  without it (measured: six unchecked index reads in `kanban-primitive.ts`). Fix it in the registry; turning
  the option off in `packages/ui` is a recorded exception, never a silent one.
- **Updates**: the registry is the source of the components and of `ui_sdk_version`. Reinstalling from it is a
  pull request of its own, `registry-intake` trusts it live, and step 1 runs again first.
