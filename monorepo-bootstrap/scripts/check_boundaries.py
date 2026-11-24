#!/usr/bin/env python3
"""check_boundaries.py — enforce the package boundaries a monorepo declares in `boundaries.json`.

Usage:
    python3 check_boundaries.py <project-root>        # exit 0 clean, 1 violations, 2 cannot run
    python3 check_boundaries.py --self-test           # builds a throwaway monorepo with one violation
                                                      # of each kind and proves every one is refused

`boundaries.json` at the root is the single source for which packages exist and who may use whom:

    {
      "scope": "@acme",
      "packages": {
        "packages/db":       { "purpose": "schema, migrations", "may_depend_on": ["config"] },
        "packages/services": { "purpose": "the only domain door", "may_depend_on": ["platform", "board"] },
        "capabilities/*":    { "purpose": "eve extensions", "may_depend_on": ["contracts", "services"] },
        "apps/web":          { "purpose": "the Next.js app", "may_depend_on": ["*"] }
      },
      "paths": {
        "apps/web/agent": { "may_import": ["contracts", "services", "capability-*"] }
      }
    }

Names in `may_depend_on` / `may_import` are workspace package names without the scope (`db` means
`@acme/db`); `*` allows every workspace package; a trailing `*` matches a prefix (`capability-*`).
Only workspace packages are policed — npm dependencies are the package's own business.

Five checks:
  0. declared — every workspace package (from pnpm-workspace.yaml) is covered by boundaries.json: a
     package nobody declared has no rule, so it is refused rather than let through;
  1. dependencies — every `@scope/*` entry in a package.json (dependencies, devDependencies,
     peerDependencies) is allowed by that package's `may_depend_on`;
  2. undeclared imports — a source file imports a workspace package its package.json does not declare;
  3. internals — `@scope/pkg/sub/path` is allowed only if `pkg`'s package.json `exports` declares that
     subpath: a package's public surface is what it exports, everything else is internal;
  4. paths — files under a `paths` entry import only the workspace packages it lists, and never reach
     outside that folder: no relative path out of it, no `@/` / `~/` / `#` alias, no alias declared in
     the nearest tsconfig.json `paths`.

Imports are found in ES `import`/`export … from`, `import(…)` (quotes or a backtick without `${}`),
`require(…)`, `vi.mock`/`jest.mock`, in .ts/.tsx/.js/.jsx/.mts/.cts/.mjs/.cjs/.vue/.svelte/.astro files,
after comments are removed by a scanner that respects string and template literals. Imports built at
runtime (`import(name)`) cannot be read statically and are not policed.
Pure standard library.
"""
from __future__ import annotations

import fnmatch
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

SOURCE_SUFFIXES = {".ts", ".tsx", ".mts", ".cts", ".js", ".jsx", ".mjs", ".cjs", ".vue", ".svelte", ".astro"}
SKIP_DIRS = {"node_modules", ".next", ".turbo", "dist", "build", ".output", ".eve", ".git", "coverage", ".vercel"}
QUOTED = r"""(?:"([^"\n]+)"|'([^'\n]+)'|`([^`$\n]+)`)"""
IMPORT = re.compile(
    r"""(?:^|[^\w$.])(?:import\s+(?:type\s+)?(?:[\w*{}\s,$]+?\s+from\s+)?|export\s+(?:type\s+)?[\w*{}\s,$]+?\s+from\s+|"""
    r"""import\s*\(\s*|require\s*\(\s*|(?:vi|jest)\.mock\s*\(\s*)""" + QUOTED,
    re.M,
)
DEP_FIELDS = ("dependencies", "devDependencies", "peerDependencies")


class Unreadable(Exception):
    pass


def load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError) as exc:
        raise Unreadable(f"{path}: {exc}") from exc
    if not isinstance(data, dict):
        raise Unreadable(f"{path}: not a JSON object")
    return data


def strip_comments(code: str) -> str:
    """Remove // and /* */ comments, leaving string and template literals untouched."""
    out: list[str] = []
    i, n = 0, len(code)
    while i < n:
        c = code[i]
        if c in "\"'`":
            j = i + 1
            while j < n and code[j] != c:
                if code[j] == "\\":
                    j += 1
                elif c != "`" and code[j] == "\n":
                    break
                j += 1
            out.append(code[i:j + 1])
            i = j + 1
        elif code.startswith("//", i):
            j = code.find("\n", i)
            i = n if j < 0 else j
        elif code.startswith("/*", i):
            j = code.find("*/", i + 2)
            out.append("\n" * code.count("\n", i, n if j < 0 else j))
            i = n if j < 0 else j + 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def imports_in(path: Path) -> list[str]:
    code = strip_comments(path.read_text(encoding="utf-8", errors="replace"))
    return [a or b or c for a, b, c in IMPORT.findall(code)]


