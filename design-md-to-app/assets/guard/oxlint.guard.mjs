// The write-time guard's lint on Oxlint (primitives-guard.mjs, units with "engine": "oxlint"): only the two
// design rules, loaded as an Oxlint JS plugin from the project's rules module, so it answers in well under a
// second on every file an agent writes. The same interface as eslint.guard.mjs — `lintText(text, { filePath })`
// resolving to `[{ messages: [{ ruleId, message, line }] }]` — so the guard itself does not change.
//
// Oxlint reads no stdin: the text is written to a temporary file with the same name and linted there, outside
// the project. Path-based policy is applied here instead: the unit's ignores, and the overrides in
// .oxlintrc.json that turn a design rule off for some files (Oxlint's form of a recorded exception).
// Copied by design-md-to-app/scripts/setup_primitives_guard.py — do not edit here; re-run the script.
import { execFileSync } from "node:child_process"
import { existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs"
import os from "node:os"
import path from "node:path"

/** A glob as a RegExp: `**` crosses folders, `*` does not, `{a,b}` is a choice. Enough for lint globs. */
function globRegExp(glob) {
  let re = ""
  for (let i = 0; i < glob.length; i++) {
    const c = glob[i]
    if (c === "*" && glob[i + 1] === "*") {
      re += glob[i + 2] === "/" ? "(?:.*/)?" : ".*"
      i += glob[i + 2] === "/" ? 2 : 1
    } else if (c === "*") re += "[^/]*"
    else if (c === "?") re += "[^/]"
    else if (c === "{") {
      const end = glob.indexOf("}", i)
      re += `(?:${glob.slice(i + 1, end).split(",").map((s) => s.replace(/[.+^$()|[\]\\]/g, "\\$&")).join("|")})`
      i = end
    } else re += c.replace(/[.+^$()|[\]\\]/g, "\\$&")
  }
  return new RegExp(`^${re}$`)
}

const matches = (rel, globs) => (globs ?? []).some((g) => globRegExp(g).test(rel))

function oxlintBin(root, unit) {
  for (const d of [unit.dir, "."]) {
    const bin = path.join(root, d, "node_modules", ".bin", "oxlint")
    if (existsSync(bin)) return bin
  }
  throw new Error("primitives guard: cannot find node_modules/.bin/oxlint in the project — is oxlint installed?")
}

/** Files .oxlintrc.json exempts from a design rule: overrides that turn it off. */
function exemptions(root, unit) {
  try {
    const cfg = JSON.parse(readFileSync(path.join(root, unit.config ?? ".oxlintrc.json"), "utf8"))
    const off = (v) => v === "off" || v === 0 || (Array.isArray(v) && (v[0] === "off" || v[0] === 0))
    const out = {}
    for (const o of cfg.overrides ?? [])
      for (const [rule, value] of Object.entries(o.rules ?? {}))
        if (rule.startsWith("design/") && off(value)) (out[rule] ??= []).push(...(o.files ?? []))
    return out
  } catch {
    return {}
  }
}

export async function guardLinter(root, unit) {
  const bin = oxlintBin(root, unit)
  const plugin = path.join(root, unit.preset)
  if (!readFileSync(plugin, "utf8").includes("designPlugin"))
    throw new Error(`primitives guard: ${unit.preset} does not export designPlugin — re-run setup_design_lint.py`)
  const work = mkdtempSync(path.join(os.tmpdir(), "primitives-guard-"))
  process.on("exit", () => rmSync(work, { recursive: true, force: true }))
  const config = path.join(work, "oxlintrc.json")
  // only the design rules: every other category off, so a project's own rules never block a write here
  writeFileSync(config, JSON.stringify({
    plugins: [],
    jsPlugins: [plugin],
    categories: { correctness: "off", suspicious: "off", pedantic: "off", perf: "off", style: "off",
                  restriction: "off", nursery: "off" },
    rules: unit.rules,
  }))
  const exempt = exemptions(root, unit)
  return {
    async lintText(text, { filePath }) {
      const rel = path.relative(path.join(root, unit.dir), filePath).split(path.sep).join("/")
      if (matches(rel, unit.ignores)) return [{ messages: [] }]
      const file = path.join(work, path.basename(filePath))
      writeFileSync(file, text)
      let out
      try {
        out = execFileSync(bin, ["-c", config, "--format", "json", file], { cwd: work, encoding: "utf8",
                                                                            stdio: ["ignore", "pipe", "pipe"] })
      } catch (e) {
        out = e.stdout // exit 1 when a rule at "error" fires: the report is still on stdout
      }
      let rows = []
      try {
        rows = JSON.parse(out).diagnostics ?? []
      } catch {
        throw new Error(`primitives guard: oxlint gave no report for ${rel}`)
      }
      const messages = rows
        .map((r) => {
          const m = /^([\w@/.-]+)\((.+)\)$/.exec(r.code ?? "")
          return { ruleId: m ? `${m[1]}/${m[2]}` : r.code, message: r.message, line: r.labels?.[0]?.span?.line ?? 0 }
        })
        .filter((m) => !matches(rel, exempt[m.ruleId]))
      return [{ messages }]
    },
  }
}
