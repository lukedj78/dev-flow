---
name: registry-intake
description: 'Govern third-party source from a shadcn-format registry — `shadcn add @ns/item`, a registry-item URL, `eve add @ns/…` — with a per-project allowlist, a static review of the item and its whole dependency closure (targets, npm deps and licences, env vars, theme tokens, eve tools), a hashed snapshot installed instead of the live URL, a Claude Code PreToolUse hook that refuses installs around it, and a `check` in dev-flow''s phase gate; `@coss` stays live only when stack.ui is coss. Use when the user wants something from a community registry (pdfcn, emailcn, ogimagecn, mcpcn, agentcn, evex, shadcn-labs…), asks "is this registry safe / can we use this component", updates an installed registry item, or a hook refused a `shadcn add`. Runs automatically at scaffold. Not for: shadcn''s own components (`shadcn add button` is not governed), porting eve code by hand into a multi-tenant app (eve-registry-porting), or building UI (design-md-to-app).'
---

# registry-intake — nothing third-party lands unreviewed, unpinned or around the gate

A shadcn-format registry is a **code mine, not a dependency**: `shadcn add @ns/item` copies someone
else's source into the repo, installs their npm packages, can write env vars and rewrite theme tokens,
and fetches whatever the URL serves **today**. Once copied, the bugs are ours and nothing updates.

The risks are concrete, not hypothetical. Checked on 2026-09-15 against agentcn (466★, MIT): every eve
tool in its registry declares `needsApproval: always()/never()`. eve's field is `approval`;
`needsApproval` is the AI SDK's deprecated one, and eve's loader **throws on unknown keys**
(`expectOnlyKnownKeys` in `internal/authored-definition/schema-backed.js`, eve 0.34, 0.51 and 0.55).
The five tools that were meant to ask first — `post_message`, `update_range`, `write_file`,
`run_shell`, `generate_image` — carry an approval that never loads, and `claw/run_shell` executes on
the host through `node:child_process`, not in eve's sandbox. This skill's review blocks all of it.

## The four barriers

| # | Barrier | Command | Enforced by |
|---|---|---|---|
| 1 | **Allowlist** of registries per project, each with a reason | `allow` / `deny` | `approve` refuses other namespaces; `check` refuses a `components.json` registry not on it |
| 2 | **Review** of the item and its whole `registryDependencies` closure | `review` | exit `1` blocked · `3` needs a human · `0` clean |
| 3 | **Snapshot** in `vendor/registry/`, hashed in `registry-lock.json`, installed instead of the URL | `approve` → `install` | `install` and the hook refuse a snapshot whose hash changed |
| 4 | **Nothing around it** | `check`, `hook` | the PreToolUse hook; `set-phase scaffolded`; `show_state.py` |

## Commands

```bash
S=registry-intake/scripts/registry_intake.py
python3 $S setup   <root>                                   # lock + hook + AGENTS.md section; idempotent
python3 $S review  <root> @pdfcn/takumi/card --registry '@pdfcn=https://pdfcn.dev/r/{name}.json'   # before allowing
python3 $S allow   <root> @pdfcn 'https://pdfcn.dev/r/{name}.json' --reason "PDF export of tender documents" --by <name>
python3 $S approve <root> @pdfcn/takumi/card --by <name> [--accept CODE="why" ...] [--note ...]
python3 $S install <root> @pdfcn/takumi/card [--cwd packages/ui] -- --yes
python3 $S review  <root> @pdfcn/takumi/card                # later: shows the upstream diff against the snapshot
python3 $S check   <root>                                   # gate / CI
python3 $S caps    <root> --reason "..."                    # record a deliberately raised lint cap
```

`<item>` is `@ns/name`, a registry-item URL, or a local `.json`. **Bare names are shadcn's own registry
and are not governed.** `review` is read-only; `--json` gives the report to an agent.

### The workflow an agent follows

**The agent always stops and asks before `allow` and before `approve`**, whatever the tier, even when the
review is clean, the prompt says to hurry, or the user asked for the component by name. Asking for a
component is not agreeing to a registry or to its code. `review` is read-only, so the agent runs it
without asking; `allow`, `approve` and every `--accept` are the user's decisions, taken after they have
seen the report. `--by` is the name of the person who said yes, in this conversation, to *this*
registry or item. It is never the OS login or the agent, and never someone who was not asked. In
an autonomous run (dev-flow §Autonomous runs), the run stops at the review with *"needs a human:
allowlist @ns / approve @ns/item"* and delivers the report.

Measured on 2026-09-22 (`evals/compliance`, gate `registry-intake`): with the text as it stood, the
agent stopped and asked in one session out of three. In the other two it allowlisted and approved
itself, putting the operator's login in `--by`, so the lock recorded a human approval that never
happened. The hook now backs this rule (below).

1. The user wants a component from a registry → `review` it (with `--registry` if the namespace is not
   allowlisted yet). Show the report: files and targets, npm packages with licences, findings.
2. **Stop and ask.** A new registry: *"allowlist @ns → url, reason …?"*, then `allow` with the reason and
   `--by` from their answer. Then the item: *"approve @ns/item as reviewed?"*, then `approve --by <them>`.
   Both questions can go in one message, but they are two decisions and need a yes to each.
3. Exit `1` → do not propose approving it. Each blocking code is one of: fixed upstream, **ported by
   hand** (eve code → `eve-registry-porting`), or accepted by the user with a written reason
   (`--accept CODE="reason"`, recorded in the lock). An `--accept` without a reason is refused.
4. Exit `3` (high tier, or review-level findings) → say so when asking. The findings are what the
   user is deciding on.
