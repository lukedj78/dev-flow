// The write-time guard's lint (primitives-guard.mjs): only the two design rules, so it answers in about a
// second on every file an agent writes. The full policy is the project's design-system preset, whose
// `designPlugin` and `designExceptions` this imports. Copied by design-md-to-app/scripts/setup_primitives_guard.py
// — do not edit here; re-run the script.
import { existsSync } from "node:fs"
import { createRequire } from "node:module"
import path from "node:path"
import { pathToFileURL } from "node:url"

/** createRequire for every place a package may sit: the app, the preset's package, the root. pnpm does not
 * hoist, so the TypeScript parser is usually reachable only through the package that depends on it. */
function requirers(root, unit) {
  const dirs = [unit.dir, path.dirname(unit.preset), ".", "packages/eslint-config"]
  return [...new Set(dirs)]
    .map((d) => path.join(root, d, "package.json"))
    .filter((p) => existsSync(p))
    .map((p) => createRequire(p))
}

function first(reqs, strategies, what) {
  for (const req of reqs) {
    for (const s of strategies) {
      try {
        const found = s(req)
        if (found) return found
      } catch {
        // not reachable from here: try the next place
      }
    }
  }
  throw new Error(`primitives guard: cannot resolve ${what} from the project — is it installed?`)
}

export async function guardLinter(root, unit) {
  const reqs = requirers(root, unit)
  const { ESLint } = first(reqs, [(r) => r("eslint")], "eslint")
  const parser = first(
    reqs,
    [
      (r) => r("@typescript-eslint/parser"),
      (r) => createRequire(r.resolve("eslint-config-next"))("@typescript-eslint/parser"),
      (r) => r("typescript-eslint").parser,
      (r) => createRequire(r.resolve("typescript-eslint"))("@typescript-eslint/parser"),
    ],
    "@typescript-eslint/parser",
  )
  const preset = await import(pathToFileURL(path.join(root, unit.preset)).href)
  if (!preset.designPlugin) throw new Error(`primitives guard: ${unit.preset} does not export designPlugin — re-run setup_design_lint.py`)
  const overrideConfig = [
    {
      files: ["**/*.{tsx,jsx}"],
      ignores: unit.ignores,
      languageOptions: { parser, parserOptions: { ecmaFeatures: { jsx: true } } },
      plugins: { design: preset.designPlugin },
      rules: unit.rules,
    },
    ...(preset.designExceptions ?? []),
  ]
  return new ESLint({ cwd: path.join(root, unit.dir), overrideConfigFile: true, overrideConfig })
}
