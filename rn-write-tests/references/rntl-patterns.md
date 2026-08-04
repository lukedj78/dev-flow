> Sources: https://callstack.github.io/react-native-testing-library/ (v14 docs), tanstack.com/query testing guide.

# Patterns — React Native Testing Library

## ⚠️ v14 — the core API is async

RNTL **v14** (2026-06-05, `latest` = 14.0.1) adopts React 19's async rendering model. `render`, `renderHook`, `fireEvent` and `act` **all return Promises and must be awaited** — as do `rerender()` and `unmount()`. Every example below is written in the awaited form; a non-awaited call silently asserts against an unrendered tree.

Also in v14:
- **New peer dep `test-renderer@^1`** — `react-test-renderer` was dropped (see `jest-setup.md`). Node `^22.13 || >=24`, React ≥ 19, RN ≥ 0.78.
- **Removed**: the `UNSAFE_*` queries (`UNSAFE_getByType`, `UNSAFE_getAllByType`, `UNSAFE_getByProps`, `UNSAFE_getAllByProps`), `UNSAFE_root` (→ `container` / `root`), `createNodeMock`, `concurrentRoot`, `unstable_validateStringsRenderedWithinText` (validation is always on now), `update` (→ `rerender`), `getQueriesForElement` (→ `within`), and the v13.3 `renderAsync` / `renderHookAsync` / `fireEventAsync` (the plain names are async now).
- Unknown options passed to `render` / `renderHook` / `configure` now log a warning — useful for catching leftovers.

Migrating an existing suite? Two codemods do most of it:

```bash
npx codemod@latest rntl-v14-update-deps --target . && npm install
npx codemod@latest rntl-v14-async-functions --target ./src
```

If you use a custom render helper, tell the second codemod about it so it awaits those calls too:

```bash
npx codemod@latest rntl-v14-async-functions --target ./src \
  --param customRenderFunctions="renderWithProviders"
```

## Render a screen with QueryClient

The biggest pitfall in RN tests: components that use TanStack Query need a `QueryClientProvider` in the test tree.

```tsx
// __tests__/helpers/render.tsx
import { render as rtlRender, RenderOptions } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactElement } from "react";

export async function renderWithProviders(ui: ReactElement, options?: RenderOptions) {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, staleTime: Infinity },
      mutations: { retry: false },
    },
  });
  return rtlRender(<QueryClientProvider client={client}>{ui}</QueryClientProvider>, options);
}
```

`retry: false` + `staleTime: Infinity` make tests deterministic: no background retries, no unexpected refetches.

The helper is `async` because `render` is async in v14 — **every call site must `await renderWithProviders(...)`**.

## Component test (assertions, interactions)

```tsx
// __tests__/components/PostCard.test.tsx
import { fireEvent, screen } from "@testing-library/react-native";
import { renderWithProviders } from "../helpers/render";
import { PostCard } from "@/components/PostCard";

describe("PostCard", () => {
  it("renders title and author", async () => {
    await renderWithProviders(
      <PostCard post={{ id: "1", title: "Hello", author: "alice" }} onPress={jest.fn()} />,
    );
    expect(screen.getByText("Hello")).toBeOnTheScreen();
    expect(screen.getByText(/alice/)).toBeOnTheScreen();
  });

  it("calls onPress when tapped", async () => {
    const onPress = jest.fn();
    await renderWithProviders(
      <PostCard post={{ id: "1", title: "Hello", author: "alice" }} onPress={onPress} />,
    );
    await fireEvent.press(screen.getByText("Hello"));
    expect(onPress).toHaveBeenCalledWith("1");
  });
});
```

Note the tests are `async` and every `renderWithProviders` / `fireEvent` call is awaited — that is the v14 contract, not a stylistic choice. Queries (`getBy*` / `findBy*`) stay synchronous and still come from the imported `screen`.

**Queries** (prefer in this order — most accessible first):
- `getByRole("button", { name: /save/i })` — when a11y is set up.
- `getByText("...")` — visible text.
- `getByPlaceholderText("Email")` — inputs.
- `getByLabelText("Email")` — when `accessibilityLabel` is set.
- `getByTestId("submit-btn")` — last resort, when nothing else uniquely identifies the node.

**Async**: `await screen.findByText("…")` when the element appears after a state change.

