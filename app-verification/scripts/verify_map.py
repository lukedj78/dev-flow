#!/usr/bin/env python3
"""verify_map.py — the mechanical half of a project's verification manual.

    python3 verify_map.py scaffold <project-root> [--app web] [--json]
    python3 verify_map.py check    <project-root> [--app web] [--json]

`scaffold` writes `.claude/skills/verify-<app>/`: a SKILL.md with the six sections to fill, and one feature file per
PRD story (`- **US-N.** …`), each pre-filled with the screens, routes, roles and states the wireframe inventory maps
to it (`docs/wireframes/screen-inventory.md`); with no inventory it lists the app's routes instead and says so. It
never overwrites a file, so a filled manual survives a re-run and a new story gets its file.

`check` refuses a manual with a gap: a `<fill: …>` left anywhere (code blocks included), a missing section, a story
with no feature file, a feature file out of shape or missing from the index, a script that is not executable or that
SKILL.md never names, an evidence directory git does not ignore.

The other half — the launch command, the selectors, the results, and one live run that proves it — is the agent's,
following `app-verification/SKILL.md`. Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import surfaces as sf  # noqa: E402 — vendored copy of dev-flow/scripts/surfaces.py; lint_skills.py keeps it identical

SECTIONS = ("Launch", "Doctor", "Drive", "Evidence", "Cleanup", "Isolation")
FEATURE_SECTIONS = ("Sub-features", "How to get to it (user POV)", "Driving it with", "Gotchas")
FILL = re.compile(r"<fill:[^>]*>")
LOCALE_SEGMENTS = {"[locale]", "[lang]", "[lng]"}
STATE_NAMES = {"L": "loading", "E": "empty", "Er": "error", "S": "success"}
EVIDENCE_DIR = ".verification/evidence"
# `- **US-1.** …`, `- **US-1 (P1).** …`, `- **US-1:** …`, `- **US-1** …` — the PRD template and what projects wrote
STORY = re.compile(r"^\s*-\s+\*\*(US-\d+)(?:\s*\([^)]*\))?[.:]?\*\*[.:]?\s+(.+?)\s*$", re.M)

FILL_TEXT = {
    "Launch": "<fill: the exact command that starts the app for verification, its port and env vars, and how to tell "
              "it is READY — usable, not just answering: from an empty data dir, migrations and seed included. Name "
              "the configuration in .claude/launch.json that runs the same command. Record the PID and port it "
              "started, for Cleanup.>",
    "Doctor": "<fill: one read-only check that says whether this instance is worth driving — the process is ours, the "
              "build is the right one, the port is ours, the session is valid. Run it first, and again after anything "
              "surprising.>",
    "Drive": "<fill: the harness for this stack (references/stack-recipes.md) with the repo's real handles — ARIA "
             "roles and accessible names, data- attributes, routes — never coordinates or tab order.>",
    "Evidence": "Proof goes to `" + EVIDENCE_DIR + "/<UTC timestamp>/`, which git ignores, and survives Cleanup.\n\n"
                "- Exercise the real user path: never a test-only endpoint or an internal setter.\n"
                "- Capture the action and the state it produced, not only the final screen.\n"
                "- Verify the side effects too: the row written, the file created, the message sent.\n"
                "- Mocks only where a production boundary already isolates the external system.\n"
                "- A dry-run or test mode is verified by observing what it really skips, never trusted by its name.\n"
                "- Never weaken a journey to make it pass: a missing precondition is a failure, written down.\n\n"
                "<fill: what this app's proof looks like — which snapshot, which query, which log line.>",
    "Cleanup": "<fill: how to stop what this run started — by the PID and port recorded at Launch, never by process "
               "name — and remove scratch data. Never delete the evidence.>",
    "Isolation": "<fill: whether two instances can run side by side (port, data dir, profile). If not, say so: this "
                 "manual refuses to drive an instance it did not start.>",
}


@dataclass
class Screen:
    id: str
    area: str
    name: str
    route: str
    roles: list[str] = field(default_factory=list)
    stories: list[str] = field(default_factory=list)
    states: list[str] = field(default_factory=list)


def read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def stories(prd: str) -> list[tuple[str, str]]:
    """The PRD's stories, from `- **US-N.** …` list items only — a table that mentions US-N is not a story."""
    out, seen = [], set()
    for m in STORY.finditer(prd):
        if m.group(1) not in seen:
            seen.add(m.group(1))
            out.append((m.group(1), m.group(2)))
    return out


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _list(cell: str) -> list[str]:
    return [x.strip() for x in cell.split(",") if x.strip() and x.strip() not in ("—", "-")]


