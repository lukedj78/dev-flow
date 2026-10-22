#!/usr/bin/env python3
"""The gate between a rendered guide and a guide anyone is shown.

A guide that hard-codes one value stops reflecting the system it claims to show, and it does it
silently: the page still looks fine, and the person deciding what to change is now arguing with a
picture. So nothing is shown until this passes.

Two halves, because two different things can be false:

  static (here)       — the file does not reach the network, fits its budget, carries every section,
                        carries the Unofficial label, and its token JSON parses.
  in page (verify_page.js) — the rebuilt controls' COMPUTED styles equal the token values, and the
                        page does not scroll sideways at 390px. Only a browser can answer those,
                        and an answer that was never obtained is never counted as a pass.

    verify.py <brand-guide.html> [--inpage <result.json>] [--hero] [--json]

Exit 0 all checks passed, 1 a check failed, 2 the file could not be read.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

LIGHT_BUDGET = 150 * 1024
HERO_BUDGET = 4 * 1024 * 1024

REQUIRED_SECTIONS = ["overview", "rebuild", "typography", "fonts", "colour",
                     "layout", "components", "tokens", "method"]

# Anything that would make the page fetch when opened from a file:// URL on a plane.
EXTERNAL = re.compile(r"""(?:src|href)\s*=\s*["'](https?:)?//|url\(\s*["']?(?:https?:)?//""", re.I)


class Result:
    def __init__(self):
        self.checks = []

    def add(self, name, ok, detail=""):
        self.checks.append({"check": name, "ok": bool(ok), "detail": detail})
        return ok

    @property
    def failed(self):
        return [c for c in self.checks if not c["ok"]]

    def report(self, as_json=False):
        if as_json:
            print(json.dumps({"ok": not self.failed, "checks": self.checks}, indent=2))
            return
        for c in self.checks:
            mark = "✓" if c["ok"] else "✗"
            print(f"  {mark} {c['check']}" + (f" — {c['detail']}" if c["detail"] else ""))
        print(f"\n{len(self.checks) - len(self.failed)}/{len(self.checks)} passed")



# Rule 11 of `design-md-to-app/references/anti-slop-fallbacks.md` — "the tells that are structural,
# not textual" — applied to our own artefact. It has to live in the gate rather than in anyone's
# eye: the guide is generated the same way every time, so if its silhouette reads as AI slop it does
# so on every site, for ever, and the tokens being accurate does not rescue it. Caught on the first
# real run: the user looked at the adidas guide and saw it before any check did.
def slop_checks(html, res):
    import collections

    # "A row of identical metric boxes. Four numbers in four boxes state four facts and no argument."
    metric_rows = len(re.findall(r'class="grid grid--4"', html))
    boxes = len(re.findall(r'<div class="card"><div class="note">[^<]+</div>'
                           r'<div style="font-size:var\(--size-3xl', html))
    res.add("no row of identical metric boxes", boxes < 3,
            f"{boxes} metric box(es) in {metric_rows} row(s)" if boxes else "none")

    # "The same section silhouette repeated for sections that answer different questions."
    silhouettes = collections.Counter()
    for sec in re.findall(r"<section[^>]*>(.*?)</section>", html, re.S):
        shape = (("h2" if "<h2" in sec else "")
                 + ("+lede" if 'class="lede"' in sec else "")
                 + ("+grid" if 'class="grid' in sec else "")
                 + ("+table" if "<table" in sec else ""))
        if shape:
            silhouettes[shape] += 1
    worst = silhouettes.most_common(1)[0] if silhouettes else ("", 0)
    res.add("sections do not all share one silhouette", worst[1] <= 3,
            f"{worst[1]} sections shaped `{worst[0]}`" if worst[1] else "varied")

    # "Decorative gradients, glows, blobs, mesh backgrounds, glassmorphism."
    glass = "backdrop-filter" in html
    res.add("no glassmorphism", not glass,
            "backdrop-filter present" if glass else "none")

    # "A badge or pill for ordinary metadata. A date is a date."
    pills = re.findall(r'<span class="pill"[^>]*>([^<]{1,40})</span>', html)
    status_pills = [p for p in pills if "unofficial" in p.lower() or "decision" in p.lower()
                    or "before" in p.lower()]
    res.add("pills are used for status, not for data", len(pills) - len(status_pills) <= 1,
            f"{len(pills) - len(status_pills)} pill(s) carrying measurements")

    # "Repeated summary / recommendation blocks that restate one another."
    repeats = html.count("Not observed")
    res.add("no section restates another", repeats <= 2,
            f"'Not observed' appears {repeats} times")


def static_checks(path: Path, hero: bool, res: Result):
    html = path.read_text(encoding="utf-8", errors="replace")
    size = path.stat().st_size
    budget = HERO_BUDGET if hero else LIGHT_BUDGET
    res.add("size budget", size <= budget,
            f"{size / 1024:.1f} KB of {budget / 1024:.0f} KB")

    external = [m.group(0) for m in EXTERNAL.finditer(html)]
    # Linking the source's own @font-face files is a declared trade, not a defect: the guide renders
    # in the real typeface and stops being offline. The gate has to tell the two apart, or the
    # honest edition always looks broken and the check stops being read.
    # Count RULES, not the words. The page also says "No @font-face rule was readable" in
    # prose, and counting that made an injected external stylesheet look like a linked font.
    faces = len(re.findall(r"@font-face\s*\{", html))
    if faces and external:
        # One face legitimately declares several URLs — woff2 and woff, sometimes ttf — so the
        # budget is per format, not per rule. More than that and something other than a font is
        # being fetched, which is the case this check exists for.
        res.add("external references are only the linked font faces", len(external) <= faces * 3,
                f"{len(external)} reference(s) from {faces} @font-face rule(s) — "
                f"this edition is NOT offline, by choice (--link-fonts)")
    else:
        res.add("opens offline, no external reference", not external,
                f"{len(external)} external reference(s)" if external else "no http(s) reference")

    present = [s for s in REQUIRED_SECTIONS if f'id="{s}"' in html]
    res.add("every required section is present", len(present) == len(REQUIRED_SECTIONS),
            f"missing: {', '.join(set(REQUIRED_SECTIONS) - set(present))}"
            if len(present) != len(REQUIRED_SECTIONS) else f"{len(present)} sections")

    labels = html.count("Unofficial analysis")
    res.add("Unofficial label on cover, bar and footer", labels >= 3, f"{labels} occurrence(s)")
    res.add("disclaimer names the owner of the marks",
            "Trademarks" in html and "belong to their owners" in html)

    m = re.search(r'<script type="application/json" id="tokens-json">(.*?)</script>', html, re.S)
    if not m:
        res.add("token JSON is embedded and parses", False, "no tokens-json block")
        return None
    try:
        tokens = json.loads(m.group(1))
        res.add("token JSON is embedded and parses", True,
                f"{len(tokens.get('color', {}).get('roles', {}))} colour roles")
        tokens["_linkedFaces"] = faces
    except json.JSONDecodeError as e:
        res.add("token JSON is embedded and parses", False, str(e))
        return None

    # Every image in the hero edition must say it is generated. An unlabelled AI image in a document
    # about someone else's brand is the one thing here that could mislead a reader.
    imgs = len(re.findall(r'class="img-\d+"', html))
    if imgs:
        res.add("every image carries its AI label",
                html.count("AI-generated image") >= imgs, f"{imgs} image(s)")

    voice = tokens.get("voice")
    if voice:
        res.add("voice carries three rules", len(voice.get("rules", [])) >= 3,
                f"{len(voice.get('rules', []))} rule(s)")
        if tokens["source"].get("origin") and voice.get("quotes"):
            res.add("voice quotes are short enough to be fair use",
                    all(len(q.get("text", "").split()) <= 15 for q in voice["quotes"]),
                    f"{len(voice['quotes'])} quote(s)")

    slop_checks(html, res)

    # The whole point: a value that appears as a literal where a token should be. The guide's own
    # controls are checked properly in the browser; this catches the gross case cheaply.
    style = re.search(r"<style>(.*?)</style>", html, re.S)
    if style:
        rules = re.sub(r":root\s*\{.*?\}", "", style.group(1), flags=re.S)
        literals = re.findall(r"(?<!-)\b(?:background|color|border-radius|box-shadow)\s*:\s*"
                              r"(#[0-9a-fA-F]{3,8})\s*[;}]", rules)
        res.add("the stylesheet holds no literal colour outside :root", not literals,
                f"{len(literals)} literal(s): {', '.join(sorted(set(literals))[:4])}"
                if literals else "every rule reads a variable")
    return tokens


def inpage_checks(path: Path, tokens, res: Result):
    """Fold in what only a browser could answer. A missing file is a FAILED check, never a skipped
    one: a verification that was not run must never look like one that passed."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        res.add("in-page checks were obtained", False, str(e))
        return

    res.add("in-page checks were obtained", True, f"{len(data.get('rebuild', []))} control(s)")

    mismatches = [r for r in data.get("rebuild", []) if not r.get("ok")]
    res.add("rebuilt controls equal their tokens", not mismatches,
            "; ".join(f"{m['control']}.{m['property']}: {m['computed']} != {m['token']}"
                      for m in mismatches[:3]) if mismatches else
            f"{len(data.get('rebuild', []))} property checks")

    res.add("no horizontal scroll at 390px", data.get("noHorizontalScroll") is True,
            f"scrollWidth {data.get('scrollWidth')} > clientWidth {data.get('clientWidth')}"
            if data.get("noHorizontalScroll") is not True else "390px clean")
    if "networkRequests" in data:
        # Same declared trade as the static half: with --link-fonts the page fetches the source's
        # own font files and nothing else. A check that cannot tell that from a stray tracker is a
        # check people learn to ignore.
        faces = (tokens or {}).get("_linkedFaces", 0)
        if faces:
            res.add("network requests are only the linked fonts",
                    data["networkRequests"] <= faces * 3,
                    f"{data['networkRequests']} request(s) for {faces} face(s) — not offline, by choice")
        else:
            res.add("zero network requests when opened", data["networkRequests"] == 0,
                    f"{data['networkRequests']} request(s)")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("guide", type=Path)
    ap.add_argument("--inpage", type=Path, default=None)
    ap.add_argument("--hero", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if not args.guide.is_file():
        print(f"{args.guide}: not a file", file=sys.stderr)
        return 2

    res = Result()
    tokens = static_checks(args.guide, args.hero, res)
    if args.inpage:
        inpage_checks(args.inpage, tokens, res)
    else:
        res.add("in-page checks were obtained", False,
                "not run — pass --inpage with the result of verify_page.js")

    if not args.json:
        print(f"verify {args.guide.name}")
    res.report(args.json)
    return 1 if res.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
