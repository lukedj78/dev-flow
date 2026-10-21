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


def static_checks(path: Path, hero: bool, res: Result):
    html = path.read_text(encoding="utf-8", errors="replace")
    size = path.stat().st_size
    budget = HERO_BUDGET if hero else LIGHT_BUDGET
    res.add("size budget", size <= budget,
            f"{size / 1024:.1f} KB of {budget / 1024:.0f} KB")

    external = [m.group(0) for m in EXTERNAL.finditer(html)]
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