def inventory(text: str) -> list[Screen]:
    """Rows of wireframe-canvas's screen inventory: `| ID | Screen | Route | Roles | Stories | States |` under `## …`."""
    out, area, header = [], "", None
    for line in text.splitlines():
        if line.startswith("## "):
            area, header = line[3:].strip(), None
        elif line.strip().startswith("|"):
            cells = _cells(line)
            if header is None and [c.lower() for c in cells[:6]] == ["id", "screen", "route", "roles", "stories", "states"]:
                header = cells
            elif header and not set("".join(cells)) <= set("-: "):
                if len(cells) >= 6:
                    out.append(Screen(cells[0], area, cells[1], cells[2].strip("`"), _list(cells[3]),
                                      _list(cells[4]), _list(cells[5])))
    return out


def is_expo(root: Path) -> bool:
    """Expo Router has an app/ directory too: expo without next in package.json, app.config.*, or app.json."""
    try:
        pkg = json.loads(read(root / "package.json") or "{}")
    except ValueError:
        pkg = {}
    deps = set(pkg.get("dependencies") or {}) | set(pkg.get("devDependencies") or {}) if isinstance(pkg, dict) else set()
    if "next" in deps:
        return False
    return "expo" in deps or any(root.glob("app.config.*")) or '"expo"' in read(root / "app.json")


def routes(root: Path) -> list[str]:
    """The app's routes when there is no inventory: Next `page.*` files, or Expo Router screens. Route groups
    `(x)` are dropped, dynamic segments `[x]` kept."""
    expo = is_expo(root)
    found = set()
    for base in (root / "app", root / "src" / "app"):
        for p in (q for q in base.rglob("*") if q.is_file()) if base.is_dir() else []:
            if expo:
                if p.suffix not in (".tsx", ".ts", ".jsx", ".js") or p.stem.startswith(("_", "+")):
                    continue
                segments = list(p.relative_to(base).parts[:-1]) + ([] if p.stem == "index" else [p.stem])
            else:
                if p.stem != "page" or p.suffix not in (".tsx", ".ts", ".jsx", ".js"):
                    continue
                segments = list(p.relative_to(base).parts[:-1])
            segments = [x for x in segments if not (x.startswith("(") and x.endswith(")"))]
            if segments and segments[0] in LOCALE_SEGMENTS:   # the i18n prefix: next-intl serves the default without it
                segments = segments[1:]
            found.add("/" + "/".join(segments))
    return sorted(found)


def slug(sentence: str) -> str:
    """What the user wants, up to six words: `I want (to) <this>, so that …` → `<this>`."""
    m = re.search(r"\b(?:I want(?: to)?|voglio)\s+(.+?)(?:,?\s+(?:so that|così che|così da|in modo da)\b|[.,;]|$)", sentence)
    action = m.group(1) if m else sentence
    words = re.findall(r"[a-z0-9]+", action.lower())[:6]
    return "-".join(words) or "feature"


def manual_dir(root: Path, app: str) -> Path:
    return root / ".claude" / "skills" / f"verify-{app}"