## Mock a useQuery

```tsx
// __tests__/screens/Posts.test.tsx
import { screen } from "@testing-library/react-native";
import { renderWithProviders } from "../helpers/render";
import PostsScreen from "@/app/posts/index";
import { api } from "@/lib/api";

jest.mock("@/lib/api");
const mockedApi = api as jest.MockedFunction<typeof api>;

describe("PostsScreen", () => {
  beforeEach(() => mockedApi.mockReset());

  it("renders the list once the query resolves", async () => {
    mockedApi.mockResolvedValueOnce([
      { id: "1", title: "First", author: "alice" },
      { id: "2", title: "Second", author: "bob" },
    ]);

    await renderWithProviders(<PostsScreen />);

    expect(await screen.findByText("First")).toBeOnTheScreen();
    expect(screen.getByText("Second")).toBeOnTheScreen();
  });

  it("shows an error state on failure", async () => {
    mockedApi.mockRejectedValueOnce(new Error("boom"));

    await renderWithProviders(<PostsScreen />);

    expect(await screen.findByText(/could not load/i)).toBeOnTheScreen();
  });
});
```

## Hook test with `renderHook`

```tsx
// __tests__/lib/queries/usePosts.test.ts
import { renderHook, waitFor } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { usePosts } from "@/lib/queries/usePosts";
import { api } from "@/lib/api";
import { ReactNode } from "react";

jest.mock("@/lib/api");
const mockedApi = api as jest.MockedFunction<typeof api>;

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

it("fetches posts", async () => {
  mockedApi.mockResolvedValueOnce([{ id: "1", title: "Hi", author: "alice" }]);

  const { result } = await renderHook(() => usePosts(), { wrapper });

  await waitFor(() => expect(result.current.isSuccess).toBe(true));
  expect(result.current.data).toHaveLength(1);
});
```

`renderHook` resolves to `{ result: { current: Result }, rerender, unmount }` — `result.current` is unchanged from v13, but the call itself is awaited and both `rerender(props)` and `unmount()` now return Promises (`await rerender(5)`, `await unmount()`). If the hook you're testing exposes a state-mutating function, wrap the call in `await act(() => result.current.increment())`.

## Mock Expo modules

For each Expo module a test touches, mock it at the top of the file or in `jest.setup.ts`:

```ts
jest.mock("expo-router", () => ({
  useRouter: () => ({ push: jest.fn(), back: jest.fn(), replace: jest.fn() }),
  useLocalSearchParams: () => ({ id: "test-id" }),
  Link: ({ children }: { children: React.ReactNode }) => children,
  Stack: ({ children }: { children: React.ReactNode }) => children,
}));

jest.mock("expo-notifications", () => ({
  requestPermissionsAsync: jest.fn(() => Promise.resolve({ status: "granted" })),
  scheduleNotificationAsync: jest.fn(),
  setNotificationHandler: jest.fn(),
}));

jest.mock("expo-image", () => ({
  Image: "Image", // simple string ref, RN treats it as a native component
}));
```

Put commonly-used Expo mocks in `jest.setup.ts` so every test gets them.

## Anti-patterns

- ❌ Asserting on internal state (`expect(component.state.loading).toBe(true)`) — test user-visible output.
- ❌ Wrapping every test in `act` manually — `render` / `fireEvent` / `renderHook` already use async `act` internally. Reach for `act` only to drive a function the hook returned, and then `await` it.
- ❌ Calling `render` / `fireEvent` / `renderHook` without `await` (v14) — assertions run against an unrendered or stale tree.
- ❌ `UNSAFE_getByType` / `UNSAFE_getByProps` — removed in v14 (Test Renderer only renders host elements). Use `getByRole` / `getByText` / `getByTestId`.
- ❌ Using `setTimeout` + `done` — use `waitFor`.
- ❌ Snapshot test on a screen — it churns. Use targeted assertions.
- ❌ Forgetting `mockReset` between tests when reusing a mock — leakage.

## Recommended assertions

Native matchers are built into `@testing-library/react-native` (v12.4+) — no separate import needed. Use these instead of generic equivalents:

```ts
expect(node).toBeOnTheScreen();
expect(node).toBeDisabled();
expect(node).toHaveTextContent(/welcome/i);
expect(node).toHaveStyle({ opacity: 0.5 });
```
