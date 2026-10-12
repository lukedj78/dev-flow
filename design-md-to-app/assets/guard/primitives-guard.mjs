#!/usr/bin/env node
// Golden rule 3 «The primitive renders the design» (R90) — the guard at write time, for every agent and subagent working in
// this repo, wired in .claude/settings.json. The lint finds hand-made UI after the fact; this refuses it while
// it is being written, so an agent cannot build a screen out of raw <button>s, <label>s and div-cards and find
// out at review.
//
//   pre   PreToolUse on Write|Edit|MultiEdit: lints the file as it would be after the write and refuses the
//         write (exit 2) when it adds a finding of design/no-handmade-ui or design/no-card-in-card. Only what
//         the write adds counts, so converting a file that still has old findings is never blocked.
//   stop  Stop / SubagentStop: the same check on every .tsx/.jsx changed since HEAD, compared with HEAD — it
//         catches what was written through the shell (sed, heredocs) instead of Write/Edit.
//
// Units, presets and ignores come from scripts/guard/guard.json. Copied by
// design-md-to-app/scripts/setup_primitives_guard.py — do not edit here; re-run the script.
import { execFileSync } from "node:child_process"
import { existsSync, readdirSync, readFileSync } from "node:fs"
import path from "node:path"
import { guardLinter } from "./eslint.guard.mjs"

const root = process.env.CLAUDE_PROJECT_DIR || process.cwd()
const mode = process.argv[2]
const RULES = new Set(["design/no-handmade-ui", "design/no-card-in-card"])

function loadConfig() {
  try {
    return JSON.parse(readFileSync(path.join(root, "scripts/guard/guard.json"), "utf8"))
  } catch {
    return null
  }
}
const config = loadConfig()

function primitives(unit) {
  try {
    return readdirSync(path.join(root, unit.components))
      .filter((f) => /\.(tsx|jsx)$/.test(f))
      .map((f) => f.replace(/\.(tsx|jsx)$/, ""))
      .join(", ")
  } catch {
    return `see ${unit.components}/`
  }
}

const stopAndAsk = (unit) =>
  `Use the primitive from ${unit.components} (golden rule 3, «The primitive renders the design»). If it looks ` +
  "different from the board, tune its cva variant and the DESIGN.md tokens (a new variant goes into DESIGN.md " +
  "first) until it matches pixel by pixel. Do NOT write the element by hand, do NOT add classes that redraw " +
  "it and do NOT eslint-disable it; if no primitive can render it without a fork, stop and ask the user. Read " +
  "design-md-to-app/references/primitives-first.md for the pattern → primitive table. Primitives: " +
  primitives(unit)

/** The unit a file belongs to (the longest matching dir), or null when the guard does not cover it. */
function unitOf(file) {
  if (!config) return null
  const rel = path.relative(root, path.resolve(root, file))
  if (rel.startsWith("..") || !/\.(tsx|jsx)$/.test(rel) || /(^|\/)(node_modules|\.next)\//.test(rel)) return null
  const units = config.units
    .filter((u) => u.dir === "." || rel === u.dir || rel.startsWith(u.dir + "/"))
    .sort((a, b) => b.dir.length - a.dir.length)
  return units[0] ?? null
}

const linters = new Map()
async function findings(unit, text, file) {
  if (text == null) return []
  if (!linters.has(unit.dir)) linters.set(unit.dir, await guardLinter(root, unit))
  const [result] = await linters.get(unit.dir).lintText(text, { filePath: path.resolve(root, file) })
  const lines = text.split("\n")
  return (result?.messages ?? [])
    .filter((m) => RULES.has(m.ruleId))
    .map((m) => ({ ...m, key: `${m.ruleId}|${m.message}|${(lines[m.line - 1] ?? "").trim()}` }))
}

/** The findings of `after` that `before` does not have (as a multiset: moving a line is not adding one). */
function added(before, after) {
  const left = new Map()
  for (const f of before) left.set(f.key, (left.get(f.key) ?? 0) + 1)
  return after.filter((f) => {
    const n = left.get(f.key) ?? 0
    if (n > 0) {
      left.set(f.key, n - 1)
      return false
    }
    return true
  })
}

const describe = (file, list) => list.map((f) => `  ${file}:${f.line} — ${f.message}`).join("\n")

function afterEdit(current, input) {
  const edits = input.edits ?? [{ old_string: input.old_string, new_string: input.new_string, replace_all: input.replace_all }]
  let text = current
  for (const e of edits) {
    if (e.old_string == null || !text.includes(e.old_string)) return null // the tool itself will refuse it
    text = e.replace_all ? text.split(e.old_string).join(e.new_string) : text.replace(e.old_string, () => e.new_string)
  }
  return text
}

async function pre(event) {
  const input = event.tool_input ?? {}
  const file = input.file_path
  const unit = file ? unitOf(file) : null
  if (!unit) return 0
  const abs = path.resolve(root, file)
  const current = existsSync(abs) ? readFileSync(abs, "utf8") : null
  const next = event.tool_name === "Write" ? input.content : current == null ? null : afterEdit(current, input)
  if (next == null) return 0
  const fresh = added(await findings(unit, current, file), await findings(unit, next, file))
  if (fresh.length === 0) return 0
  process.stderr.write(`Write refused — it adds hand-made UI:\n${describe(path.relative(root, abs), fresh)}\n${stopAndAsk(unit)}\n`)
  return 2
}

function git(args) {
  return execFileSync("git", args, { cwd: root, encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] })
}

function changedFiles() {
  const lines = (s) => s.split("\n").filter(Boolean)
  let tracked = []
  try {
    tracked = lines(git(["diff", "--name-only", "--relative", "HEAD"]))
  } catch {
    tracked = lines(git(["ls-files"])) // no commit yet: everything is new
  }
  return [...new Set([...tracked, ...lines(git(["ls-files", "--others", "--exclude-standard"]))])]
}

async function stop(event) {
  if (event.stop_hook_active) return 0 // already sent back once in this turn: do not loop
  let changed
  try {
    changed = changedFiles()
  } catch {
    return 0 // not a git repository
  }
  const report = []
  let unitForMessage = null
  for (const file of changed) {
    const unit = unitOf(file)
    const abs = path.join(root, file)
    if (!unit || !existsSync(abs)) continue
    let head = null
    try {
      head = git(["show", `HEAD:./${file}`])
    } catch {
      // new file: everything in it is added
    }
    const fresh = added(await findings(unit, head, file), await findings(unit, readFileSync(abs, "utf8"), file))
    if (fresh.length) {
      report.push(describe(file, fresh))
      unitForMessage ??= unit
    }
  }
  if (report.length === 0) return 0
  process.stderr.write(`Hand-made UI added since the last commit:\n${report.join("\n")}\n${stopAndAsk(unitForMessage)}\n`)
  return 2
}

let raw = ""
for await (const chunk of process.stdin) raw += chunk
const event = raw ? JSON.parse(raw) : {}
try {
  process.exit(mode === "stop" ? await stop(event) : await pre(event))
} catch (e) {
  // exit 1 is a non-blocking error: shown, never silently passed off as a clean write
  process.stderr.write(`primitives guard could not run: ${e?.message ?? e}\n`)
  process.exit(1)
}
