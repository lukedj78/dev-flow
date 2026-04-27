# write-tests → component (Vitest + React Testing Library)

Components live at `components/<group>/<name>.tsx` (e.g., `components/site/site-top-nav.tsx`). Their tests use Vitest + RTL with `userEvent` for interactions. Tests run in `jsdom`, not a real browser — anything that depends on real DOM measurement (canvas, intersection observer, ResizeObserver) needs explicit mocks.

## Test file location

Two valid conventions — match what the project already does:

- **Co-located**: `components/<group>/<name>.test.tsx` (next to source). Easier to keep in sync.
- **`__tests__` folder**: `components/<group>/__tests__/<name>.test.tsx`. Cleaner at scale.

Default to **co-located** for new tests if no convention is established yet — fewer paths to remember.

## Canonical shape

```typescript
import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

// `next/navigation` is already mocked globally in vitest.setup.ts.
// Override per-test only when asserting on router calls.

import { SiteTopNav } from "../site-top-nav";

describe("SiteTopNav", () => {
  it("renders the logo and primary nav links", () => {
    render(<SiteTopNav />);
    expect(screen.getByRole("link", { name: /home/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /about/i })).toBeInTheDocument();
  });

  it("highlights the active route", () => {
    // The component reads `usePathname()` from next/navigation.
    // Override the global mock for this test.
    vi.doMock("next/navigation", () => ({
      usePathname: () => "/about",
      useRouter: () => ({ push: vi.fn() }),
    }));

    render(<SiteTopNav />);
    const aboutLink = screen.getByRole("link", { name: /about/i });
    expect(aboutLink).toHaveAttribute("aria-current", "page");
  });

  it("opens the mobile menu on burger click", async () => {
    const user = userEvent.setup();
    render(<SiteTopNav />);

    const burger = screen.getByRole("button", { name: /menu/i });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    await user.click(burger);
    expect(await screen.findByRole("dialog")).toBeInTheDocument();
  });

  it("calls onSearch when the user types and presses Enter", async () => {
    const user = userEvent.setup();
    const onSearch = vi.fn();

    render(<SiteTopNav onSearch={onSearch} />);
    const input = screen.getByLabelText(/search/i);

    await user.type(input, "compravendita");
    await user.keyboard("{Enter}");

    expect(onSearch).toHaveBeenCalledWith("compravendita");
  });
});
```

## What to cover (per component)

A component test is about the **prop surface** + **interactive behavior**. Cover:

1. **Render with default props** — does it mount without throwing? Are the visible parts visible?
2. **One assertion per public prop** — for props that affect rendering (`variant`, `size`, `disabled`), one `it()` per non-trivial value.
3. **One assertion per interactive state** — clicking opens, toggling flips, submitting calls. **userEvent**, not `fireEvent` — `userEvent` simulates real interaction (focus events, key sequences).
4. **One assertion per conditional render branch** — `if (loading)`, `if (error)`, `if (items.length === 0)`. Each gets one `it()`.
5. **One accessibility check** — does the interactive element have an accessible name? (`screen.getByRole("button", { name: /.../ })` will fail if not.) RTL forces this naturally.

## What NOT to cover

- **Implementation details** — `useState` calls, hook return shapes, internal helper functions. Test the rendered output and the side effects, not the wiring.
- **Style values** — don't assert `expect(el).toHaveStyle({ color: "red" })`. Visual regression tools handle this; brittle.
- **Children rendering** — a `<Card>` rendering its `children` is React's job, not yours. Test that `<Card title="Foo">` renders "Foo", not that `<Card>{...}</Card>` renders the children.

## Server vs Client components

- **Server Components** (no `"use client"` at top): test with **e2e** (Playwright), not RTL. RTL doesn't render RSC correctly without aggressive mocking.
- **Client Components** (`"use client"`): test with RTL.
- **Mixed** (RSC that imports a Client Component): test the Client Component directly with RTL; test the RSC integration via e2e.

If you're unsure whether a component is RSC or Client, look at the top of the file:
- `"use client"` → Client → RTL.
- No directive → RSC → Playwright.

## Common interactive patterns

### Form input + submit

```typescript
const user = userEvent.setup();
const onSubmit = vi.fn();
render(<ContactForm onSubmit={onSubmit} />);

await user.type(screen.getByLabelText(/email/i), "user@example.com");
await user.type(screen.getByLabelText(/message/i), "ciao");
await user.click(screen.getByRole("button", { name: /send/i }));

expect(onSubmit).toHaveBeenCalledWith({
  email: "user@example.com",
  message: "ciao",
});
```

### Async data (component fetches on mount)

```typescript
import { vi } from "vitest";

vi.spyOn(global, "fetch").mockResolvedValueOnce({
  ok: true,
  json: () => Promise.resolve({ items: [{ id: 1, name: "Foo" }] }),
} as Response);

render(<DashboardWidget />);

// Wait for the async render — RTL has `findBy*` for this.
expect(await screen.findByText("Foo")).toBeInTheDocument();
```

### Component that uses a Context provider

```typescript
import { ThemeProvider } from "@/components/site/theme-provider";

function renderWithTheme(ui: React.ReactElement) {
  return render(
    <ThemeProvider attribute="class" defaultTheme="light">{ui}</ThemeProvider>
  );
}

it("renders correctly inside ThemeProvider", () => {
  renderWithTheme(<ModeToggle />);
  expect(screen.getByRole("button", { name: /toggle theme/i })).toBeInTheDocument();
});
```

## Mocking `next/navigation` per-test

The global mock in `vitest.setup.ts` returns a default. To override:

```typescript
import { useRouter } from "next/navigation";

it("navigates after successful submit", async () => {
  const push = vi.fn();
  vi.mocked(useRouter).mockReturnValue({
    push,
    replace: vi.fn(),
    refresh: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    prefetch: vi.fn(),
  } as ReturnType<typeof useRouter>);

  // ... render + interact ...

  expect(push).toHaveBeenCalledWith("/clienti");
});
```

## Common pitfalls

- **Forgetting `userEvent.setup()`**: calling `userEvent.click(...)` directly (the legacy API) causes weird race conditions. Always `const user = userEvent.setup()` at the top of the test or in a `beforeEach`.
- **`getBy*` instead of `findBy*` for async**: `getBy*` throws synchronously if the element isn't there yet. Use `findBy*` (returns a Promise) for elements that appear after a network call or animation.
- **Asserting on shadcn primitive internals**: `<Dialog>` uses Radix's portal, so the dialog content lives at `document.body` not inside the test container. RTL's `screen.getByRole(...)` searches the whole document — use that, not `container.querySelector(...)`.
- **Snapshot tests by default**: don't auto-write `expect(container).toMatchSnapshot()`. Snapshots rot. Specific assertions instead.
- **`act()` warnings**: if you see `Warning: An update to X inside a test was not wrapped in act(...)`, you're missing an `await` on a state update. RTL queries already wrap in `act`, so 99% of the time the fix is `await user.click(...)` not `user.click(...)`.
