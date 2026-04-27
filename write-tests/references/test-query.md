# write-tests → query

Queries live at `lib/queries/<domain>.ts`. They're **read-only** server-side functions called from RSC (and occasionally from server actions). Their tests are simpler than action tests — no mutation, no `revalidatePath`, often no auth (queries that don't filter by tenant are public).

## Test file location

`lib/queries/__tests__/<name>.test.ts` — same convention as actions.

## Canonical shape

```typescript
import { describe, expect, it, vi, beforeEach } from "vitest";

vi.mock("@/lib/auth-server", () => ({
  getCurrentTenantId: vi.fn(() => Promise.resolve("tenant_7")),
}));

const mockDb = {
  select: vi.fn(() => mockDb),
  from: vi.fn(() => mockDb),
  where: vi.fn(() => mockDb),
  orderBy: vi.fn(() => mockDb),
  limit: vi.fn(() => mockDb),
  innerJoin: vi.fn(() => mockDb),
  leftJoin: vi.fn(() => mockDb),
  // The terminal call that returns rows. Configure per-test.
  execute: vi.fn(() => Promise.resolve([])),
  // Drizzle also lets you await the query directly — make `then` return rows.
  then: undefined as unknown,
};
vi.mock("@/lib/db", () => ({ db: mockDb }));

import { getClienti, getClienteById } from "@/lib/queries/clienti";

beforeEach(() => {
  vi.clearAllMocks();
});

describe("getClienti", () => {
  it("returns an empty array when no rows match", async () => {
    // Drizzle queries are awaited directly — the chain ends in a Promise.
    // Mock the final `.where()` to resolve to [].
    mockDb.where = vi.fn(() => Promise.resolve([]));

    const result = await getClienti();
    expect(result).toEqual([]);
  });

  it("returns the rows in the order specified by the source", async () => {
    const rows = [
      { id: 1, name: "Bianchi", createdAt: new Date("2026-01-01") },
      { id: 2, name: "Rossi", createdAt: new Date("2026-02-01") },
    ];
    mockDb.orderBy = vi.fn(() => Promise.resolve(rows));

    const result = await getClienti();
    expect(result).toHaveLength(2);
    expect(result[0].name).toBe("Bianchi");
  });

  it("scopes to the current tenant", async () => {
    mockDb.where = vi.fn(() => Promise.resolve([]));
    await getClienti();
    // The query must call `.where(...)` with a tenantId predicate.
    expect(mockDb.where).toHaveBeenCalled();
    // For stricter assertion, capture the call arg and verify it references
    // the tenantId column. This is brittle — only do it when tenant-bleed
    // would be catastrophic.
  });
});

describe("getClienteById", () => {
  it("returns null when the row is not found", async () => {
    mockDb.limit = vi.fn(() => Promise.resolve([]));
    const result = await getClienteById(999);
    expect(result).toBeNull();
  });

  it("returns the row when found", async () => {
    const row = { id: 1, name: "Mario Rossi" };
    mockDb.limit = vi.fn(() => Promise.resolve([row]));
    const result = await getClienteById(1);
    expect(result).toEqual(row);
  });
});
```

## What to cover (per query)

For every exported query function, write:

1. **Empty result path** — DB returns `[]`, query returns `[]` or `null` correctly. Catches off-by-one bugs in `[0]` access.
2. **Single result path** — DB returns one row, query returns the row in the expected shape.
3. **Multi-result path** (for list queries) — DB returns 3+ rows, query preserves order and shape.
4. **Tenant scoping** (if multi-tenant) — assert `.where()` was called. Don't try to verify the exact predicate shape unless the consequence of getting it wrong is severe.
5. **Pagination** (if the query supports `limit`/`offset`) — one test confirming the args reach Drizzle.

## What NOT to cover

- **Drizzle's correctness** — it's tested upstream.
- **The exact SQL emitted** — Drizzle's SQL output is internal; asserting on it locks the test to the ORM version.
- **Performance** — N+1 queries are caught by integration tests against a real DB, not by unit tests.

## Queries that JOIN

When the query joins multiple tables (e.g., `clienti` + `pratiche`), the mock chain gets longer:

```typescript
mockDb.innerJoin = vi.fn(() => mockDb);
mockDb.where = vi.fn(() => Promise.resolve([
  { client: { id: 1, name: "Rossi" }, practice: { id: 10, type: "compravendita" } },
]));

const result = await getClientiWithPractices();
expect(result[0].practice.type).toBe("compravendita");
```

The exact mock shape depends on whether the query uses Drizzle's `with` (relational) syntax or manual joins. Read the source first.

## Queries with parameters

If the query takes filters (search string, status, date range), test each branch:

```typescript
it("filters by search string when provided", async () => {
  mockDb.where = vi.fn(() => Promise.resolve([]));
  await getClienti({ search: "Rossi" });
  expect(mockDb.where).toHaveBeenCalled();
});

it("does not call .where() when no filters are provided", async () => {
  mockDb.where = vi.fn(() => Promise.resolve([]));
  await getClienti();
  // Note: tenant-scoping still calls .where(), so this assertion is wrong
  // for tenant-aware queries. Adjust based on the source.
});
```

## Queries called from RSC vs Server Actions

Queries are typically `await`ed in RSC (`async function Page()`) **or** inside server actions before a write. The test doesn't care about the call site — it tests the query's return contract regardless. But the **mock auth** behavior should match the call site:

- Public query (no auth): don't mock `getCurrentTenantId`; the query shouldn't import it.
- Tenant-scoped query: mock `getCurrentTenantId` to return a known id and assert the where-clause uses it.

## Common pitfalls

- **Mocking `db` chain depth wrong**: if the query is `db.select().from().leftJoin().where().limit(1)`, you need 5 mock methods returning the chain. If you forget one, the test silently calls the un-mocked method on the real Drizzle, which may throw or return unexpected things. Read the source FIRST, count the chain, mock all of them.
- **Asserting on `mockDb.select` call count**: not useful. Multiple queries internally hit `select`. Assert on the **return** of the function being tested.
- **Date comparisons**: queries that return `Date` objects fail equality checks (`expect(d1).toBe(d2)` is identity, not value). Use `expect(result.createdAt.getTime()).toBe(expected.getTime())` or `toEqual` (deep) instead of `toBe` (identity).
- **Forgetting to await**: queries return Promises. `expect(getClienti()).toEqual([])` always passes regardless — it's checking a Promise against an array. Always `await`.
