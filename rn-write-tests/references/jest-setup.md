> Sources: https://docs.expo.dev/develop/unit-testing/, jest-expo README, internal opinion.
> **Verified 2026-08-26** against `@testing-library/react-native@14.0.1`, whose `package.json` states
> every claim below in one place: `peerDependencies` = `jest >=29.0.0`, `react >=19.0.0`,
> `react-native >=0.78`, **`test-renderer ^1.0.0`**; `engines.node` = **`^22.13.0 || >=24`**.
> `test-renderer` is a real package (latest `1.2.0`, peer `react ^19.0.0`), published as `1.0.0` /
> `1.1.0` / `1.2.0` — one line per React 19 minor, exactly as described below.
> ⚠️ **Only `jest-expo` is pinned by the SDK** (`~57.0.4` in `expo@57.0.16`'s `bundledNativeModules`);
> `jest`, `@testing-library/react-native` and `test-renderer` are **not**, so `npx expo install` hands
> you npm `latest` for those three. That is why the version ranges above are written by hand.

# Jest + React Native Testing Library setup for Expo

Run this once per project, on the first call of `rn-write-tests`.

## 1. Install

```bash
npx expo install --dev \
  jest jest-expo \
  @testing-library/react-native@^14 \
  test-renderer@^1 \
  @types/jest -- --legacy-peer-deps
```

- **`test-renderer@^1` is a required peer dependency of RNTL v14** — it replaces the deprecated `react-test-renderer`, which was dropped. If the project still has `react-test-renderer` / `@types/react-test-renderer`, remove them.
- Pick the `test-renderer` line that matches your React 19 minor: `1.2` for React 19.2, `1.1` for 19.1, `1.0` for 19.0. A newer line than your React version produces peer warnings (or an install error on npm); an older line blocks newer React 19 features in tests.
- **Node `^22.13 || >=24` is required** by RNTL v14 (along with React ≥ 19 and RN ≥ 0.78). CI images pinned to Node 20 will fail to install — bump the runner before pinning the dep.
- Native matchers like `toBeOnTheScreen()` are built into `@testing-library/react-native` v12.4+; the standalone `@testing-library/jest-native` package is deprecated and no longer needed.

⚠️ RNTL v14 made `render`, `renderHook`, `fireEvent` and `act` **async** — see the v14 section at the top of `rntl-patterns.md` before writing (or migrating) any test.

## 2. `package.json` — add jest config + script

```json
{
  "scripts": {
    "test": "jest"
  },
  "jest": {
    "preset": "jest-expo",
    "transformIgnorePatterns": [
      "node_modules/(?!((jest-)?react-native|@react-native(-community)?|expo(nent)?|@expo(nent)?/.*|@expo-google-fonts/.*|react-navigation|@react-navigation/.*|@unimodules/.*|unimodules|sentry-expo|native-base|react-native-svg|nativewind))"
    ],
    "setupFilesAfterEnv": ["<rootDir>/jest.setup.ts"],
    "moduleNameMapper": {
      "^@/(.*)$": "<rootDir>/$1"
    }
  }
}
```

The `transformIgnorePatterns` is the standard jest-expo recipe; keep it verbatim. NativeWind is added at the end (it ships ESM and needs transform).

## 3. `jest.setup.ts` — global mocks + matchers

```ts
// Reanimated 4's recommended test setup
require("react-native-reanimated").setUpTests();

// Mock NativeWind colorScheme (not reactive in tests)
jest.mock("nativewind", () => ({
  useColorScheme: () => ({ colorScheme: "light", setColorScheme: jest.fn() }),
}));

// Silence specific noisy warnings if needed
const originalWarn = console.warn;
console.warn = (...args: unknown[]) => {
  if (typeof args[0] === "string" && args[0].includes("useNativeDriver")) return;
  originalWarn(...args);
};
```

## 4. (Optional) tsconfig path

```json
{
  "compilerOptions": {
    "types": ["jest"]
  }
}
```

## 5. Smoke test

Create `__tests__/smoke.test.ts`:

```ts
test("smoke", () => {
  expect(1 + 1).toBe(2);
});
```

Run:

```bash
npm test -- --runInBand
```

Expected: 1 test pass.

## 6. Pure function test (example)

```ts
// lib/format.ts
export function formatPrice(cents: number, currency = "EUR"): string {
  return new Intl.NumberFormat("it-IT", { style: "currency", currency }).format(cents / 100);
}

// __tests__/lib/format.test.ts
import { formatPrice } from "@/lib/format";

describe("formatPrice", () => {
  it("formats EUR by default", () => {
    expect(formatPrice(1999)).toContain("19,99");
  });

  it("respects the currency arg", () => {
    expect(formatPrice(1999, "USD")).toMatch(/USD|US\$/);
  });
});
```

## Common pitfalls

- **`SyntaxError: Unexpected token 'export'`** when importing a node_modules package → add the package name to `transformIgnorePatterns` (last segment after `nativewind`).
- **Async warnings** about React state updates → you probably forgot to `await` a `render` / `fireEvent` / `renderHook` call (v14 made them async). Otherwise use `waitFor`, or `await act(...)`.
- **`Invariant Violation: Text strings must be rendered within a <Text> component`** → v14 always enforces this (the `unstable_validateStringsRenderedWithinText` opt-out was removed). Fix the component; it would fail at runtime too.
- **`useNativeDriver` warnings spam** → silenced by the setup file above.
- **`window is not defined`** → you're testing a node-only file with the wrong env. Set `/** @jest-environment node */` at the top.
