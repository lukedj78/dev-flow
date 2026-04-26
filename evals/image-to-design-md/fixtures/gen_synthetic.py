#!/usr/bin/env python3
"""Generate synthetic test images with known palettes.

Why synthetic: real screenshots get stale (Figma editor chrome shifts, font
rendering differs). Synthetic PNGs of solid blocks are reproducible across
machines and CI, and the expected palette is the input palette by definition.

Output:
  evals/image-to-design-md/inputs/synthetic-light.png   — light dashboard-ish
  evals/image-to-design-md/inputs/synthetic-dark.png    — dark editorial-ish

Run from repo root:
    python3 evals/image-to-design-md/fixtures/gen_synthetic.py
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError:
    sys.stderr.write("Pillow required: pip3 install Pillow\n")
    sys.exit(1)

OUT_DIR = Path(__file__).resolve().parent.parent / "inputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def make_synthetic(name: str, palette: list[tuple[str, tuple[int, int, int]]]) -> None:
    """Render a 1440×900 image where each palette color occupies a known area.

    Layout: largest color = full background (100% area = guaranteed first
    cluster from k-means). Subsequent colors painted as decreasing-size
    rectangles. This gives k-means a clean signal — synthetic test inputs
    should have unambiguous expected outputs.
    """
    W, H = 1440, 900
    bg_color = palette[0][1]
    img = Image.new("RGB", (W, H), bg_color)
    draw = ImageDraw.Draw(img)

    # Each subsequent color: shrinking rectangle, top-left to bottom-right.
    for i, (_, rgb) in enumerate(palette[1:], start=1):
        # Decreasing area: ~30% / 18% / 11% / 7% / …
        scale = 0.55 * (0.6 ** (i - 1))
        rw, rh = int(W * scale), int(H * scale)
        x0 = 50 + (i - 1) * 30
        y0 = 50 + (i - 1) * 30
        draw.rectangle([x0, y0, x0 + rw, y0 + rh], fill=rgb)

    out_path = OUT_DIR / f"{name}.png"
    img.save(out_path, "PNG")
    print(f"  → {out_path.relative_to(Path.cwd())}")


# Light theme — near-white bg, primary blue, neutrals.
LIGHT_PALETTE = [
    ("background", (248, 249, 250)),    # almost white
    ("primary",    (37, 99, 235)),      # blue
    ("on-surface", (17, 24, 39)),       # near black
    ("secondary",  (217, 70, 239)),     # magenta
    ("muted",      (156, 163, 175)),    # gray
]

# Dark theme — near-black bg, lime, neutrals.
DARK_PALETTE = [
    ("background", (10, 10, 15)),       # almost black
    ("primary",    (190, 242, 100)),    # lime
    ("on-surface", (243, 244, 246)),    # near white
    ("secondary",  (251, 146, 60)),     # orange
    ("muted",      (107, 114, 128)),    # gray
]


def main() -> int:
    print("Generating synthetic fixtures …")
    make_synthetic("synthetic-light", LIGHT_PALETTE)
    make_synthetic("synthetic-dark", DARK_PALETTE)
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