5. `install`, then the gates the imported code must pass: typecheck, the **capped** design lint,
   `eve build` when `agent/` changed, tests. Raising `--max-warnings` to make room fails `check` — fix
   the warnings, or record why with `caps --reason`.
6. Updating = `review` again (it prints the diff against the snapshot) → `approve` → `install`.

## What the review checks

Tier **high** = anything server-side (`app/api/`, route handlers, server actions, `agent/`), any eve
code, or any T1 finding. High tier always needs a human, even with no findings.

| Code | Level | Finding |
|---|---|---|
| T1 | block | target is a config/tooling/env file (`next.config`, `package.json`, lockfiles, `.env*`, `.github/`, `.claude/`, `proxy.ts`, `components.json`, `eslint.config`, `vendor/registry/`…) or escapes the project |
| T2 | review | server-side surface → high tier |
| S1 | block | `child_process`, `eval(`, `new Function(` |
| S2 | block | minified/obfuscated lines or a large encoded blob |
| S3 · S4 · S5 | review | reads `process.env` · hard-coded hosts · `dangerouslySetInnerHTML` |
| S6 | review | lines over 1000 characters in a `.tsx` — usually a class list of arbitrary values the design lint counts one by one (React Bits' `SwipeToast`: 1070) |
| E1 · E2 | review · block | declares env vars · ships a value for a secret-looking one |
| C1 | block | `cssVars` / `css` / `tailwind` / `theme` — DESIGN.md owns the tokens |
| D1 · D2 · D4 | block | npm package does not exist · (A)GPL/SSPL/BUSL/no licence · install scripts |
| D3 · D5 · D6 | review | weak copyleft or NC · published < 30 days ago · `npm view` failed |
| D7 | review | the item's dependency range excludes the major the project has installed (React Bits asks `motion@^12`, our projects run 13) |
| R1 | block | the closure reaches a registry that is not allowlisted |
| R2 · R3 | info · block | no registry-item `$schema` · unknown item type |
| V1 | block | eve tool key the **installed** eve's loader rejects (read from `node_modules/eve`; fallback: eve 0.55.0) |
| V2 | block | eve tool with a side effect (name or body) and no working `approval` |
| V3 · V4 · V5 · V6 | review | global credential · one shared store · US-shaped PII regexes · a whole standalone agent |

These are **heuristics over source text, not a sandbox and not a proof**. They exist to stop the
failures already seen and to force the conversation; the post-install gates are still required.

## Trust levels

Every allowlisted registry is `trust: "snapshot"`. The one exception is the registry of the **UI system
the project chose**: with `stack.ui = "coss"`, `setup` records `@coss` as `trust: "live"`, and the hook
lets `shadcn add @coss/…` through — that registry is the project's component library, owned by
`coss-ui`. `allow --trust live` is refused for anything else.

## Where it runs

- **Automatically at scaffold.** `design-md-to-app` (Step 4.10), `monorepo-bootstrap` (Step 8) and
  `eve-agent` (layout C) run `setup` right after the design lint.
- **The phase gate.** `dev-flow/scripts/update_meta.py set-phase` refuses `scaffolded` for a Next app on
  a Tailwind UI or an eve agent until `check` passes, or `stack.registry_intake = "none"` is recorded with
  `stack_config.registry_intake_reason`. `show_state.py` warns on projects already past it.
- **The hook** lives in the project's `.claude/settings.json` and runs a vendored copy of the script,
  `.claude/hooks/registry_intake.py`, through `$CLAUDE_PROJECT_DIR` — both committable. Never an absolute
  path to the installed skill: committed, it breaks on every other machine, and `python3` on a missing
  file exits `2`, which Claude Code reads as *block* — every Bash call would be refused. `check` flags a
  copy that differs from the installed skill; `setup` refreshes it. Verified in a headless `claude -p`
  session: `shadcn add @pdfcn/…` and a registry URL were both refused with the reason. It uses the documented
  PreToolUse contract — stdin `tool_input.command`, stdout `hookSpecificOutput.permissionDecision: "deny"`
  with a reason (<https://code.claude.com/docs/en/hooks-guide>). It allows bare shadcn names,
  `--dry-run/--view/--diff`, eve's official `eve add <kind>/<name>`, approved snapshots with a matching
  hash, and `live` registries; it denies every other `shadcn add`, `eve add @…` and `eve registry add`.
  For `registry_intake.py allow` and `approve` it answers **`"ask"`**: Claude Code shows the user a
  permission prompt naming the registry or the item and the `--by`, so an agent that skipped the
  question still cannot record a decision nobody made (<https://code.claude.com/docs/en/hooks>, PreToolUse
  decision control: `allow` / `deny` / `ask` / `defer`). Where no permission prompt can be shown, the
  call does not go through.

## Limits, stated

- The hook covers **Claude Code**. Other agents and humans are covered by `check` (phase gate,
  `show_state`, and CI if the project runs it — the script is one stdlib file).
- The hook reads the command string and the session `cwd`; it does not follow a `cd` inside the command,
  so a relative snapshot path after `cd` is denied (fail closed).
- `install` runs `shadcn@4.21.0` from the lock's root: local items and root-relative
  `registryDependencies` were verified on that version. Bump `shadcn` in the lock deliberately.
- Items already in a project before `setup` are not retro-reviewed; their registries are allowlisted
  with the reason "already in components.json when intake was set up" so the decision is visible.

## Files

- `scripts/registry_intake.py` — the whole mechanism (stdlib only).
- `scripts/test_registry_intake.py` — 27 tests, no network; run in CI.
- `references/contracts.md` — the vendored `.workflow/` contract (`stack.registry_intake`).
- `registry-lock.json`, `vendor/registry/`, `.claude/settings.json` and `.claude/hooks/registry_intake.py`
  in the project — commit all four.
