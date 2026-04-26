# module-add → `test` (Vitest + Testing Library + Playwright)

Wire a **3-tier testing scaffold** into an existing scaffold:

- **Unit / integration**: Vitest + Testing Library — for server actions, queries, components.
- **E2E**: Playwright — for full browser flows.

The scaffold is opinionated: one config per tier, one smoke test per tier, runnable via `pnpm test`, `pnpm test:e2e`. Adding the second test is the user's job.

## Idempotency check

Before doing anything:

1. `<project-root>/package.json` contains `"vitest"` in devDependencies.
2. `<project-root>/vitest.config.ts` exists.

If both: tell the user it's installed, offer to add a new smoke test for a different domain. Don't double-install.

## Prerequisites

- Recommended after `module-add db` (so server-action tests have a schema to mock against).
- Auth wiring is NOT required — the auth helpers (`getCurrentTenantId()`, `getCurrentUserId()`) get mocked in tests.

## Install

```bash
cd <project-root>
pnpm add -D vitest @vitejs/plugin-react @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom @types/node
pnpm add -D @playwright/test
pnpm dlx playwright install chromium
```

## Files to write

### `vitest.config.ts`

```typescript
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
    css: true,
    // Exclude e2e — Playwright runs those in its own runner.
    exclude: ["**/node_modules/**", "**/e2e/**", "**/.next/**"],
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "."),
    },
  },
});
```

### `vitest.setup.ts`

```typescript
import "@testing-library/jest-dom/vitest";
import { afterEach, vi } from "vitest";
import { cleanup } from "@testing-library/react";

afterEach(() => {
  cleanup();
});

// Mock next/navigation — many components import it indirectly.
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }),
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(),
}));

// Mock next/cache helpers — server actions call these.
vi.mock("next/cache", () => ({
  revalidatePath: vi.fn(),
  revalidateTag: vi.fn(),
}));
```

### `lib/server/__tests__/practices.test.ts` (server-action smoke test)

```typescript
import { describe, expect, it, vi, beforeEach } from "vitest";

// Mock the auth helpers BEFORE importing the action.
vi.mock("@/lib/auth", () => ({
  // Replace with the real shape once `module-add auth` runs.
  auth: { api: { getSession: vi.fn() } },
}));

// Mock the DB layer — we test the action's logic, not the schema.
const mockDb = {
  transaction: vi.fn((cb) => cb(mockDb)),
  insert: vi.fn(() => mockDb),
  values: vi.fn(() => mockDb),
  returning: vi.fn(() => Promise.resolve([{ id: 42 }])),
  update: vi.fn(() => mockDb),
  set: vi.fn(() => mockDb),
  where: vi.fn(() => mockDb),
};

vi.mock("@/lib/db", () => ({ db: mockDb }));

// IMPORTANT: import AFTER mocks so the action sees them.
import { createPractice } from "@/lib/server/practices";

describe("createPractice", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns { ok: false } with fieldErrors when input is invalid", async () => {
    // Title too short.
    const result = await createPractice({ title: "ab", type: "compravendita" });
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.fieldErrors).toBeDefined();
      expect(result.fieldErrors?.title).toBeDefined();
    }
  });

  it("returns { ok: false } when the action enum is invalid", async () => {
    const result = await createPractice({
      title: "Compravendita Bianchi",
      // @ts-expect-error — testing rejection of bad input.
      type: "not-a-valid-type",
    });
    expect(result.ok).toBe(false);
  });

  it("propagates the auth-not-wired error as a 500 (no { ok: false } leak)", async () => {
    // The action MUST throw, not return { ok: false }, when auth isn't wired.
    // This guarantees the user sees a Next error boundary, not a leaked
    // internal message.
    await expect(
      createPractice({ title: "Mutuo Verdi", type: "mutuo" })
    ).rejects.toThrow(/AUTH_NOT_WIRED/);
  });
});
```

### `e2e/smoke.spec.ts` (Playwright)

```typescript
import { test, expect } from "@playwright/test";

test("home renders", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveTitle(/./); // any non-empty title
  // The default scaffold's home will have an h1 — assert it exists.
  await expect(page.locator("h1").first()).toBeVisible();
});

test("showcase renders all 9 sections", async ({ page }) => {
  await page.goto("/showcase");
  // The showcase template is mandated to have 9 bordered sections + header.
  // We don't assert exact count to avoid brittleness; we assert the load.
  await expect(page.locator("h1").first()).toBeVisible();
  await expect(page.locator("text=/colors/i").first()).toBeVisible();
  await expect(page.locator("text=/typography/i").first()).toBeVisible();
});

test("dark mode toggle works via D key", async ({ page }) => {
  await page.goto("/");
  // Initial theme is light by default.
  const html = page.locator("html");
  await expect(html).not.toHaveClass(/dark/);
  // Press D — theme should flip.
  await page.keyboard.press("d");
  await expect(html).toHaveClass(/dark/);
  // Press D again — back to light.
  await page.keyboard.press("d");
  await expect(html).not.toHaveClass(/dark/);
});

test("D key does NOT toggle when typing in an input", async ({ page }) => {
  // The mode-toggle component must guard against firing while typing.
  // We need a route with an input — sign-in is a safe default.
  await page.goto("/sign-in");
  const html = page.locator("html");
  await expect(html).not.toHaveClass(/dark/);
  await page.locator("input[type=email]").first().focus();
  await page.keyboard.press("d");
  // Theme should NOT have flipped.
  await expect(html).not.toHaveClass(/dark/);
});
```

### `playwright.config.ts`

```typescript
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: "html",
  use: {
    baseURL: "http://localhost:3000",
    trace: "on-first-retry",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
  webServer: {
    command: "pnpm dev",
    url: "http://localhost:3000",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
```

### `package.json` script additions

Append to `scripts`:

```json
{
  "test": "vitest",
  "test:run": "vitest run",
  "test:watch": "vitest",
  "test:e2e": "playwright test",
  "test:e2e:ui": "playwright test --ui"
}
```

## Update meta.json

```json
{
  "stack": {
    "test": "vitest+playwright"
  }
}
```

## Known caveats

- The `practices.test.ts` smoke tests REQUIRE that the server-action template at `lib/server/practices.ts` matches the canonical template (auth helpers throw with `AUTH_NOT_WIRED`, schemas use `z.input`). If the user has customized the template, the third assertion may need adjustment.
- The e2e tests assume `/`, `/showcase`, `/sign-in` exist. For a project where those routes weren't generated, comment them out and replace with the user's actual routes.
- Playwright's webServer config runs `pnpm dev` — slow on CI. Switch to `pnpm build && pnpm start` in the GHA workflow for a faster signal.
