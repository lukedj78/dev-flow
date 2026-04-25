#!/usr/bin/env python3
"""Extract a dominant color palette from a screenshot via k-means.

Designed for the figma-to-design-md skill, Path C-bis. Strip Figma's editor
chrome (left sidebar, top bar, bottom banner) and run k-means on the
remaining canvas pixels. Filters out near-white clusters that correspond
to the editor's grey background, not the design itself.

Usage:
    python3 quantize_palette.py <image.png> [--k 12] [--no-crop]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from PIL import Image
    import numpy as np
    from sklearn.cluster import KMeans
except ImportError as e:
    sys.stderr.write(
        f"Missing dependency: {e}. Install with:\n"
        f"  python3 -m pip install Pillow numpy scikit-learn\n"
    )
    sys.exit(1)


def crop_canvas(img: Image.Image) -> Image.Image:
    """Strip Figma chrome from a typical 1440x900 editor screenshot."""
    w, h = img.size
    # Heuristics tuned to Figma's web editor at 1440x900; adjust manually
    # for other viewports.
    left = min(290, w // 5)
    top = min(60, h // 15)
    bottom_offset = min(160, h // 6)
    return img.crop((left, top, w, h - bottom_offset))


def quantize(
    img: Image.Image,
    k: int = 12,
    sample: tuple[int, int] = (400, 250),
    drop_brightness_above: int = 245,
) -> list[tuple[tuple[int, int, int], float]]:
    img = img.convert('RGB').resize(sample)
    arr = np.array(img).reshape(-1, 3).astype(np.float32)
    bright = arr.mean(axis=1)
    mask = bright < drop_brightness_above
    arr_filt = arr[mask] if mask.sum() > 1000 else arr
    km = KMeans(n_clusters=k, n_init=4, random_state=42).fit(arr_filt)
    centers = km.cluster_centers_.round().astype(int)
    counts = np.bincount(km.labels_, minlength=k)
    total = counts.sum()
    return sorted(
        [(tuple(c.tolist()), counts[i] / total) for i, c in enumerate(centers)],
        key=lambda x: -x[1],
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('image', type=Path)
    ap.add_argument('--k', type=int, default=12, help='Number of clusters (default 12)')
    ap.add_argument('--no-crop', action='store_true', help='Skip Figma-chrome crop')
    args = ap.parse_args()

    if not args.image.exists():
        sys.stderr.write(f"File not found: {args.image}\n")
        sys.exit(1)

    img = Image.open(args.image)
    if not args.no_crop:
        img = crop_canvas(img)

    palette = quantize(img, k=args.k)
    print(f"# Palette from {args.image.name}  (top {len(palette)} clusters)")
    print(f"# {'hex':<10} {'pct':>6}  rgb")
    for (r, g, b), pct in palette:
        hex_ = f"#{r:02x}{g:02x}{b:02x}"
        print(f"{hex_:<10} {pct*100:>5.1f}%  rgb({r},{g},{b})")


if __name__ == '__main__':
    main()
