> Sources: https://docs.expo.dev/develop/unit-testing/, jest-expo README, internal opinion.

# Jest + React Native Testing Library setup for Expo

Run this once per project, on the first call of `rn-write-tests`.

## 1. Install

```bash
npx expo install --dev \
  jest jest-expo \
  @testing-library/react-native \
  @testing-library/jest-native \
  @types/jest -- --legacy-peer-deps
```

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
import "@testing-library/jest-native/extend-expect";

// Silence Reanimated worklets warnings in tests
jest.mock("react-native-reanimated", () => require("react-native-reanimated/mock"));

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
    "types": ["jest", "@testing-library/jest-native"]
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
- **Async warnings** about React state updates → wrap in `act` or use `waitFor`.
- **`useNativeDriver` warnings spam** → silenced by the setup file above.
- **`window is not defined`** → you're testing a node-only file with the wrong env. Set `/** @jest-environment node */` at the top.
