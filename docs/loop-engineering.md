# Loop engineering — autonomous Linear → Claude Code → PR loop

Operational runbook for building a **monorepo** (`apps/web` Next.js + `apps/agent` eve)
through an **autonomous development loop**: Linear issues drive Claude Code running headless
on a Hetzner server, which implements one issue per iteration, opens a GitHub PR, and lets
CI gates decide what merges.

> This document is end-to-end setup guidance. It pairs the `dev-flow` orchestrator and the
> `eve-agent` skill (which already encode *what one iteration does*) with the infrastructure
> that *repeats* it. Copy it into your project repo when you bootstrap it.
>
> Claude Code flags below are verified against Claude Code v2.1+ (June 2026). Items marked
> *(verify)* are version-dependent or need confirmation against your installed versions.

## The loop in one line

```
Linear (Todo)
   → runner (systemd, Hetzner)
      → claude -p (headless) + dev-flow → eve-agent / web skills
         → PR (gh)
            → GitHub Actions: lint · typecheck · build · eve eval --strict · web tests
               → merge → Vercel deploy
                  → Linear (Done) → next issue
```

One issue = one atomic operation = one file = one PR. That 1:1 mapping is what makes the
loop reliable — eve tools are a single auto-registered file (`agent/tools/x.ts`), so "give
the agent a tool to do X" is a clean, verifiable unit of work.

## What the skills give you vs. what you build

| Piece | Provided by |
|---|---|
| `.workflow/` contract + web/agent routing | `dev-flow` + `eve-agent` |
| eve conventions, scaffold, capability verification | `eve-agent` (references + `check_eve_state.py`) |
| Monorepo skeleton | `monorepo-bootstrap` (web/mobile) + `eve-agent` scaffold mode (`apps/agent`) |
| **The runner** (claim → run → PR → update Linear) | **you build it** — §4 (or adapt `ralph-tui-*`) |
| **CI gates + branch protection** | **you configure it** — §2 |
| **Hetzner box: auth, secrets, MCP, systemd** | **you set it up** — §3 |

---

## 0. Accounts, costs, and the two-billing rule

Accounts: **GitHub** (repo + Actions), **Linear** (task queue), **Anthropic** (Claude Code
auth), **Vercel + AI Gateway** (eve runtime), **Hetzner** (server).

**Two separate meters — do not conflate them:**

- Claude Code *writing the code* in the loop → billed via your Anthropic subscription or API
  key.
- The eve agent's *model calls at runtime* (in dev/CI evals and in production) → billed via
  the **Vercel AI Gateway**.

A heavy loop spends the first; a popular app spends the second.

---

## 1. Linear — the queue

1. **Workflow states:** `Todo → In Progress → In Review → Done` (+ `Blocked`). The runner
   moves each issue along these as it claims, opens a PR, and merges.
2. **Atomic issues, 1:1 with a skill operation.** Examples:
   - "Give the agent a tool to list the user's open tasks" → `apps/agent/agent/tools/list_tasks.ts` (eve-agent capability mode)
   - "Generate the /clienti page from the screenshot" → `screenshot-to-page`
   - "Wire Stripe billing" → `module-add` (web)
   Keep each issue to one file / one capability. Oversized issues are where loops drift.
3. **Labels** to hint the side: e.g. `area:agent` vs `area:web`. dev-flow also deduces this
   from `meta.json#stack`, but labels make the per-iteration prompt unambiguous.
4. **API token:** Linear → Settings → API → personal API key (`lin_api_...`). The runner
   uses it to read and update issues. **No browser OAuth on the server.**

---

## 2. GitHub — the merge gate (guardrail #1)

The PR is the control point. The loop may write anything; **broken code must not reach
`main`.**

- **Branch protection on `main`:** require a PR, require status checks to pass, block direct
  pushes.
- **GitHub Actions** running on every PR:

