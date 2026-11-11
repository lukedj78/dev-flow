#!/usr/bin/env python3
"""pixel_diff.py — the half of the conformity rule that had no script.

    python3 pixel_diff.py before.png after.png
    python3 pixel_diff.py before.png after.png --out diff.png --json
    python3 pixel_diff.py before.png after.png --tolerance 2 --max-changed 40

`contracts.md` §Primitives says a screen is conform when **both** halves are zero:
`design/no-handmade-ui` at zero, **and the pixel diff at zero**. The lint half has an installer, a
write-time guard and a phase gate. The pixel half had a sentence naming `npx pixelmatch` or
ImageMagick `compare -metric AE` — two dependencies nothing in this suite installs, and no check
that either ever ran. So in practice the proof was "the agent looked at the screenshot and it seemed
fine", which is the exact thing that rule exists to forbid (smart-travel, 2026-10-12: 238 hand-made
elements behind a green lint, every verification visual).

This is that check, stdlib only like every script here, so there is nothing to install.

## What it compares, and the one thing it refuses to do

Two screenshots of **the same screen, same viewport, same state**: before a retrofit and after.
Native size, pixel for pixel, no resampling.

🔴 **It refuses two images of different dimensions instead of scaling them to a common width.**
The tool this was ported from scales both to 480px first, which is right for its job — comparing
your screenshot against somebody else's, taken at an unknown device pixel ratio. It is wrong for
ours twice over: nearest-neighbour resampling invents differences, so a genuinely identical pair
reports non-zero and the target "zero changed pixels" becomes unreachable; and it hides the opposite
failure, because a layout that grew 20px taller is exactly the regression a retrofit causes and
scaling makes it disappear. A size change between before and after **is** the finding, so it is
reported and it fails.

## Reading the output

- `changed` — pixels whose channel distance exceeds `--tolerance`. The contract's target is **0**.
- `regions` — the changed pixels grouped into rectangles, biggest first, in the image's own
  coordinates, each with a plain-words position, so a report says *"top left, 1 240 px"* and not
  just a number.
- exit **1** when `changed` is over the threshold (default 0), so it can sit in a gate.

`--tolerance` is for antialiasing noise between two runs of the same renderer; it is not for
accepting a difference you can see. A difference the user wants is a design change: the board
changes, both screenshots are retaken, and this goes back to zero.

PNG reading and writing ported from `replica-diff/imgdiff.py`
(https://github.com/Jakeschincariol/replica-skill, MIT) — 8 and 16 bit, greyscale, RGB, palette,
with or without alpha, alpha composited over white the way a page renders. Interlaced PNGs are
refused with the command that fixes them. The comparison itself is ours, for the reason above.
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
import zlib

SIG = b"\x89PNG\r\n\x1a\n"


class PngError(Exception):
    pass


# ----------------------------------------------------------------- PNG reading

def _paeth(a, b, c):
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def _unfilter(raw, height, stride, bpp):
    rows = []
    prev = bytearray(stride)
    pos = 0
    for _ in range(height):
        if pos + 1 + stride > len(raw):
            raise PngError("image data is truncated")
        ftype = raw[pos]
        line = bytearray(raw[pos + 1:pos + 1 + stride])
        pos += 1 + stride
        if ftype == 1:
            for i in range(bpp, stride):
                line[i] = (line[i] + line[i - bpp]) & 0xFF
        elif ftype == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif ftype == 3:
            for i in range(stride):
                left = line[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + ((left + prev[i]) >> 1)) & 0xFF
        elif ftype == 4:
            for i in range(stride):
                left = line[i - bpp] if i >= bpp else 0
                upleft = prev[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + _paeth(left, prev[i], upleft)) & 0xFF
        elif ftype != 0:
            raise PngError("unknown filter type %d" % ftype)
        rows.append(line)
        prev = line
    return rows


def _samples(line, width, channels, depth):
    """Unpack one unfiltered scanline into a flat list of 8 bit samples."""
    n = width * channels
    if depth == 8:
        return list(line[:n])
    if depth == 16:
        return [line[2 * i] for i in range(n)]
    out = []
    per_byte = 8 // depth
    mask = (1 << depth) - 1
    for byte in line:
        for k in range(per_byte):
            shift = 8 - depth * (k + 1)
            out.append((byte >> shift) & mask)
            if len(out) == n:
                return out
    return out


def _over_white(r, g, b, a):
    if a == 255:
        return (r, g, b)
    inv = 255 - a
    return ((r * a + 255 * inv) // 255, (g * a + 255 * inv) // 255,
            (b * a + 255 * inv) // 255)


def read_png(path):
    """Return (width, height, rows). rows[y][x] is an (r, g, b) tuple, alpha over white."""
    with open(path, "rb") as fh:
        data = fh.read()
    if data[:8] != SIG:
        raise PngError("%s is not a PNG" % path)
    pos = 8
    ihdr = None
    plte = None
    trns = None
    idat = []
    while pos + 8 <= len(data):
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        ctype = data[pos + 4:pos + 8]
        chunk = data[pos + 8:pos + 8 + length]
        pos += 12 + length
        if ctype == b"IHDR":
            ihdr = struct.unpack(">IIBBBBB", chunk)
        elif ctype == b"PLTE":
            plte = [tuple(chunk[i:i + 3]) for i in range(0, len(chunk), 3)]
        elif ctype == b"tRNS":
            trns = chunk
        elif ctype == b"IDAT":
            idat.append(chunk)
        elif ctype == b"IEND":
            break
    if ihdr is None:
        raise PngError("%s has no IHDR chunk" % path)
    width, height, depth, color, _comp, _filt, interlace = ihdr
    if interlace:
        raise PngError("%s is interlaced. Re-save it without interlacing "
                       "(on a Mac: sips -s format png in.png --out out.png)" % path)
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(color)
    if channels is None:
        raise PngError("unsupported PNG colour type %d" % color)
    if depth not in (1, 2, 4, 8, 16):
        raise PngError("unsupported bit depth %d" % depth)
    if color == 3 and plte is None:
        raise PngError("palette PNG without a palette")
    bits = depth * channels
    bpp = max(1, bits // 8)
    stride = (width * bits + 7) // 8
    raw = zlib.decompress(b"".join(idat))
    lines = _unfilter(raw, height, stride, bpp)

    scale = 255 // ((1 << depth) - 1) if depth < 8 else 1
    alpha_pal = list(trns) if (color == 3 and trns) else []
    rows = []
    for line in lines:
        s = _samples(line, width, channels, depth)
        row = []
        if color == 0:
            for v in s:
                g = v * scale
                row.append((g, g, g))
        elif color == 2:
            for i in range(0, len(s), 3):
                row.append((s[i], s[i + 1], s[i + 2]))
        elif color == 3:
            for idx in s:
                r, g, b = plte[idx] if idx < len(plte) else (0, 0, 0)
                a = alpha_pal[idx] if idx < len(alpha_pal) else 255
                row.append(_over_white(r, g, b, a))
        elif color == 4:
            for i in range(0, len(s), 2):
                g = s[i]
                row.append(_over_white(g, g, g, s[i + 1]))
        else:
            for i in range(0, len(s), 4):
                row.append(_over_white(s[i], s[i + 1], s[i + 2], s[i + 3]))
        rows.append(row)
    return width, height, rows


# ----------------------------------------------------------------- PNG writing

def write_png(path, width, height, rows):
    """Write 8 bit RGB. rows[y][x] is an (r, g, b) tuple."""
    raw = bytearray()
    for row in rows:
        raw.append(0)
        for r, g, b in row:
            raw.extend((r, g, b))

    def chunk(kind, body):
        crc = zlib.crc32(kind + body) & 0xFFFFFFFF
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    with open(path, "wb") as fh:
        fh.write(SIG + chunk(b"IHDR", ihdr) +
                 chunk(b"IDAT", zlib.compress(bytes(raw), 6)) +
                 chunk(b"IEND", b""))


# ------------------------------------------------------------------- comparing

def _where(x0, y0, x1, y1, width, height):
    """Plain words for where a region sits, so a report reads like a sentence."""
    mid_x = (x0 + x1) / 2.0 / max(1, width - 1)
    mid_y = (y0 + y1) / 2.0 / max(1, height - 1)
    vert = "top" if mid_y < 0.34 else ("bottom" if mid_y > 0.66 else "middle")
    horiz = "left" if mid_x < 0.34 else ("right" if mid_x > 0.66 else "centre")
    return "%s %s" % (vert, horiz)


def _regions(flags, width, height, cell):
    """Group changed pixels into rectangles, via a coarse grid so the report stays readable."""
    n_cols = (width + cell - 1) // cell
    n_rows = (height + cell - 1) // cell
    hot = [[False] * n_cols for _ in range(n_rows)]
    for r in range(n_rows):
        for c in range(n_cols):
            for y in range(r * cell, min(height, (r + 1) * cell)):
                row = flags[y]
                if any(row[c * cell:min(width, (c + 1) * cell)]):
                    hot[r][c] = True
                    break

    seen = set()
    out = []
    for r in range(n_rows):
        for c in range(n_cols):
            if not hot[r][c] or (r, c) in seen:
                continue
            stack = [(r, c)]
            seen.add((r, c))
            cells = []
            while stack:
                cr, cc = stack.pop()
                cells.append((cr, cc))
                for nr, nc in ((cr + 1, cc), (cr - 1, cc), (cr, cc + 1), (cr, cc - 1)):
                    if 0 <= nr < n_rows and 0 <= nc < n_cols and hot[nr][nc] \
                            and (nr, nc) not in seen:
                        seen.add((nr, nc))
                        stack.append((nr, nc))
            rs = [t[0] for t in cells]
            cs = [t[1] for t in cells]
            x0, y0 = min(cs) * cell, min(rs) * cell
            x1 = min(width, (max(cs) + 1) * cell) - 1
            y1 = min(height, (max(rs) + 1) * cell) - 1
            changed = sum(sum(flags[y][x0:x1 + 1]) for y in range(y0, y1 + 1))
            out.append({"x": x0, "y": y0, "w": x1 - x0 + 1, "h": y1 - y0 + 1,
                        "changed": changed, "where": _where(x0, y0, x1, y1, width, height)})
    out.sort(key=lambda d: -d["changed"])
    return out


def compare(before, after, tolerance=0, cell=32, mark=True):
    """Compare two decoded images at native size. Returns (report, diff rows or None)."""
    wb, hb, rows_b = before
    wa, ha, rows_a = after
    report = {
        "before": {"width": wb, "height": hb},
        "after": {"width": wa, "height": ha},
        "tolerance": tolerance,
    }
    if (wb, hb) != (wa, ha):
        report.update({
            "status": "size mismatch",
            "changed": None,
            "changed_pct": None,
            "regions": [],
            "detail": "before is %dx%d, after is %dx%d — a size change between the two IS the "
                      "regression, so they are not scaled to match" % (wb, hb, wa, ha),
        })
        return report, None

    total = wb * hb
    changed = 0
    flags = []
    diff = [] if mark else None
    for y in range(hb):
        fr = bytearray(wb)
        drow = [] if mark else None
        for x in range(wb):
            pb = rows_b[y][x]
            pa = rows_a[y][x]
            d = max(abs(pb[0] - pa[0]), abs(pb[1] - pa[1]), abs(pb[2] - pa[2]))
            if d > tolerance:
                fr[x] = 1
                changed += 1
                if mark:
                    drow.append((220, 30, 30))
            elif mark:
                g = (299 * pb[0] + 587 * pb[1] + 114 * pb[2]) // 1000
                drow.append((200 + g // 5,) * 3)
        flags.append(fr)
        if mark:
            diff.append(drow)

    report.update({
        "status": "identical" if changed == 0 else "differs",
        "changed": changed,
        "changed_pct": round(100.0 * changed / total, 4) if total else 0.0,
        "regions": _regions(flags, wb, hb, cell) if changed else [],
    })
    return report, diff


def render_text(report, before_name, after_name):
    lines = ["  %s vs %s" % (before_name, after_name)]
    if report["status"] == "size mismatch":
        lines.append("  SIZE MISMATCH  %s" % report["detail"])
        return "\n".join(lines)
    if report["changed"] == 0:
        lines.append("  IDENTICAL  0 changed pixels (tolerance %d)" % report["tolerance"])
        return "\n".join(lines)
    lines.append("  DIFFERS  %d changed pixels (%.4f%%, tolerance %d)" % (
        report["changed"], report["changed_pct"], report["tolerance"]))
    for reg in report["regions"][:8]:
        lines.append("    %-14s %5d px at %d,%d  %dx%d" % (
            reg["where"], reg["changed"], reg["x"], reg["y"], reg["w"], reg["h"]))
    extra = len(report["regions"]) - 8
    if extra > 0:
        lines.append("    ... and %d more region(s)" % extra)
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Pixel diff two screenshots of the same screen.")
    ap.add_argument("before")
    ap.add_argument("after")
    ap.add_argument("--out", help="write a diff PNG, changed pixels in red over a dimmed before")
    ap.add_argument("--tolerance", type=int, default=0,
                    help="per-channel distance tolerated, for antialiasing noise (default 0)")
    ap.add_argument("--max-changed", type=int, default=0,
                    help="changed pixels allowed before exiting 1 (default 0, the contract's target)")
    ap.add_argument("--cell", type=int, default=32, help="region grid size in pixels (default 32)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    try:
        before = read_png(args.before)
        after = read_png(args.after)
    except (PngError, OSError, zlib.error) as exc:
        print("pixel_diff: %s" % exc, file=sys.stderr)
        return 2

    report, diff = compare(before, after, tolerance=args.tolerance, cell=args.cell,
                           mark=bool(args.out))
    if args.out and diff is not None:
        write_png(args.out, before[0], before[1], diff)
        report["diff_image"] = args.out

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(render_text(report, args.before, args.after))

    if report["status"] == "size mismatch":
        return 1
    return 1 if report["changed"] > args.max_changed else 0


if __name__ == "__main__":
    raise SystemExit(main())
