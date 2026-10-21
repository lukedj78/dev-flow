#!/usr/bin/env python3
"""snapshot(s) -> tokens. Pure stdlib, no browser, no network.

`extract.js` answers *what is painted*. This answers *what system is that*, and it is deliberately
a separate program: the browser half cannot be unit-tested, this half is nothing but. Every number
below is checked against `fixtures/snapshot-known-site-*.json`, whose true values are written in
`fixtures/known-site.html`.

Three rules run through all of it, and they are the difference between a measurement and a guess:

  * Nothing observed is nothing written. A slot with no evidence is omitted and named in `missing`,
    never filled with a plausible default. A padded system reads as measured and is not.
  * Type goes into the numeric scale shadcn's own primitives use (`text-sm` … `text-7xl`), never a
    parallel set of semantic names. See `dev-flow/references/contracts.md` and the note in
    `design-md-to-app/SKILL.md:51`.
  * Weight decides, not count. Text is weighted by characters and backgrounds by painted area, so a
    1px border on 400 rows does not outvote a hero.

Usage:
    analyze.py <snapshot.json> [more.json ...] --out <dir> [--mode site|app]
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

SCHEMA = 1

# Tailwind's own type slots, which are the ones shadcn's primitives are written with. A measured
# size is mapped onto the nearest slot and REDEFINES it; no name is ever added beside them.
TW_TEXT_SLOTS = [
    ("text-xs", 12), ("text-sm", 14), ("text-base", 16), ("text-lg", 18), ("text-xl", 20),
    ("text-2xl", 24), ("text-3xl", 30), ("text-4xl", 36), ("text-5xl", 48), ("text-6xl", 60),
    ("text-7xl", 72), ("text-8xl", 96), ("text-9xl", 128),
]

# The shadcn theme slots. Writing only the observed ones is the whole point: a theme padded out with
# plausible values reads as measured.
SHADCN_SLOTS = [
    "background", "foreground", "card", "card-foreground", "popover", "popover-foreground",
    "primary", "primary-foreground", "secondary", "secondary-foreground", "muted",
    "muted-foreground", "accent", "accent-foreground", "destructive", "destructive-foreground",
    "border", "input", "ring",
]


# --------------------------------------------------------------------------- colour


def parse_hex(value):
    """'#rrggbb' -> (r, g, b) 0-255, or None for a translucent/authored value."""
    if not isinstance(value, str):
        return None
    m = re.fullmatch(r"#([0-9a-fA-F]{6})", value.strip())
    if not m:
        return None
    h = m.group(1)
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _srgb_to_linear(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def to_oklch(value):
    """sRGB hex -> (L, C, h). The conversion is Bjorn Ottosson's OKLab, written out rather than
    imported: one dependency for twenty lines of arithmetic is a bad trade in a skill."""
    rgb = parse_hex(value)
    if rgb is None:
        return None
    r, g, b = (_srgb_to_linear(c) for c in rgb)
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = (math.copysign(abs(v) ** (1 / 3), v) for v in (l, m, s))
    L = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    bb = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    C = math.sqrt(a * a + bb * bb)
    h = math.degrees(math.atan2(bb, a)) % 360
    return (round(L, 4), round(C, 4), round(h, 2))


def oklch_css(value):
    t = to_oklch(value)
    if t is None:
        return None
    return f"oklch({t[0]:.4f} {t[1]:.4f} {t[2]:.2f})"


def _linear_to_srgb(c):
    c = max(0.0, min(1.0, c))
    return 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055


def from_oklch(L, C, h):
    """OKLCH -> '#rrggbb'. The inverse of `to_oklch`, and it exists for one job: moving a colour
    along lightness without moving its hue. Darkening in sRGB turns a blue grey into a different
    colour; darkening in OKLab keeps it the same colour, less light."""
    a = C * math.cos(math.radians(h))
    b = C * math.sin(math.radians(h))
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    r = 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    bb = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
    return "#" + "".join(f"{round(_linear_to_srgb(v) * 255):02x}" for v in (r, g, bb))


def adjust_for_contrast(value, ground, target=4.5, steps=200):
    """Move `value` along lightness until it reaches `target` against `ground`, hue and chroma held.

    Returns (hex, ratio) or (None, best_ratio) when the target cannot be reached without changing
    the colour — which happens, and saying so is better than returning a different colour and
    calling it the same one.
    """
    start = to_oklch(value)
    ground_l = relative_luminance(ground)
    if start is None or ground_l is None:
        return None, None
    L, C, h = start
    direction = -1 if ground_l > 0.5 else 1          # darken on a light ground, lighten on a dark one
    best, best_ratio = None, contrast(value, ground) or 0
    for i in range(1, steps + 1):
        candidate_l = L + direction * (i / steps) * (1.0 if direction > 0 else L)
        if not 0 <= candidate_l <= 1:
            break
        candidate = from_oklch(candidate_l, C, h)
        ratio = contrast(candidate, ground)
        if ratio and ratio > best_ratio:
            best, best_ratio = candidate, ratio
        if ratio and ratio >= target:
            return candidate, ratio
    return None, round(best_ratio, 2)


def relative_luminance(value):
    rgb = parse_hex(value)
    if rgb is None:
        return None
    r, g, b = (_srgb_to_linear(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = relative_luminance(a), relative_luminance(b)
    if la is None or lb is None:
        return None
    hi, lo = max(la, lb), min(la, lb)
    return round((hi + 0.05) / (lo + 0.05), 2)


def wcag_grade(ratio, large=False):
    if ratio is None:
        return None
    if large:
        return "AAA" if ratio >= 4.5 else "AA" if ratio >= 3.0 else "fail"
    return "AAA" if ratio >= 7.0 else "AA" if ratio >= 4.5 else "fail"


# --------------------------------------------------------------------------- merge


def merge_snapshots(snaps, mode):
    """Fold N snapshots into one picture, and keep how many pages each value came from.

    Cross-page confidence is the one idea taken wholesale from dembrandt: a colour seen on four
    pages is the system, the same colour seen once may be a campaign banner. The number is carried
    through to the report and shown — never used to silently drop anything.
    """
    pages = {s.get("path") or s.get("url") for s in snaps}
    page_count = max(1, len(pages))

    merged = {
        "mode": mode,
        "pages": sorted(p for p in pages if p),
        "pageCount": page_count,
        "viewports": sorted({s["viewport"]["width"] for s in snaps}),
        "schemes": sorted({s.get("colorScheme", "light") for s in snaps}),
        "origin": snaps[0].get("origin"),
        "documentBackground": snaps[0].get("documentBackground"),
    }

    # In `site` mode the header and footer repeat on every page, so counting them per page lets the
    # chrome outvote the content. In `app` mode the inverse holds: the sidebar and the topbar ARE
    # the product, and deduplicating them throws away the thing the measurement was for.
    dedupe_chrome = (mode == "site")

    def fold(getter, weight_key):
        acc = defaultdict(lambda: {"weight": 0.0, "elements": 0, "pages": set()})
        for s in snaps:
            page = s.get("path") or s.get("url")
            for row in getter(s) or []:
                v = row["value"]
                e = acc[v]
                e["weight"] += row.get(weight_key, 0)
                e["elements"] += row.get("elements", 0)
                e["pages"].add(page)
        out = []
        for v, e in acc.items():
            seen = len(e["pages"])
            weight = e["weight"] / seen if (dedupe_chrome and seen > 1) else e["weight"]
            out.append({
                "value": v,
                "weight": round(weight),
                "elements": e["elements"],
                "pages": seen,
                "confidence": round(seen / page_count, 2),
            })
        out.sort(key=lambda r: (-r["weight"], -r["elements"]))
        return out

    merged["colors"] = {
        "text": fold(lambda s: s["colors"]["text"], "chars"),
        "background": fold(lambda s: s["colors"]["background"], "area"),
        "border": fold(lambda s: s["colors"]["border"], "length"),
        "fill": fold(lambda s: s["colors"]["fill"], "area"),
    }
    merged["gradients"] = fold(lambda s: s["gradients"], "area")

    # A box-shadow with no blur and no spread is a LINE, not an elevation. Measured on adidas.it,
    # where the commonest box-shadow was `rgb(227,43,43) 0 1px 0 0` — their red underline — and it
    # became `--shadow`, i.e. every card in the guide got a red rule under it. Elevation and hairline
    # are different tokens and the site draws them with the same property.
    def is_hairline(value):
        nums = re.findall(r"(-?[\d.]+)px", value or "")
        return len(nums) >= 3 and float(nums[2]) == 0 and (len(nums) < 4 or float(nums[3]) == 0)

    all_shadows = fold(lambda s: s["shadows"], "area")
    merged["shadows"] = [s for s in all_shadows if not is_hairline(s["value"])]
    merged["hairlines"] = [s for s in all_shadows if is_hairline(s["value"])]
    merged["fontFamilies"] = fold(lambda s: s["fontFamilies"], "chars")

    # Type is kept per viewport: the pair (390, 1440) is what a clamp() is derived from, and
    # flattening it here would throw the responsive ramp away before anyone could read it.
    merged["typeByViewport"] = defaultdict(list)
    for s in snaps:
        merged["typeByViewport"][s["viewport"]["width"]].extend(s["type"])
    merged["typeByViewport"] = dict(merged["typeByViewport"])

    def tally(getter):
        acc = defaultdict(int)
        for s in snaps:
            for k, n in (getter(s) or {}).items():
                acc[k] += n
        return dict(acc)

    merged["spacing"] = {
        "padding": tally(lambda s: s["spacing"]["padding"]),
        "margin": tally(lambda s: s["spacing"]["margin"]),
        "gap": tally(lambda s: s["spacing"]["gap"]),
    }
    merged["radius"] = tally(lambda s: s["radius"])
    merged["containers"] = tally(lambda s: s["containers"])

    merged["declared"] = {"customProperties": {}, "breakpoints": [], "fontFaces": [], "opaque": 0}
    for s in snaps:
        d = s.get("declared", {})
        merged["declared"]["customProperties"].update(d.get("customProperties", {}))
        for bp in d.get("breakpoints", []):
            if bp not in merged["declared"]["breakpoints"]:
                merged["declared"]["breakpoints"].append(bp)
        for ff in d.get("fontFaces", []):
            if ff not in merged["declared"]["fontFaces"]:
                merged["declared"]["fontFaces"].append(ff)
        merged["declared"]["opaque"] += d.get("opaqueSheets", 0)
    merged["declared"]["breakpoints"].sort(key=lambda b: b["px"])

    merged["candidates"] = [s.get("candidates", {}) for s in snaps]
    merged["states"] = [s.get("states", {}) for s in snaps]
    merged["text"] = [s.get("text", {}) for s in snaps]
    merged["media"] = [s.get("media", {}) for s in snaps]
    merged["notes"] = sorted({n for s in snaps for n in s.get("notes", [])})
    merged["focusMeasured"] = any(s.get("documentHasFocus") for s in snaps)
    return merged


# --------------------------------------------------------------------------- colour roles


def colour_roles(merged, missing):
    """Assign the role names a DESIGN.md needs, each with the evidence that chose it."""
    roles = {}
    bgs = [r for r in merged["colors"]["background"] if parse_hex(r["value"])]
    texts = [r for r in merged["colors"]["text"] if parse_hex(r["value"])]
    borders = [r for r in merged["colors"]["border"] if parse_hex(r["value"])]

    doc_bg = merged.get("documentBackground")
    page_bg = doc_bg if parse_hex(doc_bg) else (bgs[0]["value"] if bgs else None)

    def ev(row, why):
        return {
            "value": row["value"],
            "oklch": oklch_css(row["value"]),
            "weight": row["weight"],
            "elements": row["elements"],
            "pages": row["pages"],
            "confidence": row["confidence"],
            "why": why,
        }

    if page_bg:
        row = next((r for r in bgs if r["value"] == page_bg), None)
        roles["background"] = ev(row, "the document background") if row else {
            "value": page_bg, "oklch": oklch_css(page_bg), "why": "the document background",
            "weight": 0, "elements": 0, "pages": merged["pageCount"], "confidence": 1.0}
    else:
        missing.append("background")

    # The ink cannot be the ground. Measured on adidas.it from a single page: 2608 white characters
    # against 2456 black — a 6% margin decided by one dark hero band — and `foreground` came out
    # #ffffff on a #ffffff page. Every other check passed; only drawing it showed white on white.
    # So the winner has to be legible against the ground it was chosen for, and if it is not, the
    # next candidate that is takes the role and the near-miss is recorded.
    if texts and page_bg:
        legible = [r for r in texts if (contrast(r["value"], page_bg) or 0) >= 3.0]
        if legible and legible[0] is not texts[0]:
            roles["foreground"] = ev(legible[0],
                                     f"most characters that are legible on the ground "
                                     f"({texts[0]['value']} had more but only "
                                     f"{contrast(texts[0]['value'], page_bg)}:1)")
        elif legible:
            roles["foreground"] = ev(legible[0], "most characters on the page")
        else:
            missing.append(f"foreground (no measured text colour reaches 3:1 on {page_bg})")
    elif texts:
        roles["foreground"] = ev(texts[0], "most characters on the page")

    # text-muted is the next text colour with clearly lower contrast against the ground. Derived
    # from the foreground that was CHOSEN, not from the heaviest candidate: when the guard above
    # swaps the winner, measuring against the rejected one makes the threshold unreachable.
    # (It also has to sit OUTSIDE the branches — nested under one of them it ran only in the case
    # that never happens, and the role vanished silently. Caught by a test, not by reading.)
    if page_bg and "foreground" in roles:
        chosen = roles["foreground"]["value"]
        base_c = contrast(chosen, page_bg)
        for r in texts:
            if r["value"] == chosen:
                continue
            c = contrast(r["value"], page_bg)
            if c and base_c and c < base_c * 0.75 and c >= 1.6:
                roles["muted-foreground"] = ev(r, "second text colour, lower contrast on the ground")
                break

    if not texts:
        missing.append("foreground")

    # A surface is a background that is not the page ground and not inverted: cards, panels, wells.
    surfaces = [r for r in bgs if r["value"] != page_bg]
    if surfaces and page_bg:
        ground_l = relative_luminance(page_bg)
        near = [r for r in surfaces if abs((relative_luminance(r["value"]) or 0) - ground_l) < 0.25]
        far = [r for r in surfaces if abs((relative_luminance(r["value"]) or 0) - ground_l) >= 0.5]
        if near:
            roles["card"] = ev(near[0], "a background near the ground: a surface, not an inversion")
        if far:
            roles["surface-inverse"] = ev(far[0], "a background far from the ground: an inverted band")

    # The action colour is the painted layer of the buttons, not the loudest colour on the page.
    action_counts = defaultdict(lambda: {"weight": 0, "elements": 0, "fg": defaultdict(int)})
    for cand in merged["candidates"]:
        for b in (cand.get("buttons") or {}).get("sample", []):
            bg = b.get("background")
            if not parse_hex(bg) or bg == page_bg:
                continue
            a = action_counts[bg]
            a["weight"] += max(1, (b.get("width") or 1) * (b.get("height") or 1))
            a["elements"] += 1
            if parse_hex(b.get("color")):
                a["fg"][b["color"]] += 1
    if action_counts:
        best = max(action_counts.items(), key=lambda kv: (kv[1]["elements"], kv[1]["weight"]))
        roles["primary"] = {
            "value": best[0], "oklch": oklch_css(best[0]), "weight": best[1]["weight"],
            "elements": best[1]["elements"], "pages": merged["pageCount"], "confidence": 1.0,
            "why": f"the painted layer of {best[1]['elements']} button(s)",
        }
        if best[1]["fg"]:
            fg = max(best[1]["fg"].items(), key=lambda kv: kv[1])[0]
            roles["primary-foreground"] = {
                "value": fg, "oklch": oklch_css(fg), "weight": 0, "elements": best[1]["fg"][fg],
                "pages": merged["pageCount"], "confidence": 1.0, "why": "the text on the primary button",
            }
        others = [k for k in action_counts if k != best[0]]
        if others:
            second = max(others, key=lambda k: action_counts[k]["elements"])
            roles["secondary"] = {
                "value": second, "oklch": oklch_css(second), "weight": action_counts[second]["weight"],
                "elements": action_counts[second]["elements"], "pages": merged["pageCount"],
                "confidence": 1.0, "why": "the second most common button ground",
            }
    else:
        missing.append("primary")

    if borders:
        roles["border"] = ev(borders[0], "the most border length on the page")
    else:
        missing.append("border")

    # The focus ring, and the trap that makes this twelve lines instead of three: every focusable
    # element has an outline, because when the page authors none the BROWSER draws its own. On the
    # test page the first focused control reported `#e59700` — Chrome's default ring, not one byte
    # of the site's design. A UA default written into a measured theme is the exact failure this
    # whole file is built to avoid, so a ring is only accepted when its colour is one the page
    # actually uses elsewhere; otherwise it is reported as a default, which is a finding of its own.
    # Which KINDS of control the page declares a focus rule for. A measured ring is only the site's
    # when its own kind is in that set: on the test page `button:focus` reports Chrome's `#e59700`
    # and `input:focus` reports the authored `#0b5fff`, and only the declared selectors separate
    # them. "The page declares focus somewhere, so take the first ring" picked the browser's.
    KIND_WORDS = {"button": ("button", "[role=button]", "[type=submit]"),
                  "input": ("input", "textarea", "select", "field"),
                  "link": (" a:", "a:focus", "a:", "link")}
    declared_kinds = set()
    for st in merged["states"]:
        for rule in st.get("focusDeclared") or []:
            sel = rule["selector"].lower().replace('"', "").replace("'", "")
            generic = sel.strip().startswith((":focus", "*:focus"))
            for kind, words in KIND_WORDS.items():
                if generic or any(w in sel for w in words):
                    declared_kinds.add(kind)

    rings = []
    for st in merged["states"]:
        for key, val in st.items():
            if key.endswith(":focus") and isinstance(val, dict) and val.get("outline"):
                colour = val["outline"].get("color")
                if parse_hex(colour):
                    rings.append((key.split(":")[0], colour))

    authored = None
    candidates_ = [c for kind, c in rings if kind in declared_kinds]
    if candidates_:
        palette = {r["value"] for group in ("text", "background", "border")
                   for r in merged["colors"][group] if parse_hex(r["value"])}
        palette |= {roles[k]["value"] for k in ("primary", "secondary") if k in roles}
        authored = next((c for c in candidates_ if c in palette), candidates_[0])
    if authored:
        roles["ring"] = {"value": authored, "oklch": oklch_css(authored), "weight": 0,
                         "elements": 1, "pages": merged["pageCount"], "confidence": 1.0,
                         "why": "the measured focus outline, and the page declares a :focus rule"}
    elif rings:
        missing.append(f"ring (every focus outline measured is the browser default, "
                       f"e.g. {rings[0][1]} on {rings[0][0]}: this page authors none)")
    elif not merged["focusMeasured"]:
        missing.append("ring (focus was not measured: see notes)")
    else:
        missing.append("ring")

    for slot in SHADCN_SLOTS:
        if slot not in roles and slot not in ("surface-inverse",):
            label = slot
            if label not in [m.split(" ")[0] for m in missing]:
                missing.append(label)

    return roles


# --------------------------------------------------------------------------- type


def cluster_sizes(rows, tolerance=0.12):
    """Group font sizes within `tolerance` of each other, weighted by characters.

    A real page has 17px, 17.6px and 18px for one role, because a rem lands between pixels. Reading
    those as three steps produces a scale nobody designed. 12% is the gist's number and it holds on
    the corpus here: it joins 16/17/18 and keeps 20 apart.
    """
    sized = sorted((r for r in rows if r.get("size")), key=lambda r: -r["size"])
    clusters = []
    def same_role(a, b):
        """Size alone is not a role. Measured on adidas.it: a wide-tracked uppercase label sat
        within 12% of a heading, won the cluster on character count, and handed the heading its
        0.098em tracking — so every h2 in the guide came out spaced like a label."""
        ta = (a.get("letterSpacing") or 0) / max(1, a["size"])
        tb = (b.get("letterSpacing") or 0) / max(1, b["size"])
        if abs(ta - tb) > 0.03:
            return False
        return (a.get("textTransform") or None) == (b.get("textTransform") or None)

    for row in sized:
        placed = False
        for c in clusters:
            if abs(row["size"] - c["size"]) <= c["size"] * tolerance and same_role(row, c):
                c["members"].append(row)
                total = c["chars"] + row["chars"]
                if total:
                    c["size"] = round((c["size"] * c["chars"] + row["size"] * row["chars"]) / total, 2)
                c["chars"] = total
                c["elements"] += row["elements"]
                placed = True
                break
        if not placed:
            clusters.append({"size": row["size"], "chars": row["chars"],
                             "elements": row["elements"], "members": [row]})
    for c in clusters:
        dominant = max(c["members"], key=lambda m: m["chars"])
        c["weight"] = dominant["weight"]
        c["lineHeight"] = dominant["lineHeight"]
        c["letterSpacing"] = dominant["letterSpacing"]
        c["family"] = dominant["family"]
        c["textTransform"] = dominant.get("textTransform")
        tags = defaultdict(int)
        for m in c["members"]:
            for t in m.get("tags", []):
                tags[t] += 1
        c["tags"] = sorted(tags, key=lambda t: -tags[t])[:3]
        c["size"] = round(c["size"], 1)
        del c["members"]
    clusters.sort(key=lambda c: -c["size"])
    return clusters


def nearest_slot(size):
    return min(TW_TEXT_SLOTS, key=lambda s: abs(s[1] - size))


def type_scale(merged, missing):
    viewports = sorted(merged["typeByViewport"])
    if not viewports:
        missing.append("typography")
        return {"slots": [], "ramp": None, "ratio": None}

    wide = max(viewports)
    narrow = min(viewports)
    wide_clusters = cluster_sizes(merged["typeByViewport"][wide])
    narrow_clusters = cluster_sizes(merged["typeByViewport"][narrow]) if narrow != wide else []

    slots, used = [], {}
    for c in wide_clusters:
        name, nominal = nearest_slot(c["size"])
        # Two clusters can land on one slot; the heavier one keeps it and the lighter moves to the
        # next free step rather than overwriting a value that more of the page is set in.
        if name in used:
            if c["chars"] <= used[name]["chars"]:
                continue
            slots = [s for s in slots if s["slot"] != name]
        used[name] = c

        mobile = None
        if narrow_clusters:
            match = min(narrow_clusters, key=lambda n: abs(n["size"] - c["size"]))
            # only pair them when they are plausibly the same role
            if abs(match["size"] - c["size"]) <= c["size"] * 0.45:
                mobile = match["size"]

        lh = c["lineHeight"]
        slots.append({
            "slot": name,
            "nominal": nominal,
            "size": c["size"],
            "mobileSize": mobile,
            "clamp": (f"clamp({mobile}px, {round(mobile + (c['size'] - mobile) * 0.6, 2)}px + 1.2vw, {c['size']}px)"
                      if mobile and abs(mobile - c["size"]) > 0.5 else None),
            "lineHeight": lh,
            "lineHeightRatio": round(lh / c["size"], 3) if (lh and c["size"]) else None,
            "weight": c["weight"],
            "tracking": (round(c["letterSpacing"] / c["size"], 4)
                         if c.get("letterSpacing") and c["size"] else 0),
            "textTransform": c.get("textTransform"),
            "family": c["family"],
            "chars": c["chars"],
            "elements": c["elements"],
            "tags": c["tags"],
        })

    slots.sort(key=lambda s: -s["size"])

    # A scale ratio is only a fact when the steps agree. Real pages jump — 72 to 32 is a decision,
    # 16 to 14 is a step — and averaging those two produced 1.561 on the test page, a number that
    # names no interval and describes nothing. So: report every step, the median, and the spread;
    # name a musical interval ONLY when the steps are actually uniform. Otherwise say so.
    steps = [round(slots[i]["size"] / slots[i + 1]["size"], 3)
             for i in range(len(slots) - 1) if slots[i + 1]["size"]]
    ratio = named = None
    uniform = False
    if steps:
        ordered = sorted(steps)
        mid = len(ordered) // 2
        median = ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2
        spread = max(steps) - min(steps)
        uniform = spread <= 0.15
        if uniform:
            ratio = round(median, 3)
            known = [("minor second", 1.067), ("major second", 1.125), ("minor third", 1.2),
                     ("major third", 1.25), ("perfect fourth", 1.333), ("augmented fourth", 1.414),
                     ("perfect fifth", 1.5), ("golden", 1.618)]
            best = min(known, key=lambda k: abs(k[1] - ratio))
            if abs(best[1] - ratio) < 0.06:
                named = best[0]

    return {"slots": slots, "steps": steps, "ratio": ratio, "uniform": uniform,
            "nearestInterval": named,
            "note": None if uniform else
                   "the steps are not uniform, so no single ratio describes this scale",
            "viewports": {"narrow": narrow, "wide": wide}}


# --------------------------------------------------------------------------- spacing


def spacing_scale(merged, missing):
    pads = merged["spacing"]["padding"]
    gaps = merged["spacing"]["gap"]
    margins = merged["spacing"]["margin"]
    pool = defaultdict(int)
    for src in (pads, gaps, margins):
        for k, n in src.items():
            try:
                v = float(k)
            except ValueError:
                continue
            if 0 < v <= 256:
                pool[v] += n
    if not pool:
        missing.append("spacing")
        return {"base": None, "onGrid": [], "offGrid": [], "coverage": 0}

    total = sum(pool.values())

    # The LARGEST base that still explains most of the values, not the base with the best coverage.
    # Measured on the test page, which is an 8px system: coverage was 100% for 2, 100% for 4 and 97%
    # for 8, so "highest coverage wins" answered 2 — true, useless, and it would have put a 2px grid
    # in a DESIGN.md. Every system is on a 2px grid; the question is the step a designer reaches for.
    coverage = {}
    for base in (8, 4, 2):
        coverage[base] = sum(n for v, n in pool.items()
                             if abs(v / base - round(v / base)) < 1e-6) / total
    best = next((b for b in (8, 4, 2) if coverage[b] >= 0.80), 1)
    best_cov = coverage.get(best, 1.0)

    on = sorted(v for v in pool if abs(v / best - round(v / best)) < 1e-6)
    off = sorted(v for v in pool if abs(v / best - round(v / best)) >= 1e-6)
    return {
        "base": best,
        "coverage": round(best_cov, 3),
        "onGrid": [int(v) if v == int(v) else v for v in on][:24],
        "offGrid": [{"value": v, "count": pool[v]} for v in off][:12],
        "total": total,
    }


# --------------------------------------------------------------------------- components


def components(merged, missing):
    out = {}
    buttons, cards, inputs = [], [], []
    for cand in merged["candidates"]:
        buttons.extend((cand.get("buttons") or {}).get("sample", []))
        cards.extend((cand.get("cards") or {}).get("sample", []))
        inputs.extend((cand.get("inputs") or {}).get("sample", []))

    def variants(rows, key):
        groups = defaultdict(list)
        for r in rows:
            groups[key(r)].append(r)
        return [{"signature": k, "count": len(v), "example": v[0]}
                for k, v in sorted(groups.items(), key=lambda kv: -len(kv[1]))]

    if buttons:
        out["button"] = {
            "variants": variants(buttons, lambda b: (b.get("background"), b.get("borderWidth"),
                                                     b.get("radiusIsPill"), b.get("radius")))[:6],
            "paintedOnChild": any(b.get("paintedOnChild") for b in buttons),
        }
    else:
        missing.append("button")

    if cards:
        out["card"] = {"variants": variants(cards, lambda c: (c.get("background"), c.get("radius"),
                                                              bool(c.get("shadow"))))[:4]}
    else:
        missing.append("card")

    if inputs:
        out["input"] = {"variants": variants(inputs, lambda i: (i.get("height"), i.get("radius"),
                                                                i.get("borderColor")))[:3],
                        "inferred": False}
    else:
        out["input"] = {"variants": [], "inferred": True}
        missing.append("input (no form on the pages read: inferred, not measured)")

    headers = [c.get("header") for c in merged["candidates"] if c.get("header")]
    if headers:
        h = headers[0]
        out["header"] = {"height": h.get("height"), "sticky": h.get("sticky"),
                         "background": h.get("background"), "logo": h.get("logo")}
    if merged["mode"] == "app":
        for key in ("sidebar", "table", "dialog", "badges"):
            found = [c.get(key) for c in merged["candidates"] if c.get(key)]
            if found:
                out[key] = found[0]
            else:
                missing.append(f"{key} (not present on the pages read)")
    return out


def motion(merged, missing):
    """Durations and easings, taken from what the controls actually declare."""
    durations, easings = defaultdict(int), defaultdict(int)
    for cand in merged["candidates"]:
        for group in ("buttons", "cards", "inputs", "links"):
            for row in (cand.get(group) or {}).get("sample", []):
                t = row.get("transition")
                if not t:
                    continue
                for d in re.findall(r"([\d.]+)s", t.get("duration", "")):
                    ms = round(float(d) * 1000)
                    if 0 < ms <= 2000:
                        durations[ms] += 1
                e = (t.get("easing") or "").strip()
                if e and e != "ease":
                    easings[e] += 1
    if not durations and not easings:
        missing.append("motion (no transition declared on the controls read)")
        return None
    return {
        "durations": sorted(durations.items(), key=lambda kv: -kv[1]),
        "easings": sorted(easings.items(), key=lambda kv: -kv[1]),
    }


def voice(merged, missing):
    """Three rules from statistics, never from an impression. Strings are only present in `site`
    mode; in `app` mode this works from shape alone, which is the point of keeping shape."""
    headings, paras, ctas = [], [], []
    you = we = exclam = digits = upper = title = comma = 0
    samples = []
    for t in merged["text"]:
        shape = t.get("shape") or {}
        headings += shape.get("headings", [])
        paras += shape.get("paragraphs", [])
        ctas += shape.get("ctaLabels", [])
        you += shape.get("you", 0)
        we += shape.get("we", 0)
        exclam += shape.get("exclamations", 0)
        digits += shape.get("digits", 0)
        upper += shape.get("upperHeadings", 0)
        title += shape.get("titleHeadings", 0)
        comma += shape.get("commaPattern", 0)
        samples += t.get("samples", [])

    if not headings and not paras:
        missing.append("voice")
        return None

    def avg(rows, key):
        vals = [r[key] for r in rows if r.get(key)]
        return round(sum(vals) / len(vals), 1) if vals else None

    stats = {
        "headingWords": avg(headings, "words"),
        "paragraphWords": avg(paras, "words"),
        "ctaWords": avg(ctas, "words"),
        "headings": len(headings),
        "paragraphs": len(paras),
        "ctas": len(ctas),
        "youVsWe": {"you": you, "we": we},
        "exclamations": exclam,
        "upperCaseHeadings": upper,
        "titleCaseHeadings": title,
        "commaPatternHeadings": comma,
    }

    rules = []
    if stats["headingWords"]:
        rules.append(f"Headings run about {stats['headingWords']} words "
                     f"({len(headings)} measured); keep new ones in that range.")
    if you or we:
        side = "the reader" if you >= we else "the company"
        rules.append(f"The copy addresses {side}: 'you' {you} times against 'we' {we}.")
    if stats["ctaWords"]:
        rules.append(f"Calls to action are {stats['ctaWords']} words on average "
                     f"({len(ctas)} measured){', and never exclaim' if exclam == 0 else ''}.")
    return {"stats": stats, "rules": rules[:3], "quotes": samples[:5]}


# --------------------------------------------------------------------------- tokens out



# The look that AI-generated design keeps landing on. Not a style judgement: these are the specific
# defaults that appear when nobody chose anything, and the divergence step is exactly where a
# measured system drifts into them — you move away from the source and arrive at the average.
SLOP = {
    "faces": {"inter", "space grotesk", "poppins", "montserrat", "dm sans"},
    "grounds": {"#f4f1ea", "#faf9f6", "#fdfcfa", "#fffbf5"},      # the warm cream
    "accents": {"#c45d3a", "#e07a5f", "#d97757", "#b85c38",       # terracotta
                "#a3e635", "#84cc16", "#bef264"},                 # the lone acid green
    "radii": {8.0, 12.0},                                          # rounded-lg on everything
}


def slop_drift(final, measured):
    """What moved AWAY from the measurement and TOWARDS the generic look.

    Only drift counts. A site that genuinely uses Inter on cream is not sloppy — it is that site,
    and reporting it would punish an accurate measurement. What is worth a question is a value that
    was something else when measured and is now one of these.
    """
    if not measured:
        return []
    hits = []

    def role(tokens, name):
        return (tokens.get("color", {}).get("roles", {}).get(name) or {}).get("value")

    fam_now = (final["typography"]["families"] or [""])[0].strip().lower()
    fam_was = (measured["typography"]["families"] or [""])[0].strip().lower()
    if fam_now in SLOP["faces"] and fam_now != fam_was:
        hits.append(("typeface", f"{fam_was or '—'} → {fam_now}",
                     "the safe face everything defaults to"))

    for name, key in (("background", "grounds"), ("primary", "accents"), ("accent", "accents")):
        now, was = role(final, name), role(measured, name)
        if now and now.lower() in SLOP[key] and now != was:
            hits.append((name, f"{was or '—'} → {now}", "a stock palette value"))

    r_now, r_was = final["radius"].get("default"), measured["radius"].get("default")
    if r_now in SLOP["radii"] and r_was is not None and float(r_was) != float(r_now):
        def _px(v):
            return f"{int(v)}px" if float(v) == int(float(v)) else f"{v}px"
        hits.append(("radius", f"{_px(r_was)} → {_px(r_now)}", "rounded-lg on everything"))

    grad_now = (final["color"]["gradients"] or [""])[0].lower()
    if grad_now and grad_now not in [g.lower() for g in measured["color"]["gradients"]]:
        if ("purple" in grad_now or "violet" in grad_now or "#7c3aed" in grad_now
                or "#8b5cf6" in grad_now) and ("blue" in grad_now or "#3b82f6" in grad_now):
            hits.append(("gradient", "added", "the purple-to-blue hero"))
    return hits


def open_questions(tokens, merged):
    """The decisions a person has to make, each with its evidence and a default.

    This is what turns the guide from a document into a review step. The questions are DERIVED, not
    written: every one of them is a condition the measurement can detect, so a run that finds
    nothing says so instead of inventing a concern. Each carries `default` — what happens if nobody
    answers — because an unanswered question that silently did something is worse than no question.
    """
    out = []

    for c in tokens["contrast"]:
        if c["grade"] == "fail":
            out.append({
                "id": f"contrast:{c['pair']}",
                "kind": "accessibility",
                "question": f"{c['pair']} is {c['ratio']}:1, below the 4.5 that WCAG AA asks for.",
                "evidence": "measured on the real pair, not on a palette swatch",
                "options": ["keep it — the source site ships this and it is a faithful record",
                            "darken the text until it passes, and record the new value"],
                "default": "kept as measured",
            })

    weak = [(n, r) for n, r in tokens["color"]["roles"].items()
            if r.get("confidence", 1) < 0.5 and merged["pageCount"] > 1]
    if weak:
        out.append({
            "id": "confidence:colour",
            "kind": "confidence",
            "question": f"{len(weak)} colour role(s) were seen on fewer than half the pages read: "
                        f"{', '.join(n for n, _ in weak)}.",
            "evidence": f"{merged['pageCount']} page(s) read",
            "options": ["read more pages before deciding",
                        "accept them — a role can legitimately live on one page"],
            "default": "accepted",
        })

    inferred = [n for n, d in tokens["components"].items()
                if isinstance(d, dict) and d.get("inferred")]
    if inferred:
        out.append({
            "id": "inferred:components",
            "kind": "gap",
            "question": f"No {', '.join(inferred)} was present on the pages read, so its values are "
                        f"inferred rather than measured.",
            "evidence": "marked `inferred` everywhere it appears",
            "options": ["point me at a page that has one",
                        "let the framework default stand"],
            "default": "framework default",
        })

    if tokens["missing"]:
        out.append({
            "id": "missing:slots",
            "kind": "gap",
            "question": f"{len(tokens['missing'])} slot(s) had no evidence and were left empty.",
            "evidence": "; ".join(tokens["missing"][:5]),
            "options": ["fine — shadcn's own defaults fill them",
                        "read more pages, or a dark-mode pass, to find them"],
            "default": "shadcn defaults",
        })

    scale = tokens["typography"]["scale"]
    big = [s for s in scale["slots"] if s["mobileSize"] and s["mobileSize"] >= 56]
    if big:
        out.append({
            "id": "type:mobile",
            "kind": "judgement",
            "question": f"{big[0]['slot']} is {big[0]['mobileSize']}px on a 390px screen — "
                        f"about {big[0]['mobileSize'] / 390:.0%} of the viewport width per line.",
            "evidence": f"measured at both {scale['viewports']['narrow']}px and "
                        f"{scale['viewports']['wide']}px",
            "options": ["keep the source's ramp", "lighten the mobile end and regenerate"],
            "default": "kept as measured",
        })

    if not scale["uniform"] and len(scale["slots"]) >= 3:
        out.append({
            "id": "type:scale",
            "kind": "judgement",
            "question": "The type steps are not uniform, so this is a set of chosen sizes rather "
                        "than a scale.",
            "evidence": f"steps {scale['steps']}",
            "options": ["keep the measured sizes",
                        "regularise onto one ratio and regenerate"],
            "default": "kept as measured",
        })

    if merged["mode"] == "site" and len(merged["schemes"]) == 1:
        out.append({
            "id": "coverage:scheme",
            "kind": "coverage",
            "question": f"Only the {merged['schemes'][0]} theme was read.",
            "evidence": "one pass, one colour scheme",
            "options": ["read the other theme too", "this project ships one theme"],
            "default": "one theme",
        })

    # --- below here: every place the measurement had to CHOOSE, and could have chosen otherwise.
    # The seven rules above are the obvious failures. These are the judgements, and they are where
    # a measurement quietly becomes an opinion if nobody is asked.

    if merged["pageCount"] == 1:
        out.append({
            "id": "coverage:pages",
            "kind": "coverage",
            "question": "One page was read, so nothing has cross-page confirmation.",
            "evidence": "a campaign banner and the brand's own colour look identical on one page",
            "options": ["read three or four more", "this is all there is"],
            "default": "accepted on one page",
        })

    # A site that DECLARES one value and PAINTS another. Both are real; they are not the same fact.
    declared = {k: v for k, v in merged["declared"]["customProperties"].items()
                if parse_hex(v.strip())}
    painted = {r["value"] for r in merged["colors"]["background"] + merged["colors"]["text"]}
    painted |= {r["value"] for r in tokens["color"]["roles"].values()}
    orphan = {k: v for k, v in declared.items() if v.strip() not in painted}
    if orphan:
        first = list(orphan.items())[0]
        out.append({
            "id": "declared:unpainted",
            "kind": "judgement",
            "question": f"{len(orphan)} declared custom propert{'y' if len(orphan) == 1 else 'ies'} "
                        f"holds a colour that is painted nowhere — e.g. `{first[0]}: {first[1]}`.",
            "evidence": "the stylesheet names it; the rendered pages never use it. "
                        "It may be the brand's real value and the painted one a drift, or the "
                        "reverse",
            "options": ["trust what is painted — that is what people see",
                        f"take the declared value: it is what the team wrote down"],
            "default": "the painted value",
        })

    # Two candidates close enough that the winner was nearly a coin toss — but ONLY for a role that
    # was actually decided by weight. `background` usually is not: it comes from the document's own
    # computed background, and comparing the two heaviest painted colours then describes a contest
    # that never happened. The first version did exactly that and asked the user to fix a role that
    # was correct, which is worse than silence: a questionnaire that invents doubt gets switched off
    # as fast as one that hides it.
    roles_now = tokens["color"]["roles"]
    for role, group in (("foreground", "text"), ("background", "background")):
        why = roles_now.get(role, {}).get("why", "")
        if "document background" in why:
            continue                    # not a contest: the document said so
        rows = [r for r in merged["colors"][group] if parse_hex(r["value"])][:2]
        if len(rows) == 2 and rows[1]["weight"] > rows[0]["weight"] * 0.8:
            out.append({
                "id": f"close:{role}",
                "kind": "judgement",
                "question": f"`{role}` was close: {rows[0]['value']} won with "
                            f"{rows[0]['weight']} against {rows[1]['value']} with {rows[1]['weight']}.",
                "evidence": "within 20% — the winner is not obvious",
                "options": [f"keep {rows[0]['value']}", f"use {rows[1]['value']} instead"],
                "default": f"{rows[0]['value']}",
            })

    buttons = tokens["components"].get("button") or {}
    if buttons.get("paintedOnChild"):
        out.append({
            "id": "button:paintlayer",
            "kind": "judgement",
            "question": "At least one button's paint sits on a child of the link, not the link "
                        "itself, so the variants were grouped from the inner element.",
            "evidence": "read on the painted layer, which is the only one that carries the design",
            "options": ["fine — the grouping looks right in the guide",
                        "the variants are wrong, let me point at the real button"],
            "default": "accepted",
        })

    if tokens["radius"]["pill"] and tokens["radius"]["values"]:
        out.append({
            "id": "radius:both",
            "kind": "judgement",
            "question": f"Both a pill shape and a {tokens['radius']['default']}px radius are in "
                        f"use. `--radius` was set to the px one.",
            "evidence": f"pill on the primary action; {tokens['radius']['default']}px on "
                        f"{tokens['radius']['values'][0]['count']} element(s)",
            "options": ["right — the pill is only for the primary action",
                        "the pill is the default shape, swap them"],
            "default": f"{tokens['radius']['default']}px as default",
        })

    if len(tokens["shadows"]) > 1:
        out.append({
            "id": "elevation:scale",
            "kind": "judgement",
            "question": f"{len(tokens['shadows'])} distinct shadows were measured; the commonest "
                        f"became `--shadow`.",
            "evidence": "an elevation scale needs an order, and a count does not give one",
            "options": ["one shadow is enough for this project",
                        "build an elevation scale from all of them"],
            "default": "one shadow",
        })

    fams = merged["fontFamilies"]
    if len(fams) > 1 and fams[1]["weight"] < fams[0]["weight"] * 0.1:
        out.append({
            "id": "type:secondfamily",
            "kind": "judgement",
            "question": f"A second family, `{fams[1]['value']}`, carries only "
                        f"{fams[1]['weight']} characters against {fams[0]['weight']}.",
            "evidence": "too little to tell a deliberate display face from an element that simply "
                        "never inherited the body font",
            "options": ["it is a real second face, keep it",
                        "drop it — one family"],
            "default": "kept",
        })

    space = tokens["spacing"]
    if space["base"] and space["coverage"] < 0.9 and space["offGrid"]:
        off = ", ".join(f"{o['value']}px" for o in space["offGrid"][:4])
        out.append({
            "id": "spacing:offgrid",
            "kind": "judgement",
            "question": f"{(1 - space['coverage']) * 100:.0f}% of spacing values are off the "
                        f"{space['base']}px grid — {off}.",
            "evidence": "either the grid is finer than it looks, or those are accidents",
            "options": [f"keep {space['base']}px and treat the rest as accidents",
                        "use a finer base so everything is on the grid"],
            "default": f"{space['base']}px",
        })

    if tokens["color"]["gradients"]:
        out.append({
            "id": "colour:gradient",
            "kind": "judgement",
            "question": f"{len(tokens['color']['gradients'])} gradient(s) were measured and the "
                        f"first became `--gradient`.",
            "evidence": "a gradient can be the brand or a single hero's decoration",
            "options": ["it is part of the system", "it belongs to that one page, drop it"],
            "default": "kept as a token",
        })

    return out


def build_tokens(merged):
    missing = []
    roles = colour_roles(merged, missing)
    type_info = type_scale(merged, missing)
    space = spacing_scale(merged, missing)
    comps = components(merged, missing)

    radius = merged["radius"]
    radius_px = sorted(((float(k), n) for k, n in radius.items() if k != "pill"),
                       key=lambda kv: -kv[1])

    # The default shape is decided on the CONTROLS, by majority, not by whether a pill exists
    # anywhere. Measured on adidas.it: 13 of 14 buttons had radius 0 and one 24px dot was round,
    # and "any pill makes it a pill system" turned a famously square brand into a rounded one.
    button_radii = [b["example"] for d in [comps.get("button") or {}] for b in d.get("variants", [])]
    pills = sum(1 for b in button_radii if b.get("radiusIsPill"))
    squares = sum(1 for b in button_radii
                  if not b.get("radiusIsPill") and (b.get("radius") or 0) == 0)
    pill_is_default = bool(button_radii) and pills > len(button_radii) / 2
    containers = sorted(((float(k), n) for k, n in merged["containers"].items()),
                        key=lambda kv: -kv[1])

    tokens = {
        "schema": SCHEMA,
        "source": {
            "origin": merged["origin"],
            "pages": merged["pages"],
            "pageCount": merged["pageCount"],
            "viewports": merged["viewports"],
            "schemes": merged["schemes"],
        },
        "color": {
            "roles": roles,
            "palette": [
                {"value": r["value"], "oklch": oklch_css(r["value"]), "share": r["weight"],
                 "pages": r["pages"], "confidence": r["confidence"]}
                for r in merged["colors"]["background"][:12] if parse_hex(r["value"])
            ],
            "gradients": [g["value"] for g in merged["gradients"][:4]],
        },
        "typography": {
            "families": [f["value"] for f in merged["fontFamilies"][:4]],
            "fontFaces": merged["declared"]["fontFaces"][:12],
            "scale": type_info,
        },
        "spacing": space,
        "radius": {
            "values": [{"px": v, "count": n} for v, n in radius_px[:8]],
            "pill": pill_is_default,
            "pillSeen": radius.get("pill", 0) > 0,
            "buttonShape": {"pill": pills, "square": squares, "of": len(button_radii)},
            "default": radius_px[0][0] if radius_px else None,
        },
        "layout": {
            "container": containers[0][0] if containers else None,
            "breakpoints": merged["declared"]["breakpoints"],
        },
        "shadows": [s["value"] for s in merged["shadows"][:4]],
        "motion": motion(merged, missing),
        "components": comps,
        "voice": voice(merged, missing),
        "declaredCustomProperties": merged["declared"]["customProperties"],
        "contrast": [],
        "missing": missing,
        "notes": merged["notes"],
    }

    bg = roles.get("background", {}).get("value")
    for name in ("foreground", "muted-foreground", "primary-foreground"):
        fg = roles.get(name, {}).get("value")
        ground = roles.get("primary", {}).get("value") if name == "primary-foreground" else bg
        if fg and ground:
            ratio = contrast(fg, ground)
            tokens["contrast"].append({
                "pair": f"{name} on {'primary' if name == 'primary-foreground' else 'background'}",
                "ratio": ratio, "grade": wcag_grade(ratio),
            })

    # Last, because every rule above has to have run first.
    tokens["questions"] = open_questions(tokens, merged)
    return tokens


def write_css(tokens, path):
    lines = [
        "/* Generated by url-to-design-md from a measured page. Do not hand-edit:",
        "   change tokens.json and regenerate, or the guide stops reflecting the system. */",
        ":root {",
    ]
    for name, role in tokens["color"]["roles"].items():
        lines.append(f"  --{name}: {role['value']};"
                     f"{'  /* ' + role['oklch'] + ' */' if role.get('oklch') else ''}")
    for slot in tokens["typography"]["scale"]["slots"]:
        value = slot["clamp"] or f"{slot['size']}px"
        lines.append(f"  --font-size-{slot['slot'].replace('text-', '')}: {value};")
        if slot["lineHeight"]:
            lines.append(f"  --line-height-{slot['slot'].replace('text-', '')}: {slot['lineHeight']}px;")
    if tokens["spacing"]["base"]:
        lines.append(f"  --space-base: {tokens['spacing']['base']}px;")
        for v in tokens["spacing"]["onGrid"][:10]:
            lines.append(f"  --space-{v}: {v}px;")
    if tokens["radius"]["default"] is not None:
        lines.append(f"  --radius: {tokens['radius']['default']}px;")
    if tokens["layout"]["container"]:
        lines.append(f"  --container: {tokens['layout']['container']}px;")
    if tokens["typography"]["families"]:
        lines.append(f"  --font-sans: {tokens['typography']['families'][0]};")
    lines.append("}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_shadcn(tokens, path):
    """The `:root` block shadcn needs under Tailwind v4, with the unobserved slots named in the
    header and left to shadcn's own default. A theme padded with plausible values reads as
    measured, and that is the one thing a theme must never do."""
    roles = tokens["color"]["roles"]
    written = [s for s in SHADCN_SLOTS if s in roles]
    absent = [s for s in SHADCN_SLOTS if s not in roles]
    head = [
        "/* shadcn/ui theme — observed slots only.",
        f"   Measured from {tokens['source']['origin']} "
        f"across {tokens['source']['pageCount']} page(s).",
        f"   WRITTEN ({len(written)}): {', '.join(written) or 'none'}",
        f"   NOT OBSERVED ({len(absent)}): {', '.join(absent) or 'none'}",
        "   The not-observed slots keep shadcn's default on purpose. Do not fill them in by hand:",
        "   a value nobody measured, sitting in a measured file, is indistinguishable from one.",
        "*/",
        ":root {",
    ]
    for slot in written:
        head.append(f"  --{slot}: {roles[slot].get('oklch') or roles[slot]['value']};")
    if tokens["radius"]["default"] is not None:
        head.append(f"  --radius: {tokens['radius']['default']}px;")
    head.append("}")
    head.append("")
    head.append("@theme inline {")
    for slot in written:
        head.append(f"  --color-{slot}: var(--{slot});")
    head.append("}")
    path.write_text("\n".join(head) + "\n", encoding="utf-8")


def write_dtcg(tokens, path):
    """W3C design-tokens, with the OKLCH beside the hex as the gist asks."""
    out = {"$description": f"Measured from {tokens['source']['origin']}", "color": {}, "dimension": {}}
    for name, role in tokens["color"]["roles"].items():
        out["color"][name] = {
            "$type": "color", "$value": role["value"],
            "$extensions": {"oklch": role.get("oklch"), "confidence": role.get("confidence"),
                            "why": role.get("why")},
        }
    for slot in tokens["typography"]["scale"]["slots"]:
        out["dimension"][slot["slot"]] = {"$type": "dimension", "$value": f"{slot['size']}px",
                                          "$extensions": {"mobile": slot["mobileSize"],
                                                          "lineHeight": slot["lineHeight"]}}
    if tokens["spacing"]["base"]:
        out["dimension"]["space-base"] = {"$type": "dimension",
                                          "$value": f"{tokens['spacing']['base']}px"}
    path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("snapshots", nargs="+", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--mode", choices=("site", "app"), default=None)
    args = ap.parse_args(argv)

    snaps = []
    for p in args.snapshots:
        data = json.loads(p.read_text(encoding="utf-8"))
        if data.get("schema") != SCHEMA:
            print(f"{p}: snapshot schema {data.get('schema')} != {SCHEMA}", file=sys.stderr)
            return 2
        snaps.append(data)

    mode = args.mode or snaps[0].get("mode", "site")
    if any(s.get("mode") != mode for s in snaps):
        print("snapshots disagree on mode; pass --mode to settle it", file=sys.stderr)
        return 2

    merged = merge_snapshots(snaps, mode)
    tokens = build_tokens(merged)

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "tokens.json").write_text(json.dumps(tokens, indent=2) + "\n", encoding="utf-8")
    write_css(tokens, args.out / "tokens.css")
    write_shadcn(tokens, args.out / "shadcn.css")
    write_dtcg(tokens, args.out / "tokens.dtcg.json")

    print(f"read {len(snaps)} snapshot(s), mode={mode}, "
          f"{merged['pageCount']} page(s), viewports {merged['viewports']}")
    print(f"  colour roles : {len(tokens['color']['roles'])}")
    print(f"  type slots   : {len(tokens['typography']['scale']['slots'])}"
          f" (ratio {tokens['typography']['scale']['ratio']})")
    print(f"  spacing base : {tokens['spacing']['base']}px "
          f"({tokens['spacing']['coverage']:.0%} of values on the grid)")
    if tokens["missing"]:
        print(f"  NOT OBSERVED : {', '.join(tokens['missing'])}")
    for n in tokens["notes"]:
        print(f"  note: {n}")
    print(f"  -> {args.out}/tokens.json, tokens.css, shadcn.css, tokens.dtcg.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