UI_KINDS = ("web", "mobile")
DRIVE_HINT = {
    "web": "the built-in browser (or the repo's Playwright), by ARIA role and accessible name",
    "mobile": "the iOS simulator (or the repo's Maestro flows), by accessibilityLabel / testID",
    "agent": "a request to the agent's channel (its HTTP API, its MCP channel) with a fixed prompt per tool, as the seeded test identity",
    "api": "HTTP requests to the service's endpoints, with a test credential from the project's example config",
    "cli": "the command in its own terminal session, with literal arguments",
    "other": "whatever this surface exposes — find out from its scripts and say how",
}


def _skill_md(app: str, project: str, kind: str = "web", mounted_in: str | None = None) -> str:
    text = dict(FILL_TEXT)
    text["Drive"] = text["Drive"].replace("<fill: the harness for this stack (references/stack-recipes.md) with",
                                          f"<fill: {DRIVE_HINT.get(kind, DRIVE_HINT['other'])} — with")
    if mounted_in:
        text["Launch"] = (f"This surface is served by the `{mounted_in}` surface: launch it with "
                          f"`.claude/skills/verify-{mounted_in}/` (its Launch section) and come back here once that "
                          f"manual's Doctor passes. It never starts on its own.\n\n<fill: the URL prefix it is served "
                          f"under and how a caller authenticates to it locally.>")
        text["Cleanup"] = (f"Cleanup is `verify-{mounted_in}`'s: this surface started nothing of its own.\n\n<fill: "
                           f"anything this surface's journeys create (sessions, records) and how to remove it.>")
    sections = "\n\n".join(f"## {s}\n\n{text[s]}" for s in SECTIONS)
    return (f"---\nname: verify-{app}\ndescription: <fill: one sentence naming the app ({project}), the surface "
            f"({app}) and when to reach for this manual — to prove a feature works on the real app.>\n---\n\n"
            f"# Verify {project} ({app})\n\nThis manual is for the next agent, read cold mid-task: it takes you from "
            f"the app switched off to a saved proof and back to switched off. Features are in "
            f"[`features/`](features/README.md), one per PRD story.\n\n{sections}\n")


def _feature_md(sid: str, sentence: str, screens: list[Screen]) -> str:
    def state_id(st: str) -> str:   # `Er (bloccato)` → `error-bloccato`: one id per screen and state, no spaces
        head, _, rest = st.partition(" ")
        return "-".join(re.findall(r"[a-z0-9]+", (STATE_NAMES.get(head, head) + " " + rest).lower()))
    subs = [f"- `{sid.lower()}-{s.id.lower()}-{state_id(st)}` {STATE_NAMES.get(st.split(' ')[0], st)} state of {s.id} {s.name}"
            + (f" ({st.split(' ', 1)[1].strip('()')})" if " " in st else "")
            for s in screens for st in s.states]
    subs.append("- <fill: the story's branches — create, cancel, edit, the paths its acceptance names>")
    how = [f"- {s.id} {s.name} — `{s.route}` ({', '.join(s.roles) or 'any role'})" for s in screens] \
        or ["- <fill: the routes or entry points a user takes to reach this story>"]
    return (f"# {sid} — {sentence}\n\n<fill: one paragraph, the user-visible behaviour this story delivers.>\n\n"
            f"## Sub-features\n\n" + "\n".join(subs) + "\n\n"
            f"## How to get to it (user POV)\n\n" + "\n".join(how) + "\n\n"
            f"## Driving it with <fill: harness>\n\nPreconditions:\n\n- <fill: state this journey needs>\n\n"
            f"- **<fill: action>.** <fill: user action>. Run `<fill: command>`. <fill: observable result>.\n\n"
            f"## Gotchas\n\n- <fill: traps that waste or invalidate a run, or `none found yet`>\n")