```yaml
# .github/workflows/ci.yml
name: ci
on:
  pull_request:
    branches: [main]
jobs:
  gates:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
      - uses: actions/setup-node@v4
        with: { node-version: 24, cache: pnpm }
      - run: pnpm install --frozen-lockfile
      - run: pnpm -r lint
      - run: pnpm -r typecheck
      - run: pnpm -r build
      - run: pnpm --filter agent eval -- --strict --junit .eve/junit.xml
        env:
          AI_GATEWAY_API_KEY: ${{ secrets.AI_GATEWAY_API_KEY }}   # evals call the model
      - run: pnpm --filter web test
```

- The eval job needs a model credential because `eve eval` actually runs the agent. Use a
  cheap model or a small eval set to keep CI cost bounded.
- Only when all checks are green is the PR mergeable. This is what stops an autonomous loop
  from shipping regressions.

---

## 3. Hetzner — the server

### 3.1 Provision
A small VPS is enough for a **single-worker** loop (e.g. CX22/CX32, Ubuntu LTS).

### 3.2 Runtime
Install: `git`, **Node ≥ 24** (required by eve), `pnpm`, `gh` (GitHub CLI), and the Claude
Code CLI. Verify Node: `node -v` → must be ≥ 24.

### 3.3 Claude Code auth (headless — pick one)

- **Subscription** (uses your Pro/Max/Team plan): on your laptop run `claude setup-token`,
  then on the server export the generated token:
  ```bash
  export CLAUDE_CODE_OAUTH_TOKEN="..."   # ~1-year token, needs an active subscription
  ```
- **API key** (pay-per-token):
  ```bash
  export ANTHROPIC_API_KEY="sk-ant-..."
  ```

Smoke test: `claude -p "print 'auth ok'" --output-format json | jq .result`

### 3.4 Secrets

Put everything in `/etc/loop.env` (root-only, `chmod 600`), never in the repo:

```bash
# /etc/loop.env
CLAUDE_CODE_OAUTH_TOKEN=...      # or ANTHROPIC_API_KEY=...
LINEAR_API_KEY=lin_api_...
GH_TOKEN=ghp_...                 # for gh CLI (PRs)
AI_GATEWAY_API_KEY=...           # eve evals / runtime
LOOP_MAX_COST_USD=5              # per-iteration budget guard (your runner enforces it)
```

### 3.5 Skills on the box

Copy `dev-flow` + `eve-agent` + the family into `~/.claude/skills/` (same install you'd do
locally). **Installed skills are available in `-p` (headless) mode**, so dev-flow routing
and eve-agent work unattended. Invoke a specific one in a prompt with `/dev-flow` if needed.

### 3.6 Linear via MCP (token, not OAuth)

```json
// .mcp.json  (in the repo, or ~/.claude/.mcp.json)
{
  "mcpServers": {
    "linear": {
      "command": "npx",
      "args": ["-y", "<linear-mcp-package>"],
      "env": { "LINEAR_API_KEY": "${LINEAR_API_KEY}" }
    }
  }
}
```

Pass it to a headless run with `--mcp-config .mcp.json` and allow it via
`--allowedTools "mcp__linear__*"`. Use the **API key**, not browser OAuth (OAuth blocks in
headless). *(Verify the exact Linear MCP package/name and tool names against the current
Linear MCP docs.)*

---

## 4. The runner — the engine that repeats (you build this)

A **concurrency-1** loop. For each issue:

