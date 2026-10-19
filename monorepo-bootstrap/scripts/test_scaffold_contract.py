"""The monorepo scripts must agree with each other: what scaffold-web.sh / scaffold-mobile.sh make each app's
tsconfig extend, and what verify.ts checks, must be files init-monorepo.sh actually writes.

Found on a branch of 2026-08-12 and recovered on 2026-10-19: the scaffold scripts extended `../../tsconfig.base.json`,
which init never writes (it builds the Turborepo `packages/typescript-config/` preset instead), so `tsc` failed on
every generated app and verify.ts — checking for that same root file — kept the phase from ever reaching scaffolded.
init-monorepo.sh only writes files, so it runs here for real; the scaffold scripts need create-next-app and the
network, so they are read, not run.
"""

from __future__ import annotations

import re
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SLUG = "demo"


class Contract(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls._tmp.name)
        r = subprocess.run(["bash", str(HERE / "init-monorepo.sh"), str(cls.root), SLUG], capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def resolve(self, extends: str, app: str) -> Path:
        """An `extends` value as the app sees it: a workspace package name, or a path relative to apps/<app>/."""
        pkg = f"@{SLUG}/typescript-config/"
        target = extends.replace("${SLUG}", SLUG).replace("$SLUG", SLUG)
        if target.startswith(pkg):
            return self.root / "packages" / "typescript-config" / target[len(pkg):]
        return (self.root / "apps" / app / target).resolve()

    def test_each_app_extends_a_preset_init_writes(self) -> None:
        for script, app in (("scaffold-web.sh", "web"), ("scaffold-mobile.sh", "mobile")):
            text = (HERE / script).read_text(encoding="utf-8")
            m = re.search(r"cfg\.extends\s*=\s*['\"]([^'\"]+)['\"]", text)
            self.assertIsNotNone(m, script)
            self.assertTrue(self.resolve(m.group(1), app).is_file(),
                            f"{script} extends {m.group(1)}, which init-monorepo.sh does not write")

    def test_each_app_depends_on_the_preset_package(self) -> None:
        # without the workspace dependency pnpm never links the preset, and the extends cannot resolve
        for script in ("scaffold-web.sh", "scaffold-mobile.sh"):
            text = (HERE / script).read_text(encoding="utf-8")
            found = re.search(r"typescript-config['\"]?\s*\]?\s*=\s*['\"]workspace:\*['\"]", text)
            self.assertTrue(found, f"{script} never adds @<slug>/typescript-config as a workspace dependency")

    def test_verify_checks_only_files_init_writes(self) -> None:
        text = (HERE / "verify.ts").read_text(encoding="utf-8")
        for path in re.findall(r'name: "root: [^"]*", run: \(\) => fileExists\("([^"]+)"\)', text):
            self.assertTrue((self.root / path).exists(), f"verify.ts checks {path}, which init-monorepo.sh does not write")
        self.assertIn('fileExists("packages/typescript-config/base.json")', text)

    def test_init_header_names_what_it_writes(self) -> None:
        header = (HERE / "init-monorepo.sh").read_text(encoding="utf-8").split("set -euo")[0]
        writes = header[header.index("# Writes:"):].split("\n# Idempotent")[0].split("No tsconfig")[0]
        self.assertNotIn("tsconfig.base.json", writes)   # it may say it does NOT write one
        self.assertFalse((self.root / "tsconfig.base.json").exists())


if __name__ == "__main__":
    unittest.main()
