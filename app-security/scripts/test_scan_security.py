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

    def test_action_returning_a_row_is_found(self) -> None:
        self.next_app()
        self.write("app/actions.ts", '"use server"\nexport async function create(v: V) {\n  const u = await getCurrentUserId()\n  return await db.insert(x).values(v).returning()\n}\n')
        self.assertEqual(self.find("action-returns-row").status, ss.FOUND)


class RouteHandlers(Fixture):
    def test_route_handler_post_without_session_is_found(self) -> None:
        self.next_app()
        self.write("app/api/items/route.ts", "export async function POST(req: Request) {\n  return Response.json(await req.json())\n}\n")
        self.assertEqual(self.find("route-handler-unauthenticated").status, ss.FOUND)

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

    def test_raw_sql(self) -> None:
        self.next_app()
        self.write("lib/server/search.ts", "export const q = (id: string) => db.execute(sql.raw(`select * from t where id = ${id}`))\n")
        self.assertEqual(self.find("raw-sql").status, ss.FOUND)


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
        self.write("lib/db/index.ts", "export const db = createDb()\n")
        self.assertEqual(self.find("server-only-missing").status, ss.FOUND)
        self.write("lib/db/index.ts", 'import "server-only"\nexport const db = createDb()\n')
        self.assertEqual(self.find("server-only-missing").status, ss.OK)

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


if __name__ == "__main__":
    unittest.main()
