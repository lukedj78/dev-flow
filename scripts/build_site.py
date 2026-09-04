#!/usr/bin/env python3
"""build_site.py — generate the docs/ site from skills.json + the SKILL.md files

The browsable index at docs/index.html (the Pages root), plus one page per
skill under docs/skills/. The skill pages are foldered rather than loose in
docs/ so that one HTML file per skill does not sit among the hand-written docs.

GENERATED, never hand-edited. The catalogue in README.md is hand-written prose
and stays that way (see lint check 10); this is the other thing — a complete,
mechanical index that cannot drift because nobody maintains it. Same principle
as .claude-plugin/plugin.json: one taxonomy, several artefacts built from it.

Usage:
    python3 scripts/build_site.py            # write docs/site/
    python3 scripts/build_site.py --check    # fail if the output is stale (CI)

Run from the repo root.
"""
from __future__ import annotations

import html
import json
import re
import sys

import yaml
from pathlib import Path

OUT = Path("docs")
SKILLS_DIR = "skills"
REPO = "https://github.com/lukedj78/dev-flow"
# The footer count lives here, not as a literal in `shell()`: it sat at 44 on every
# generated page while skills.json already said 46, and no lint check covers the
# generated site. Read it from the registry like every other number on the page.
TOTAL = len(json.loads(Path("skills.json").read_text())["skills"])

FAMILY_LABEL = {
    "core": ("Core", "Stack-agnostic. Every project uses these."),
    "web": ("Web", "Next.js 16 · App Router · shadcn / Base UI / MUI / Coss."),
    "agent": ("Agent", "The eve engine — inside the app, beside it, or alone."),
    "mobile": ("Mobile", "Expo + React Native. Nine teach the stack, seven operate on it."),
    "monorepo": ("Monorepo", "turborepo + shared packages across web, mobile and agent."),
    "refactor": ("Refactor", "Stack-agnostic composition and colocation."),
}
FAMILY_ORDER = ["core", "web", "agent", "mobile", "monorepo", "refactor"]
ROLE_NOTE = {
    "orchestrator": "routes, never builds",
    "discovery": "turns intent into artefacts",
    "operative": "changes the codebase",
    "knowledge": "teaches; changes nothing",
}