```bash
#!/usr/bin/env bash
# runner.sh — skeleton, not production. Single worker.
set -euo pipefail
set -a; source /etc/loop.env; set +a

REPO=/srv/agentic-app
PAUSE=/etc/loop.paused

while true; do
  [ -f "$PAUSE" ] && { echo "paused"; sleep 30; continue; }   # kill-switch

  # 1. CLAIM: next Todo issue via Linear MCP, move it to In Progress
  #    (use a tiny claude -p call with --allowedTools "mcp__linear__*",
  #     or call the Linear API directly with curl + LINEAR_API_KEY)
  ISSUE_ID=... ; ISSUE_TEXT=...
  [ -z "$ISSUE_ID" ] && { sleep 60; continue; }               # empty queue

  # 2. ISOLATE: a worktree + branch per issue
  cd "$REPO"
  git fetch origin main
  WT="../wt/$ISSUE_ID"
  git worktree add -B "loop/$ISSUE_ID" "$WT" origin/main
  cd "$WT"

  # 3. IMPLEMENT: headless Claude Code, dev-flow drives the routing
  timeout 1800 claude -p "Implement Linear issue $ISSUE_ID.
$ISSUE_TEXT
Use the dev-flow skill to orient on .workflow/meta.json and route to the right
specialist: eve-agent for apps/agent work, screenshot-to-page / module-add for
apps/web. Add exactly one capability/file plus its test/eval. Run the local gates
(pnpm -r lint typecheck build; pnpm --filter agent eval). When green, open a PR
with gh against main referencing $ISSUE_ID." \
    --permission-mode acceptEdits \
    --allowedTools "Bash(git *),Bash(pnpm *),Bash(npx *),Bash(gh *),Read,Edit,Write" \
    --max-turns 20 \
    --output-format json | tee /var/log/loop/$ISSUE_ID.json
  CODE=${PIPESTATUS[0]}

  # 4. RESULT: on success move issue → In Review; on failure → Blocked
  if [ "$CODE" -eq 0 ]; then : ; else : ; fi   # update Linear via MCP/API

  # 5. CLEANUP
  cd "$REPO"; git worktree remove --force "$WT" || true
done
```

Key facts (verified):

- **`--permission-mode acceptEdits` + an explicit `--allowedTools` allowlist** is the
  recommended way to run unattended *without* full `bypassPermissions`. It auto-approves
  edits and the listed Bash prefixes, nothing else.
- **`--output-format json`** → read `.result`, `.session_id`, `.total_cost_usd`, `.usage`
  for logging and the budget guard.
- **`--max-turns`** caps agentic iterations; wrap the call in `timeout` (there is no internal
  execution timeout).
- **`--resume <session_id>`** if you split an iteration into steps (implement, then open PR).
- **Exit code ≠ 0** means failure (auth, rate limit, a tool blocked by permissions) → send
  the issue to `Blocked`, don't proceed.
- **Agent SDK alternative:** `@anthropic-ai/claude-agent-sdk` (TS) / `claude_agent_sdk` (Py)
  if you want programmatic message streaming and custom approval logic instead of shelling
  out. CLI `-p` is enough for this loop.
- **`--bare`** *(v2.1.175+, verify)* gives a reproducible run that ignores stray local
  config — but in `--bare` mode skills are **not** auto-loaded unless invoked explicitly, so
  pass `/dev-flow` in the prompt.

Run it under **systemd**:

```ini
# /etc/systemd/system/loop.service
[Unit]
Description=Agentic dev loop
After=network-online.target

[Service]
Type=simple
EnvironmentFile=/etc/loop.env
WorkingDirectory=/srv/agentic-app
ExecStart=/srv/agentic-app/ops/runner.sh
Restart=on-failure
RestartSec=15

[Install]
WantedBy=multi-user.target
```

- **Kill-switch:** `touch /etc/loop.paused` → the loop finishes the current iteration and
  idles; remove the file to resume.
- **Logging:** per-issue JSON under `/var/log/loop/`, plus `journalctl -u loop`.

---

## 5. Guardrails (the heart of loop engineering)

Without these, an autonomous loop drifts. In priority order:

1. **CI gates are the merge requirement** (§2) — non-bypassable. The loop opens PRs; green
   checks merge them.
2. **HITL on irreversible actions.** **Deploy is not autonomous.** In eve, every tool with a
   non-idempotent side effect (payment, delete, external write) uses `approval: always()`;
   an interrupted durable step re-runs, so approval gating is also replay-safety. The loop
   never runs `eve deploy` / `vercel deploy` itself.
