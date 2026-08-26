> Sources: https://www.nativewind.dev/docs/getting-started/installation (was `/v4/getting-started/expo-router`, which 404s since the docs restructure — checked 2026-08-26)

# NativeWind v4 setup for Expo Router

Run this *once* per project, at bootstrap time. `rn-bootstrap`'s `install-stack.sh` automates this — these are the manual steps for reference.

> ⚠️ **Tailwind version constraint**: NativeWind v4 requires `tailwindcss@^3.4.x`. **Do NOT install Tailwind 4.x** — it changed config format and NativeWind v4 cannot parse it yet. See `rn-fundamentals/references/stack-defaults.md` for the canonical version table.

## 1. Install

```bash
npm install nativewind@^4 tailwindcss@^3.4 react-native-reanimated react-native-safe-area-context
```

## 2. `tailwind.config.js`

```js
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{js,jsx,ts,tsx}", "./components/**/*.{js,jsx,ts,tsx}"],
  presets: [require("nativewind/preset")],
  theme: {
    extend: {
      // populated from DESIGN.md by rn-bootstrap/scripts/wire-nativewind.ts
      colors: {
        primary: { DEFAULT: "#0ea5e9" /* example */ },
      },
    },
  },
  plugins: [],
};
```

## 3. `global.css`

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

## 4. `babel.config.js`

```js
module.exports = function (api) {
  api.cache(true);
  return {
    presets: [
      ["babel-preset-expo", { jsxImportSource: "nativewind" }],
      "nativewind/babel",
    ],
  };
};
```

## 5. `metro.config.js`

```js
const { getDefaultConfig } = require("expo/metro-config");
const { withNativeWind } = require("nativewind/metro");

const config = getDefaultConfig(__dirname);
module.exports = withNativeWind(config, { input: "./global.css" });
```

## 6. Import the CSS in the root layout

```tsx
// app/_layout.tsx
import "../global.css";
import { Stack } from "expo-router";

export default function RootLayout() {
  return <Stack />;
}
```

## 7. Verify

```bash
npx expo start --clear
```

A `<Text className="text-2xl text-blue-500">hello</Text>` somewhere should render styled. If not, clear Metro cache: `npx expo start --clear`.

## Troubleshooting

- **Classes ignored**: check `content` glob in `tailwind.config.js` covers your files.
- **`Unable to resolve "nativewind/preset"`**: NativeWind v4 not installed. `npm ls nativewind`.
- **iOS simulator shows unstyled text**: babel cache stale. `rm -rf node_modules/.cache && npx expo start --clear`.
- **`Cannot read property 'config' of undefined`** or other parse errors: you probably installed Tailwind 4 by accident. Run `npm ls tailwindcss` — must be `3.4.x`.