CSS = """
*,*::before,*::after{box-sizing:border-box}
:root{
  --bg:#eef1f8; --panel:#fff; --panel-2:#f3f6fd;
  --bd:rgba(30,45,110,.12); --bd-2:rgba(30,45,110,.22);
  --tx:#0f1526; --dim:#4a5573; --faint:#8590ac;
  --ac:#3a53e6; --ac-soft:rgba(58,83,230,.10);
  --c-core:#c07d17; --c-web:#3a53e6; --c-agent:#7c4fe0;
  --c-mobile:#0c9f92; --c-monorepo:#1c86a6; --c-refactor:#e0475f;
  --shadow:0 1px 0 rgba(255,255,255,.7) inset, 0 12px 26px -20px rgba(20,30,80,.35);
  --fS:ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif;
  --fM:ui-monospace,"SF Mono","JetBrains Mono",Menlo,Consolas,monospace;
  --maxw:1080px;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --bg:#0a0c13; --panel:#111524; --panel-2:#151a2b;
  --bd:rgba(139,163,255,.11); --bd-2:rgba(139,163,255,.22);
  --tx:#eef1fb; --dim:#9aa4c0; --faint:#5c6688;
  --ac:#6f8bff; --ac-soft:rgba(111,139,255,.16);
  --c-core:#f0b64d; --c-web:#6f8bff; --c-agent:#b487ff;
  --c-mobile:#33d3c2; --c-monorepo:#4ec6e6; --c-refactor:#ff7d92;
  --shadow:0 1px 0 rgba(255,255,255,.04) inset, 0 12px 30px -18px rgba(0,0,0,.8);
}}
:root[data-theme="dark"]{
  --bg:#0a0c13; --panel:#111524; --panel-2:#151a2b;
  --bd:rgba(139,163,255,.11); --bd-2:rgba(139,163,255,.22);
  --tx:#eef1fb; --dim:#9aa4c0; --faint:#5c6688;
  --ac:#6f8bff; --ac-soft:rgba(111,139,255,.16);
  --c-core:#f0b64d; --c-web:#6f8bff; --c-agent:#b487ff;
  --c-mobile:#33d3c2; --c-monorepo:#4ec6e6; --c-refactor:#ff7d92;
  --shadow:0 1px 0 rgba(255,255,255,.04) inset, 0 12px 30px -18px rgba(0,0,0,.8);
}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--tx);font-family:var(--fS);
  line-height:1.6;-webkit-font-smoothing:antialiased}
.wrap{max-width:var(--maxw);margin:0 auto;padding:0 22px}
a{color:var(--ac);text-decoration:none}
a:hover{text-decoration:underline}
a:focus-visible,button:focus-visible{outline:2px solid var(--ac);outline-offset:2px;border-radius:4px}
code{font-family:var(--fM);font-size:.9em;background:var(--ac-soft);
  padding:.12em .38em;border-radius:5px}
pre{background:var(--panel-2);border:1px solid var(--bd);border-radius:12px;
  padding:14px 16px;overflow-x:auto;font-family:var(--fM);font-size:13px;line-height:1.55}
pre code{background:none;padding:0}
header.top{border-bottom:1px solid var(--bd);background:var(--panel);position:sticky;top:0;z-index:5}
header.top .wrap{display:flex;align-items:center;gap:14px;height:56px}
.brand{font-weight:650;letter-spacing:-.01em;color:var(--tx)}
.brand:hover{text-decoration:none}
.top nav{margin-left:auto;display:flex;gap:18px;font-size:14px}
.hero{padding:56px 0 30px}
h1{font-size:clamp(30px,5vw,46px);line-height:1.08;letter-spacing:-.025em;margin:0 0 14px;
  text-wrap:balance;font-weight:680}
h1 .g{color:var(--ac)}
.lede{font-size:17px;color:var(--dim);max-width:62ch;margin:0}
.eyebrow{font-family:var(--fM);font-size:11.5px;letter-spacing:.16em;text-transform:uppercase;
  color:var(--faint);margin:0 0 10px}
section{padding:34px 0}
h2{font-size:23px;letter-spacing:-.015em;margin:0 0 6px;font-weight:660}
.sub{color:var(--dim);margin:0 0 20px;max-width:64ch}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(268px,1fr));gap:14px}
.card{background:var(--panel);border:1px solid var(--bd);border-radius:14px;padding:16px 17px;
  box-shadow:var(--shadow);display:flex;flex-direction:column;gap:7px}
a.card:hover{border-color:var(--bd-2);text-decoration:none}
.card .nm{font-family:var(--fM);font-size:14px;font-weight:600;color:var(--tx);
  display:flex;align-items:center;gap:8px}
.card .nm i{width:7px;height:7px;border-radius:99px;flex:0 0 auto}
.card p{margin:0;font-size:13.5px;color:var(--dim);line-height:1.5}
.role{font-family:var(--fM);font-size:10.5px;letter-spacing:.06em;text-transform:uppercase;
  color:var(--faint);margin-left:auto}
.fam-core i{background:var(--c-core)} .fam-web i{background:var(--c-web)}
.fam-agent i{background:var(--c-agent)} .fam-mobile i{background:var(--c-mobile)}
.fam-monorepo i{background:var(--c-monorepo)} .fam-refactor i{background:var(--c-refactor)}
.chips{display:flex;flex-wrap:wrap;gap:7px;margin:0 0 18px;padding:0;list-style:none}
.chip{font-family:var(--fM);font-size:11.5px;border:1px solid var(--bd);border-radius:99px;
  padding:3px 10px;color:var(--dim);background:var(--panel)}
.meta{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 22px;padding:0;list-style:none}
.prose h3{font-size:16px;margin:26px 0 8px;letter-spacing:-.01em}
.prose ul{padding-left:20px;margin:8px 0}
.prose li{margin:5px 0;color:var(--dim)}
.prose li strong,.prose li code{color:var(--tx)}
.back{font-size:14px;color:var(--dim)}
footer{border-top:1px solid var(--bd);margin-top:40px;padding:22px 0 40px;
  color:var(--faint);font-size:13px}
footer .wrap{display:flex;flex-wrap:wrap;gap:14px}
footer a{color:var(--dim)}
@media (max-width:640px){.grid{grid-template-columns:1fr}.hero{padding:36px 0 22px}}
"""

# localStorage throws a SecurityError on restricted origins (file:, data:,
# sandboxed iframes). Unguarded, that exception kills the IIFE before __t is
# assigned and the toggle silently does not exist — which is exactly how it
# first shipped. Every access is wrapped; the toggle degrades to
# session-only rather than disappearing.
THEME_JS = """
(function(){var k='devflow-theme',d=document.documentElement;
function get(){try{return localStorage.getItem(k)}catch(e){return null}}
function set(v){try{localStorage.setItem(k,v)}catch(e){}}
var s=get(); if(s){d.setAttribute('data-theme',s)}
window.__t=function(){var c=d.getAttribute('data-theme');
if(!c){c=matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'}
var n=c==='dark'?'light':'dark';d.setAttribute('data-theme',n);set(n)}})();
"""


