"""pixel_diff.py: the cases where a screenshot comparison lies.

The contract's target is **zero** changed pixels, so the tests that matter are the ones that could
quietly report zero when they should not, and the one that could report a difference when there is
none:

- one changed pixel must fail, because "almost zero" is not the rule;
- two images of different sizes must be **refused**, not scaled — scaling is what the tool this was
  ported from does, and it would both invent differences and hide a height regression;
- a file that cannot be read exits **2**, never 1, because "I could not look" must not arrive
  looking like "I looked and they differ";
- the decoder has to handle the PNG flavours a screenshot tool actually emits (RGBA from a browser,
  palette from an optimiser, 16 bit from a design tool), or a real zero-diff pair reports garbage.

    cd design-md-to-app/scripts && python3 -m unittest test_pixel_diff -v
"""

from __future__ import annotations

import io
import struct
import sys
import tempfile
import unittest
import zlib
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pixel_diff as pd  # noqa: E402

SIG = b"\x89PNG\r\n\x1a\n"


def _chunk(kind, body):
    crc = zlib.crc32(kind + body) & 0xFFFFFFFF
    return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", crc)


def build_png(path, width, height, raw_rows, color, depth=8, palette=None,
              trns=None, interlace=0):
    """Write a PNG from already-packed scanlines (no filtering), for decoder tests."""
    body = b"".join(b"\x00" + bytes(r) for r in raw_rows)
    out = SIG + _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, depth, color,
                                            0, 0, interlace))
    if palette is not None:
        out += _chunk(b"PLTE", b"".join(bytes(c) for c in palette))
    if trns is not None:
        out += _chunk(b"tRNS", bytes(trns))
    out += _chunk(b"IDAT", zlib.compress(body, 6)) + _chunk(b"IEND", b"")
    Path(path).write_bytes(out)


def solid(width, height, rgb):
    return [[rgb] * width for _ in range(height)]


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def rgb_png(self, name, rows):
        path = self.dir / name
        pd.write_png(str(path), len(rows[0]), len(rows), rows)
        return str(path)

    def cli(self, *argv):
        """Named cli, not run: a method called `run` shadows TestCase.run and the suite goes quiet."""
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = pd.main(list(argv))
        return code, out.getvalue(), err.getvalue()


class TestTheTarget(Base):
    def test_identical_is_zero_and_exits_zero(self):
        a = self.rgb_png("a.png", solid(40, 30, (12, 34, 56)))
        b = self.rgb_png("b.png", solid(40, 30, (12, 34, 56)))
        code, out, _ = self.cli(a, b)
        self.assertEqual(code, 0)
        self.assertIn("IDENTICAL", out)

    def test_one_changed_pixel_fails(self):
        rows = solid(40, 30, (255, 255, 255))
        a = self.rgb_png("a.png", rows)
        rows2 = [list(r) for r in rows]
        rows2[5][7] = (0, 0, 0)
        b = self.rgb_png("b.png", rows2)
        code, out, _ = self.cli(a, b)
        self.assertEqual(code, 1, "the contract's target is zero, so one pixel is a failure")
        self.assertIn("1 changed pixels", out)

    def test_max_changed_allows_a_budget_but_zero_is_the_default(self):
        rows = solid(20, 20, (255, 255, 255))
        a = self.rgb_png("a.png", rows)
        rows2 = [list(r) for r in rows]
        for x in range(3):
            rows2[0][x] = (0, 0, 0)
        b = self.rgb_png("b.png", rows2)
        self.assertEqual(self.cli(a, b)[0], 1)
        self.assertEqual(self.cli(a, b, "--max-changed", "3")[0], 0)
        self.assertEqual(self.cli(a, b, "--max-changed", "2")[0], 1)

    def test_tolerance_absorbs_antialiasing_noise_only(self):
        a = self.rgb_png("a.png", solid(10, 10, (100, 100, 100)))
        b = self.rgb_png("b.png", solid(10, 10, (102, 100, 100)))
        self.assertEqual(self.cli(a, b)[0], 1)
        self.assertEqual(self.cli(a, b, "--tolerance", "2")[0], 0)
        self.assertEqual(self.cli(a, b, "--tolerance", "1")[0], 1)


class TestSizeMismatch(Base):
    """The divergence from the ported tool, and the reason it exists."""

    def test_different_sizes_are_refused_not_scaled(self):
        a = self.rgb_png("a.png", solid(40, 30, (10, 10, 10)))
        b = self.rgb_png("b.png", solid(40, 50, (10, 10, 10)))
        code, out, _ = self.cli(a, b)
        self.assertEqual(code, 1)
        self.assertIn("SIZE MISMATCH", out)
        self.assertIn("40x30", out)
        self.assertIn("40x50", out)

    def test_size_mismatch_reports_no_score_rather_than_a_flattering_one(self):
        a = pd.read_png(self.rgb_png("a.png", solid(8, 8, (0, 0, 0))))
        b = pd.read_png(self.rgb_png("b.png", solid(8, 9, (0, 0, 0))))
        report, diff = pd.compare(a, b)
        self.assertEqual(report["status"], "size mismatch")
        self.assertIsNone(report["changed"])
        self.assertIsNone(diff)

    def test_a_taller_after_is_not_silently_cropped(self):
        """Two images identical over the shared height still fail: the extra height is the finding."""
        a = self.rgb_png("a.png", solid(16, 16, (7, 7, 7)))
        b = self.rgb_png("b.png", solid(16, 24, (7, 7, 7)))
        self.assertEqual(self.cli(a, b)[0], 1)