def _readme_md(project: str, entries: list[tuple[str, str, str]], source: str, found_routes: list[str]) -> str:
    index = "\n".join(f"- [{sid} — {sentence}](./{name})" for sid, sentence, name in entries) or "- (no stories in the PRD)"
    origin = ("Screens, routes, roles and states come from `docs/wireframes/screen-inventory.md`. The inventory's routes "
              "are the design's: check each against the app before driving (on Archi Studio four had moved, `/sign-in` "
              "→ `/it/login`), and write the real one in the feature file." if source == "wireframes"
              else "There is no screen inventory (`docs/wireframes/screen-inventory.md`): the entry points below were "
                   "read from the app's routes (a leading `[locale]` segment dropped: it is the language prefix — add it back, e.g. `/it/…`, where the app always shows it) and must be matched to the stories by hand.\n\nRoutes found:\n\n"
                   + ("\n".join(f"- `{r}`" for r in found_routes) or "- (none)"))
    return (f"# {project} verification map\n\nThe maintained source for proving {project}'s user-facing behaviour. "
            f"Read this index before driving the app, then use the matching feature file as the recipe.\n\n{origin}\n\n"
            f"## Baseline preconditions\n\n- <fill: how the app is launched for every recipe, the seed data, the test "
            f"accounts (from the project's seed or .env.test — never typed in chat)>\n\n"
            f"## Driving conventions\n\n- Start every recipe from the baseline state unless its preconditions say otherwise.\n"
            f"- Prefer ARIA roles and accessible names over CSS selectors or DOM position.\n"
            f"- Treat every command as literal.\n- Restore seeded data after a mutation; never remove proof artifacts.\n\n"
            f"## Proof and skip reporting\n\n- Capture the user action and the resulting state, not only the final screen.\n"
            f"- A mutation is proven by a second, read-only view of the stored value.\n"
            f"- Report an unreachable path with the attempted entry point and the unmet precondition.\n"
            f"- Never report an entry point as verified through a different one.\n\n"
            f"## Features\n\n{index}\n")


def _project(root: Path) -> str:
    try:
        meta = json.loads(read(root / ".workflow" / "meta.json") or "{}")
    except ValueError:
        meta = {}
    return str(meta.get("project_name") or root.name)


def _tools(root: Path, surface: "sf.Surface") -> list[tuple[str, str]]:
    """An agent's features are its tools: (id, title) per file in <agent>/tools/."""
    base = root / surface.path
    tools_dir = base / "tools" if (base / "tools").is_dir() else base / "agent" / "tools"
    out = []
    for p in sorted(tools_dir.glob("*")) if tools_dir.is_dir() else []:
        if p.suffix in (".ts", ".js", ".mjs") and not p.stem.startswith(("_", "index")) and ".test" not in p.name:
            out.append((f"tool-{re.sub(r'[^a-z0-9]+', '-', p.stem.lower()).strip('-')}", f"the `{p.stem}` tool"))
    return out


def _surface(root: Path, app: str) -> "sf.Surface":
    found = [s for s in sf.surfaces(root) if s.name == app]
    return found[0] if found else sf.Surface("web", app, ".")


def scaffold(root: Path, app: str = "web") -> dict:
    root = root.resolve()
    surface = _surface(root, app)
    if surface.kind not in UI_KINDS:
        return _scaffold_other(root, surface)
    m = manual_dir(root, app)
    story_list = stories(read(root / ".workflow" / "PRD.md"))
    inv_path = root / "docs" / "wireframes" / "screen-inventory.md"
    screens = inventory(read(inv_path)) if inv_path.is_file() else []
    source = "wireframes" if screens else "routes"
    found_routes = [] if screens else routes(root)
    written, kept, entries = [], [], []

    def put(p: Path, text: str) -> None:
        rel = str(p.relative_to(root))
        if p.exists():
            kept.append(rel)
            return
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        written.append(rel)

    project = _project(root)
    put(m / "SKILL.md", _skill_md(app, project, surface.kind, surface.mounted_in))
    features = m / "features"
    existing = {p.name.split("-", 2)[0] + "-" + p.name.split("-", 2)[1]: p.name
                for p in features.glob("US-*-*.md")} if features.is_dir() else {}
    for sid, sentence in story_list:
        name = existing.get(sid) or f"{sid}-{slug(sentence)}.md"
        entries.append((sid, sentence, name))
        put(features / name, _feature_md(sid, sentence, [s for s in screens if sid in s.stories]))
    readme = features / "README.md"
    if readme.exists():
        text = read(readme)
        missing = [e for e in entries if f"({'./' + e[2]})" not in text and f"]({e[2]})" not in text]
        if missing:   # a new story joins the index; the filled part is left alone
            readme.write_text(text.rstrip("\n") + "\n" + "\n".join(f"- [{s} — {t}](./{n})" for s, t, n in missing) + "\n",
                              encoding="utf-8")
        kept.append(str(readme.relative_to(root)))
    else:
        put(readme, _readme_md(project, entries, source, found_routes))
    return {"path": str(m.relative_to(root)), "source": source, "written": written, "kept": kept,
            "stories": len(story_list), "kind": surface.kind}


