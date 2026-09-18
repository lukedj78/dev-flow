"""Tests for registry_intake.py. No network: registry items and npm facts are faked.

    cd registry-intake/scripts && python3 -m unittest test_registry_intake -v
"""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import registry_intake as ri  # noqa: E402

SCHEMA = "https://ui.shadcn.com/schema/registry-item.json"
REG = "https://reg.example.dev/r/{name}.json"

TOOL_NEEDS_APPROVAL = """import { defineTool } from 'eve/tools'
import { always } from 'eve/tools/approval'
export default defineTool({
  needsApproval: always(),
  description: 'Posts a message. Uses { braces } in a string.',
  inputSchema: z.object({ text: z.string() }),
  async execute({ text }) {
    return fetch('https://slack.com/api/chat.postMessage', { method: 'POST', body: text })
  },
})
"""
TOOL_GATED = TOOL_NEEDS_APPROVAL.replace("needsApproval: always()", "approval: always()")
TOOL_READ = """import { defineTool } from 'eve/tools'
import { never } from 'eve/tools/approval'
export default defineTool({
  approval: never(),
  description: 'Reads',
  inputSchema: z.object({}),
  execute: async () => ({ ok: true }),
})
"""


def item(name: str, files: list[dict], **extra) -> dict:
    return {"$schema": SCHEMA, "name": name, "type": "registry:ui", "files": files, **extra}


def ui_file(target: str, content: str = "export const X = 1\n") -> dict:
    return {"path": f"registry/{target}", "type": "registry:component", "target": target, "content": content}


def fake_npm(table: dict):
    def npm(spec: str):
        spec = ri.re.sub(r"(?<=.)@[^/]*$", "", spec)  # what npm view is asked for: the name, not the range
        return table.get(spec,{"name": spec, "license": "MIT", "created": "2020-01-01T00:00:00Z", "scripts": {}, "version": "1.0.0"})
    return npm


def write(root: Path, rel: str, data) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(data if isinstance(data, str) else json.dumps(data, indent=2))
    return p


def project(root: Path, ui: str | None = "shadcn", registries: dict | None = None) -> None:
    write(root, "package.json", {"name": "app", "scripts": {"lint": "eslint --max-warnings 12"}})
    write(root, "components.json", {"aliases": {"components": "@/components"}, "registries": registries or {}})
    write(root, ".workflow/meta.json", {"phase": "scaffolded", "stack": {"framework": "next", "ui": ui}})


def quiet(fn, *a, **k):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = fn(*a, **k)
    return rc, out.getvalue() + err.getvalue()