def allowed(name: str, patterns: list) -> bool:
    return any(isinstance(p, str) and (p == "*" or p == name or (p.endswith("*") and name.startswith(p[:-1])))
               for p in patterns)


def workspace_globs(root: Path) -> list[str]:
    """The `packages:` globs of pnpm-workspace.yaml (enough of YAML for that one list)."""
    f = root / "pnpm-workspace.yaml"
    if not f.is_file():
        return []
    globs, inside = [], False
    for line in f.read_text(encoding="utf-8").splitlines():
        if re.match(r"^packages\s*:", line):
            inside = True
            continue
        if inside:
            m = re.match(r"^\s*-\s*['\"]?([^'\"#]+?)['\"]?\s*(?:#.*)?$", line)
            if m:
                globs.append(m.group(1).strip())
            elif line.strip() and not line.startswith((" ", "\t", "-")):
                inside = False
    return globs


def dirs_for(root: Path, key: str) -> list[Path]:
    if any(ch in key for ch in "*?["):
        return [d.resolve() for d in sorted(root.glob(key)) if (d / "package.json").is_file()]
    return [(root / key).resolve()] if (root / key / "package.json").is_file() else []


def source_files(directory: Path):
    for here, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if Path(f).suffix in SOURCE_SUFFIXES:
                yield Path(here) / f


def split_spec(spec: str, scope: str) -> tuple[str, str] | None:
    """`@acme/db/src/x` → ("db", "src/x"); `@acme/db` → ("db", ""); anything else → None."""
    if not spec.startswith(scope + "/"):
        return None
    name, _, sub = spec[len(scope) + 1:].partition("/")
    return name, sub


def exported(pkg_json: dict, sub: str) -> bool:
    exports = pkg_json.get("exports")
    if not sub:
        return True
    if not isinstance(exports, dict):
        return False
    want = "./" + sub
    return any(key == want or ("*" in key and fnmatch.fnmatchcase(want, key)) for key in exports)


def tsconfig_aliases(start: Path, stop: Path) -> list[str]:
    """Prefixes of the `paths` aliases in the nearest tsconfig.json at or above `start`."""
    d = start
    while True:
        f = d / "tsconfig.json"
        if f.is_file():
            try:
                cfg = json.loads(re.sub(r",(\s*[}\]])", r"\1", strip_comments(f.read_text(encoding="utf-8-sig"))))
                paths = (cfg.get("compilerOptions") or {}).get("paths") or {}
                return [k.split("*", 1)[0] for k in paths if isinstance(k, str) and k.split("*", 1)[0]]
            except (json.JSONDecodeError, OSError, UnicodeDecodeError, AttributeError):
                return []
        if d == stop or d.parent == d:
            return []
        d = d.parent