def e(t: str) -> str:
    return html.escape(t or "", quote=True)


def inline_md(t: str) -> str:
    """The small subset that appears in these files: code, bold, links."""
    t = e(t)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    return t


def shell(title: str, desc: str, body: str, depth: str = "") -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<style>{CSS}</style>
<script>{THEME_JS}</script>
</head>
<body>
<header class="top"><div class="wrap">
  <a class="brand" href="{depth}index.html">dev-flow</a>
  <nav>
    <a href="{REPO}">GitHub</a>
    <a href="{REPO}/blob/main/CHANGELOG.md">Changelog</a>
    <a href="#" onclick="__t();return false">Theme</a>
  </nav>
</div></header>
{body}
<footer><div class="wrap">
  <span>{TOTAL} skills, one contract. MIT.</span>
  <a href="{REPO}">github.com/lukedj78/dev-flow</a>
  <span>Generated from <code>skills.json</code> — do not edit by hand.</span>
</div></footer>
</body>
</html>
"""


def first_sentence(d: str) -> str:
    m = re.match(r"(.+?[.!?])(\s|$)", d.strip())
    return (m.group(1) if m else d)[:190]


def full_description(md: Path) -> str | None:
    """The WHOLE description, from the frontmatter.

    Not skills.json's: that registry truncates to 300 chars for compactness, and
    a page that renders the truncation shows a sentence cut mid-word — with an
    unpaired backtick where the cut landed inside `code`. The registry is right
    to be terse; a detail page is the wrong place to inherit it.
    """
    try:
        fm = yaml.safe_load(md.read_text().split("---", 2)[1])
        return fm.get("description")
    except Exception:
        return None


def extract(md: Path) -> dict:
    """The two sections worth surfacing, where a skill has them."""
    text = md.read_text()
    out = {}
    for key, head in (("when", "When this skill applies"), ("not", "What this skill does NOT do")):
        m = re.search(rf"^## {re.escape(head)}\s*\n(.+?)(?=\n## |\Z)", text, re.S | re.M)
        if m:
            items = [inline_md(x.strip()) for x in re.findall(r"^[-*] (.+)$", m.group(1), re.M)]
            if items:
                out[key] = items[:6]
    return out


def build() -> dict[str, str]:
    data = json.loads(Path("skills.json").read_text())
    skills = data["skills"]
    by_family: dict[str, list] = {}
    for s in skills:
        by_family.setdefault(s["family"], []).append(s)

    pages: dict[str, str] = {}

    # ---- index -------------------------------------------------------------
    counts = " · ".join(
        f"{len(by_family.get(f, []))} {FAMILY_LABEL[f][0].lower()}" for f in FAMILY_ORDER if by_family.get(f)
    )
    parts = [f"""<div class="wrap hero">
  <p class="eyebrow">github.com/lukedj78/dev-flow · MIT</p>
  <h1><span class="g">{len(skills)} skills</span> that take an idea<br>all the way to production.</h1>
  <p class="lede">Every project lives in one folder — <code>.workflow/</code> — with one state file.
  The skills read and write it, so each one knows what the last one did. The contract is the product;
  the skills are replaceable consumers of it.</p>
</div>

<section><div class="wrap">
  <h2>Install</h2>
  <p class="sub">As a Claude Code plugin, or as plain files for Codex, Gemini, Copilot and Cursor.</p>
  <pre><code>/plugin marketplace add lukedj78/dev-flow
/plugin install dev-flow@dev-flow</code></pre>
  <pre><code>git clone {REPO}.git &amp;&amp; cd dev-flow
./install.sh --platform claude   # or codex | gemini | cursor</code></pre>
</div></section>

<section><div class="wrap">
  <h2>The {len(skills)} skills</h2>
  <p class="sub">{counts}. A <strong>knowledge</strong> skill teaches and changes nothing;
  an <strong>operative</strong> one edits the codebase; <strong>discovery</strong> turns intent into
  artefacts; the <strong>orchestrator</strong> only routes.</p>