class Base(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.served: dict[str, dict] = {}
        self._fetch, self._npm = ri.fetch_json, ri.npm_facts
        ri.fetch_json = lambda source, root: json.loads(json.dumps(self.served[source]))
        ri.npm_facts = fake_npm({})

    def tearDown(self) -> None:
        ri.fetch_json, ri.npm_facts = self._fetch, self._npm
        self.tmp.cleanup()

    def serve(self, name: str, data: dict) -> None:
        self.served[REG.replace("{name}", name)] = data

    def cli(self, *argv: str) -> tuple[int, str]:
        return quiet(ri.main, list(argv))


class Scanner(unittest.TestCase):
    def test_top_level_keys_only(self) -> None:
        (keys,) = ri.object_keys(TOOL_NEEDS_APPROVAL, "defineTool")
        self.assertEqual(keys, ["needsApproval", "description", "inputSchema", "execute"])
        (keys,) = ri.object_keys(TOOL_READ, "defineTool")
        self.assertEqual(keys, ["approval", "description", "inputSchema", "execute"])

    def test_eve_keys_come_from_the_installed_eve(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write(root, "node_modules/eve/package.json", {"version": "9.9.9"})
            write(root, "node_modules/eve/dist/src/internal/authored-definition/schema-backed.js",
                  "expectOnlyKnownKeys(i,[`description`,`execute`,`inputSchema`,`approval`,`needsApproval`],r)")
            self.assertEqual(ri.eve_tool_keys(root), ("9.9.9", ["description", "execute", "inputSchema", "approval", "needsApproval"]))
            self.assertEqual(ri.eve_tool_keys(root / "nowhere")[0], ri.EVE_TOOL_KEYS_FALLBACK[0])


class Checks(unittest.TestCase):
    def run_checks(self, data: dict) -> tuple[set[tuple[str, str]], bool]:
        it = ri.Item(key="@x/a", source="s", data=data)
        findings, high = ri.check_files(it, Path("/nonexistent"), ri.EVE_TOOL_KEYS_FALLBACK)
        return {(f.code, f.level) for f in findings}, high

    def test_agentcn_shape_is_blocked_twice(self) -> None:
        codes, high = self.run_checks(item("a", [{"path": "t", "type": "registry:file", "target": "agent/tools/post_message.ts",
                                                   "content": TOOL_NEEDS_APPROVAL}]))
        self.assertTrue(high)
        self.assertIn(("V1", "block"), codes, "needsApproval is not an eve key")
        self.assertIn(("V2", "block"), codes, "an approval the loader never reads gates nothing")

    def test_gated_side_effect_and_read_tool_pass(self) -> None:
        for content in (TOOL_GATED, TOOL_READ):
            codes, _ = self.run_checks(item("a", [{"path": "t", "type": "registry:file",
                                                   "target": "agent/tools/post_message.ts" if content is TOOL_GATED else "agent/tools/read_x.ts",
                                                   "content": content}]))
            self.assertFalse({c for c, lvl in codes if lvl == "block"}, codes)

    def test_never_on_a_writer_is_blocked(self) -> None:
        codes, _ = self.run_checks(item("a", [{"path": "t", "type": "registry:file", "target": "agent/tools/delete_row.ts",
                                               "content": TOOL_READ}]))
        self.assertIn(("V2", "block"), codes)

    def test_file_and_item_level_rules(self) -> None:
        cases = [
            (item("a", [ui_file("next.config.ts")]), ("T1", "block")),
            (item("a", [ui_file("../../etc/passwd")]), ("T1", "block")),
            (item("a", [ui_file("components/x.tsx", "import { exec } from 'node:child_process'")]), ("S1", "block")),
            (item("a", [ui_file("components/x.tsx", "const k = 'A" + "b" * 900 + "'")]), ("S2", "block")),
            (item("a", [ui_file("components/x.tsx")], cssVars={"light": {"primary": "red"}}), ("C1", "block")),
            (item("a", [ui_file("components/x.tsx")], envVars={"STRIPE_SECRET_KEY": "sk_live_x"}), ("E2", "block")),
            (item("a", [ui_file("components/x.tsx")], envVars={"NEXT_PUBLIC_URL": ""}), ("E1", "review")),
            (item("a", [ui_file("lib/pii.ts", r"[/\b\d{3}-\d{2}-\d{4}\b/g, '[redacted-ssn]']")]), ("V5", "review")),
            (item("a", [ui_file("components/x.tsx", "<div dangerouslySetInnerHTML={{__html: h}} />")]), ("S5", "review")),
        ]
        for data, expected in cases:
            with self.subTest(expected=expected):
                self.assertIn(expected, self.run_checks(data)[0])

    def test_a_wide_class_list_is_reviewed_not_blocked(self) -> None:
        # React Bits' SwipeToast has one 1070-char Tailwind class list; minified code packs statements
        wide = "      className={`" + "data-[inline=false]:right-8 " * 60 + "`}\n"
        codes, _ = self.run_checks(item("a", [ui_file("components/x.tsx", wide)]))
        self.assertIn(("S6", "review"), codes)
        self.assertNotIn(("S2", "block"), codes)
        packed = "const a=1;" * 200 + "\n"
        self.assertIn(("S2", "block"), self.run_checks(item("a", [ui_file("components/y.tsx", packed)]))[0])

    def test_dependency_range_against_the_installed_major(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write(root, "package.json", {"name": "app", "dependencies": {"motion": "^13.4.0"}})
            it = ri.Item("@x/a", "s", item("a", [], dependencies=["motion@^12.23.12", "clsx@^2.1.0"]))
            codes = {(f.code, f.item, f.message) for f in ri.check_deps([it], fake_npm({}), root)[0]}
            self.assertTrue(any(c == "D7" and "motion" in m for c, _, m in codes), codes)
            self.assertFalse(any(c == "D7" and "clsx" in m for c, _, m in codes), "no conflict, no finding")
            self.assertEqual(ri.installed_version(root, "motion"), "13.4.0")
            self.assertFalse(ri.major_conflict("^13.0.0", "13.4.0"))
            self.assertTrue(ri.major_conflict("~12.23.12", "13.4.0"))

    def test_plain_ui_component_is_clean_and_low(self) -> None:
        codes, high = self.run_checks(item("a", [ui_file("components/pdf/card.tsx")]))
        self.assertEqual(codes, set())
        self.assertFalse(high)

    def test_dependencies(self) -> None:
        npm = fake_npm({
            "ghost-pkg": {"missing": True, "name": "ghost-pkg"},
            "gpl-pkg": {"name": "gpl-pkg", "license": "AGPL-3.0", "created": "2020-01-01T00:00:00Z", "scripts": {}},
            "hook-pkg": {"name": "hook-pkg", "license": "MIT", "created": "2020-01-01T00:00:00Z", "scripts": {"postinstall": "node x"}},
            "new-pkg": {"name": "new-pkg", "license": "MIT", "created": ri.now(), "scripts": {}},
            "mpl-pkg": {"name": "mpl-pkg", "license": "MPL-2.0", "created": "2020-01-01T00:00:00Z", "scripts": {}},
        })
        it = ri.Item("@x/a", "s", item("a", [], dependencies=["ghost-pkg", "gpl-pkg@^1", "hook-pkg", "new-pkg", "mpl-pkg", "fine"]))
        codes = {(f.code, f.level) for f in ri.check_deps([it], npm)[0]}
        self.assertEqual(codes, {("D1", "block"), ("D2", "block"), ("D4", "block"), ("D5", "review"), ("D3", "review")})


class Flow(Base):
    def setUp(self) -> None:
        super().setUp()
        project(self.root)
        self.serve("pdf/utils", item("pdf/utils", [ui_file("lib/pdf.ts")], type="registry:lib"))
        self.serve("pdf/card", item("pdf/card", [ui_file("components/pdf/card.tsx")],
                                    registryDependencies=["@x/pdf/utils", "button"], dependencies=["takumi-pdf"]))
        self.assertEqual(self.cli("setup", str(self.root))[0], 0)

    def test_approve_needs_the_allowlist_then_snapshots_the_closure(self) -> None:
        with self.assertRaises(SystemExit):  # @x is unknown: not even resolvable
            quiet(ri.main, ["approve", str(self.root), "@x/pdf/card", "--by", "luca"])
        self.assertEqual(self.cli("allow", str(self.root), "@x", REG, "--reason", "pdf export")[0], 0)
        rc, out = self.cli("approve", str(self.root), "@x/pdf/card", "--by", "luca")
        self.assertEqual(rc, 0, out)
        lock = json.loads((self.root / ri.LOCK).read_text())
        self.assertEqual(sorted(lock["items"]), ["@x/pdf/card", "@x/pdf/utils"])
        snap = json.loads((self.root / "vendor/registry/x/pdf/card.json").read_text())
        self.assertEqual(snap["registryDependencies"], ["./vendor/registry/x/pdf/utils.json", "button"],
                         "governed deps point at snapshots, shadcn's own names stay as they are")
        self.assertEqual(lock["items"]["@x/pdf/utils"]["via"], "@x/pdf/card")
        self.assertTrue(ri.check(self.root)[0])

    def test_blocking_findings_need_a_reason_each(self) -> None:
        self.serve("bad", item("bad", [ui_file("next.config.ts")]))
        self.cli("allow", str(self.root), "@x", REG, "--reason", "r")
        self.assertEqual(self.cli("approve", str(self.root), "@x/bad", "--by", "luca")[0], 1)
        self.assertEqual(self.cli("approve", str(self.root), "@x/bad", "--by", "luca", "--accept", "T1")[0], 1)
        rc, out = self.cli("approve", str(self.root), "@x/bad", "--by", "luca", "--accept", "T1=we own this config")
        self.assertEqual(rc, 0, out)
        self.assertEqual(json.loads((self.root / ri.LOCK).read_text())["items"]["@x/bad"]["accepted"], {"T1": "we own this config"})

    def test_closure_into_another_registry_is_blocked(self) -> None:
        self.served["https://other.dev/r/lib.json"] = item("lib", [ui_file("lib/o.ts")])
        self.serve("mixed", item("mixed", [ui_file("components/m.tsx")], registryDependencies=["https://other.dev/r/lib.json"]))
        self.cli("allow", str(self.root), "@x", REG, "--reason", "r")
        rep, _ = ri.review("@x/mixed", self.root)
        self.assertIn("R1", {f.code for f in rep.findings})

    def test_review_shows_what_changed_upstream(self) -> None:
        self.cli("allow", str(self.root), "@x", REG, "--reason", "r")
        self.cli("approve", str(self.root), "@x/pdf/utils", "--by", "luca")
        self.served[REG.replace("{name}", "pdf/utils")]["files"][0]["content"] = "export const X = 2\n"
        rc, out = self.cli("review", str(self.root), "@x/pdf/utils")
        self.assertIn("-export const X = 1", out)
        self.assertIn("+export const X = 2", out)

    def test_check_catches_every_bypass(self) -> None:
        self.cli("allow", str(self.root), "@x", REG, "--reason", "r")
        self.cli("approve", str(self.root), "@x/pdf/card", "--by", "luca")
        snap = self.root / "vendor/registry/x/pdf/utils.json"
        snap.write_text(snap.read_text() + " ")
        write(self.root, "vendor/registry/x/stray.json", {})
        write(self.root, "components.json", {"registries": {"@evil": "https://evil.dev/r/{name}.json"}})
        write(self.root, "package.json", {"name": "app", "scripts": {"lint": "eslint --max-warnings 40"}})
        ok, problems = ri.check(self.root)
        self.assertFalse(ok)
        text = "\n".join(problems)
        for needle in ("edited after approval", "stray.json", "@evil", "rose 12 → 40"):
            self.assertIn(needle, text)
        (self.root / ".claude/settings.json").unlink()
        self.assertIn("no registry-intake PreToolUse hook", "\n".join(ri.check(self.root)[1]))

    def test_hook_is_portable_and_replaces_an_absolute_one(self) -> None:
        # a committed absolute path breaks on every other machine, where python3 exits 2 = "block"
        settings_path = self.root / ".claude/settings.json"
        data = json.loads(settings_path.read_text())
        data["hooks"]["PreToolUse"] = [
            {"matcher": "Bash", "hooks": [{"type": "command", "command": "python3 /Users/someone/skills/registry_intake.py hook"}]},
            {"matcher": "Edit", "hooks": [{"type": "command", "command": "./format.sh"}]}]
        settings_path.write_text(json.dumps(data))
        self.assertFalse(ri.check(self.root)[0])
        self.cli("setup", str(self.root))
        pre = json.loads(settings_path.read_text())["hooks"]["PreToolUse"]
        self.assertEqual([h["command"] for m in pre for h in m["hooks"]],
                         ["./format.sh", 'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/registry_intake.py" hook'])
        self.assertEqual((self.root / ri.HOOK_COPY).read_bytes(), Path(ri.__file__).read_bytes())
        (self.root / ri.HOOK_COPY).write_text("# stale\n")
        self.assertIn("differs from the installed skill", "\n".join(ri.check(self.root)[1]))

    def test_setup_is_idempotent(self) -> None:
        self.cli("setup", str(self.root))
        settings = json.loads((self.root / ".claude/settings.json").read_text())
        self.assertEqual(len(settings["hooks"]["PreToolUse"]), 1)
        self.assertEqual((self.root / "AGENTS.md").read_text().count(ri.SETUP_MARK[0]), 1)
        meta = json.loads((self.root / ".workflow/meta.json").read_text())
        self.assertEqual(meta["stack"]["registry_intake"], "enforced")


class Hook(Base):
    def decide(self, command: str, cwd: Path | None = None) -> str | None:
        return ri.hook_decision({"tool_name": "Bash", "cwd": str(cwd or self.root), "tool_input": {"command": command}})

    def test_matrix(self) -> None:
        project(self.root, ui="coss", registries={"@coss": "https://coss.com/ui/r/{name}.json"})
        self.serve("pdf/card", item("pdf/card", [ui_file("components/pdf/card.tsx")]))
        quiet(ri.main, ["setup", str(self.root)])
        quiet(ri.main, ["allow", str(self.root), "@x", REG, "--reason", "r"])
        quiet(ri.main, ["approve", str(self.root), "@x/pdf/card", "--by", "luca"])
        allowed = [
            "npx shadcn@latest add button dialog",
            "npx shadcn add @x/pdf/card --dry-run",
            "npx shadcn@4.21.0 add ./vendor/registry/x/pdf/card.json --yes",
            "pnpm dlx shadcn add @coss/button",          # stack.ui = coss → live
            "eve add connection/stripe",
            "ls && git status",
        ]
        denied = [
            "npx shadcn add @x/pdf/card",
            "bunx shadcn add https://agentcn.vercel.app/r/eve/claw.json",
            "npx shadcn add ./vendor/registry/x/other.json",
            "eve add @evex/stripe-metrics",
            "eve registry add @evex=https://www.evex.sh/r/{name}.json",
            "git pull; npx shadcn@latest add @mapcn/map",
        ]
        for c in allowed:
            with self.subTest(allow=c):
                self.assertIsNone(self.decide(c))
        for c in denied:
            with self.subTest(deny=c):
                self.assertIsNotNone(self.decide(c))
        snap = self.root / "vendor/registry/x/pdf/card.json"
        snap.write_text(snap.read_text() + " ")
        self.assertIn("changed after approval", self.decide("npx shadcn add ./vendor/registry/x/pdf/card.json"))

    def test_coss_is_live_only_when_the_stack_chose_it(self) -> None:
        project(self.root, ui="shadcn", registries={"@coss": "https://coss.com/ui/r/{name}.json"})
        quiet(ri.main, ["setup", str(self.root)])
        self.assertIsNotNone(self.decide("npx shadcn add @coss/button"))
        rc, _ = quiet(ri.main, ["allow", str(self.root), "@x", REG, "--reason", "r", "--trust", "live"])
        self.assertEqual(rc, 1, "only a chosen UI system's registry can be live")

    def test_no_lock_means_no_third_party_installs(self) -> None:
        project(self.root)
        self.assertIsNone(self.decide("npx shadcn add button"))
        self.assertIn("no registry-lock.json", self.decide("npx shadcn add @x/pdf/card"))

    def test_hook_output_is_the_documented_deny_shape(self) -> None:
        project(self.root)
        payload = json.dumps({"tool_name": "Bash", "cwd": str(self.root), "tool_input": {"command": "npx shadcn add @x/a"}})
        out = io.StringIO()
        stdin = sys.stdin
        try:
            sys.stdin = io.StringIO(payload)
            with redirect_stdout(out):
                self.assertEqual(ri.cmd_hook(None), 0)
        finally:
            sys.stdin = stdin
        decision = json.loads(out.getvalue())["hookSpecificOutput"]
        self.assertEqual((decision["hookEventName"], decision["permissionDecision"]), ("PreToolUse", "deny"))


class PhaseGate(unittest.TestCase):
    DEVFLOW = HERE.parents[1] / "dev-flow" / "scripts"

    def set_phase(self, root: Path) -> "subprocess.CompletedProcess[str]":
        import subprocess
        return subprocess.run([sys.executable, str(self.DEVFLOW / "update_meta.py"), str(root), "set-phase", "scaffolded"],
                              capture_output=True, text=True, check=False)

    def meta(self, root: Path, **stack) -> None:
        write(root, ".workflow/meta.json", {"phase": "design_extracted", "stack": {"data_residency": "none", **stack},
                                            "stack_config": {"design_lint_reason": "not under test here"}})

    def test_scaffolded_needs_intake_on_web_and_agent_stacks(self) -> None:
        for stack in ({"framework": "next", "ui": "shadcn", "design_lint": "none"},
                      {"framework": "agent", "agent": "eve"}):
            with self.subTest(stack=stack), tempfile.TemporaryDirectory() as d:
                root = Path(d); project(root); self.meta(root, **stack)
                r = self.set_phase(root)
                self.assertEqual(r.returncode, 1, r.stderr)
                self.assertIn("registry intake", r.stderr)
                self.assertIn("registry_intake.py setup", r.stderr)
                quiet(ri.main, ["setup", str(root)])
                self.assertEqual(self.set_phase(root).returncode, 0, self.set_phase(root).stderr)

    def test_opt_out_needs_a_reason_and_mobile_is_untouched(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); project(root)
            self.meta(root, framework="next", ui="shadcn", design_lint="none", registry_intake="none")
            self.assertEqual(self.set_phase(root).returncode, 1)
            m = json.loads((root / ".workflow/meta.json").read_text())
            m["stack_config"]["registry_intake_reason"] = "internal prototype, no third-party registries"
            write(root, ".workflow/meta.json", m)
            self.assertEqual(self.set_phase(root).returncode, 0)
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); self.meta(root, framework="expo-rn")
            self.assertEqual(self.set_phase(root).returncode, 0)


if __name__ == "__main__":
    unittest.main()
