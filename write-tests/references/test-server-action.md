# write-tests → server action

Server actions live at `lib/server/<domain>.ts`, are marked `"use server";`, and follow the canonical shape: a Zod schema, a typed `ActionResult<T>` return for **business** errors (`{ ok: false, fieldErrors? }`), and a `throw` for **system** errors (DB down, auth not wired, unauthorized). The test must cover all three lanes.

## Test file location

`lib/server/__tests__/<name>.test.ts` — never co-located, since server actions are server-only and a co-located `.test.ts` next to a `"use server"` file confuses some bundlers.

## Canonical shape

```typescript
import { describe, expect, it, vi, beforeEach } from "vitest";

// 1. Mock auth helpers BEFORE importing the action.
//    Path matches the project's `lib/auth-server.ts` (created by `module-add auth`)
//    or the placeholder stubs at the top of the action file (pre-auth).
vi.mock("@/lib/auth-server", () => ({
  getCurrentUserId: vi.fn(() => Promise.resolve("user_42")),
  getCurrentTenantId: vi.fn(() => Promise.resolve("tenant_7")),
  getSession: vi.fn(() => Promise.resolve({ user: { id: "user_42" } })),
}));

// 2. Mock the DB layer — test the action's logic, not Drizzle.
const mockDb = {
  transaction: vi.fn((cb) => cb(mockDb)),
  insert: vi.fn(() => mockDb),
  values: vi.fn(() => mockDb),
  returning: vi.fn(() => Promise.resolve([{ id: 42 }])),
  select: vi.fn(() => mockDb),
  from: vi.fn(() => mockDb),
  where: vi.fn(() => Promise.resolve([])),
  update: vi.fn(() => mockDb),
  set: vi.fn(() => mockDb),
  delete: vi.fn(() => mockDb),
};
vi.mock("@/lib/db", () => ({ db: mockDb }));

// 3. Mock revalidatePath — every action that mutates calls it.
//    Already mocked globally in vitest.setup.ts — only re-mock if the test
//    needs to assert it was called with specific args.

// 4. IMPORT the action AFTER the mocks. ESM hoists `vi.mock` but importing
//    the action before declaring mocks risks subtle race conditions.
import { createClient, updateClient, archiveClient } from "@/lib/server/clienti";

beforeEach(() => {
  vi.clearAllMocks();
});

describe("createClient", () => {
  it("returns { ok: false } with fieldErrors when name is too short", async () => {
    const result = await createClient({ name: "X", email: "user@example.com" });
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.fieldErrors?.name).toBeDefined();
    }
  });

  it("returns { ok: false } when email is malformed", async () => {
    const result = await createClient({ name: "Mario Rossi", email: "not-an-email" });
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.fieldErrors?.email).toBeDefined();
    }
  });

  it("returns { ok: true, data } on the happy path", async () => {
    mockDb.returning = vi.fn(() => Promise.resolve([{ id: 42, name: "Mario Rossi" }]));
    const result = await createClient({ name: "Mario Rossi", email: "mario@example.com" });
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.data.id).toBe(42);
    }
  });

  it("throws (not returns { ok: false }) when auth is not wired", async () => {
    // Re-mock to simulate the placeholder auth stubs throwing.
    vi.mocked(getCurrentUserId).mockRejectedValueOnce(new Error("AUTH_NOT_WIRED"));
    await expect(
      createClient({ name: "Mario Rossi", email: "mario@example.com" })
    ).rejects.toThrow(/AUTH_NOT_WIRED/);
  });
});

describe("updateClient", () => {
  it("returns { ok: false } when the row is not found", async () => {
    mockDb.where = vi.fn(() => Promise.resolve([])); // no rows
    const result = await updateClient({ id: 999, name: "New name" });
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error).toMatch(/not found/i);
    }
  });

  it("scopes the update to the current tenant", async () => {
    mockDb.where = vi.fn(() => Promise.resolve([{ id: 1, tenantId: "tenant_7" }]));
    await updateClient({ id: 1, name: "Updated" });
    // Drizzle `.where()` should have been called with both id AND tenantId.
    // The exact call shape depends on the action's query — read the source.
    expect(mockDb.where).toHaveBeenCalled();
  });
});
```

## What to cover (per action)

For every action exported from the source file, write tests covering:

1. **One happy path** — valid input → `{ ok: true, data: ... }`. Don't write 5 happy paths; one is enough to verify the success-shape contract.
2. **Validation errors** — one `it()` per Zod field with a non-trivial constraint (min length, regex, enum). Skip fields that only have `z.string()` with no constraints.
3. **Business errors** — one `it()` per `{ ok: false }` branch in the source (e.g., "row not found", "already archived", "quota exceeded").
4. **Auth errors** — one `it()` confirming the action **throws** when auth helpers throw. This is the most-skipped case and the most important: it guarantees unauthorized requests hit the Next error boundary, not leak through `{ ok: false }`.
5. **Tenant scoping (if multi-tenant)** — one `it()` confirming the WHERE clause includes `tenantId`. Don't skip this; tenant-bleed bugs are silent and disastrous.

## What NOT to cover

- Drizzle's correctness (it's tested upstream).
- Zod's correctness (same).
- The DB connection (integration tests live elsewhere).
- The exact SQL string emitted (brittle — assert behavior, not the query string).

## Mocking the action's collaborators

If the action calls another internal helper (e.g., `await sendNotification(...)`), mock that helper at the file boundary:

```typescript
vi.mock("@/lib/notifications", () => ({
  sendNotification: vi.fn(() => Promise.resolve()),
}));
```

Then assert it was called when expected:

```typescript
import { sendNotification } from "@/lib/notifications";

it("sends a notification on successful create", async () => {
  await createClient({ name: "...", email: "..." });
  expect(sendNotification).toHaveBeenCalledWith(
    expect.objectContaining({ kind: "client_created" })
  );
});
```

## Common pitfalls

- **Forgetting to `vi.clearAllMocks()` in `beforeEach`**: mocks leak between tests, causing phantom failures. The setup template above already pins this.
- **Asserting on call counts that depend on mock chains**: if the action calls `db.select().from().where()`, asserting `expect(mockDb.where).toHaveBeenCalledTimes(1)` breaks when an unrelated branch also hits `.where()`. Prefer asserting on the **return** of the action, not internal call shapes.
- **Mixing real and mocked auth**: don't do `vi.mocked(getCurrentUserId).mockResolvedValueOnce(undefined)` to simulate "no user" — `undefined` isn't the contract. The contract is: helper throws. Mock the throw.
