# Capability package — a product capability as its own eve extension

Use this when `meta.json#stack_config.agent_capabilities == "packages"`: the product sells or switches
**capabilities** (a code reviewer, an implementer, a triage desk) per workspace, so each one is a
versioned package with a contract, not a handful of files dropped into `agent/`. One deployed agent
serves every workspace; what a workspace sees depends on which capabilities it has on.

Measured on eve 1.4.0 (2026-11-24) with one agent, two workspaces and 32 capability packages: a
capability that is off never reaches the model — neither its tools' names nor its descriptions — and
switching it on takes effect at the next model call, without a redeploy.

## The shape

```
capabilities/<id>/                 # kebab-case id, e.g. code-review
├─ package.json                    # @<slug>/capability-<id>, eve.extension { source, dist }
├─ capability.json                 # the contract — validated by the project's schema
├─ extension/
│  ├─ extension.ts                 # defineExtension()
│  ├─ instructions.ts              # the agent-facing description, behind defineDynamic
│  ├─ tools/<tool>.ts              # snake_case names, each behind defineDynamic
│  └─ skills/…
├─ evals/                          # listed in capability.json#evals
└─ THIRD_PARTY_NOTICES             # only when capability.json#thirdPartyCode is true
apps/<agent app>/agent/extensions/<id_snake>.ts   # the mount: export { default } from "@<slug>/capability-<id>";
```

## Preconditions — check before creating anything

- The project has a **contract package** (in a dev-flow monorepo, `packages/contracts`) exporting:
  - the `capability.json` schema **and a command that validates a file against it**;
  - the activation helper, `isActive(ctx, "<id>")`, which reads the caller's workspace from
    `ctx.session.auth` and answers from a cache, not one query per call. With 32 capabilities a single
    model call runs more than 200 activation checks (measured), so a query each is not an option.
- A **service package** (`packages/services`) is the only door to domain logic. A capability never
  imports the database package.
- The id is kebab-case; the mount name is the id with `-` → `_`, matching `^[a-z][a-z0-9_]*$`. The
  mount becomes the tool prefix (`code_review.ts` → `code_review__review_pull_request`), so a dash
  there yields tool names that other parts of the system reject. Keep the longest
  `<mount>__<tool>` within 64 characters (`eve-conventions.md`, tool names).

If either package is missing, stop and say which: creating it is `monorepo-add-shared-package`'s job,
not this one.

## Procedure

1. **Scaffold with the official command, from inside the workspace:**
   `cd capabilities && pnpm dlx eve@<stack_config.eve_version> extension init <id>`.
   It brings `@types/node`, the build, the exports and an `AGENTS.md`; a hand-written package without
   `@types/node` failed every build in the measurement. Inside an existing Git repository it does
   **not** create a nested repository. It **may edit the workspace root** (`package.json` or the
   workspace configuration) and prints `Updated workspace root …` when it does — read that diff before
   you continue.
2. **`package.json`:** name `@<slug>/capability-<id>`; dependencies **only** `@<slug>/contracts` and
   `@<slug>/services` (`workspace:*`), `zod`, and `eve` as a peer/dev dependency at the pinned version.
   Add `"private": true` unless the package is meant for a registry.
3. **`capability.json`:** from the project's draft when one exists, otherwise from the schema's own
   example. Leave `provides` and `config` as `"generated": true`: the build fills them, so they can
   never disagree with the code.
4. **Gate everything that reaches the model:**

   ```ts title="extension/tools/review_pull_request.ts"
   import { isActive } from "@<slug>/contracts";
   import { defineDynamic, defineTool } from "eve/tools";
   import { z } from "zod";

   export default defineDynamic(async (ctx) =>
     (await isActive(ctx, "<id>"))
       ? defineTool({ description: "…", inputSchema: z.object({ … }), execute: async (input, ctx) => { … } })
       : null,
   );
   ```

   Same for `instructions.ts` (the agent-facing description is injected only where the capability is
   on) and for each skill. **Hiding is not authorizing:** `execute` calls a service, and the service
   checks the caller again — person, capability permissions, workspace rules — because a tool can be
   reached in ways the activation check does not cover.
5. **Mount it:** `apps/<agent app>/agent/extensions/<id_snake>.ts` →
   `export { default } from "@<slug>/capability-<id>";` (or the call form with config, when the
   extension declares a config schema; `eve-capabilities.md` §Extension).
6. **Build order:** in `turbo.json`, `build` has `dependsOn: ["^build"]`, so `contracts` compiles before
   any capability. Without it the first install ran the capability's `prepare` (`eve extension build`)
   before `contracts` was linked and produced a package **with no tools**, silently.
7. **Evals** in `capabilities/<id>/evals/`, each listed in `capability.json#evals`.
8. **Third-party code:** `thirdPartyCode` is `true` only if files were actually copied from another
   project; then `THIRD_PARTY_NOTICES` names each file, its origin and licence.

## Done when

`python3 scripts/check_capability.py <root> <id>` passes, and then:

- `pnpm turbo build --filter=@<slug>/capability-<id>...` and the agent's `eve build` exit 0;
- a test with a mock model that records the request (the agent's baseline eval method) shows that,
  for a workspace with the capability **off**, the request contains none of its tool names or
  descriptions, and after switching it **on** the next call contains them;
- `meta.json#history` gets `{ "skill": "eve-agent", "action": "add-capability-package", "inputs": { "id": "<id>" } }`.