def _scaffold_other(root: Path, surface: "sf.Surface") -> dict:
    """A surface that is not a UI: an agent's features are its tools; an api, cli or other surface starts with one
    feature file to fill, because there is no PRD story or screen to seed it from."""
    m = manual_dir(root, surface.name)
    written, kept = [], []

    def put(p: Path, text: str) -> None:
        rel = str(p.relative_to(root))
        if p.exists():
            kept.append(rel)
            return
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        written.append(rel)

    project = _project(root)
    put(m / "SKILL.md", _skill_md(surface.name, project, surface.kind, surface.mounted_in))
    feats = _tools(root, surface) if surface.kind == "agent" else [(f"{surface.name}-main", f"the main {surface.kind} journey")]
    for fid, title in feats:
        put(m / "features" / f"{fid}.md", _feature_md(fid, title, []))
    index = "\n".join(f"- [{t}](./{f}.md)" for f, t in feats) or "- (no tools found)"
    origin = (f"Features are the agent's tools, one file per file in `{surface.path}/tools/`." if surface.kind == "agent"
              else f"There is no PRD story or screen for a {surface.kind} surface: list its journeys here.")
    readme = m / "features" / "README.md"
    if readme.exists():   # a feature added since the first run joins the index; the filled part is left alone
        text = read(readme)
        missing = [(f, t) for f, t in feats if f"{f}.md" not in text]
        if missing:
            readme.write_text(text.rstrip("\n") + "\n" + "\n".join(f"- [{t}](./{f}.md)" for f, t in missing) + "\n",
                              encoding="utf-8")
    put(readme,
        f"# {project} {surface.name} verification map\n\n{origin}\n\n## Baseline preconditions\n\n"
        f"- <fill: what every recipe needs>\n\n## Proof and skip reporting\n\n- Capture the request and the resulting "
        f"state, not only the response.\n- A side effect is proven by a second, read-only view of where it landed.\n"
        f"- Report an unreachable path with the unmet precondition.\n\n## Features\n\n{index}\n")
    return {"path": str(m.relative_to(root)), "source": "tools" if surface.kind == "agent" else "none",
            "written": written, "kept": kept, "stories": 0, "kind": surface.kind}


def scaffold_all(root: Path) -> list[dict]:
    """One manual per surface the project has; a project where none is detected gets the web manual."""
    found = sf.surfaces(root.resolve())
    return [scaffold(root, s.name) for s in found] or [scaffold(root, "web")]


def _sections(text: str) -> list[str]:
    return [m.group(1).strip() for m in re.finditer(r"^## (.+)$", text, re.M)]


