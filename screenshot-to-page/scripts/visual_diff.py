#!/usr/bin/env python3
"""Pixel-diff two screenshots and report a delta percentage + annotated diff.

Designed for the screenshot-to-page skill's pixel-perfect loop. The
"reference" is the source screenshot the user wants the page to match;
the "render" is what Playwright just captured of the live route.

Usage:
    python3 visual_diff.py <reference.png> <render.png> [--threshold 2.0] [--out diff.png]

Output:
    - prints a one-line summary with delta percentage
    - exits 0 if delta < threshold, 1 otherwise (so a shell loop can branch on it)
    - writes an annotated diff PNG (red where pixels differ above noise floor)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from PIL import Image, ImageChops
    import numpy as np
except ImportError as e:
    sys.stderr.write(f"Missing dependency: {e}. Install: pip install Pillow numpy\n")
    sys.exit(2)


def normalize(img: Image.Image, target: tuple[int, int]) -> Image.Image:
    """Resize img to target dims preserving content; pad with transparent if aspect mismatched."""
    img = img.convert('RGBA')
    if img.size == target:
        return img
    # Resize maintaining aspect ratio, then pad
    img.thumbnail(target, Image.LANCZOS)
    canvas = Image.new('RGBA', target, (0, 0, 0, 0))
    x = (target[0] - img.width) // 2
    y = (target[1] - img.height) // 2
    canvas.paste(img, (x, y))
    return canvas


def diff(reference: Image.Image, render: Image.Image, noise: int = 12) -> tuple[float, Image.Image]:
    """Return (delta_percent, annotated_diff). noise = per-channel tolerance (0-255)."""
    target = reference.size
    render_norm = normalize(render, target)
    ref_norm = reference.convert('RGBA')

    a = np.array(ref_norm, dtype=np.int16)
    b = np.array(render_norm, dtype=np.int16)
    delta = np.abs(a[:, :, :3] - b[:, :, :3]).max(axis=-1)
    differs = delta > noise
    delta_pct = 100.0 * differs.sum() / differs.size

    # Build annotated diff: original reference, but pixels that differ painted red at 60% opacity
    annotated = ref_norm.copy()
    arr = np.array(annotated)
    arr[differs] = [220, 30, 30, 200]
    return delta_pct, Image.fromarray(arr)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('reference', type=Path)
    ap.add_argument('render', type=Path)
    ap.add_argument('--threshold', type=float, default=2.0, help='Delta percentage threshold (default 2.0)')
    ap.add_argument('--out', type=Path, default=None, help='Annotated diff output (default: <render>.diff.png)')
    ap.add_argument('--noise', type=int, default=12, help='Per-channel pixel-difference tolerance, 0-255 (default 12)')
    args = ap.parse_args()

    if not args.reference.exists() or not args.render.exists():
        sys.stderr.write("Both inputs must exist.\n")
        return 2

    ref = Image.open(args.reference)
    ren = Image.open(args.render)
    delta_pct, annotated = diff(ref, ren, noise=args.noise)

    out = args.out or args.render.with_suffix('.diff.png')
    annotated.save(out)

    verdict = "PASS" if delta_pct < args.threshold else "FAIL"
    print(f"{verdict}  delta={delta_pct:.2f}%  threshold={args.threshold:.2f}%  diff={out}")
    return 0 if delta_pct < args.threshold else 1


if __name__ == '__main__':
    sys.exit(main())
