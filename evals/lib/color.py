"""Color helpers for the eval harness — ΔE, hex parsing, lightness.

Implements ΔE76 (CIE76) — the simple Euclidean distance in Lab space. Not as
perceptually accurate as ΔE2000 but good enough for our use case (catching
"this palette doesn't contain blue at all" vs "this palette's blue is slightly
off"). For the quantization-stability check, even ΔE76 catches real drift.

No external dependencies — implements the math directly. Pillow handles RGB
conversion when needed.
"""
from __future__ import annotations

import math
import re
from typing import Tuple

RGB = Tuple[int, int, int]


def parse_hex(s: str) -> RGB:
    """Parse `#rrggbb` or `rrggbb` into (r, g, b)."""
    s = s.strip().lstrip("#")
    if not re.fullmatch(r"[0-9a-fA-F]{6}", s):
        raise ValueError(f"Invalid hex color: {s!r}")
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


def to_hex(rgb: RGB) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


# sRGB → linear RGB (gamma decode), per IEC 61966-2-1.
def _gamma_decode(c: float) -> float:
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


# D65 reference white (CIE 1931 2°).
_XN, _YN, _ZN = 0.95047, 1.00000, 1.08883


def rgb_to_xyz(rgb: RGB) -> Tuple[float, float, float]:
    r, g, b = (_gamma_decode(c) for c in rgb)
    # sRGB → XYZ matrix (D65).
    x = r * 0.4124564 + g * 0.3575761 + b * 0.1804375
    y = r * 0.2126729 + g * 0.7151522 + b * 0.0721750
    z = r * 0.0193339 + g * 0.1191920 + b * 0.9503041
    return (x, y, z)


def _f(t: float) -> float:
    delta = 6 / 29
    return t ** (1 / 3) if t > delta ** 3 else (t / (3 * delta * delta) + 4 / 29)


def rgb_to_lab(rgb: RGB) -> Tuple[float, float, float]:
    """Convert sRGB → CIE Lab. Returns (L*, a*, b*)."""
    x, y, z = rgb_to_xyz(rgb)
    fx, fy, fz = _f(x / _XN), _f(y / _YN), _f(z / _ZN)
    L = 116 * fy - 16
    a = 500 * (fx - fy)
    b = 200 * (fy - fz)
    return (L, a, b)


def lightness(rgb: RGB) -> float:
    """L* in [0, 100]. 100 = white, 0 = black."""
    return rgb_to_lab(rgb)[0]


def delta_e76(c1: RGB, c2: RGB) -> float:
    """ΔE CIE76 — Euclidean distance in Lab. Lower = more similar."""
    L1, a1, b1 = rgb_to_lab(c1)
    L2, a2, b2 = rgb_to_lab(c2)
    return math.sqrt((L1 - L2) ** 2 + (a1 - a2) ** 2 + (b1 - b2) ** 2)
