> Sources: synthesized from jest-expo, RNTL guides, Maestro docs.

# Decision tree — what to test, how

## Q1: Which testing tool?

```
What am I testing?
├── A pure function / utility       → plain Jest
├── A hook in isolation             → RNTL renderHook
├── A single component              → RNTL render + fireEvent
├── A whole screen (with data)      → RNTL render + mocked queryFn
├── A flow across multiple screens  → Maestro e2e
└── Native module / device behavior → Maestro e2e
```

## Q2: How deep should the test go?

```
What's the risk if this breaks?
├── Catastrophic (auth, payments)        → unit + integration + e2e
├── Important (core flow)                → unit + integration
├── Minor (rarely-used screen)           → smoke integration only
└── Trivial (presentational component)   → maybe one render test, often skip
```

100% coverage is a metric, not a goal. Test what you'd be sad to ship broken.

## Q3: Mock the network or use MSW?

```
For Wave 2 we mock at the `api()` function boundary (one level above fetch).
- Simpler than MSW.
- No service worker setup.
- Easy to swap to MSW later if you want HTTP-level mocking.

Pattern:
  jest.mock("@/lib/api");
  mockedApi.mockResolvedValueOnce(fixtureData);
```

When you want HTTP-level mocking (e.g. testing the api() function itself), use `nock` or vanilla `fetch` mocking via `global.fetch = jest.fn()`.

## Q4: Snapshot tests — when?

```
Component is part of a stable design system?
├── YES → one snapshot per variant. Update intentionally on design change.
└── NO  → NEVER. Snapshots of pages/screens churn on every change.
```

If you add snapshots, add `npm run test:update-snapshots` to scripts and document the intent.

## Q5: Where do test files go?

```
Test scope?
├── Unit / Integration → __tests__/<mirror-source-path>.test.tsx
│                        e.g. components/PostCard.tsx → __tests__/components/PostCard.test.tsx
└── e2e Maestro        → .maestro/<flow-name>.yaml
```

Some teams prefer co-located `<source>.test.tsx`. We pick `__tests__/` to keep source files tidy and to make test discovery trivial.

## Q6: Should the test mock TanStack Query itself?

```
Almost never.

- To test a screen that uses useQuery: render with a real QueryClient
  (retry:false, staleTime:Infinity) and mock the api() function it calls.
- To test the QueryClientProvider setup: don't — it's third-party code.
- To test a custom hook that wraps useQuery: render with QueryClientProvider
  and mock api(). Assert on the hook's returned object.

The ONE exception: testing your application's QueryClient config (defaults,
retry policies) — there a thin integration test against a real client.
```

## Q7: How do I test navigation?

```
Action      → tool
-----------------------------------------------------------------
Push button → RNTL: assert that router.push was called with right args
              (mock useRouter; assert on the mock).

Real nav    → Maestro: actually navigate and assert post-nav screen
              has expected content.
```

Mocked `useRouter` lets you test "did we call push correctly?" in isolation. Maestro tests "does the user actually arrive on the right screen?". They are complementary, not redundant.

## Q8: How fast should the test suite be?

```
Phase        → budget
-----------------------------------------------------------------
PR check     → < 60 sec for the unit/integration tier
              (run e2e on merge, not PR — too slow)
nightly      → full e2e on multiple devices via maestro cloud
```

If unit tests exceed 60 sec for a small app, you're testing too much UI in one file or you forgot `retry:false` on the query client.