</div></section>"""]

    for fam in FAMILY_ORDER:
        group = sorted(by_family.get(fam, []), key=lambda s: (s["role"] != "orchestrator", s["name"]))
        if not group:
            continue
        label, blurb = FAMILY_LABEL[fam]
        cards = "\n".join(
            f"""    <a class="card fam-{fam}" href="{SKILLS_DIR}/{s['name']}.html">
      <span class="nm"><i></i>{e(s['name'])}<span class="role">{e(s['role'])}</span></span>
      <p>{inline_md(first_sentence(s['description']))}</p>
    </a>""" for s in group
        )
        parts.append(f"""<section id="{fam}"><div class="wrap">
  <h2>{e(label)} <span style="color:var(--faint);font-weight:400">· {len(group)}</span></h2>
  <p class="sub">{e(blurb)}</p>
  <div class="grid">
{cards}
  </div>
</div></section>""")

    pages["index.html"] = shell(
        f"dev-flow — {len(skills)} skills, one contract",
        "A contract-driven skill suite that takes a product idea to production: PRD, design, scaffold, modules, tests, gates, deploy.",
        "\n".join(parts),
    )

    # ---- one page per skill ------------------------------------------------
    for s in skills:
        name, fam = s["name"], s["family"]
        sec = extract(Path(s["skill_file"]))
        meta = [f'<li class="chip">{e(FAMILY_LABEL[fam][0])}</li>',
                f'<li class="chip">{e(s["role"])} — {e(ROLE_NOTE.get(s["role"], ""))}</li>',
                f'<li class="chip">{s["skill_md_lines"]} lines</li>']
        if s["references"]:
            meta.append(f'<li class="chip">{len(s["references"])} reference'
                        f'{"s" if len(s["references"]) != 1 else ""}</li>')
        if s["scripts"]:
            meta.append(f'<li class="chip">{len(s["scripts"])} script'
                        f'{"s" if len(s["scripts"]) != 1 else ""}</li>')

        body = [f'<div class="wrap hero">',
                f'  <p class="eyebrow"><a class="back" href="../index.html">← all skills</a></p>',
                f'  <h1 style="font-family:var(--fM);font-size:clamp(26px,4vw,36px)">{e(name)}</h1>',
                f'  <ul class="meta">{"".join(meta)}</ul>',
                f'  <p class="lede">{inline_md(full_description(Path(s["skill_file"])) or s["description"])}</p>',
                f'</div>',
                f'<section><div class="wrap prose">']
        if sec.get("when"):
            body.append("  <h3>When it applies</h3>\n  <ul>" +
                        "".join(f"<li>{x}</li>" for x in sec["when"]) + "</ul>")
        if sec.get("not"):
            body.append("  <h3>What it does not do</h3>\n  <ul>" +
                        "".join(f"<li>{x}</li>" for x in sec["not"]) + "</ul>")
        if s["references"]:
            body.append("  <h3>References it ships</h3>\n  <ul>" + "".join(
                f'<li><a href="{REPO}/blob/main/{name}/references/{e(r)}"><code>{e(r)}</code></a></li>'
                for r in s["references"]) + "</ul>")
        body.append(f"""  <h3>Get it</h3>
  <pre><code>/plugin install dev-flow@dev-flow      # the whole suite
./install.sh --platform claude        # or drop {e(s['bundle'])} into Claude Code</code></pre>
  <p class="sub"><a href="{REPO}/blob/main/{e(s['skill_file'])}">Read {e(s['skill_file'])} on GitHub →</a></p>
</div></section>""")
        pages[f"{SKILLS_DIR}/{name}.html"] = shell(f"{name} — dev-flow",
                                      first_sentence(s["description"]), "\n".join(body), "../")
    return pages


def main() -> int:
    if not Path("skills.json").exists():
        sys.stderr.write("skills.json not found. Run from the repo root.\n")
        return 2
    pages = build()
    check = "--check" in sys.argv[1:]
    stale = []
    for rel, content in pages.items():
        p = OUT / rel
        if check:
            if not p.exists() or p.read_text() != content:
                stale.append(rel)
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content)
    # Only ever consider pages we own: docs/ also holds the hand-made
    # dev-flow-skill-map.html, which must never be swept up as an orphan.
    sd = OUT / SKILLS_DIR
    existing = {f"{SKILLS_DIR}/{f.name}" for f in sd.glob("*.html")} if sd.exists() else set()
    orphans = sorted(existing - set(pages))
    if check:
        if stale or orphans:
            for r in stale:
                sys.stderr.write(f"✗ stale: docs/{r}\n")
            for r in orphans:
                sys.stderr.write(f"✗ orphan page (skill removed?): docs/{r}\n")
            sys.stderr.write("Run: python3 scripts/build_site.py\n")
            return 2
        print(f"✓ docs/ site up to date ({len(pages)} pages)")
        return 0
    for r in orphans:
        (OUT / r).unlink()
        print(f"  removed orphan {r}")
    print(f"✓ docs/ site regenerated ({len(pages)} pages)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
