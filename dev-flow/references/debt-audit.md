# Debt audit — formats, bands, coverage

`scripts/debt_audit.py collect <root>` composes every audit the project has, plus a test check, into one ordered
list. This page is what the agent needs to run it well: what goes where, the two files it reads from the agent, and
the commands that produce coverage. The how-and-when is `../SKILL.md` §Debt audit.

## The bands

The table lives in `scripts/debt_model.py` as `BAND_RULES` (the first matching row wins); it is repeated here for
the reader.

| Band | What goes in it |
|---|---|
| **before the next release** | every app-security finding (secrets, authorization, vulnerable dependencies, exposed data); compliance `H`; a blocking registry-intake problem; observability `errors` missing — or never chosen, since an app online without error tracking does not know when it breaks; a file that writes data with no test **and** an authorization finding on the same file |
| **with the features that touch these files** | compliance `M`; registry-intake review items; files that write data with no test; shadscan `fix`; vercel-doctor high and medium; launch-audit `missing`; recipe violations `HIGH` and `MEDIUM` |
| **later** | observability `logs` / `uptime` missing; shadscan `verify` / `decide`; vercel-doctor low; promote-component candidates; recipe violations `LOW` |
| *not checked* (apart) | each source or check that could not see: not installed, skipped, timed out, unreadable output, no coverage file — and each source that saw only **part** (`partial`: app-security without gitleaks or Semgrep, observability without a visible DSN), with what it missed. Listed, never ordered, never counted clean |

Inside a band, the files changed most often in the last 90 days come first (`git log --since=90.days`): "with the
features" means that file will be reopened. Ties, and findings without a file, keep the source's order. Without git,
the source's order.

A row reads `- [to confirm] [stale] file:line — detail (source/check → owner)`:
- `[to confirm]`: a scanner's signal (app-security, compliance) nobody has reviewed yet. `meta.json#debt_audit.bands`
  counts confirmed findings only; `to_confirm` counts these.
- `[stale]`: from a recorded run (shadscan, vercel-doctor) older than the last material change — re-run that gate.

## The sources

| Source | How it is read | Notes |
|---|---|---|
| app-security | `scan_security.py <root> --json`, run | needs the network for dependencies and Semgrep rules; offline, `--skip app-security`. Timeout 1800 s |
| launch-audit | `scan_launch.py <root> --json`, run | web only |
| observability | `observability_check.py <root> --json`, run | `--all` when `stack.observability` is empty |
| compliance | `compliance-audit/scripts/scan.py <root>`, run | findings have no file; signals |
| registry-intake | `registry_intake.py check <root>`, run | only when `registry-lock.json` exists |
| promote-component | `scan_promotion.py <root>`, run | rows whose suggestion starts with `Promote` |
| shadscan | `docs/ui/shadscan.json` → `agentHandoff.actionables[]`, read | never run by the script (network, `npx`) |
| vercel-doctor | `meta.json#vercel_doctor.findings{high,medium,low}`, read | counts only: one row per severity |
| manual | `.workflow/debt/manual.json`, read | the prose recipes' findings, written by the agent |
| tests / coverage | `scripts/debt_tests.py` | below |

Every scanner is found by path beside dev-flow. A skill that is not installed makes its source *not checked*, so the
audit runs with whatever is there.

## The two files the agent writes

**`.workflow/debt/reviewed.json`** — the verdict on a finding, keyed by its id (`source:check:file`, from
`.workflow/debt/findings.json`):

```json
{
  "app-security:server-action-unauthenticated:app/actions/plan.ts": {
    "verdict": "confirmed", "reason": "", "at": "2026-10-18", "hash": ""
  },
  "app-security:raw-sql:lib/report.ts": {
    "verdict": "false_positive", "reason": "the template is a constant", "at": "2026-10-18", "hash": "<from findings.json>"
  }
}
```

- `confirmed` turns a signal into a finding counted in its band;
- `false_positive` and `accepted` move it to *kept on purpose* — until the file changes: write the file's `hash`
  (`debt_model.file_hash`, the first 16 hex of its SHA-256) with the verdict, and a different hash brings the finding
  back as a signal;
- the gates' own acceptances (`security.findings.accepted`, `launch_audit.dismissed`, `shadscan.false_positives` /
  `rules_left_red`) apply **per check**, on every file, as the gate decided; `compliance.flagged` is never kept — it
  means a legal decision is still owed.

**`.workflow/debt/manual.json`** — what the prose recipes found (`state-discipline/references/audit-recipe.md`,
`data-fetching/references/audit-recipe.md`, `forms/references/audit-recipe.md`), one object per violation:

```json
[
  { "source": "forms", "check": "C", "severity": "HIGH", "file": "app/[locale]/settings/form.tsx", "line": 41,
    "detail": "Save is enabled while the form is pristine", "routed_to": "forms" }
]
```

`severity` is the recipe's own `HIGH | MEDIUM | LOW`. Rewrite the file on each pass: it is the recipes' latest
answer, not a log.

## The test check

- **Writes data**: a `"use server"` file, a route handler exporting `POST | PUT | PATCH | DELETE`, or a file calling
  `db.insert / update / delete` (or `tx.`).
- **Reached by a unit test**: a `*.test.*` / `*.spec.*` outside `e2e/` that imports it (relative or `@/`) or names
  its path.
- **Reached by e2e**: a spec under `e2e/` or `tests/e2e/` containing a path literal (`goto("/plans")`) that matches
  the URL of a page importing it. The URL drops `(groups)` and leading dynamic segments (`[locale]`); an inner
  `[id]` matches any value.
- Web surfaces only (each one in a monorepo); mobile and agent read *not applicable*.

**Coverage**, when `coverage/coverage-summary.json` exists (istanbul `json-summary`, the same for Vitest and Jest):
the line percentage per surface. Without it, *not checked*, with the command:

```bash
pnpm add -D @vitest/coverage-v8            # once, with the user's yes
pnpm vitest run --coverage --coverage.reporter=json-summary --coverage.reportOnFailure=true
npx jest --coverage --coverageReporters=json-summary   # Expo / Jest
```

`reportOnFailure` matters: without it, one red test file and Vitest writes no summary at all (found on fit-coach,
where one hook timed out under instrumentation). There is no threshold: a percentage is optimised against; a file that writes data with no test is not.

## From findings to tasks

With the user's yes, the before-release band becomes tasks through `prd-to-tasks` revise mode, each citing
`debt:<id>`. Nothing enters `tasks.md` without that yes.
