#!/usr/bin/env -S npx tsx
// verify.ts — post-bootstrap smoke test. Exits 0 if all checks pass, 1 otherwise.
//
// Usage: npx tsx verify.ts <project-root>

import * as fs from "node:fs";
import * as path from "node:path";
import { execSync } from "node:child_process";

type Check = { name: string; run: () => boolean };

const projectRoot = process.argv[2];
if (!projectRoot) {
  console.error("Usage: verify.ts <project-root>");
  process.exit(1);
}
// Fix 1: guard against a non-existent project root (consistent with wire-nativewind.ts)
if (!fs.existsSync(projectRoot)) {
  console.error(`[verify] project root not found: ${projectRoot}`);
  process.exit(1);
}

const fileExists = (rel: string) => fs.existsSync(path.join(projectRoot, rel));

// Load package.json once at startup, not on every hasDep() call. Subsequent
// dep checks read from this cached value — avoids 11+ redundant disk reads.
type PackageJson = { dependencies?: Record<string, string>; devDependencies?: Record<string, string> };
const PKG: PackageJson | null = (() => {
  try {
    return JSON.parse(fs.readFileSync(path.join(projectRoot, "package.json"), "utf8")) as PackageJson;
  } catch {
    return null;
  }
})();
const hasDep = (name: string): boolean => {
  if (!PKG) return false;
  return Boolean(PKG.dependencies?.[name]) || Boolean(PKG.devDependencies?.[name]);
};

const checks: Check[] = [
  { name: "package.json exists", run: () => fileExists("package.json") },
  { name: "dep: expo", run: () => hasDep("expo") },
  { name: "dep: expo-router", run: () => hasDep("expo-router") },
  { name: "dep: nativewind", run: () => hasDep("nativewind") },
  { name: "dep: tailwindcss", run: () => hasDep("tailwindcss") },
  { name: "dep: zustand", run: () => hasDep("zustand") },
  { name: "dep: @tanstack/react-query", run: () => hasDep("@tanstack/react-query") },
  { name: "dep: react-native-reanimated", run: () => hasDep("react-native-reanimated") },
  { name: "dep: react-native-gesture-handler", run: () => hasDep("react-native-gesture-handler") },
  { name: "dep: react-native-safe-area-context", run: () => hasDep("react-native-safe-area-context") },
  { name: "dep: expo-image", run: () => hasDep("expo-image") },
  { name: "dep: @shopify/flash-list", run: () => hasDep("@shopify/flash-list") },
  { name: "file: app/_layout.tsx", run: () => fileExists("app/_layout.tsx") },
  { name: "file: app/index.tsx", run: () => fileExists("app/index.tsx") },
  { name: "file: global.css", run: () => fileExists("global.css") },
  { name: "file: tailwind.config.js", run: () => fileExists("tailwind.config.js") },
  { name: "file: babel.config.js", run: () => fileExists("babel.config.js") },
  { name: "file: metro.config.js", run: () => fileExists("metro.config.js") },
  { name: "file: app.json with typedRoutes", run: () => {
    const p = path.join(projectRoot, "app.json");
    if (!fileExists("app.json")) return false;
    // Fix 2: wrap JSON.parse in try/catch so malformed app.json returns false
    // instead of crashing with an unhandled exception.
    try {
      const cfg = JSON.parse(fs.readFileSync(p, "utf8"));
      return cfg?.expo?.experiments?.typedRoutes === true;
    } catch {
      return false;
    }
  }},
  { name: "tsc --noEmit passes", run: () => {
    try {
      execSync("npx tsc --noEmit", { cwd: projectRoot, stdio: "pipe" });
      return true;
    } catch {
      return false;
    }
  }},
];

let failed = 0;
for (const check of checks) {
  const ok = check.run();
  console.log(`${ok ? "✅" : "❌"} ${check.name}`);
  if (!ok) failed++;
}

if (failed > 0) {
  console.error(`\n${failed} check(s) failed.`);
  process.exit(1);
}
console.log("\nAll checks passed.");