def check(root: Path, app: str = "web") -> list[str]:
    root = root.resolve()
    m = manual_dir(root, app)
    skill = m / "SKILL.md"
    if not skill.is_file():
        return [f"{skill.relative_to(root)} does not exist — run `verify_map.py scaffold` first"]
    problems = []
    text = read(skill)
    if not re.match(rf"---\n(?:.*\n)*?name:\s*verify-{re.escape(app)}\s*\n(?:.*\n)*?description:\s*\S", text):
        problems.append(f"SKILL.md: frontmatter needs `name: verify-{app}` and a description")
    heads = _sections(text)
    for s in SECTIONS:
        if s not in heads:
            problems.append(f"SKILL.md: section `## {s}` is missing")
    for p in sorted(m.rglob("*")):
        if p.is_file() and p.suffix in (".md", ".sh", ".py", ".ts", ".js", ".json", ".txt"):
            for hit in FILL.findall(read(p)):
                problems.append(f"{p.relative_to(m)}: still to fill — {hit[:70]}")
    features = m / "features"
    index = read(features / "README.md")
    if not index:
        problems.append("features/README.md is missing")
    surface = _surface(root, app)
    files = sorted(f for f in features.glob("*.md") if f.name != "README.md") if features.is_dir() else []
    if surface.kind in UI_KINDS:
        for sid, _ in stories(read(root / ".workflow" / "PRD.md")):
            if not any(f.name.startswith(f"{sid}-") for f in files):
                problems.append(f"features/: story {sid} has no feature file")
    elif surface.kind == "agent":
        for fid, _ in _tools(root, surface):
            if not (features / f"{fid}.md").is_file():
                problems.append(f"features/: tool {fid} has no feature file")
    for f in files:
        heads = _sections(read(f))
        order = [next((i for i, h in enumerate(heads) if h.startswith(want)), None) for want in FEATURE_SECTIONS]
        if None in order or order != sorted(order):
            problems.append(f"features/{f.name}: needs the four sections in order — " + ", ".join(FEATURE_SECTIONS))
        if f.name not in index:
            problems.append(f"features/{f.name} is not linked from features/README.md")
    scripts = m / "scripts"
    for s in sorted(scripts.rglob("*")) if scripts.is_dir() else []:
        if s.is_file():
            if not os.access(s, os.X_OK):
                problems.append(f"scripts/{s.name} is not executable")
            if s.name not in text:
                problems.append(f"scripts/{s.name} is never named in SKILL.md — a helper nobody is told to run is not one")
    if EVIDENCE_DIR not in text:
        problems.append(f"SKILL.md: the evidence directory `{EVIDENCE_DIR}/` is never named")
    ignore = read(root / ".gitignore")
    if not re.search(r"^/?\.verification/?\s*$", ignore, re.M):
        problems.append("`.verification/` is not in the project's .gitignore — the evidence would end up in git")
    return problems


def check_all(root: Path) -> list[str]:
    """Every surface has its manual, and every manual is complete. Problems are prefixed by the manual."""
    root = root.resolve()
    found = sf.surfaces(root) or [sf.Surface("web", "web", ".")]
    problems = []
    for s in found:
        if not (manual_dir(root, s.name) / "SKILL.md").is_file():
            problems.append(f"verify-{s.name}: no manual for the {s.kind} surface at {s.path} — "
                            f"run `verify_map.py scaffold {root}`")
        else:
            problems += [f"verify-{s.name}: {p}" for p in check(root, s.name)]
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("op", choices=("scaffold", "check"))
    ap.add_argument("project_root", type=Path)
    ap.add_argument("--app", default=None, help="one surface by name; every surface when omitted")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    root = a.project_root
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2
    if a.op == "scaffold":
        results = [scaffold(root, a.app)] if a.app else scaffold_all(root)
        if a.json:
            print(json.dumps(results if not a.app else results[0], indent=2))
        else:
            for r in results:
                what = (f"{r['stories']} stories found, entry points from {r['source']}" if r["kind"] in UI_KINDS
                        else f"{r['kind']} surface, features from {r['source']}")
                print(f"{r['path']}: {what}; {len(r['written'])} written, {len(r['kept'])} kept.")
                if r["kind"] in UI_KINDS and r["stories"] == 0:
                    print("  No `- **US-N.** …` story in .workflow/PRD.md — the map has no features to seed.")
        return 0
    problems = check(root, a.app) if a.app else check_all(root)
    if a.json:
        print(json.dumps({"problems": problems}, indent=2))
    else:
        print("\n".join(problems) if problems else "The manual is complete. Prove it live before handing it over.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
