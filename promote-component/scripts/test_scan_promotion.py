"""Tests for scan_promotion.py — the web scan covers components/<area>/ as well as app/**/_components/.

    cd promote-component/scripts && python3 -m unittest test_scan_promotion
"""

from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import promote as pr  # noqa: E402
import scan_promotion as sp  # noqa: E402


def write(root: Path, rel: str, text: str = "export function X() { return null }\n") -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def imp(spec: str) -> str:
    return f'import {{ X }} from "{spec}"\n'


class WebAreas(unittest.TestCase):
    def project(self, root: Path) -> None:
        write(root, ".workflow/meta.json", '{"stack": {"framework": "next"}}')
        write(root, "components/ui/button.tsx")
        write(root, "components/brand/logo.tsx")
        write(root, "components/auth/code-input.tsx")
        write(root, "components/trips/parts.tsx")
        write(root, "components/traveller/parts.tsx")
        write(root, "components/auth/auth-shell.tsx")
        # code-input: auth itself + two other areas → L2
        write(root, "components/auth/sign-in.tsx", imp("./code-input"))
        write(root, "components/privacy/delete.tsx", imp("@/components/auth/code-input"))
        write(root, "components/traveller/email.tsx", imp("@/components/auth/code-input"))
        # auth-shell: only the (auth) pages → stays
        for page in ("sign-in", "sign-up", "reset"):
            write(root, f"app/(auth)/{page}/page.tsx", imp("@/components/auth/auth-shell"))
        # two files named parts: each used inside its own area only
        write(root, "components/trips/a.tsx", imp("./parts"))
        write(root, "components/traveller/b.tsx", imp("./parts"))
        for i in range(3):
            write(root, f"components/brand/use{i}.tsx", imp("@/components/brand/logo"))

    def test_components_area_is_scanned_and_suggested(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); self.project(root)
            rows = {(r[0], r[2]): r for r in sp.scan_web_areas(root)}
            self.assertIn("Promote to L2", rows[("code-input", "L1 (components/auth)")][3])
            self.assertEqual(rows[("code-input", "L1 (components/auth)")][1], 3)
            self.assertIn("OK — stays", rows[("auth-shell", "L1 (components/auth)")][3], "pages of one group are its consumers")
            self.assertEqual(rows[("parts", "L1 (components/trips)")][1], 1, "same file name in another area is not an importer")
            self.assertNotIn(("button", "L1 (components/ui)"), rows)
            self.assertFalse(any(r[0] == "logo" for r in rows.values()), "brand is app-wide by design")

    def test_report_is_not_empty_without_underscore_components(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); self.project(root)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                sp.scan_one_root_web(root, "next")
            self.assertIn("components/<area>/", out.getvalue())
            self.assertIn("`code-input`", out.getvalue())

    def test_underscore_components_still_scanned(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write(root, "app/(app)/posts/_components/PostCard.tsx")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                sp.scan_one_root_web(root, "next")
            self.assertIn("`PostCard`", out.getvalue())


class SuffixNames(unittest.TestCase):
    """A component whose name ends another's (Card, PostCard) must not be mistaken for it. Found on a branch of
    2026-08-12, recovered 2026-10-19: promoting Card rewrote the import of PostCard, and the scan counted PostCard's
    importers as Card's."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        write(self.root, "app/a/page.tsx", 'import { Card } from "./_components/Card"\n')
        write(self.root, "app/b/page.tsx", 'import { PostCard } from "@/components/feed/PostCard"\n')

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_scan_counts_only_the_component_itself(self) -> None:
        self.assertEqual({p.relative_to(self.root).as_posix() for p in sp.count_imports("Card", self.root)},
                         {"app/a/page.tsx"})

    def test_promote_finds_only_the_component_itself(self) -> None:
        self.assertEqual([p.relative_to(self.root).as_posix() for p in pr.find_importers("Card", self.root)],
                         ["app/a/page.tsx"])

    def test_promote_never_rewrites_another_components_import(self) -> None:
        importers = [self.root / "app/a/page.tsx", self.root / "app/b/page.tsx"]
        pr.rewrite_imports(importers, [], self.root / "components/shared/Card.tsx", self.root, "Card")
        self.assertEqual((self.root / "app/b/page.tsx").read_text(), 'import { PostCard } from "@/components/feed/PostCard"\n')
        self.assertIn('"@/components/shared/Card"', (self.root / "app/a/page.tsx").read_text())


if __name__ == "__main__":
    unittest.main()
