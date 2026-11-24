"""check_rls.py against a fake psql: the verdicts, without a database. (Measured live on Postgres 18 too.)"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
FAKE = '''import json, sys
state = json.load(open(sys.argv[sys.argv.index("-X") + 1]))
sql = sys.argv[sys.argv.index("-c") + 1]
out = []
if "from pg_roles where rolname = current_user" in sql:
    out = [state["role"]]
elif "rolsuper or r.rolbypassrls" in sql:
    out = [[r] for r in state["inherited"]]
elif "pg_has_role" in sql:
    out = [["app_rls"], [state["role"][0]]]
elif "has_table_privilege" in sql:
    out = state["tables"]
elif "from pg_policies" in sql:
    out = state["policies"]
elif sql.startswith("select count(*)"):
    out = [[str(state["rows"])]]
print("\\n".join("\\t".join(r) for r in out))
'''


class CheckRls(unittest.TestCase):
    def run_check(self, state: dict, root: Path | None = None) -> tuple[int, str]:
        with tempfile.TemporaryDirectory() as d:
            fake, st = Path(d) / "fake_psql.py", Path(d) / "state.json"
            fake.write_text(FAKE)
            st.write_text(json.dumps(state))
            args = [sys.executable, str(HERE / "check_rls.py"), "--url", f"{st}",
                    "--psql-cmd", f"{sys.executable} {fake}"]
            if root:
                args += ["--root", str(root)]
            r = subprocess.run(args, capture_output=True, text=True)
            return r.returncode, r.stdout

    good = {"role": ["app_user", "f", "f"], "inherited": [], "rows": 0,
            "tables": [["public", "projects", "t", "t", "t"]],
            "policies": [["tenant_isolation", "{public}", "(workspace_id = current_setting('app.workspace'::text, true))",
                          "(workspace_id = current_setting('app.workspace'::text, true))"]]}

    def test_clean(self) -> None:
        code, out = self.run_check(self.good)
        self.assertEqual(code, 0, out)
        self.assertIn("rls: clean", out)

    def test_superuser_fails(self) -> None:
        code, out = self.run_check({**self.good, "role": ["owner", "t", "t"]})
        self.assertEqual(code, 1)
        self.assertIn("FAIL  role: owner", out)

    def test_inherited_bypass_fails(self) -> None:
        code, out = self.run_check({**self.good, "inherited": ["neon_superuser"]})
        self.assertEqual(code, 1)
        self.assertIn("inherits from neon_superuser", out)

    def test_missing_force_or_policy_fails(self) -> None:
        code, out = self.run_check({**self.good, "tables": [["public", "leaky", "t", "f", "t"]], "policies": []})
        self.assertEqual(code, 1)
        self.assertIn("FAIL  flags: public.leaky", out)

    def test_permissive_true_policy_fails(self) -> None:
        open_all = ["open_all", "{public}", "true", ""]
        code, out = self.run_check({**self.good, "policies": [*self.good["policies"], open_all]})
        self.assertEqual(code, 1)
        self.assertIn("not filtering on app.workspace: open_all", out)

    def test_policy_for_another_role_does_not_count(self) -> None:
        code, out = self.run_check({**self.good, "policies": [["p", "{someone_else}", "(workspace_id = current_setting('app.workspace'::text, true))", ""]]})
        self.assertEqual(code, 1)
        self.assertIn("policies=0", out)

    def test_uncovered_table_fails_unless_allowed(self) -> None:
        state = {**self.good, "tables": [*self.good["tables"], ["public", "settings", "f", "f", "f"]]}
        code, out = self.run_check(state)
        self.assertEqual(code, 1)
        self.assertIn("FAIL  coverage: public.settings", out)

    def test_rows_without_tenant_fail(self) -> None:
        code, out = self.run_check({**self.good, "rows": 3})
        self.assertEqual(code, 1)
        self.assertIn("returns 3 row(s)", out)

    def test_neon_driver_in_code_fails(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "db.ts").write_text('import { neon } from "@neondatabase/serverless";\n')
            (Path(d) / "node_modules").mkdir()
            (Path(d) / "node_modules" / "ok.ts").write_text('import "@neondatabase/serverless";\n')
            code, out = self.run_check(self.good, Path(d))
        self.assertEqual(code, 1)
        self.assertIn("driver: found in db.ts", out)
        self.assertNotIn("node_modules", out)


if __name__ == "__main__":
    unittest.main()