class TestRegions(Base):
    def test_two_blobs_are_two_regions_biggest_first(self):
        rows = [list(r) for r in solid(200, 120, (255, 255, 255))]
        for y in range(4, 12):            # small blob, top left
            for x in range(4, 10):
                rows[y][x] = (0, 0, 0)
        for y in range(80, 110):          # big blob, bottom right
            for x in range(150, 190):
                rows[y][x] = (0, 0, 0)
        a = self.rgb_png("a.png", solid(200, 120, (255, 255, 255)))
        b = self.rgb_png("b.png", rows)
        before, after = pd.read_png(a), pd.read_png(b)
        report, _ = pd.compare(before, after)
        self.assertEqual(len(report["regions"]), 2)
        self.assertGreater(report["regions"][0]["changed"], report["regions"][1]["changed"])
        self.assertEqual(report["regions"][0]["where"], "bottom right")
        self.assertEqual(report["regions"][1]["where"], "top left")

    def test_identical_images_have_no_regions(self):
        a = pd.read_png(self.rgb_png("a.png", solid(64, 64, (1, 2, 3))))
        report, _ = pd.compare(a, a)
        self.assertEqual(report["regions"], [])
        self.assertEqual(report["status"], "identical")


class TestDecoder(Base):
    """A screenshot arrives in whatever flavour the tool that took it emits."""

    def test_rgba_is_composited_over_white(self):
        path = self.dir / "rgba.png"
        row = bytes([255, 0, 0, 128]) * 2
        build_png(path, 2, 1, [row], color=6)
        w, h, rows = pd.read_png(str(path))
        self.assertEqual((w, h), (2, 1))
        self.assertEqual(rows[0][0], (255, 127, 127))

    def test_greyscale(self):
        path = self.dir / "grey.png"
        build_png(path, 3, 1, [bytes([0, 128, 255])], color=0)
        _, _, rows = pd.read_png(str(path))
        self.assertEqual(rows[0], [(0, 0, 0), (128, 128, 128), (255, 255, 255)])

    def test_palette_with_transparency(self):
        path = self.dir / "pal.png"
        build_png(path, 2, 1, [bytes([0, 1])], color=3,
                  palette=[(255, 0, 0), (0, 0, 255)], trns=[0])
        _, _, rows = pd.read_png(str(path))
        self.assertEqual(rows[0][0], (255, 255, 255), "index 0 is fully transparent, so white")
        self.assertEqual(rows[0][1], (0, 0, 255))

    def test_sixteen_bit_is_read_as_eight(self):
        path = self.dir / "deep.png"
        row = struct.pack(">HHH", 65535, 0, 32768)
        build_png(path, 1, 1, [row], color=2, depth=16)
        _, _, rows = pd.read_png(str(path))
        self.assertEqual(rows[0][0], (255, 0, 128))

    def test_low_bit_depth_greyscale_is_scaled_to_full_range(self):
        path = self.dir / "bw.png"
        build_png(path, 8, 1, [bytes([0b10101010])], color=0, depth=1)
        _, _, rows = pd.read_png(str(path))
        self.assertEqual(rows[0][0], (255, 255, 255))
        self.assertEqual(rows[0][1], (0, 0, 0))

    def test_interlaced_is_refused_with_the_fix(self):
        path = self.dir / "inter.png"
        build_png(path, 1, 1, [bytes([0, 0, 0])], color=2, interlace=1)
        with self.assertRaises(pd.PngError) as ctx:
            pd.read_png(str(path))
        self.assertIn("interlaced", str(ctx.exception))
        self.assertIn("sips", str(ctx.exception), "say the command that fixes it, not just the name")

    def test_round_trip_through_our_own_writer(self):
        rows = [[(1, 2, 3), (250, 128, 0)], [(0, 0, 0), (255, 255, 255)]]
        path = self.rgb_png("rt.png", rows)
        w, h, back = pd.read_png(path)
        self.assertEqual((w, h), (2, 2))
        self.assertEqual(back, rows)


class TestFailureModes(Base):
    def test_an_unreadable_file_exits_two_not_one(self):
        bad = self.dir / "bad.png"
        bad.write_bytes(b"not a png at all")
        good = self.rgb_png("good.png", solid(4, 4, (0, 0, 0)))
        code, _, err = self.cli(str(bad), good)
        self.assertEqual(code, 2, "a check that could not run must not read as a check that failed")
        self.assertIn("not a PNG", err)

    def test_a_missing_file_also_exits_two(self):
        good = self.rgb_png("good.png", solid(4, 4, (0, 0, 0)))
        code, _, _ = self.cli(str(self.dir / "nope.png"), good)
        self.assertEqual(code, 2)

    def test_diff_image_is_written_and_readable(self):
        rows = [list(r) for r in solid(32, 32, (255, 255, 255))]
        rows[1][1] = (0, 0, 0)
        a = self.rgb_png("a.png", solid(32, 32, (255, 255, 255)))
        b = self.rgb_png("b.png", rows)
        out = str(self.dir / "diff.png")
        code, _, _ = self.cli(a, b, "--out", out)
        self.assertEqual(code, 1)
        w, h, drows = pd.read_png(out)
        self.assertEqual((w, h), (32, 32))
        self.assertEqual(drows[1][1], (220, 30, 30), "the changed pixel is marked red")

    def test_no_diff_image_is_written_when_not_asked(self):
        a = self.rgb_png("a.png", solid(8, 8, (0, 0, 0)))
        b = self.rgb_png("b.png", solid(8, 8, (0, 0, 0)))
        report, diff = pd.compare(pd.read_png(a), pd.read_png(b), mark=False)
        self.assertIsNone(diff)
        self.assertEqual(report["changed"], 0)


if __name__ == "__main__":
    unittest.main()
