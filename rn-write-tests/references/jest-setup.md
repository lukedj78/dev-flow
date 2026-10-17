> Sources: https://docs.expo.dev/develop/unit-testing/, jest-expo README, internal opinion.
> **Verified 2026-08-26** against `@testing-library/react-native@14.0.1`, whose `package.json` states
> every claim below in one place: `peerDependencies` = `jest >=29.0.0`, `react >=19.0.0`,
> `react-native >=0.78`, **`test-renderer ^1.0.0`**; `engines.node` = **`^22.13.0 || >=24`**.
> `test-renderer` is a real package (latest `1.2.0`, peer `react ^19.0.0`), published as `1.0.0` /
> `1.1.0` / `1.2.0` — one line per React 19 minor, exactly as described below.
> ⚠️ **Only `jest-expo` is pinned by the SDK** (and `@react-native/jest-preset` is not either — see §1) (`~58.0.11` in `expo@58.0.14`'s `bundledNativeModules`);
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

# jest-expo declares `@react-native/jest-preset` as a peer (58: `^0.88.0`), and that package is
# NOT in the SDK's bundledNativeModules — so `expo install` hands you npm latest, which breaks as
# soon as it is a minor ahead of the project's RN (SDK 57, 2026-09-08: 0.87.1 against RN 0.86).
# Pin it to the React Native version the project actually has:
RN_VERSION="$(node -p "require('react-native/package.json').version")"
npm install --save-dev --legacy-peer-deps "@react-native/jest-preset@${RN_VERSION}"
```

- **`@react-native/jest-preset` must match the React Native minor.** jest-expo lists it as a peer (58: `^0.88.0` — `npm view jest-expo@58 peerDependencies`; 57 said `^0.86.3`), but peers are not installed under `--legacy-peer-deps`, and the package is not SDK-pinned, so `npx expo install` picks npm `latest`. On 2026-09-08 that was `0.87.1` against RN `0.86.3`: its `jest/setup.js` mocks `react-native/setup-env`, a file that only exists from RN 0.87, so every suite fails before running. The `RN_VERSION` line above resolves the exact match; re-run it after every `rn-upgrade`. On 2026-10-17 npm `latest` happens to equal SDK 58's RN (`0.88.0`); the pin is what keeps it so when 0.89 ships.
- **`test-renderer@^1` is a required peer dependency of RNTL v14** — it replaces the deprecated `react-test-renderer`, which was dropped. If the project still has `react-test-renderer` / `@types/react-test-renderer`, remove them.
- Pick the `test-renderer` line that matches your React 19 minor: `1.3` for React 19.3 (SDK 58), `1.2` for React 19.2, `1.1` for 19.1, `1.0` for 19.0. A newer line than your React version produces peer warnings (or an install error on npm); an older line blocks newer React 19 features in tests.
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
    "resolver": "react-native-reanimated/jest/resolver",
    "setupFilesAfterEnv": ["<rootDir>/jest.setup.ts"],
    "moduleNameMapper": {
      "^@/(.*)$": "<rootDir>/$1"
    }
  }
}
```

The `transformIgnorePatterns` is the standard jest-expo recipe; keep it verbatim. NativeWind is added at the end (it ships ESM and needs transform).

⚠️ **`resolver` is required from Reanimated 4.7 (SDK 58).** Without it `setUpTests()` in `jest.setup.ts` crashes every suite with *"Cannot read properties of undefined (reading 'loadUnpackersWithCode')"*: Jest resolves the worklets runtime's `.native.ts` files, which call a native module that does not exist in Node. `react-native-reanimated/jest/resolver` (shipped since 4.7.0, absent in 4.5.1 and 4.6.0) sends Reanimated's and Worklets' own internals to their web implementations and leaves everything else to Jest's default resolver. Do not use `react-native-worklets/jest/resolver` alone: it fails later with *"`runOnUISync` is not supported on web"*. Verified 2026-10-17 on a fresh SDK 58 app (expo 58.0.14, RN 0.88.0, reanimated 4.7.1, worklets 0.13.0, jest-expo 58.0.11, jest 30.5): smoke test and an RNTL v14 render test pass.

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

## 4. tsconfig `types` (required on TypeScript 6)

The SDK 57 and 58 templates ship TypeScript 6, and `expo/tsconfig.base` sets no `types`. Without this line jest runs green but `tsc --noEmit` fails on every test file (*"Cannot find name 'test'"*, TS2593) and on `jest.setup.ts` — so does `rn-bootstrap`'s `verify.ts`. Re-checked 2026-10-17 on a fresh SDK 58 app.

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
