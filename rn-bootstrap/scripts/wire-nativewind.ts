#!/usr/bin/env -S npx tsx
// wire-nativewind.ts — generate NativeWind v4 config files from DESIGN.md tokens.
// Idempotent: overwrites the 5 generated files on every run.
//
// Usage: npx tsx wire-nativewind.ts <project-root>

import * as fs from "node:fs";
import * as path from "node:path";

type Tokens = {
  colors?: Record<string, string | Record<string, string>>;
  spacing?: Record<string, string>;
  borderRadius?: Record<string, string>;
  fontFamily?: Record<string, string[]>;
  fontSize?: Record<string, string | [string, { lineHeight?: string }]>;
};

function readDesignTokens(projectRoot: string): Tokens {
  const designPath = path.join(projectRoot, "DESIGN.md");
  if (!fs.existsSync(designPath)) {
    console.warn(`[wire-nativewind] no DESIGN.md at ${designPath}, using defaults`);
    return defaultTokens();
  }
  const md = fs.readFileSync(designPath, "utf8");
  // Convention: a fenced ```json block tagged "tokens" holds the tokens.
  // Accept CRLF (\r\n) line endings too — common on Windows-authored DESIGN.md.
  // Only the first matching block is used; additional blocks are silently ignored.
  const match = md.match(/```json tokens\r?\n([\s\S]*?)\r?\n```/);
  if (!match) {
    console.warn("[wire-nativewind] no ```json tokens block in DESIGN.md, using defaults");
    return defaultTokens();
  }
  try {
    return JSON.parse(match[1]) as Tokens;
  } catch (e) {
    console.error("[wire-nativewind] failed to parse tokens JSON:", e);
    process.exit(1);
  }
}

function defaultTokens(): Tokens {
  return {
    colors: {
      primary: "#0ea5e9",
      background: { DEFAULT: "#ffffff", dark: "#09090b" },
      foreground: { DEFAULT: "#09090b", dark: "#fafafa" },
    },
    borderRadius: { lg: "12px", md: "8px", sm: "4px" },
  };
}

function writeTailwindConfig(projectRoot: string, tokens: Tokens) {
  // Indent the JSON so its closing brace lines up with `extend:` (column 4).
  // `JSON.stringify(..., null, 2)` produces 2-space indents anchored at column 0;
  // prefix every newline with 4 spaces so the embedded block reads as part of the
  // surrounding `theme: { extend: ... }`.
  const tokensJson = JSON.stringify(tokens, null, 2).replace(/\n/g, "\n    ");
  const config = `/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{js,jsx,ts,tsx}", "./components/**/*.{js,jsx,ts,tsx}"],
  presets: [require("nativewind/preset")],
  darkMode: "class",
  theme: {
    extend: ${tokensJson},
  },
  plugins: [],
};
`;
  fs.writeFileSync(path.join(projectRoot, "tailwind.config.js"), config);
}

function writeGlobalCss(projectRoot: string) {
  fs.writeFileSync(
    path.join(projectRoot, "global.css"),
    "@tailwind base;\n@tailwind components;\n@tailwind utilities;\n",
  );
}

function writeBabelConfig(projectRoot: string) {
  fs.writeFileSync(
    path.join(projectRoot, "babel.config.js"),
    `module.exports = function (api) {
  api.cache(true);
  return {
    presets: [
      ["babel-preset-expo", { jsxImportSource: "nativewind" }],
      "nativewind/babel",
    ],
  };
};
`,
  );
}

function writeMetroConfig(projectRoot: string) {
  fs.writeFileSync(
    path.join(projectRoot, "metro.config.js"),
    `const { getDefaultConfig } = require("expo/metro-config");
const { withNativeWind } = require("nativewind/metro");

const config = getDefaultConfig(__dirname);
module.exports = withNativeWind(config, { input: "./global.css" });
`,
  );
}

function writeNativewindEnvDts(projectRoot: string) {
  // NativeWind v4 requires this ambient type declaration so JSX components have a
  // typed `className` prop. Without it, tsc fails on every NativeWind className.
  // See: https://www.nativewind.dev/v4/getting-started/typescript
  fs.writeFileSync(
    path.join(projectRoot, "nativewind-env.d.ts"),
    `/// <reference types="nativewind/types" />\n`,
  );
}

function main() {
  const projectRoot = process.argv[2];
  if (!projectRoot) {
    console.error("Usage: wire-nativewind.ts <project-root>");
    process.exit(1);
  }
  if (!fs.existsSync(projectRoot)) {
    console.error(`[wire-nativewind] project root not found: ${projectRoot}`);
    process.exit(1);
  }
  const tokens = readDesignTokens(projectRoot);
  writeTailwindConfig(projectRoot, tokens);
  writeGlobalCss(projectRoot);
  writeBabelConfig(projectRoot);
  writeMetroConfig(projectRoot);
  writeNativewindEnvDts(projectRoot);
  console.log("[wire-nativewind] wrote tailwind.config.js, global.css, babel.config.js, metro.config.js, nativewind-env.d.ts");
}

main();