def check(root: Path) -> tuple[list[str], list[str]]:
    """(violations, notes). Raises Unreadable when boundaries.json itself cannot be read."""
    root = root.resolve()
    cfg_path = root / "boundaries.json"
    if not cfg_path.is_file():
        return [], ["no boundaries.json at the root — nothing to enforce"]
    cfg = load_json(cfg_path)
    scope = cfg.get("scope")
    packages = cfg.get("packages")
    if not isinstance(scope, str) or not scope.startswith("@"):
        return ["boundaries.json: `scope` must be the npm scope, e.g. \"@acme\""], []
    if not isinstance(packages, dict):
        return ["boundaries.json: `packages` must be an object"], []

    violations: list[str] = []
    notes: list[str] = []
    rules: dict[Path, dict] = {}
    for key, rule in packages.items():
        if not isinstance(rule, dict):
            violations.append(f"boundaries.json: the rule for `{key}` must be an object")
            continue
        for d in dirs_for(root, key):
            rules[d] = rule

    manifests: dict[Path, dict] = {}
    for d in set(rules) | {x for g in workspace_globs(root) for x in dirs_for(root, g)}:
        try:
            manifests[d] = load_json(d / "package.json")
        except Unreadable as exc:
            violations.append(f"cannot read {exc}")
    by_name = {pj["name"][len(scope) + 1:]: (d, pj) for d, pj in manifests.items()
               if isinstance(pj.get("name"), str) and pj["name"].startswith(scope + "/")}

    # 0. every workspace package is declared
    for d in sorted(manifests):
        if d not in rules and d != root:
            violations.append(f"{d.relative_to(root)}: a workspace package that boundaries.json does not declare — "
                              "add it with its `may_depend_on` first")

    for d, rule in sorted(rules.items()):
        pj = manifests.get(d)
        if pj is None:
            continue
        rel = d.relative_to(root)
        may = rule.get("may_depend_on", [])
        may = may if isinstance(may, list) else []
        declared: set[str] = set()
        # 1. dependencies
        for field in DEP_FIELDS:
            deps = pj.get(field) or {}
            for dep in deps if isinstance(deps, dict) else {}:
                parts = split_spec(dep, scope)
                if not parts:
                    continue
                declared.add(parts[0])
                if not allowed(parts[0], may):
                    violations.append(f"{rel}/package.json: {field} has `{dep}`, but {rel} may depend only on "
                                      f"{', '.join(map(str, may)) or 'no workspace package'} (boundaries.json)")
        own = pj.get("name")
        # 2–3. imports
        for f in source_files(d):
            frel = f.relative_to(root)
            for spec in imports_in(f):
                parts = split_spec(spec, scope)
                if not parts or f"{scope}/{parts[0]}" == own:
                    continue
                name, sub = parts
                if name not in declared:
                    violations.append(f"{frel}: imports `{spec}` but {rel}/package.json does not declare {scope}/{name}")
                target = by_name.get(name)
                if sub and target and not exported(target[1], sub):
                    violations.append(f"{frel}: imports `{spec}`, an internal file of {scope}/{name} — "
                                      f"use its entry point, or add the subpath to its `exports`")

    # 4. path rules
    paths = cfg.get("paths") or {}
    for prefix, prule in (paths.items() if isinstance(paths, dict) else []):
        base = (root / prefix).resolve()
        if not base.is_dir():
            notes.append(f"paths: {prefix} does not exist yet — its rule is not checked until it does")
            continue
        may = prule.get("may_import", []) if isinstance(prule, dict) else []
        aliases = tsconfig_aliases(base, root)
        for f in source_files(base):
            frel = f.relative_to(root)
            for spec in imports_in(f):
                parts = split_spec(spec, scope)
                if parts:
                    if not allowed(parts[0], may):
                        violations.append(f"{frel}: `{prefix}` imports only {', '.join(map(str, may))}, not `{spec}`")
                elif spec.startswith(("@/", "~/", "#")) or any(spec.startswith(a) for a in aliases):
                    violations.append(f"{frel}: `{spec}` is an alias into the app from `{prefix}` — import a package instead")
                elif spec.startswith("."):
                    target = (f.parent / spec).resolve()
                    if base != target and base not in target.parents:
                        violations.append(f"{frel}: `{spec}` leaves `{prefix}` — import a package instead")
    return violations, notes


