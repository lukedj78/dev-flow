"""Tests for scan_security.py — the fifth pre-deploy gate's scanner. Temp trees only; no tool is executed.

    cd app-security/scripts && python3 -m unittest test_scan_security -v

Why this exists: none of the four other gates asks whether the app's code can be attacked. Next.js makes every
exported Server Action a public POST endpoint, so authorization has to live inside each one; a page or proxy
check does not cover it. The scanner's own checks are heuristics that point the review at the right files, and
the tests pin both halves of each: it finds the case, and it stays quiet on the right code.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import scan_security as ss  # noqa: E402

UNAUTH = '"use server"\nimport { db } from "@/lib/db"\nexport async function deleteInvoice(id: string) {\n  await db.delete(invoices).where(eq(invoices.id, id))\n}\n'
AUTHED = UNAUTH.replace("  await db.delete", "  const userId = await getCurrentUserId()\n  await db.delete")


class Fixture(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def write(self, rel: str, text: str) -> None:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def next_app(self) -> None:
        self.write("app/page.tsx", "export default function P() { return null }\n")
        self.write("package.json", '{"dependencies": {"next": "16.4.2"}}')

    def find(self, check: str) -> ss.Finding:
        return next(f for f in ss.code_findings(self.root) if f.check == check)


class ServerActions(Fixture):
    def test_action_without_session_is_found(self) -> None:
        self.next_app()
        self.write("app/actions.ts", UNAUTH)
        f = self.find("server-action-unauthenticated")
        self.assertEqual(f.status, ss.FOUND)
        self.assertTrue(any("actions.ts" in w and "deleteInvoice" in w for w in f.where), f.where)
        self.assertEqual(f.routed_to, "module-add auth")

    def test_action_with_session_is_ok(self) -> None:
        self.next_app()
        self.write("app/actions.ts", AUTHED)
        self.assertEqual(self.find("server-action-unauthenticated").status, ss.OK)

    def test_a_mention_is_not_a_call(self) -> None:
        self.next_app()
        self.write("app/actions.ts", UNAUTH.replace("  await db.delete", "  // auth: TODO getSession later\n  const auth = true\n  await db.delete"))
        self.assertEqual(self.find("server-action-unauthenticated").status, ss.FOUND)

    def test_declared_helper_is_a_session_call(self) -> None:
        self.next_app()
        self.write("app/actions.ts", UNAUTH.replace("  await db.delete", "  await requireOwner(id)\n  await db.delete"))
        self.assertEqual(self.find("server-action-unauthenticated").status, ss.FOUND)
        self.write(".workflow/meta.json", json.dumps({"stack_config": {"security_session_calls": ["requireOwner"]}}))
        self.assertEqual(self.find("server-action-unauthenticated").status, ss.OK)

    def test_a_local_helper_that_takes_the_session_counts(self) -> None:
        # found on fit-coach: run(input, schema, (who, p) => ...) takes the session; reviewer() calls getSession
        self.next_app()
        self.write("lib/server/media.ts", '''"use server"
async function reviewer() {
  const s = await getSession()
  return s?.user.id
}
async function run(input: unknown, act: (who: string) => Promise<void>) {
  const who = await reviewer()
  if (!who) return
  await act(who)
}
export async function approveMediaAction(input: unknown) {
  return run(input, (who) => approve(db, who))
}
''')
        self.assertEqual(self.find("server-action-unauthenticated").status, ss.OK)
        self.write("lib/server/media.ts", '''"use server"
async function run(input: unknown, act: () => Promise<void>) {
  await act()
}
export async function approveMediaAction(input: unknown) {
  return run(input, () => approve(db))
}
''')
        self.assertEqual(self.find("server-action-unauthenticated").status, ss.FOUND)

    def test_action_returning_a_row_is_found(self) -> None:
        self.next_app()
        self.write("app/actions.ts", '"use server"\nexport async function create(v: V) {\n  const u = await getCurrentUserId()\n  return await db.insert(x).values(v).returning()\n}\n')
        self.assertEqual(self.find("action-returns-row").status, ss.FOUND)


class RouteHandlers(Fixture):
    def test_route_handler_post_without_session_is_found(self) -> None:
        self.next_app()
        self.write("app/api/items/route.ts", "export async function POST(req: Request) {\n  return Response.json(await req.json())\n}\n")
        self.assertEqual(self.find("route-handler-unauthenticated").status, ss.FOUND)

    def test_an_action_or_component_is_not_a_session_helper(self) -> None:
        # found on fit-coach: every component that called an action, and every POST that called apiUser,
        # became a "session helper" — and an unrelated cron POST then passed as authenticated
        self.next_app()
        self.write("app/api/v1/route.ts", "export async function POST(r: Request) {\n  const u = await getSession()\n  return Response.json(u)\n}\n")
        self.write("app/actions.ts", '"use server"\nexport async function saveAction(v: V) {\n  await getCurrentUserId()\n}\n')
        self.write("app/form.tsx", '"use client"\nexport function runReminders() {\n  return saveAction(1)\n}\n')
        self.write("app/api/cron/route.ts", "export async function POST(r: Request) {\n  return Response.json(await runReminders())\n}\n")
        f = self.find("route-handler-unauthenticated")
        self.assertEqual(f.status, ss.FOUND)
        self.assertTrue(any("cron" in w for w in f.where), f.where)

    def test_route_get_is_not_judged(self) -> None:
        self.next_app()
        self.write("app/api/items/route.ts", "export async function GET() {\n  return Response.json([])\n}\n")
        self.assertEqual(self.find("route-handler-unauthenticated").status, ss.OK)


class Queries(Fixture):
    def test_query_by_input_id_without_owner_filter_is_found(self) -> None:
        self.next_app()
        self.write("lib/server/invoices.ts", "export async function get(id: string) {\n  return db.select().from(invoices).where(eq(invoices.id, id))\n}\n")
        self.assertEqual(self.find("query-by-id-unscoped").status, ss.FOUND)
        self.write("lib/server/invoices.ts", "export async function get(id: string, userId: string) {\n  return db.select().from(invoices).where(and(eq(invoices.id, id), eq(invoices.userId, userId)))\n}\n")
        self.assertEqual(self.find("query-by-id-unscoped").status, ss.OK)

    def test_a_workspace_filter_or_the_user_itself_is_scoped(self) -> None:
        # found on fit-coach: eq(clients.workspaceId, …) is a tenant filter; eq(user.id, userId) is the user
        self.next_app()
        self.write("lib/clients/a.ts", "export const a = (i: I) => db.select().from(clients).where(and(eq(clients.id, i.clientId), eq(clients.workspaceId, i.workspaceId)))\n"
                   "export const b = (userId: string) => db.select().from(user).where(eq(user.id, userId))\n"
                   "export const c = (s: S) => db.select().from(user).where(eq(user.id, session.user.id))\n")
        self.assertEqual(self.find("query-by-id-unscoped").status, ss.OK)

    def test_an_owner_check_elsewhere_in_the_function_counts(self) -> None:
        # found on fit-coach: the owner is checked in a join, or verified earlier in the same function
        self.next_app()
        self.write("lib/w.ts", '''export async function log(db: D, link: L, input: I) {
  const [day] = await db.select().from(planDays)
    .innerJoin(planAssignments, and(eq(planAssignments.planId, planDays.planId), eq(planAssignments.workspaceId, link.workspaceId)))
    .where(eq(planDays.id, input.dayId))
}
export async function rename(db: D, input: I) {
  const [p] = await db.select().from(plans).where(and(eq(plans.id, input.planId), eq(plans.workspaceId, input.workspaceId)))
  if (!p) throw new Error("not_found")
  await db.update(plans).set({ name: input.name }).where(eq(plans.id, input.planId))
}
''')
        self.assertEqual(self.find("query-by-id-unscoped").status, ss.OK)
        self.write("lib/sex.ts", "export async function getClientSex(db: D, clientId: string) {\n"
                   "  const [c] = await db.select({ sex: clients.sex }).from(clients).where(eq(clients.id, clientId))\n}\n")
        f = self.find("query-by-id-unscoped")
        self.assertEqual(f.status, ss.FOUND)
        self.assertEqual([w.split(":")[0] for w in f.where], ["lib/sex.ts"])

    def test_raw_sql(self) -> None:
        self.next_app()
        self.write("lib/server/search.ts", "export const q = (id: string) => db.execute(sql.raw(`select * from t where id = ${id}`))\n")
        self.assertEqual(self.find("raw-sql").status, ss.FOUND)

    def test_generated_and_hidden_directories_are_skipped(self) -> None:
        # found on fit-coach: eve's snapshots and the Nitro build output were read as source
        self.next_app()
        bad = "export const q = (id: string) => db.execute(sql.raw(`select * from t where id = ${id}`))\n"
        for d in (".eve/dev-runtime/snapshots/x", ".output/server", "coverage", "out"):
            self.write(f"{d}/gen.mjs", bad)
        self.assertEqual(self.find("raw-sql").status, ss.OK)


class Environment(Fixture):
    def test_public_env_secret_is_found(self) -> None:
        self.next_app()
        self.write(".env.example", "NEXT_PUBLIC_SUPABASE_ANON_KEY=\nNEXT_PUBLIC_POSTHOG_KEY=\n")
        self.assertEqual(self.find("public-env-secret").status, ss.OK)
        self.write(".env.example", "NEXT_PUBLIC_STRIPE_SECRET_KEY=\nEXPO_PUBLIC_API_TOKEN=\n")
        f = self.find("public-env-secret")
        self.assertEqual(f.status, ss.FOUND)
        self.assertIn("NEXT_PUBLIC_STRIPE_SECRET_KEY", " ".join(f.where))
        self.assertIn("EXPO_PUBLIC_API_TOKEN", " ".join(f.where))
        self.assertEqual(f.routed_to, "the user")

    def test_server_only_missing(self) -> None:
        self.next_app()
        self.write("lib/db/index.ts", "export const db = drizzle(neon(process.env.DATABASE_URL!))\n")
        self.assertEqual(self.find("server-only-missing").status, ss.FOUND)
        self.write("lib/db/index.ts", 'import "server-only"\nexport const db = drizzle(neon(process.env.DATABASE_URL!))\n')
        self.assertEqual(self.find("server-only-missing").status, ss.OK)

    def test_server_only_is_asked_only_of_modules_that_hold_a_secret_or_the_database(self) -> None:
        # found on fit-coach: 34 of 35 were Server Action files (already server-only), Drizzle schemas or types
        self.next_app()
        self.write("lib/server/notes.ts", '"use server"\nexport async function save() { await db.insert(notes) }\n')
        self.write("lib/db/notes-schema.ts", "import { pgTable, text } from \"drizzle-orm/pg-core\"\nexport const notes = pgTable(\"notes\", { id: text(\"id\") })\n")
        self.write("lib/db/__tests__/notes.test.ts", "const url = process.env.TEST_DATABASE_URL\n")
        self.write("lib/server/result.ts", "export type Result<T> = { ok: true; data: T } | { ok: false }\n")
        self.assertEqual(self.find("server-only-missing").status, ss.OK)
        self.write("lib/server/mail.ts", "export const send = (to: string) => fetch(URL, { headers: { key: process.env.RESEND_API_KEY! } })\n")
        self.assertEqual(self.find("server-only-missing").where, ["lib/server/mail.ts"])

    def test_security_headers(self) -> None:
        self.next_app()
        self.write("next.config.ts", "export default {}\n")
        self.assertEqual(self.find("security-headers-missing").status, ss.FOUND)
        self.write("next.config.ts", "export default { async headers() { return [{ source: '/(.*)', headers: [{ key: 'Content-Security-Policy', value: \"default-src 'self'\" }] }] } }\n")
        self.assertEqual(self.find("security-headers-missing").status, ss.OK)


class Layouts(Fixture):
    def test_monorepo_packages_are_scanned(self) -> None:
        self.write("apps/web/app/page.tsx", "export default function P() { return null }\n")
        self.write("apps/web/package.json", '{"dependencies": {"next": "16.4.2"}}')
        self.write("packages/api/src/actions.ts", UNAUTH)
        f = self.find("server-action-unauthenticated")
        self.assertEqual(f.status, ss.FOUND)
        self.assertTrue(any("packages/api" in w for w in f.where), f.where)

    def test_expo_project_skips_next_checks(self) -> None:
        self.write("app.json", '{"expo": {"name": "x"}}')
        self.write(".env", "EXPO_PUBLIC_SECRET=abc\n")
        found = {f.check: f for f in ss.code_findings(self.root)}
        for check in ("server-action-unauthenticated", "route-handler-unauthenticated", "security-headers-missing"):
            self.assertEqual(found[check].status, ss.OK)
            self.assertIn("not applicable", found[check].detail)
        self.assertEqual(found["public-env-secret"].status, ss.FOUND)

    def test_node_modules_ignored(self) -> None:
        self.next_app()
        self.write("node_modules/pkg/actions.ts", UNAUTH)
        self.assertEqual(self.find("server-action-unauthenticated").status, ss.OK)

    def test_every_check_is_reported(self) -> None:
        self.next_app()
        self.assertEqual({f.check for f in ss.code_findings(self.root)}, set(ss.CODE_CHECKS))


FIX = HERE / "fixtures"


class FakeTools:
    """An injectable `which` and `run`: which tools exist, and what each command prints and exits with."""

    def __init__(self, present: set, results: dict | None = None) -> None:
        self.present, self.results, self.calls, self.cwds = present, results or {}, [], []

    def which(self, name: str):
        return f"/usr/local/bin/{name}" if name in self.present else None

    def run(self, argv, **kwargs):
        import subprocess
        self.calls.append(list(argv))
        self.cwds.append(kwargs.get("cwd"))
        key = (argv[0], argv[1]) if argv[0] in ("gitleaks", "pnpm", "npm") else argv[0]
        code, out = self.results.get(key, (0, ""))
        if argv[0] == "gitleaks" and "--report-path" in argv:   # gitleaks writes its JSON to the report file
            Path(argv[argv.index("--report-path") + 1]).write_text(out or "[]", encoding="utf-8")
            out = ""
        return subprocess.CompletedProcess(argv, code, stdout=out, stderr="")


def fixture(name: str) -> str:
    return (FIX / name).read_text(encoding="utf-8")


class Tools(Fixture):
    def tools(self, fake: FakeTools) -> dict:
        return {f.check: f for f in ss.tool_findings(self.root, run=fake.run, which=fake.which)}

    def test_no_tools_means_not_checked(self) -> None:
        self.next_app()
        got = self.tools(FakeTools(set()))
        for check in ("dependencies", "secrets-working-tree", "secrets-history", "static-analysis"):
            self.assertEqual(got[check].status, ss.NOT_CHECKED, check)
        import io
        from contextlib import redirect_stdout
        out = io.StringIO()
        with redirect_stdout(out):
            ss.print_report(self.root, list(got.values()))
        self.assertNotIn("clean", out.getvalue().lower())

    def test_osv_findings_parsed(self) -> None:
        self.next_app()
        f = self.tools(FakeTools({"osv-scanner"}, {"osv-scanner": (1, fixture("osv.json"))}))["dependencies"]
        self.assertEqual(f.status, ss.FOUND)
        self.assertTrue(any("next" in w for w in f.where) and any("axios" in w for w in f.where), f.where)
        self.assertEqual(self.tools(FakeTools({"osv-scanner"}, {"osv-scanner": (0, '{"results": []}')}))["dependencies"].status, ss.OK)

    def test_osv_errors_are_not_checked(self) -> None:
        self.next_app()
        for code in (127, 128):
            with self.subTest(code=code):
                f = self.tools(FakeTools({"osv-scanner"}, {"osv-scanner": (code, "")}))["dependencies"]
                self.assertEqual(f.status, ss.NOT_CHECKED)

    def test_falls_back_to_pnpm_then_npm_audit(self) -> None:
        self.next_app()
        self.write("pnpm-lock.yaml", "lockfileVersion: '9.0'\n")
        fake = FakeTools({"pnpm", "npm"}, {("pnpm", "audit"): (1, fixture("pnpm-audit.json"))})
        f = self.tools(fake)["dependencies"]
        self.assertEqual(f.status, ss.FOUND)
        self.assertIn(["pnpm", "audit", "--json", "--prod"], fake.calls)
        (self.root / "pnpm-lock.yaml").unlink()
        fake = FakeTools({"npm"}, {("npm", "audit"): (1, fixture("npm-audit.json"))})
        self.assertEqual(self.tools(fake)["dependencies"].status, ss.FOUND)
        self.assertIn(["npm", "audit", "--json", "--omit=dev"], fake.calls)
        self.assertEqual(Path(fake.cwds[-1]), self.root)   # the audit reads the project's lockfile, not the caller's
        offline = FakeTools({"npm"}, {("npm", "audit"): (1, "npm error code ENOTFOUND")})
        self.assertEqual(self.tools(offline)["dependencies"].status, ss.NOT_CHECKED)

    def test_gitleaks_working_tree_and_history(self) -> None:
        self.next_app()
        fake = FakeTools({"gitleaks"}, {("gitleaks", "dir"): (0, "[]"), ("gitleaks", "git"): (1, fixture("gitleaks.json"))})
        got = self.tools(fake)
        self.assertEqual(got["secrets-working-tree"].status, ss.OK)
        self.assertEqual(got["secrets-history"].status, ss.FOUND)
        self.assertEqual(got["secrets-history"].routed_to, "the user")
        import io
        from contextlib import redirect_stdout
        out = io.StringIO()
        with redirect_stdout(out):
            ss.print_report(self.root, list(got.values()) + ss.code_findings(self.root))
        lines = [l for l in out.getvalue().splitlines() if l.strip().startswith(("!", "·", "?"))]
        self.assertTrue(lines[0].strip().startswith("! secrets-history"), lines[:2])
        self.assertIn("rotate", out.getvalue())

    def test_gitleaks_bad_flag_is_not_checked(self) -> None:
        self.next_app()
        got = self.tools(FakeTools({"gitleaks"}, {("gitleaks", "dir"): (126, ""), ("gitleaks", "git"): (126, "")}))
        self.assertEqual(got["secrets-working-tree"].status, ss.NOT_CHECKED)

    def test_semgrep_results_parsed(self) -> None:
        self.next_app()
        f = self.tools(FakeTools({"semgrep"}, {"semgrep": (0, fixture("semgrep.json"))}))["static-analysis"]
        self.assertEqual(f.status, ss.FOUND)
        self.assertTrue(any("page.tsx" in w for w in f.where))

    def test_semgrep_absent_is_not_checked(self) -> None:
        self.next_app()
        self.assertEqual(self.tools(FakeTools(set()))["static-analysis"].status, ss.NOT_CHECKED)

    def test_commands_are_exactly_the_documented_ones(self) -> None:
        self.next_app()
        fake = FakeTools({"osv-scanner", "gitleaks", "semgrep"})
        self.tools(fake)
        root = str(self.root)
        strip = lambda argv: [a for i, a in enumerate(argv) if not (i and argv[i - 1] == "--report-path")]
        self.assertIn(["osv-scanner", "scan", "source", "-r", root, "--format", "json"], fake.calls)
        self.assertIn(["gitleaks", "dir", root, "--redact", "--report-format", "json", "--report-path"], [strip(c) for c in fake.calls])
        self.assertIn(["gitleaks", "git", root, "--redact", "--report-format", "json", "--report-path"], [strip(c) for c in fake.calls])
        self.assertIn(["semgrep", "scan", "--config", "p/nextjs", "--config", "p/typescript", "--metrics", "off", "--json", root], fake.calls)

    def test_a_timeout_is_not_checked(self) -> None:
        import subprocess
        self.next_app()
        def boom(argv, **kwargs):
            raise subprocess.TimeoutExpired(argv, 600)
        got = {f.check: f for f in ss.tool_findings(self.root, run=boom, which=lambda n: "/x/" + n)}
        self.assertEqual(got["dependencies"].status, ss.NOT_CHECKED)


if __name__ == "__main__":
    unittest.main()
