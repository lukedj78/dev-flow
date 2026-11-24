#!/usr/bin/env python3
"""scaffold_packages.py — create every package `boundaries.json` declares, with a minimal entry point.

Usage:
    python3 scaffold_packages.py <project-root>

For each non-glob key under `packages/` in boundaries.json it writes, only if missing:
    package.json   name @<scope>/<dir>, private, ESM, `exports` on "." only, typecheck and test scripts
                   (lint runs once at the root: Biome and the boundaries check cover every package)
    src/index.ts   an empty module (`export {};`) — the package is filled in the phase that uses it
    tsconfig.json  extends ../config/tsconfig/library.json (a relative path, so no package depends on config
                   just to compile — the boundary table stays about code, not tooling)
The `config` package is special: it holds the shared configuration (ADR-062 of the project that asked for
this: no tsconfig.base.json at the root) — tsconfig/{base,library,nextjs}.json, biome.base.json (not biome.json: Biome 2 refuses a second
`biome.json` below the root as a "nested root configuration"), and
src/env.ts with a Zod schema for environment variables.

Idempotent: an existing file is never overwritten. Prints what it created. Pure standard library.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

TSCONFIG_BASE = {
    "$schema": "https://json.schemastore.org/tsconfig",
    "compilerOptions": {
        "target": "ES2023", "lib": ["ES2023"], "module": "ESNext", "moduleResolution": "Bundler",
        "strict": True, "noUncheckedIndexedAccess": True, "esModuleInterop": True, "skipLibCheck": True,
        "isolatedModules": True, "verbatimModuleSyntax": True, "resolveJsonModule": True,
        "allowImportingTsExtensions": True, "noEmit": True,
    },
}
TSCONFIG_LIBRARY = {"extends": "./base.json", "compilerOptions": {"types": ["node"]}}
TSCONFIG_NEXTJS = {
    "extends": "./base.json",
    "compilerOptions": {"lib": ["ES2023", "DOM", "DOM.Iterable"], "jsx": "preserve", "plugins": [{"name": "next"}],
                        "allowJs": True, "incremental": True},
}
BIOME = {
    "$schema": "https://biomejs.dev/schemas/latest/schema.json",
    "vcs": {"enabled": True, "clientKind": "git", "useIgnoreFile": True},
    "files": {"includes": ["**", "!**/node_modules", "!**/.next", "!**/dist", "!**/.turbo", "!**/.output", "!**/.eve"]},
    "formatter": {"enabled": True, "indentStyle": "space", "indentWidth": 2, "lineWidth": 120},
    "linter": {"enabled": True, "rules": {"recommended": True}},
}
ENV_TS = '''import { z } from "zod";

/** Environment variables shared by every app and package. Parse once at startup; never read process.env elsewhere. */
export const envSchema = z.object({
  NODE_ENV: z.enum(["development", "test", "production"]).default("development"),
});

export type Env = z.infer<typeof envSchema>;

export function readEnv(source: Record<string, string | undefined> = process.env): Env {
  return envSchema.parse(source);
}
'''


def write_if_missing(path: Path, content: str, created: list[str], root: Path) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    created.append(str(path.relative_to(root)))


def dump(obj: dict) -> str:
    return json.dumps(obj, indent=2) + "\n"


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python3 scaffold_packages.py <project-root>")
        return 2
    root = Path(sys.argv[1]).expanduser().resolve()
    cfg_path = root / "boundaries.json"
    if not cfg_path.is_file():
        print("error: no boundaries.json at the root — write it first (references/boundaries.md)")
        return 2
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    scope = cfg.get("scope", "")
    if not scope.startswith("@"):
        print("error: boundaries.json `scope` must be an npm scope such as \"@acme\"")
        return 2

    created: list[str] = []
    for key, rule in cfg.get("packages", {}).items():
        if not key.startswith("packages/") or any(ch in key for ch in "*?["):
            continue
        d = root / key
        name = key.split("/", 1)[1]
        is_config = name == "config"
        scripts = {"typecheck": "tsc --noEmit", "test": "vitest run --passWithNoTests"}
        pkg = {
            "name": f"{scope}/{name}",
            "version": "0.0.0",
            "private": True,
            "type": "module",
            "description": rule.get("purpose", ""),
            "exports": {".": "./src/index.ts"},
            "scripts": scripts,
        }
        if is_config:
            pkg["exports"] = {".": "./src/index.ts", "./tsconfig/*": "./tsconfig/*", "./biome.base.json": "./biome.base.json"}
            # zod is added by the skill with `pnpm --filter <scope>/config add zod` (current version, exact).
            write_if_missing(d / "tsconfig" / "base.json", dump(TSCONFIG_BASE), created, root)
            write_if_missing(d / "tsconfig" / "library.json", dump(TSCONFIG_LIBRARY), created, root)
            write_if_missing(d / "tsconfig" / "nextjs.json", dump(TSCONFIG_NEXTJS), created, root)
            write_if_missing(d / "biome.base.json", dump(BIOME), created, root)
            write_if_missing(d / "src" / "env.ts", ENV_TS, created, root)
            write_if_missing(d / "src" / "index.ts", 'export { envSchema, readEnv, type Env } from "./env.ts";\n',
                             created, root)
            write_if_missing(d / "tsconfig.json", dump({"extends": "./tsconfig/library.json", "include": ["src"]}),
                             created, root)
        else:
            write_if_missing(d / "src" / "index.ts", "export {};\n", created, root)
            write_if_missing(d / "tsconfig.json", dump({"extends": "../config/tsconfig/library.json", "include": ["src"]}),
                             created, root)
        write_if_missing(d / "package.json", dump(pkg), created, root)

    # The root biome.json only points at the shared one, so the rules live in packages/config.
    if "packages/config" in cfg.get("packages", {}):
        write_if_missing(root / "biome.json", dump({"$schema": BIOME["$schema"], "extends": ["./packages/config/biome.base.json"]}),
                         created, root)

    # Folders for the globbed groups (capabilities/*) and the apps, so the tree is whole from the start.
    for key in cfg.get("packages", {}):
        base = key.split("/*", 1)[0] if "*" in key else None
        if base:
            (root / base).mkdir(parents=True, exist_ok=True)

    for c in created:
        print(f"  + {c}")
    print(f"scaffold_packages: {len(created)} file(s) created" if created else "scaffold_packages: nothing to do")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