3. **Budget guard.** Sum `total_cost_usd` per iteration; stop or alert past `LOOP_MAX_COST_USD`.
4. **Concurrency 1 + a worktree per issue** — no two iterations stepping on each other.
5. **Drift detection** (`dev-flow/scripts/check_drift.py`) — surfaces when an upstream
   artifact (e.g. `DESIGN.md`) changed and a derived file is now stale.
6. **A Definition of Done per issue type** (a tool needs an eval; a page needs a test).

---

## 6. Deploy

- `apps/web` → **Vercel** (preview per PR, prod on merge to `main`).
- `apps/agent` → either:
  - **Vercel:** `eve link` (pulls AI Gateway creds) + `eve deploy`; or
  - **Self-host on Hetzner:** `eve build` + `eve start` (Node ≥ 24), `.workflow-data` on
    persistent storage, and a reverse proxy that forwards **both** `/eve/` **and**
    `/.well-known/workflow/`. Replace `placeholderAuth()` in `agent/channels/eve.ts` with
    real auth — eve fails closed in production.

Keep deploy **behind a human or a separate gated job**, not inside the autonomous loop.

---

## Bootstrapping order (zero → running loop)

1. **Project:** run `dev-flow` → `prd-from-idea` → `prd-to-tasks` → DESIGN.md → choose
   `stack.framework="monorepo"` and answer "yes" to the agent question (`stack.agent="eve"`).
2. **Scaffold:** `monorepo-bootstrap` (root + `apps/web`), then `eve-agent` scaffold mode
   (`apps/agent` + `packages/types`).
3. **Repo hygiene:** push to GitHub, add `.github/workflows/ci.yml` (§2), enable branch
   protection.
4. **Seed Linear:** import `tasks.md` as issues (one atomic operation each).
5. **Server:** provision Hetzner (§3), install runtime + Claude Code + skills, write
   `/etc/loop.env` and `.mcp.json`.
6. **Runner:** drop in `runner.sh` + `loop.service`, start with `LOOP_MAX_COST_USD` low and
   the queue holding one or two safe issues. Watch the first PRs by hand before trusting it.
7. **Scale up:** widen the queue once gates and the runner have proven themselves.

---

## Checklists

**Repo**
- [ ] Monorepo (turborepo + pnpm), `apps/web` + `apps/agent` + `packages/types`
- [ ] `.workflow/meta.json` with `stack.framework="monorepo"`, `stack.agent="eve"`
- [ ] `.github/workflows/ci.yml` with all gates; branch protection on `main`
- [ ] `.gitignore`: `.eve/`, `.output/`, `.workflow-data`, `node_modules`

**Server**
- [ ] Node ≥ 24, pnpm, gh, Claude Code installed
- [ ] Claude Code auth verified (`CLAUDE_CODE_OAUTH_TOKEN` or `ANTHROPIC_API_KEY`)
- [ ] `/etc/loop.env` (chmod 600) with all secrets
- [ ] Skills in `~/.claude/skills/`
- [ ] `.mcp.json` for Linear (API key, not OAuth)
- [ ] `runner.sh` + `loop.service`; kill-switch (`/etc/loop.paused`) tested

**Guardrails**
- [ ] CI gates block merge of broken code
- [ ] Irreversible eve tools are `approval: always()`; deploy is out of the loop
- [ ] Per-iteration budget enforced
- [ ] Concurrency 1 + worktree isolation

---

## Open items to verify before going live

- Exact **Linear MCP** package name and tool names (`mcp__linear__*`).
- Whether you'll drive Linear via MCP or directly via the Linear GraphQL API + `LINEAR_API_KEY`.
- Claude Code version-dependent flags on your box: `--bare`, `--output-format stream-json`,
  `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS`.
- eve's exact `eve eval` flags and CI auth env on the GitHub runner.
- A staging dry-run of the full loop on one throwaway issue before enabling systemd.
