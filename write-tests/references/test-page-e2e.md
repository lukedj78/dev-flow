# write-tests → page (Playwright e2e)

Pages live at `app/<route>/page.tsx`. Their tests are full-browser flows in `e2e/<route-slug>.spec.ts`. Playwright runs against `pnpm dev` (or `pnpm build && pnpm start` in CI per `playwright.config.ts`).

## Test file location

`e2e/<route-slug>.spec.ts` — flat, not nested. Slug derives from the route:

| Route | Slug | File |
|---|---|---|
| `/` | `home` | `e2e/home.spec.ts` |
| `/clienti` | `clienti` | `e2e/clienti.spec.ts` |
| `/clienti/[id]` | `clienti-detail` | `e2e/clienti-detail.spec.ts` |
| `/book-session/checkout` | `book-checkout` | `e2e/book-checkout.spec.ts` |

## Canonical shape

```typescript
import { test, expect } from "@playwright/test";

test.describe("Clienti page", () => {
  test("loads and shows the heading", async ({ page }) => {
    await page.goto("/clienti");
    await expect(page.locator("h1")).toContainText(/clienti/i);
  });

  test("renders the new-client CTA", async ({ page }) => {
    await page.goto("/clienti");
    const cta = page.getByRole("link", { name: /nuovo cliente/i });
    await expect(cta).toBeVisible();
    await expect(cta).toHaveAttribute("href", "/clienti/nuovo");
  });

  test("clicking a row navigates to the detail page", async ({ page }) => {
    await page.goto("/clienti");
    // Click the first row's link. The exact selector depends on the page —
    // prefer accessible roles + names over CSS selectors when possible.
    const firstRow = page.getByRole("row").nth(1);
    const firstLink = firstRow.getByRole("link").first();
    const href = await firstLink.getAttribute("href");
    await firstLink.click();
    await expect(page).toHaveURL(new RegExp(`^${href}$`));
  });

  test("empty state shows the right message when no clients exist", async ({ page }) => {
    // This requires either a deterministic test DB (one option) or a route
    // param to force-render the empty state. If neither is wired, mark
    // the test as todo with a comment.
    test.skip(
      true,
      "No empty-state route. Wire `?empty=1` query param OR seed a deterministic test DB."
    );
  });

  test("respects dark-mode toggle without flashing", async ({ page }) => {
    await page.goto("/clienti");
    const html = page.locator("html");
    await expect(html).not.toHaveClass(/dark/);
    await page.keyboard.press("d");
    await expect(html).toHaveClass(/dark/);
  });
});
```

## What to cover (per page)

A page e2e test is **not** a unit test. Don't try to cover every branch — a page has many. Cover the **user-visible contract**:

1. **Page loads** — `await page.goto(...)` resolves and an `h1` is visible. This catches build failures and 500s.
2. **Primary content** — the page's headline / hero / first card / nav lands on screen with the expected text.
3. **One primary CTA** — the most important action button/link is visible and points where it should.
4. **One interaction** — the most important user flow (e.g., "click row → navigate to detail", "submit form → see success state"). NOT all flows. ONE.
5. **One responsive check (optional)** — if the page has critical mobile-only behavior, add a `test.use({ viewport: { width: 375, height: 667 } })` block with one assertion.

If the page is a list/index (`/clienti`, `/scadenze`):
- Add a test that the empty state renders correctly.
- Add a test that the primary "create new" CTA is visible.

If the page is a detail page (`/clienti/[id]`):
- Add a test using a known seeded id (`/clienti/test-fixture-1`) — assert title + breadcrumb.
- Add a test for the 404 path: `page.goto("/clienti/does-not-exist")` should show the not-found UI.

If the page has a form (`/clienti/nuovo`, `/contact`):
- Add a test that submitting valid input lands on a success state.
- Add a test that submitting empty input shows validation errors.

## What NOT to cover in e2e

- **Server-action logic** — that's `test-server-action.md`. The e2e only confirms the action is reachable and returns SOMETHING. Logic branches are unit-tested.
- **Component-level prop interactions** — that's `test-component.md`.
- **Visual exactness** — Playwright has `toHaveScreenshot()` but it's brittle. Skip it unless the user asks. Prefer text + role assertions.
- **Auth flows themselves** — login / signup / forgot-password e2e is its own dedicated suite, not piggybacked on every page test. Mark `test.skip` with a TODO if needed.

## Selectors — preference order

1. `getByRole(role, { name })` — accessible, breaks only if the contract changes.
2. `getByLabel(...)` — for form inputs.
3. `getByText(/regex/i)` — for non-interactive copy.
4. `getByTestId('...')` — only when nothing else works. Add `data-testid` to the source code reluctantly.
5. CSS selectors (`page.locator(".foo > .bar")`) — last resort. They couple the test to the styling.

## Auth-aware tests

If the page requires auth, three options (in order of preference):

1. **Storage state**: log in once in `playwright/global-setup.ts`, save cookies, reuse across tests. Add a `storageState: "playwright/.auth/user.json"` to `playwright.config.ts`.
2. **Test fixture**: create a dedicated `loggedInPage` fixture that handles login.
3. **Skip until auth-test-fixture is wired**: `test.skip(true, "Auth fixture not yet set up. Add storageState in playwright/global-setup.ts.")` — honest, surfaces the gap.

Do NOT do option 4: log in via UI inside every test. Slow, brittle.

## Data dependencies — three patterns

E2E tests need data. Three strategies:

1. **Seeded test DB** (best): a `test-seed.sql` or `test-seed.ts` runs before e2e against a separate test DB. The test asserts against known fixtures (`/clienti/seed-client-1`).
2. **API mocks via `page.route()`**: intercept network calls and return canned responses. Works for client-fetched data, not RSC.
3. **Live dev DB** (worst): tests assert against whatever happens to be in the dev DB. Brittle. Avoid.

Default to (1) when `module-add db` has run AND a test seed exists. Fall back to (3) only for "smoke" tests where the assertion is structural (`h1 visible`, not `h1 contains specific text`).

## Common pitfalls

- **Hardcoding IDs that don't exist**: `page.goto("/clienti/42")` works in dev but not on a freshly-seeded CI DB. Use a deterministic seed slug (`/clienti/seed-mario-rossi`) and a setup script.
- **Asserting on text that's locale-specific**: if the project supports IT + EN, assertions on `"Clienti"` break in EN mode. Use accessible roles + regex (`/clients?/i`) or test only in one locale and document it.
- **Network race conditions**: a page that fetches data on the client may not have the data rendered yet when assertions fire. Use `page.waitForResponse(...)` before asserting on fetched content, or `page.waitForLoadState("networkidle")` for the conservative approach.
- **Skipping `webServer`**: forgetting that `playwright.config.ts` needs `webServer: { command: "pnpm dev", ... }` means tests run against nothing. Already configured by `module-add test`; only an issue if the user customized.