def self_test() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="boundaries-self-test-"))
    try:
        def write(rel: str, text: str) -> None:
            p = tmp / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8")

        def pkg(rel: str, name: str, deps: dict | None = None) -> None:
            write(f"{rel}/package.json", json.dumps({"name": name, "dependencies": deps or {},
                                                     "exports": {".": "./src/index.ts"}}))

        write("pnpm-workspace.yaml", "packages:\n  - 'apps/*'\n  - 'packages/*'\n  - 'capabilities/*'\n")
        write("boundaries.json", json.dumps({
            "scope": "@t",
            "packages": {
                "packages/config": {"may_depend_on": []},
                "packages/contracts": {"may_depend_on": []},
                "packages/db": {"may_depend_on": ["config"]},
                "packages/services": {"may_depend_on": ["db", "contracts"]},
                "capabilities/*": {"may_depend_on": ["contracts", "services"]},
                "apps/web": {"may_depend_on": ["*"]},
            },
            "paths": {"apps/web/agent": {"may_import": ["contracts", "services", "capability-*"]}},
        }))
        pkg("packages/config", "@t/config")
        pkg("packages/contracts", "@t/contracts")
        pkg("packages/db", "@t/db", {"@t/config": "workspace:*"})
        pkg("packages/services", "@t/services", {"@t/db": "workspace:*"})
        pkg("capabilities/good", "@t/capability-good", {"@t/contracts": "workspace:*"})
        pkg("capabilities/bad", "@t/capability-bad", {"@t/db": "workspace:*"})                  # V1
        pkg("packages/stray", "@t/stray", {"@t/db": "workspace:*"})                             # V0
        pkg("apps/web", "@t/web", {f"@t/{n}": "workspace:*" for n in ("services", "contracts", "db", "capability-good")})
        write("apps/web/tsconfig.json", '{ "compilerOptions": { "paths": { "@app/*": ["./*"] } }, }')
        write("packages/db/src/index.ts", "export const db = 1;\n")
        write("packages/services/src/index.ts", 'const u = "http://x"; import { db } from "@t/db";\nexport const s = db;\n')
        write("packages/services/src/sneak.ts", 'import { x } from "@t/contracts";\n')                   # V2
        write("packages/services/src/glob.ts", 'const g = "src/**/*.ts";\nimport { y } from "@t/contracts";\n')  # V2b
        write("apps/web/app/page.tsx", 'import { db } from "@t/db/src/index";\n')                       # V3
        write("apps/web/agent/agent.ts", 'import { s } from "@t/services";\nimport m from "@t/capability-good";\n'
                                         '// import { db } from "@t/db";\n/* import { db } from "@t/db"; */\n')
        write("apps/web/agent/tools/leak.ts", 'import { db } from "@t/db";\nimport { h } from "@/lib/h";\n'
                                              'import { p } from "../../app/page";\n')                 # V4a-c
        write("apps/web/agent/tools/sly.ts", 'const d = await import(`@t/db`);\nimport { q } from "@app/lib/q";\n'
                                             'import { r } from "#internal/r";\nvi.mock("@t/db");\n')     # V4d-g
        write("capabilities/good/extension/tools/ok.ts", 'import { c } from "@t/contracts";\n')
        write("capabilities/good/extension/View.vue", '<script setup lang="ts">\nimport { db } from "@t/db";\n</script>\n')  # V2c

        violations, _ = check(tmp)
        expect = {
            "undeclared package dir": "packages/stray: a workspace package that boundaries.json does not declare",
            "capability depends on db": "capabilities/bad/package.json: dependencies has `@t/db`",
            "undeclared import": "packages/services/src/sneak.ts: imports `@t/contracts` but",
            "import after a string with //": "packages/services/src/index.ts",
            "import after a string with /*": "packages/services/src/glob.ts: imports `@t/contracts` but",
            "import in a .vue file": "capabilities/good/extension/View.vue: imports `@t/db` but",
            "internal file": "apps/web/app/page.tsx: imports `@t/db/src/index`, an internal file",
            "agent imports db": "apps/web/agent/tools/leak.ts: `apps/web/agent` imports only",
            "agent alias @/": "apps/web/agent/tools/leak.ts: `@/lib/h` is an alias",
            "agent path into app": "apps/web/agent/tools/leak.ts: `../../app/page` leaves `apps/web/agent`",
            "agent template import": "apps/web/agent/tools/sly.ts: `apps/web/agent` imports only contracts, services, capability-*, not `@t/db`",
            "agent tsconfig alias": "apps/web/agent/tools/sly.ts: `@app/lib/q` is an alias",
            "agent # alias": "apps/web/agent/tools/sly.ts: `#internal/r` is an alias",
        }
        # The services index declares @t/db, so its import (after a string holding "//") must pass now…
        expect.pop("import after a string with //")
        missing = [k for k, v in expect.items() if not any(x.startswith(v) for x in violations)]
        wrong = [v for v in violations if v.startswith("packages/services/src/index.ts")]
        # …and be refused once undeclared: proof the scanner read past the "//" inside the string.
        write("packages/services/package.json", json.dumps({"name": "@t/services", "exports": {".": "./src/index.ts"}}))
        if not any(v.startswith("packages/services/src/index.ts: imports `@t/db` but") for v in check(tmp)[0]):
            missing.append("import after a string with //")
        for k in missing:
            print(f"SELF-TEST FAIL: not refused — {k}")
        for v in wrong:
            print(f"SELF-TEST FAIL: refused something legal — {v}")
        if missing or wrong:
            return 1
        print(f"self-test passed: {len(expect) + 1} kinds of violation refused; the legal imports "
              "(and the ones inside comments) accepted")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    if sys.argv[1:] == ["--self-test"]:
        return self_test()
    if len(sys.argv) != 2:
        print(__doc__.strip().splitlines()[2])
        return 2
    try:
        violations, notes = check(Path(sys.argv[1]).expanduser())
    except Unreadable as exc:
        print(f"error: cannot read {exc}")
        return 2
    for n in notes:
        print(f"note: {n}")
    for v in violations:
        print(f"BOUNDARY: {v}")
    if not violations:
        print("boundaries: clean")
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
