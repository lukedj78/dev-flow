"""Tests for data_residency.py and the gate that relies on it. No network.

    cd dev-flow/scripts && python3 -m unittest test_data_residency -v
"""

from __future__ import annotations

import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import data_residency as dr  # noqa: E402


def write(root: Path, rel: str, data) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(data if isinstance(data, str) else json.dumps(data, indent=2))
    return p


def project(root: Path, phase: str = "design_extracted", **stack) -> None:
    # the other two scaffold gates are opted out: this file tests the residency gate only
    write(root, ".workflow/meta.json", {"phase": phase, "stack": {"framework": "expo-rn", **stack}})


def run(*argv: str) -> tuple[int, str]:
    out = io.StringIO()
    with redirect_stdout(out):
        rc = dr.main(list(argv))
    return rc, out.getvalue()


class Regions(unittest.TestCase):
    def test_classification(self) -> None:
        cases = {
            "fra1": "eu", "cdg1": "eu", "dub1": "eu", "arn1": "eu", "aws-eu-central-1": "eu",
            "eu-west-1": "eu", "europe-west3": "eu", "fr-par": "eu", "nl-ams": "eu", "pl-waw": "eu", "it-mil": "eu", "fsn1": "eu", "hel1": "eu",
            "gra": "non-eu",  # an ambiguous short code is not assumed to be EU
            "Frankfurt": "eu", "iad1": "non-eu", "us-east-1": "non-eu", "sfo1": "non-eu",
            "lhr1": "adequacy", "eu-west-2": "adequacy", "europe-west6": "adequacy",
            "global": "global", "": "unknown",
        }
        for region, expected in cases.items():
            with self.subTest(region=region):
                self.assertEqual(dr.region_class(region), expected)


class Decide(unittest.TestCase):
    def test_answers_suggest_and_record(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); project(root)
            rc, out = run("decide", str(root), "--eu-subjects", "yes", "--categories", "identity-documents,tax,contact",
                          "--residency-obligations", "no", "--avoid-cloud-act", "yes")
            self.assertEqual(rc, 0)
            meta = json.loads((root / ".workflow/meta.json").read_text())
            self.assertEqual(meta["stack"]["data_residency"], "eu-sovereign")
            self.assertEqual(meta["compliance"]["data_categories"], ["identity-documents", "tax", "contact"])
            self.assertEqual(meta["stack_config"]["data_residency_answers"]["special_categories"], ["identity-documents", "tax"])
            self.assertIn("DPIA", out)
            self.assertTrue((root / dr.REGISTER_MD).exists())
        self.assertEqual(dr.suggest(False, [], True, True), "none")
        self.assertEqual(dr.suggest(True, ["contact"], False, False), "eu")

    def test_unknown_category_refused(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); project(root)
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                rc = dr.main(["decide", str(root), "--eu-subjects", "yes", "--categories", "passport-scans",
                              "--residency-obligations", "no", "--avoid-cloud-act", "no"])
            self.assertEqual(rc, 1)


class Register(unittest.TestCase):
    def test_non_eu_provider_is_flagged_not_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); project(root, data_residency="eu")
            rc, out = run("add", str(root), "--name", "Expo", "--service", "Push notifications", "--data", "device tokens",
                          "--region", "us-east-1", "--by", "rn-module-add")
            self.assertEqual(rc, 0, "a provider without an EU region never fails the module")
            self.assertIn("flagged, not blocked", out)
            meta = json.loads((root / ".workflow/meta.json").read_text())
            (row,) = meta["compliance"]["sub_processors"]
            self.assertTrue(any("not in the EU" in f for f in row["flags"]))
            self.assertTrue(any("transfer basis" in f for f in row["flags"]))
            md = (root / dr.REGISTER_MD).read_text()
            self.assertIn("| Expo | Push notifications | device tokens | us-east-1 |", md)
            # re-adding the same service replaces the row, and a DPF basis removes that flag
            run("add", str(root), "--name", "Expo", "--service", "Push notifications", "--data", "device tokens",
                "--region", "us-east-1", "--transfer", "dpf", "--eu-alternative", "none available")
            meta = json.loads((root / ".workflow/meta.json").read_text())
            (row,) = meta["compliance"]["sub_processors"]
            self.assertFalse(any("transfer basis" in f for f in row["flags"]))

    def test_sovereign_flags_us_control_even_in_an_eu_region(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); project(root, data_residency="eu-sovereign")
            run("add", str(root), "--name", "Vercel", "--service", "Hosting", "--data", "request logs",
                "--region", "fra1", "--transfer", "dpf", "--us-controlled")
            (row,) = json.loads((root / ".workflow/meta.json").read_text())["compliance"]["sub_processors"]
            self.assertTrue(any("CLOUD Act" in f for f in row["flags"]))
            self.assertFalse(any("not in the EU" in f for f in row["flags"]))

    def test_register_keeps_text_outside_markers(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); project(root, data_residency="eu")
            write(root, dr.REGISTER_MD, "# Sub-processors\n\nReviewed by our DPO on 2026-09-01.\n")
            run("add", str(root), "--name", "Neon", "--service", "Postgres", "--data", "accounts", "--region", "aws-eu-central-1",
                "--transfer", "none")
            run("render", str(root))
            md = (root / dr.REGISTER_MD).read_text()
            self.assertIn("Reviewed by our DPO", md)
            self.assertEqual(md.count(dr.MARK[0]), 1)


class Check(unittest.TestCase):
    def test_missing_rows_and_config_regions(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            project(root, data_residency="eu", deploy="vercel", db="neon-drizzle")
            write(root, "vercel.json", {"regions": ["iad1"]})
            write(root, ".env.example", "DATABASE_URL=postgresql://u:p@ep-x.us-east-2.aws.neon.tech/db\n")
            run("render", str(root))
            res = dr.check(root)
            text = "\n".join(res["warnings"])
            self.assertIn("implies Vercel", text)
            self.assertIn("implies Neon", text)
            self.assertIn("vercel.json sets region iad1", text)
            self.assertIn("us-east-2", text)
            self.assertTrue(res["decided"])
            rc, _ = run("check", str(root))
            self.assertEqual(rc, 0, "warnings inform; they do not fail")

    def test_undecided_fails(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); project(root)
            rc, _ = run("check", str(root))
            self.assertEqual(rc, 1)


class PhaseGate(unittest.TestCase):
    def set_phase(self, root: Path) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(HERE / "update_meta.py"), str(root), "set-phase", "scaffolded"],
                              capture_output=True, text=True, check=False)

    def test_only_an_undecided_residency_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); project(root)
            r = self.set_phase(root)
            self.assertEqual(r.returncode, 1)
            self.assertIn("data-residency decision", r.stderr)
            self.assertIn("data_residency.py decide", r.stderr)
            run("decide", str(root), "--eu-subjects", "yes", "--categories", "contact",
                "--residency-obligations", "no", "--avoid-cloud-act", "no")
            run("add", str(root), "--name", "RevenueCat", "--service", "In-app purchases", "--data", "purchase history",
                "--region", "us-east-1")
            r = self.set_phase(root)
            self.assertEqual(r.returncode, 0, "a flagged, non-EU provider does not block the phase: " + r.stderr)


if __name__ == "__main__":
    unittest.main()
