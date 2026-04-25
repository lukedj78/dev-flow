#!/usr/bin/env python3
"""Aggregate dominant palettes from multiple images into one ranked list.

Useful when N screenshots of the same app share a brand palette — the colors
that recur across images are the real tokens; one-off colors are content noise.

For each input image we run k-means quantization (the same as quantize_palette.py),
then merge across images by:

  1. Collecting (hex, fraction) pairs from each image.
  2. Clustering near-duplicates (Euclidean Δrgb < threshold) so #ff0000 and
     #fe0102 collapse to one entry.
  3. Scoring each cluster by `sum(fraction)` (frequency-weighted across all images).
  4. Optionally boosting scores for clusters that appear in MULTIPLE images
     (a brand color recurring across screens is more likely to be a token).

Usage:
    python3 aggregate_palettes.py img1.png img2.png img3.png [--k 12] [--out palette.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from PIL import Image
    import numpy as np
    from sklearn.cluster import KMeans
except ImportError as e:
    sys.stderr.write(f"Missing dependency: {e}. Install: pip install Pillow numpy scikit-learn\n")
    sys.exit(2)


def quantize_one(
    path: Path,
    k: int = 12,
    sample: tuple[int, int] = (400, 250),
    drop_brightness_above: int = 245,
) -> list[tuple[tuple[int, int, int], float]]:
    """Return the k dominant colors from one image as (rgb, fraction) pairs."""
    img = Image.open(path).convert("RGB").resize(sample)
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


def merge_clusters(
    pairs: list[tuple[tuple[int, int, int], float, int]],
    threshold: float = 25.0,
) -> list[tuple[tuple[int, int, int], float, int]]:
    """Merge near-duplicate colors. pairs: (rgb, weight, n_images).

    Returns merged list. Two colors are considered the same cluster if their
    Euclidean RGB distance is below `threshold` (default 25 — about half a
    JND in CIE76 space).
    """
    pairs = sorted(pairs, key=lambda x: -x[1])  # heaviest first
    merged: list[tuple[tuple[int, int, int], float, int]] = []
    used = [False] * len(pairs)
    for i, (rgb_i, w_i, n_i) in enumerate(pairs):
        if used[i]:
            continue
        used[i] = True
        cluster = [(rgb_i, w_i, n_i)]
        for j in range(i + 1, len(pairs)):
            if used[j]:
                continue
            rgb_j, _, _ = pairs[j]
            d = ((rgb_i[0] - rgb_j[0]) ** 2 + (rgb_i[1] - rgb_j[1]) ** 2 + (rgb_i[2] - rgb_j[2]) ** 2) ** 0.5
            if d < threshold:
                cluster.append(pairs[j])
                used[j] = True
        # Cluster summary: use the heaviest color as the representative,
        # sum weights, sum image counts.
        rep_rgb = cluster[0][0]
        total_w = sum(p[1] for p in cluster)
        total_n = max(p[2] for p in cluster)  # appears in this many images
        merged.append((rep_rgb, total_w, total_n))
    return merged


def hex_of(rgb: tuple[int, int, int]) -> str:
    r, g, b = rgb
    return f"#{r:02x}{g:02x}{b:02x}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("images", nargs="+", type=Path)
    ap.add_argument("--k", type=int, default=12)
    ap.add_argument("--threshold", type=float, default=25.0,
                    help="Euclidean RGB distance below which colors are merged (default 25)")
    ap.add_argument("--cross-image-boost", type=float, default=0.5,
                    help="Multiplier added to weight per additional image the cluster appears in (default 0.5)")
    ap.add_argument("--out", type=Path, default=None,
                    help="Optional JSON output path; otherwise prints to stdout")
    ap.add_argument("--top", type=int, default=20, help="Print top-N (default 20)")
    args = ap.parse_args()

    missing = [p for p in args.images if not p.exists()]
    if missing:
        sys.stderr.write(f"Missing files: {missing}\n")
        return 1

    # 1. quantize each image, tag with image-index
    flat: list[tuple[tuple[int, int, int], float, int]] = []
    for img_path in args.images:
        per_image = quantize_one(img_path, k=args.k)
        for rgb, w in per_image:
            flat.append((rgb, w, 1))  # n_images = 1 per row pre-merge

    # 2. merge near-duplicates ACROSS all images
    merged = merge_clusters(flat, threshold=args.threshold)

    # 3. score: weighted_sum + cross_image_boost
    scored = [
        (rgb, w + args.cross_image_boost * (n - 1), n)
        for rgb, w, n in merged
    ]
    scored.sort(key=lambda x: -x[1])

    output = {
        "input_images": [str(p) for p in args.images],
        "cluster_count": len(scored),
        "palette": [
            {
                "hex": hex_of(rgb),
                "rgb": list(rgb),
                "score": round(score, 4),
                "appears_in_n_images": n,
            }
            for rgb, score, n in scored[: args.top]
        ],
    }

    if args.out:
        args.out.write_text(json.dumps(output, indent=2))
        print(f"Wrote {args.out}")
    else:
        # Pretty-print to stdout
        print(f"# Aggregated palette from {len(args.images)} image(s)")
        print(f"# {'hex':<10} {'score':>7}  {'images':>6}  {'rgb'}")
        for entry in output["palette"]:
            print(f"{entry['hex']:<10} {entry['score']:>7.3f}  {entry['appears_in_n_images']:>6}  {tuple(entry['rgb'])}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
