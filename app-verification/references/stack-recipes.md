# Driving and proving, per stack

A harness the repo already has comes first: an existing Playwright config, Maestro flows, an expect script. The
recipes below are for when there is none.

## Web (Next.js)

- **Launch** with the repo's dev or start script on a port that is not the user's (`pnpm dev --port 3100`; the arguments reach `next dev`), and register it in
  `.claude/launch.json`:

  ```json
  { "version": "0.0.1", "configurations": [
    { "name": "verify-web", "runtimeExecutable": "pnpm", "runtimeArgs": ["dev", "--port", "3100"], "port": 3100 } ] }
  ```

  Claude Code's preview tools start it by that name, and the manual's Launch section names it too. They read the
  launch.json of the session's root, so from a session opened elsewhere the entry goes there, as
  `"runtimeExecutable": "sh", "runtimeArgs": ["-c", "cd <project> && <env> pnpm exec next dev -p 3100"]`. Env vars
  go on the command line (`/usr/bin/env A=1 pnpm …` or inside the `sh -c`): the launch.json shape has no env field.
- **Ready is usable, not answering**: on fit-coach the process answered in 4 s and the first `/sign-up` took 56 s
  to compile; wait for the first interactive element to be enabled (hydration), never a fixed time.
- **Drive** with the built-in browser: read the accessibility tree, act on elements by role and accessible name,
  fill forms by label. Playwright, if the repo has it, with `getByRole` / `getByLabel`.
- **Prove** with the accessibility snapshot after the action, a screenshot, the network response of the mutation,
  and a read-only second view of the stored value (a reload, or a query on the verification database).
- **Watch for**: auth cookies scoped to `localhost` vs `127.0.0.1`; `next dev` compiling a route on first visit
  (wait for the element, never a fixed sleep); a proxy redirect to the locale prefix (`/it/...`).

## Expo / React Native

- **Launch** a dev build on the iOS simulator (Claude Code's simulator tool can attach, launch, tap and screenshot);
  Metro on a port that is not the user's (`--port 8082`).
- **Drive** by `accessibilityLabel` / `testID`, never by coordinates. Maestro, if the repo has flows, by `id` and
  text.
- **Prove** with a screenshot and the UI tree after the action, the device log line, and the backend row for a
  mutation.
- **Watch for**: a stale JS bundle after a code change (reload before proving); permission prompts (camera,
  notifications) that block the first run; `EXPO_PUBLIC_` values baked at build time.

## eve agent

- **Launch** with `eve dev` (or the project's script) on its own port.
- **Drive** through the channel the agent exposes — the HTTP chat endpoint, the MCP channel — with a fixed prompt per
  feature. The identity comes from the channel, as `eve-agent` requires: use the seeded test identity.
- **Prove** with the response, the trace (which tools ran, with which arguments) and each tool's side effect read back
  where it landed.
- **Watch for**: a model call that costs money on every run — keep prompts per feature to one turn; an approval gate
  that waits for a human (approve it as the test user, or record it as an unreachable precondition).

## Monorepo

One manual per app — `verify-web`, `verify-mobile`, `verify-agent` — each scaffolded with `--app <name>` from the
project root, each with its own Launch and port. A journey that crosses apps (the mobile app calls the web API) lives
in the manual of the app the user touches, and its preconditions name the other app's launch.
