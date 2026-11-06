# Database releases — expand and contract, because a rollback does not reach the schema

## The sentence to internalise first

**A deployment rollback restores code and leaves the schema exactly as the bad release left it.**
`vercel-deploy/references/rollback-runbook.md` says it in its own words — *"External state does not
roll back. A database migration that ran during the bad deploy is still applied"* — and it is the
reason every migration is classified `critical` by `risk.py` regardless of how small it looks.

And its corollary, which is the one people get wrong under pressure: **turning a feature flag off
does not undo a schema change either.** The flag stops the new code path being chosen. The column is
still dropped.

So a release that contains a migration has no instant undo. It has a forward fix. The whole point of
expand/contract is to make sure the forward fix is never needed.

## The four phases

Each phase is **its own deployment**. Collapsing two of them into one deployment is what creates the
window where the running code and the live schema disagree.

### 1. Expand — add, never change

Only additive, backwards-compatible DDL. The **previous** version of the application must keep
working against the new schema, unchanged, because for a few minutes it will be.

```sql
-- safe: the old code does not know this column exists
ALTER TABLE invoices ADD COLUMN currency text;

-- safe: nullable, or with a DEFAULT, so existing rows are valid
ALTER TABLE invoices ADD COLUMN tier text NOT NULL DEFAULT 'standard';

-- safe: a new table, a new index (concurrently, on a large table)
CREATE INDEX CONCURRENTLY idx_invoices_currency ON invoices (currency);
```

Never in this phase: `DROP`, `RENAME`, `ALTER COLUMN … TYPE`, `SET NOT NULL` on an existing column,
or `ADD COLUMN … NOT NULL` without a `DEFAULT`. `risk.py` flags all of them
(`references/risk-assessment.md` §The destructive-SQL rules).

**A rename is never a rename.** It is `ADD` the new column, backfill, write both, read the new one,
then `DROP` the old one in a later release. `RENAME COLUMN` breaks the running code at the instant it
commits.

### 2. Migrate — code that reads both shapes

Deploy application code that tolerates the old shape and the new one: reads fall back, writes go to
both. Then backfill, and **backfill in batches** — a single `UPDATE` over a large table takes locks
and holds a transaction open for minutes.

```ts
// batched backfill: bounded work per statement, resumable, interruptible
// run it as a script or a job, never inside a migration file
while (true) {
  const rows = await db.update(invoices)
    .set({ currency: sql`coalesce(${invoices.currency}, 'EUR')` })
    .where(and(isNull(invoices.currency), /* keyset bound */))
    .limit(1000).returning({ id: invoices.id });
  if (rows.length === 0) break;
}
```

The dual-write window is where the feature flag belongs: it chooses which shape the application
*reads*, while both are being written. That is the one place where flags and migrations genuinely
cooperate.

### 3. Switch — move reads, with exposure

Flip reads to the new shape behind the flag, stage by stage
(`references/progressive-delivery.md`). Writes still go to both, so a `rollback --kind flag` is a
real undo at this phase — the only phase of the four where that sentence is true.

Watch the database, not only the application: connection count, slow queries, and on Neon the
**compute** metrics, because a backfill or a new index can keep an endpoint awake and change the
bill (`vercel-doctor` is the cost gate, but it reads the app, not the database).

### 4. Contract — remove, in a separate release, with evidence

Only after the new shape has served 100% for the soak period **and nothing reads the old one**.

```sql
-- a release of its own, with its own manifest and its own approval
ALTER TABLE invoices DROP COLUMN legacy_currency;
```

Evidence required before this is written, not after:

- the old column does not appear in the application source (`git grep`);
- no query in the last soak window referenced it — from the database's own statistics, not from
  reading the code;
- the flag that chose between the shapes is archived or removed
  (`references/release-cleanup.md`);
- a backup exists, and somebody has said out loud what the restore point is.

## What this skill will and will not do

| | |
|---|---|
| Classify a migration, and name which statements are not undoable | **yes**, `risk.py` |
| Refuse to cross into `deployed` with a destructive migration and no human approval | **yes**, `release_gate.py` |
| Produce the expand/contract plan, phase by phase, for review | **yes** |
| Write the migration file | **no** — `module-add db` owns the schema |
| **Execute a destructive migration** | **never.** `policy.py` has `destructive_db_migration` in `NEVER_AUTO`: the verdict is "ask the user" in every mode, at every risk level, and no project config can turn it into `auto` |
| Delete production data | **never**, under any instruction reachable from this skill |

`release.py rollback --kind database` records the decision and prints the procedure. It runs nothing.
Its output says so in capitals, because the moment someone reaches for it is the moment they are
least likely to read carefully.

## Neon specifics worth having before the plan

- **Branching is the rehearsal.** A Neon branch is a copy-on-write clone of production data: run the
  migration there first, against real volume and real distributions, and measure how long it takes
  and what it locks. This is the single highest-value habit on this page, and
  `dev-flow/references/before-you-build.md` §2 is the general version of it — the platform already
  has the capability.
- **A branch is not a backup.** Know the project's restore window and its point-in-time retention
  before a `critical` release, and write the number in the manifest.
- **Drizzle generates, it does not judge.** `drizzle-kit generate` happily emits `DROP COLUMN` from a
  schema edit. The generated SQL is reviewed by a person before it is committed, and `risk.py` reads
  what was committed.
- **`drizzle-kit push` is for development.** A production release applies a committed, reviewed
  migration file, so that what ran is recoverable from git.

## When a migration must be reverted anyway

There is no undo; there is a new forward migration. Write it with the same four phases, treat it as a
`critical` release of its own with its own manifest and approval, and **confirm the backup and the
restore point before it runs**. If data was lost, the recovery is a restore, which is an operation
with a different owner and a different conversation — not a step in a rollout.
