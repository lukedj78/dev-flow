# Risk assessment — a floor the agent may raise and never lower

```bash
python3 release-intelligence/scripts/risk.py <root> --base origin/main [--include-working] [--json]
```

## Why it is split in two

A single number produced by a model reading a diff is worthless for this job, in a specific way: it
is **correlated with how the diff looks**, and the releases that hurt are the ones that look fine.
`dev-flow/references/contracts.md` §Intervention levels records the measurement that settled this
inside dev-flow — every commit of 2026-10-20's gate work would have scored ✅ on all five Risk
categories, and two of them were the worst defects of the day.

So the classification is deliberately two things:

| | Deterministic (`risk.py`) | Reasoning (the agent) |
|---|---|---|
| Input | the diff, and what the gates already recorded | the PRD, the product, the conversation |
| Output | the **floor** | a **raise**, with a reason |
| May lower the level | — | **never** |
| Reviewable | re-run the command | the reason is in the manifest |

`plan --raise-to high --reason "…"` records the raise, with the floor kept beside it. There is no
instruction that lowers a level, and `plan` refuses a `--raise-to` that is not actually higher. To
argue a level down you fix the signal that produced it.

## The signal table

Each row is a path pattern. A changed file matching it raises the release to that level; the final
level is the **highest** row that matched.

| Signal | Level | Matches |
|---|---|---|
| `migration` | **critical** | `drizzle/*.sql`, `migrations/*.sql`, `supabase/migrations/*.sql`, `prisma/migrations/*/migration.sql` |
| `destructive_migration` | **critical** | the added SQL contains a statement a deployment rollback does not undo (below) |
| `infra` | **critical** | `Dockerfile`, `docker-compose.y*ml`, `fly.toml`, `terraform/*.tf` |
| `auth` | **high** | `lib/auth.ts`, `lib/auth-client.ts`, `app/api/auth/**`, `middleware.ts`, `proxy.ts`, `lib/{session,permissions,rbac,authz}.ts` |
| `payments` | **high** | `app/api/{stripe,webhook,payment}/**`, `lib/[server/]{stripe,payment,billing}.*` |
| `schema` | **high** | `lib/db/schema*`, `drizzle.config.*`, `prisma/schema.prisma` |
| `api` | **medium** | `app/api/**/route.ts` |
| `server_action` | **medium** | `lib/server/*.ts` |
| `platform_config` | **medium** | `vercel.json`, `next.config.*`, `app.config.*`, `eas.json` |
| `ci` | **medium** | `.github/workflows/*.y*ml` |
| `size` | medium ≥ 15 files, high ≥ 60 | the count of changed files |

Plus what the project already measured, read from `meta.json` rather than re-scanned:

| Signal | Level | From |
|---|---|---|
| `security_findings` | **high** | `security.findings.open > 0` — `app-security` has open findings |
| `debt_before_release` | medium | `debt_audit.bands.before_release > 0` |
| `spec_review_level` | medium | `spec_review.level >= 3` — a person had to settle something |

**Everything is re-levellable per project**, because the defaults are not universal — `app/api/` in a
design-system repo is not `app/api/` in a bank:

```json
"release": { "risk_policy": {
  "paths": { "api": "high", "ci": null },
  "size_bands": { "medium": 30, "high": 120 }
} }
```

⚠️ **A typo in that table does not silence a signal.** An unrecognised level keeps the default, and
`null` is the only way to drop a row — so `"auth": "harmless"` leaves `auth` at `high`. It has a test,
because a configurable safety table whose typos disable checks is worse than no table.

## The destructive-SQL rules

Matched case-insensitively, **one statement at a time**, against only the `+` lines of the diff.

| id | Statement | Why it is here |
|---|---|---|
| `drop_table` | `DROP TABLE` | the data is gone; a code rollback does not bring it back |
| `drop_column` | `DROP COLUMN` | same, and the old code still selects it |
| `drop_constraint` | `DROP CONSTRAINT` | invariants the old code relies on stop holding |
| `truncate` | `TRUNCATE` | — |
| `delete_rows` | `DELETE FROM` | a data change dressed as a schema change |
| `type_change` | `ALTER COLUMN … TYPE` | a table rewrite, a lock, and a shape the old code cannot read |
| `set_not_null` | `SET NOT NULL` | fails or locks on a non-empty table |
| `rename` | `RENAME COLUMN`, `RENAME TO` | the textbook expand/contract violation: old code breaks instantly |
| `add_not_null_without_default` | `ADD COLUMN … NOT NULL` with no `DEFAULT` **in the same statement** | Postgres rejects it on a non-empty table — a failed deploy |

`DROP INDEX` is deliberately **absent**: it costs performance, not data.

Two details that are each a bug we already wrote and fixed:

- **Per statement, not per file.** `ADD COLUMN tier text NOT NULL DEFAULT 'free'` is safe. A single
  regex with a negative lookahead reports it as unsafe, because `NOT NULL` is reached before
  `DEFAULT`. Caught by its own test on 2026-11-06.
- **Added lines only.** A `DROP TABLE` that already existed on the base branch is not this release's
  risk; counting the whole file makes every release after a destructive one inherit `critical`
  forever, and a level that is always `critical` is a level nobody reads.

## `NOT CHECKED` is never a pass

Everything the scan could not see is listed separately and copied into the manifest:

- no base branch resolved → **the committed diff was not read at all**;
- a `.sql` file that could not be read;
- `app-security` never ran, or ran with a scanner `not-run`;
- no verification manual proven (`meta.json#verification`), so nothing says the feature was ever
  driven on the real app.

**A release classified `low` because nothing could be read is the failure mode this section exists
for.** Read the list aloud to the user before planning the release; it is usually where the real
work is.

## What the agent should raise, and what it should not

**Raise** when the product knows something the paths cannot:

- the change is small and touches the one number a regulator reads;
- the feature is the subject of a contract or a deadline (`BidMaster`: a tender's submission window);
- the release is the first on a new infrastructure, however small the diff;
- a `low`-floor change to a file that only one customer's integration depends on;
- `NOT CHECKED` includes something that matters here — an unread diff on a payment path is not `low`.

**Do not raise** as a substitute for doing the work: an unverified feature is not "high risk", it is
unverified, and the answer is `app-verification`, not a level. Do not raise to avoid an argument
about a stage percentage either — set the stages.

## What a level actually buys

Only two things, and both are mechanical:

1. **the approval row** in `references/security-and-approvals.md`'s table — which operations the agent
   may run unattended at that level;
2. **the `deployed` gate** — `high` and `critical` do not cross into `deployed` without a person's
   recorded yes (`dev-flow/scripts/release_gate.py`).

It is **not** a score, it is not reported to anyone as a quality measure, and it never gates a build.
A level that starts being optimised for stops being information — the same trap `shadscan`'s score
has, written down in its policy.
