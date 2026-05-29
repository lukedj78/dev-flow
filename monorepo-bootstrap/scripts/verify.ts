#!/usr/bin/env -S npx tsx
// verify.ts — post-monorepo-bootstrap verification
// Checks that the scaffolded turborepo monorepo has every required file in
// place and that the workspace topology is sane.
//
// Exits 0 if everything passes, 1 otherwise.
//
// Usage: npx tsx verify.ts <project-root>

import * as fs from "node:fs";
import * as path from "node:path";

type Check = { name: string; run: () => boolean };

const projectRoot = process.argv[2];
if (!projectRoot) {
  console.error("Usage: verify.ts <project-root>");
  process.exit(1);
}

const fileExists = (rel: string) => fs.existsSync(path.join(projectRoot, rel));
const dirExists = (rel: string) => {
  const full = path.join(projectRoot, rel);
  return fs.existsSync(full) && fs.statSync(full).isDirectory();
};

function readJson(rel: string): Record<string, unknown> | null {
  try {
    return JSON.parse(fs.readFileSync(path.join(projectRoot, rel), "utf8"));
  } catch {
    return null;
  }
}

function readMeta(): { stack?: { monorepo?: any } } | null {
  return readJson(".workflow/meta.json") as { stack?: { monorepo?: any } } | null;
}

const meta = readMeta();
const slug = (() => {
  if (!meta) return null;
  const pkg = readJson("package.json") as { name?: string } | null;
  if (pkg && typeof pkg.name === "string" && pkg.name.startsWith("@")) {
    return pkg.name.slice(1).split("/")[0];
  }
  return null;
})();

const checks: Check[] = [
  // Root files
  { name: "root: pnpm-workspace.yaml exists", run: () => fileExists("pnpm-workspace.yaml") },
  { name: "root: turbo.json exists", run: () => fileExists("turbo.json") },
  { name: "root: package.json exists", run: () => fileExists("package.json") },
  { name: "root: tsconfig.base.json exists", run: () => fileExists("tsconfig.base.json") },
  { name: "root: .gitignore exists", run: () => fileExists(".gitignore") },

  // apps/web
  { name: "apps/web: directory exists", run: () => dirExists("apps/web") },
  { name: "apps/web: package.json exists", run: () => fileExists("apps/web/package.json") },
  {
    name: "apps/web: tailwind.config.{js,ts} references design preset",
    run: () => {
      if (!slug) return false;
      for (const ext of ["js", "ts"]) {
        const p = path.join(projectRoot, `apps/web/tailwind.config.${ext}`);
        if (fs.existsSync(p)) {
          const text = fs.readFileSync(p, "utf8");
          return text.includes(`@${slug}/design/tailwind`);
        }
      }
      return false;
    },
  },
  {
    name: "apps/web: package.json includes workspace dependencies",
    run: () => {
      if (!slug) return false;
      const pkg = readJson("apps/web/package.json") as { dependencies?: Record<string, string> } | null;
      if (!pkg?.dependencies) return false;
      return [`@${slug}/shared`, `@${slug}/design`, `@${slug}/api`].every(
        (dep) => pkg.dependencies![dep] === "workspace:*",
      );
    },
  },

  // apps/mobile
  { name: "apps/mobile: directory exists", run: () => dirExists("apps/mobile") },
  { name: "apps/mobile: package.json exists", run: () => fileExists("apps/mobile/package.json") },
  {
    name: "apps/mobile: metro.config.js has watchFolders + disableHierarchicalLookup",
    run: () => {
      const p = path.join(projectRoot, "apps/mobile/metro.config.js");
      if (!fs.existsSync(p)) return false;
      const text = fs.readFileSync(p, "utf8");
      return text.includes("watchFolders") && text.includes("disableHierarchicalLookup");
    },
  },
  {
    name: "apps/mobile: tailwind.config.js references nativewind design preset",
    run: () => {
      if (!slug) return false;
      const p = path.join(projectRoot, "apps/mobile/tailwind.config.js");
      if (!fs.existsSync(p)) return false;
      const text = fs.readFileSync(p, "utf8");
      return text.includes(`@${slug}/design/nativewind`);
    },
  },
  {
    name: "apps/mobile: package.json includes workspace dependencies",
    run: () => {
      if (!slug) return false;
      const pkg = readJson("apps/mobile/package.json") as { dependencies?: Record<string, string> } | null;
      if (!pkg?.dependencies) return false;
      return [`@${slug}/shared`, `@${slug}/design`, `@${slug}/api`].every(
        (dep) => pkg.dependencies![dep] === "workspace:*",
      );
    },
  },

  // packages/design
  { name: "packages/design: directory exists", run: () => dirExists("packages/design") },
  { name: "packages/design: package.json", run: () => fileExists("packages/design/package.json") },
  { name: "packages/design: src/tokens.ts", run: () => fileExists("packages/design/src/tokens.ts") },
  { name: "packages/design: src/tailwind-preset.ts", run: () => fileExists("packages/design/src/tailwind-preset.ts") },
  { name: "packages/design: src/nativewind-preset.ts", run: () => fileExists("packages/design/src/nativewind-preset.ts") },

  // packages/shared
  { name: "packages/shared: directory exists", run: () => dirExists("packages/shared") },
  { name: "packages/shared: package.json", run: () => fileExists("packages/shared/package.json") },
  { name: "packages/shared: src/index.ts", run: () => fileExists("packages/shared/src/index.ts") },

  // packages/api
  { name: "packages/api: directory exists", run: () => dirExists("packages/api") },
  { name: "packages/api: package.json", run: () => fileExists("packages/api/package.json") },

  // meta.json state
  { name: "meta.json: stack.framework == 'monorepo'", run: () => {
    const m = meta as { stack?: { framework?: string } } | null;
    return m?.stack?.framework === "monorepo";
  }},
  { name: "meta.json: stack.monorepo.web present", run: () => {
    return !!meta?.stack?.monorepo?.web;
  }},
  { name: "meta.json: stack.monorepo.mobile present", run: () => {
    return !!meta?.stack?.monorepo?.mobile;
  }},
];

let failed = 0;
for (const check of checks) {
  let ok = false;
  try { ok = check.run(); } catch { ok = false; }
  console.log(`${ok ? "✅" : "❌"} ${check.name}`);
  if (!ok) failed++;
}

if (failed > 0) {
  console.error(`\n${failed} check(s) failed out of ${checks.length}.`);
  process.exit(1);
}
console.log(`\nAll ${checks.length} checks passed.`);
