#!/usr/bin/env python3
"""Govern what a shadcn-format registry is allowed to write into a project.

`shadcn add @ns/item` copies someone else's source into the repo, pulls their npm
dependencies, can set env vars and rewrite theme tokens, and fetches whatever the URL
serves *today*. This script puts four barriers in front of that:

  1. an allowlist of registries, per project           (allow / deny)
  2. a review of the item and everything it pulls in   (review)
  3. a snapshot that is installed instead of the URL   (approve / install)
  4. a check that nothing bypassed 1-3                  (check, hook)

    registry_intake.py setup   <root>                         create the lock, wire the hook
    registry_intake.py allow   <root> @ns <url> --reason ...  add a registry to the allowlist
    registry_intake.py deny    <root> @ns                     remove it
    registry_intake.py review  <root> <item> [--json]         read-only; exit 0 clean · 3 needs a human · 1 blocked
    registry_intake.py approve <root> <item> --by NAME [--accept CODE=reason ...] [--note ...]
    registry_intake.py install <root> <item> [-- shadcn args]  install the approved snapshot
    registry_intake.py check   <root>                          gate / CI; exit 0 or 1
    registry_intake.py caps    <root> --reason ...             accept a raised design-lint cap
    registry_intake.py hook                                    Claude Code PreToolUse hook (stdin JSON)

<item> is `@ns/name`, a registry-item URL, or a local .json path. Bare names (`button`)
are shadcn's own registry and are not governed here.

Stdlib only. Network: the registry URLs and `npm view`.
"""

from __future__ import annotations

import argparse
import datetime as dt
import difflib
import hashlib
import json
import re
import shlex
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path

LOCK = "registry-lock.json"
VENDOR = "vendor/registry"
SHADCN_VERSION = "4.21.0"  # pinned: `add` accepting a local item + root-relative registryDependencies was verified on it
# UI systems dev-flow offers as `stack.ui` whose components come from their own shadcn registry.
# Only these can be trusted "live", and only when the project's stack names them.
LIVE_UI_REGISTRIES = {"@coss"}
SETUP_MARK = ("<!-- BEGIN:registry-intake -->", "<!-- END:registry-intake -->")
ITEM_TYPES = {"registry:lib", "registry:block", "registry:component", "registry:ui", "registry:hook",
              "registry:theme", "registry:page", "registry:file", "registry:style", "registry:base",
              "registry:font", "registry:item"}

# eve 0.55.0, internal/authored-definition/schema-backed.js — the loader throws on any other key.
# Read from the project's installed eve when there is one; this is the fallback.
EVE_TOOL_KEYS_FALLBACK = ("0.55.0", ["label", "auth", "description", "execute", "execution", "inputSchema",
                                     "approval", "approvalKey", "outputSchema", "toModelOutput"])

SENSITIVE_TARGETS = [
    r"(^|/)\.env", r"(^|/)\.github/", r"(^|/)\.claude/", r"(^|/)\.husky/", r"(^|/)\.git/", r"(^|/)\.npmrc$",
    r"(^|/)package\.json$", r"(^|/)(pnpm-lock\.yaml|package-lock\.json|bun\.lockb?|yarn\.lock)$",
    r"(^|/)next\.config\.", r"(^|/)(middleware|proxy|instrumentation)\.[jt]sx?$", r"(^|/)components\.json$",
    r"(^|/)eslint\.config\.", r"(^|/)tsconfig[^/]*\.json$", r"(^|/)vercel\.json$", r"(^|/)turbo\.json$",
    r"(^|/)pnpm-workspace\.yaml$", rf"(^|/){re.escape(LOCK)}$", rf"(^|/){re.escape(VENDOR)}/", r"(^|/)AGENTS\.md$",
    r"(^|/)CLAUDE\.md$", r"(^|/)\.workflow/",
]
SERVER_SURFACE = [r"(^|/)app/api/", r"(^|/)route\.[jt]s$", r"(^|/)agent/", r"(^|/)server/", r"(^|/)actions?\.[jt]s$"]
LICENSE_BLOCK = re.compile(r"\b(AGPL|GPL|SSPL|BUSL|Commons-Clause|UNLICENSED|Elastic)", re.I)
LICENSE_REVIEW = re.compile(r"\b(LGPL|MPL|EPL|CDDL|CC-BY-NC)", re.I)
SIDE_EFFECT_NAME = re.compile(r"^(post|send|write|delete|remove|update|create|run|exec|pay|charge|refund|publish|"
                              r"deploy|merge|open|upload|insert|set|put|patch|move|rename|invite|cancel|book)_")
SIDE_EFFECT_BODY = re.compile(r"method:\s*['\"](POST|PUT|PATCH|DELETE)['\"]|\.(insert|update|delete|upsert)\(|"
                              r"writeFile|unlink\(|\.exec\(|\.run(Command)?\(|\.send\(|sendMail|\.charge", re.I)


# ---------------------------------------------------------------------------------------------
# findings


@dataclass
class Finding:
    code: str
    level: str  # "block" | "review" | "info"
    item: str
    message: str
    where: str = ""


@dataclass
class Item:
    key: str             # "@ns/name", or the URL / path when there is no namespace
    source: str          # URL or absolute path it was read from
    data: dict
    requires: list[str] = field(default_factory=list)  # keys of governed items it depends on
    first_party: list[str] = field(default_factory=list)  # bare shadcn names it depends on


CODES = {
    "T1": "writes outside components/lib/app — a config, lockfile, env or tooling file",
    "T2": "server-side surface (API route, server action, agent) — high risk tier",
    "S1": "executes code or processes (child_process, eval, new Function)",
    "S2": "obfuscated or minified source",
    "S3": "reads environment variables",
    "S4": "talks to hard-coded remote hosts",
    "S5": "injects raw HTML",
    "S6": "very wide source lines — a class list of arbitrary values the design lint will count",
    "E1": "declares env vars that shadcn writes into .env",
    "E2": "ships a value for a secret-looking env var",
    "C1": "rewrites theme tokens or global CSS — DESIGN.md is the source of truth",
    "D1": "npm dependency does not exist",
    "D2": "npm dependency under a licence we do not ship",
    "D3": "npm dependency under a weak-copyleft or non-commercial licence",
    "D4": "npm dependency runs install scripts",
    "D5": "npm dependency published less than 30 days ago",
    "D6": "npm dependency could not be verified (npm view failed)",
    "D7": "npm dependency range excludes the version the project has installed",
    "D8": "npm package name was reused — a long gap between releases, likely a new owner",
    "R1": "registry dependency outside the allowlist",
    "R2": "item does not declare the shadcn registry-item $schema",
    "R3": "item type is not a shadcn registry type",
    "V1": "eve tool uses a key the eve loader rejects",
    "V2": "eve tool with a side effect and no approval gate",
    "V3": "eve code reads a global credential — per-tenant secrets required in a multi-tenant app",
    "V4": "eve code opens a single shared store — tenant isolation to review",
    "V5": "PII redaction by US-shaped regexes (SSN, US phone) — useless on Italian text",
    "V6": "ships a whole standalone eve agent — port the bricks, not the runtime",
}


# ---------------------------------------------------------------------------------------------
# lock file


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def lock_path(root: Path) -> Path:
    return root / LOCK


def load_lock(root: Path) -> dict | None:
    p = lock_path(root)
    return json.loads(p.read_text()) if p.exists() else None


def save_lock(root: Path, lock: dict) -> None:
    lock_path(root).write_text(json.dumps(lock, indent=2, sort_keys=False) + "\n")


def find_root(start: Path) -> Path | None:
    for d in [start, *start.parents]:
        if (d / LOCK).exists():
            return d
        if (d / ".git").exists():
            return None
    return None


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------------------------
# resolution


def components_jsons(root: Path) -> list[Path]:
    out = [root / "components.json"]
    for pattern in ("apps/*/components.json", "packages/*/components.json"):
        out.extend(sorted(root.glob(pattern)))
    return [p for p in out if p.exists()]


def registries_in_components(root: Path) -> dict[str, tuple[str, Path]]:
    found: dict[str, tuple[str, Path]] = {}
    for p in components_jsons(root):
        for ns, spec in (json.loads(p.read_text()).get("registries") or {}).items():
            url = spec if isinstance(spec, str) else (spec or {}).get("url", "")
            found[ns] = (url, p)
    return found


def split_ns(spec: str) -> tuple[str, str] | None:
    m = re.match(r"^(@[\w.-]+)/(.+)$", spec)
    return (m.group(1), m.group(2)) if m else None


def ns_of(key: str) -> str:
    """The namespace an item is governed under: `@ns`, else the URL's origin, else "local"."""
    if (parts := split_ns(key)) and "://" not in key:
        return parts[0]
    m = re.match(r"^(https?://[^/]+)", key)
    return m.group(1) if m else "local"


def is_bare(spec: str) -> bool:
    return not (spec.startswith("@") or "://" in spec or spec.endswith(".json") or spec.startswith((".", "/", "~")))


def ns_for_url(url: str, registries: dict[str, str]) -> str | None:
    for ns, template in registries.items():
        pre, _, post = template.partition("{name}")
        if url.startswith(pre) and url.endswith(post):
            return ns
    return None


def known_registries(root: Path, lock: dict | None) -> dict[str, str]:
    reg = {ns: url for ns, (url, _) in registries_in_components(root).items()}
    reg.update({ns: r["url"] for ns, r in ((lock or {}).get("registries") or {}).items()})
    return reg


def fetch_json(source: str, root: Path) -> dict:
    if "://" in source:
        url = source
        for _ in range(6):
            if not url.startswith("https://"):
                raise SystemExit(f"{source}: refusing a non-https URL ({url})")
            req = urllib.request.Request(url, headers={"User-Agent": "registry-intake", "Accept": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=30) as r:  # noqa: S310 — the URL is the thing under review
                    return json.loads(r.read().decode())
            except urllib.error.HTTPError as e:
                # urllib before 3.11 does not follow 308, which registries on Vercel answer with
                if e.code in (301, 302, 303, 307, 308) and e.headers.get("Location"):
                    url = urllib.parse.urljoin(url, e.headers["Location"])
                    continue
                raise SystemExit(f"{source}: HTTP {e.code}") from None
        raise SystemExit(f"{source}: too many redirects")
    return json.loads((root / source).read_text() if not Path(source).is_absolute() else Path(source).read_text())


def resolve(spec: str, root: Path, registries: dict[str, str]) -> tuple[str, str]:
    """(key, source) for a governed item spec."""
    if (parts := split_ns(spec)) and "://" not in spec:
        ns, name = parts
        if ns not in registries:
            raise SystemExit(f"{spec}: namespace {ns} is not in components.json nor in the allowlist — "
                             f"`registry_intake.py allow <root> {ns} <url-with-{{name}}> --reason ...` first")
        return spec, registries[ns].replace("{name}", name)
    if "://" in spec:
        ns = ns_for_url(spec, registries)
        if ns:
            pre, _, post = registries[ns].partition("{name}")
            return f"{ns}/{spec[len(pre):len(spec) - len(post) if post else None]}", spec
        return spec, spec
    return spec, str((root / spec).resolve())


def closure(spec: str, root: Path, registries: dict[str, str], limit: int = 40) -> list[Item]:
    items: list[Item] = []
    seen: set[str] = set()
    queue = [spec]
    while queue:
        s = queue.pop(0)
        key, source = resolve(s, root, registries)
        if key in seen:
            continue
        seen.add(key)
        if len(items) >= limit:
            raise SystemExit(f"{spec}: more than {limit} registry items in the dependency closure — refusing")
        data = fetch_json(source, root)
        it = Item(key=key, source=source, data=data)
        for dep in data.get("registryDependencies") or []:
            if is_bare(dep):
                it.first_party.append(dep)
            else:
                dkey, _ = resolve(dep, root, registries) if (split_ns(dep) or "://" in dep) else (dep, dep)
                it.requires.append(dkey)
                queue.append(dep)
        items.append(it)
    return items


# ---------------------------------------------------------------------------------------------
# checks


def target_of(f: dict) -> str:
    return (f.get("target") or f.get("path") or "").replace("\\", "/")


def eve_tool_keys(root: Path) -> tuple[str, list[str]]:
    rel = "node_modules/eve/dist/src/internal/authored-definition/schema-backed.js"
    # explicit places, never a recursive glob: walking node_modules takes minutes in a monorepo
    candidates = [root / rel, *root.glob(f"apps/*/{rel}"), *root.glob(f"packages/*/{rel}")]
    for js in (c.resolve() for c in candidates if c.exists()):
        text = js.read_text(errors="ignore")
        for m in re.finditer(r"expectOnlyKnownKeys\(\w+,\[([^\]]*)\]", text):
            keys = re.findall(r"`(\w+)`", m.group(1))
            if "approval" in keys and "execute" in keys:
                pkg = js.parents[4] / "package.json"
                version = json.loads(pkg.read_text()).get("version", "?") if pkg.exists() else "?"
                return version, keys
    return EVE_TOOL_KEYS_FALLBACK


def object_keys(src: str, call: str) -> list[list[str]]:
    """Top-level keys of every `call({ ... })` object literal. A small scanner, not a parser:
    it tracks strings, template literals, comments and bracket depth, which is enough for
    authored eve definitions."""
    results = []
    for m in re.finditer(rf"\b{re.escape(call)}\s*\(\s*\{{", src):
        i, depth, keys = m.end(), 1, []
        expect_key = True
        while i < len(src) and depth:
            c = src[i]
            if src.startswith("//", i):
                i = src.find("\n", i) if src.find("\n", i) != -1 else len(src)
                continue
            if src.startswith("/*", i):
                j = src.find("*/", i + 2)
                i = len(src) if j == -1 else j + 2
                continue
            if c in "'\"`":
                j = i + 1
                while j < len(src) and src[j] != c:
                    j += 2 if src[j] == "\\" else 1
                i = j + 1
                expect_key = False
                continue
            if c in "{[(":
                depth += 1
            elif c in "}])":
                depth -= 1
            elif c == "," and depth == 1:
                expect_key = True
            elif depth == 1 and expect_key and (c.isalpha() or c in "_$"):
                km = re.match(r"(?:async\s+)?([A-Za-z_$][\w$]*)\s*(\??:|\()", src[i:])
                if km:
                    keys.append(km.group(1))
                expect_key = False
            elif not c.isspace():
                expect_key = False if depth == 1 else expect_key
            i += 1
        results.append(keys)
    return results


def check_files(it: Item, root: Path, eve_keys: tuple[str, list[str]]) -> tuple[list[Finding], bool]:
    out: list[Finding] = []
    high = False
    add = lambda code, level, msg, where="": out.append(Finding(code, level, it.key, msg, where))  # noqa: E731
    files = it.data.get("files") or []
    tool_files, server_files = [], []
    for f in files:
        tgt = target_of(f)
        content = f.get("content") or ""
        if tgt.startswith("/") or ".." in tgt.split("/"):
            add("T1", "block", f"target escapes the project: {tgt}", tgt)
        elif any(re.search(p, tgt.removeprefix("~/")) for p in SENSITIVE_TARGETS):
            add("T1", "block", f"target is a config/tooling file: {tgt}", tgt)
        if any(re.search(p, tgt) for p in SERVER_SURFACE) or re.search(r"^['\"]use server['\"]|server-only", content, re.M):
            server_files.append(tgt)
        if re.search(r"child_process|\bexecSync\b|\beval\(|new Function\(", content):
            add("S1", "block", "executes code or processes", tgt)
        # A >1000-char line is normal in a component: one Tailwind class list with arbitrary values
        # reaches 1070 in React Bits' SwipeToast. Minified code packs statements, so require them.
        minified = [ln for ln in content.splitlines() if len(ln) > 1000 and ln.count(";") >= 3]
        if (minified and not tgt.endswith((".json", ".css", ".svg", ".md"))) or re.search(r"[A-Za-z0-9+/=]{800,}", content):
            add("S2", "block", "obfuscated, minified or large encoded blob", tgt)
        wide = [ln for ln in content.splitlines() if len(ln) > 1000 and ln not in minified]
        if wide and tgt.endswith((".tsx", ".jsx")):
            add("S6", "review", f"{len(wide)} line(s) over 1000 characters — usually a class list of arbitrary "
                                "values, which the design lint counts one by one", tgt)
        envs = sorted(set(re.findall(r"process\.env\.([A-Z0-9_]+)", content)))
        if envs:
            add("S3", "review", "reads " + ", ".join(envs), tgt)
        hosts = sorted({h for h in re.findall(r"https?://([a-z0-9.-]+\.[a-z]{2,})", content, re.I)
                        if not re.search(r"(^|\.)(w3\.org|schema\.org|ui\.shadcn\.com|example\.(com|org))$", h)})
        if hosts:
            add("S4", "review", "hosts: " + ", ".join(hosts), tgt)
        if "dangerouslySetInnerHTML" in content:
            add("S5", "review", "dangerouslySetInnerHTML", tgt)

        is_eve = bool(re.search(r"from\s+['\"]eve(/[\w/-]+)?['\"]", content)) or tgt.startswith("agent/") or "/agent/" in tgt
        if is_eve:
            high = True
            if re.search(r"(^|/)agent/agent\.[jt]s$", tgt) and "defineAgent" in content:
                add("V6", "review", "a full standalone eve agent (defineAgent) — port its tools/skills instead", tgt)
            if re.search(r"(^|/)tools/[^/]+\.[jt]s$", tgt) and "defineTool" in content:
                tool_files.append((tgt, content))
            creds = [e for e in envs if re.search(r"KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL", e)]
            if creds:
                add("V3", "review", "global credentials: " + ", ".join(creds), tgt)
            if re.search(r"['\"]file:[^'\"]*\.(db|sqlite)['\"]|createClient\(\s*\{\s*url:\s*process\.env", content):
                add("V4", "review", "one shared store for every tenant", tgt)
        if re.search(r"\\d\{3\}-\\d\{2\}-\\d\{4\}|redact-ssn|\[redacted-ssn\]", content):
            add("V5", "review", "PII patterns shaped on US formats", tgt)

    if server_files:
        high = True
        add("T2", "review", f"server-side surface in {len(server_files)} file(s)")
    version, allowed = eve_keys
    for tgt, content in tool_files:
        for keys in object_keys(content, "defineTool"):
            unknown = [k for k in keys if k not in allowed]
            for k in unknown:
                hint = " — eve's field is `approval` (`needsApproval` is the AI SDK's, deprecated)" if k == "needsApproval" else ""
                add("V1", "block", f"`{k}` is not a key eve {version} accepts; its loader throws{hint}", tgt)
            gate = re.search(r"\b(approval|needsApproval)\s*:\s*([\w.]+\([^)]*\)|true|false)", content)
            ungated = not gate or gate.group(1) == "needsApproval" or re.match(r"never\(|false", gate.group(2))
            name = Path(tgt).stem
            if ungated and (SIDE_EFFECT_NAME.match(name) or SIDE_EFFECT_BODY.search(content)):
                add("V2", "block", f"tool `{name}` has a side effect and no working approval gate "
                    "(make it `approval: always()`/`once()`, or accept with the reason it is idempotent)", tgt)

    env_vars = it.data.get("envVars") or {}
    if env_vars:
        add("E1", "review", "env vars: " + ", ".join(sorted(env_vars)))
        for k, v in env_vars.items():
            if v and re.search(r"KEY|TOKEN|SECRET|PASSWORD|DSN|CREDENTIAL", k):
                add("E2", "block", f"{k} comes with a value")
    if it.data.get("cssVars") or it.data.get("css") or it.data.get("tailwind") or it.data.get("theme"):
        add("C1", "block", "changes theme tokens / global CSS")
    if it.data.get("$schema") != "https://ui.shadcn.com/schema/registry-item.json":
        add("R2", "info", "no registry-item $schema")
    if it.data.get("type") and it.data["type"] not in ITEM_TYPES:
        add("R3", "block", f"type {it.data['type']!r}")
    return out, high


# A gap this long between two consecutive releases means the name most likely changed hands: npm
# hands abandoned names to new owners (`cn` was a Chuck Norris joke package in 2013, shadcn's class
# merger since 2026-09-01). `time.created` then says 2013, and D5 would wave a 3-week-old package through.
REUSED_GAP_DAYS = 730
# Reused names whose current owner has been checked on the package's own repository (2026-09-22):
# `cn` 0.1.x was rumpl/cn, `motion` 5.0.0-beta was steelbrain/pundle.
KNOWN_REUSED = {"cn": "github.com/shadcn-ui/cn", "motion": "github.com/motiondivision/motion"}


def repo_id(url: str) -> str:
    return re.sub(r"^(git\+)?[a-z+]+://|^git@|\.git$", "", (url or "").strip().lower()).replace("github.com:", "github.com/")


def owners(d: dict) -> set[str]:
    m = d.get("maintainers") or []
    return {str(x).split("<")[0].strip().lower() for x in (m if isinstance(m, list) else [m])}


def changed_hands(name: str, before_version: str, now: dict) -> bool:
    """A long gap alone is a paused project (clsx: 2020 → 2022, same repo, same maintainer). A reused name
    also has a different repository and no maintainer in common across the gap."""
    r = subprocess.run(["npm", "view", f"{name}@{before_version}", "repository.url", "maintainers", "--json"],
                       capture_output=True, text=True, check=False, timeout=60)
    try:
        old = json.loads(r.stdout or "{}") if not r.returncode else {}
    except json.JSONDecodeError:
        old = {}
    if not old:
        return False
    return repo_id(old.get("repository.url", "")) != repo_id(now.get("repository.url", "")) and not (owners(old) & owners(now))


def current_line(times: dict) -> tuple[str | None, dict | None]:
    """(date the current release line started, the gap before it if the name was reused)."""
    rel = sorted((v, k) for k, v in times.items() if k not in ("created", "modified"))
    if not rel:
        return times.get("created"), None
    start, gap = rel[0][0], None
    for (a, va), (b, vb) in zip(rel, rel[1:]):
        if (dt.datetime.fromisoformat(b.replace("Z", "+00:00")) -
                dt.datetime.fromisoformat(a.replace("Z", "+00:00"))).days >= REUSED_GAP_DAYS:
            start, gap = b, {"before": f"{va} ({a[:10]})", "after": f"{vb} ({b[:10]})", "before_version": va}
    return start, gap


def npm_facts(spec: str) -> dict | None:
    name = re.sub(r"(?<=.)@[^/]*$", "", spec)
    r = subprocess.run(["npm", "view", name, "name", "license", "time", "scripts", "version", "repository.url",
                        "maintainers", "--json"], capture_output=True, text=True, check=False, timeout=60)
    if r.returncode:
        return {"missing": "E404" in (r.stdout + r.stderr), "name": name}
    try:
        d = json.loads(r.stdout or "{}")
    except json.JSONDecodeError:
        return None
    times = d.get("time") if isinstance(d.get("time"), dict) else {}
    started, reused = current_line(times)
    if reused and not changed_hands(name, reused["before_version"], d):
        # a paused project, not a new owner: the whole history is one package
        started, reused = min((v for k, v in times.items() if k not in ("created", "modified")), default=None), None
    return {"name": name, "license": d.get("license"), "created": started, "reused": reused,
            "repository": d.get("repository.url") or "", "scripts": d.get("scripts") or {}, "version": d.get("version")}


def installed_version(root: Path, name: str) -> str | None:
    for pkg in [root / "node_modules" / name / "package.json",
                *root.glob(f"apps/*/node_modules/{name}/package.json"),
                *root.glob(f"packages/*/node_modules/{name}/package.json")]:
        try:
            return json.loads(pkg.read_text()).get("version")
        except (OSError, json.JSONDecodeError):
            continue
    for pj in [root / "package.json", *root.glob("apps/*/package.json"), *root.glob("packages/*/package.json")]:
        try:
            d = json.loads(pj.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        spec = {**(d.get("dependencies") or {}), **(d.get("devDependencies") or {})}.get(name)
        if spec:
            m = re.search(r"(\d+)\.(\d+)\.(\d+)", spec)
            if m:
                return m.group(0)
    return None


def major_conflict(declared: str, present: str) -> bool:
    """True when a caret/tilde range cannot accept the version already in the project. Under 1.0 a caret
    locks the minor (`^0.2.4` refuses 0.3.x): for a 0.x package the minor is the breaking number."""
    m = re.match(r"^([\^~]?)(\d+)\.(\d+)", declared.strip())
    p = re.match(r"^(\d+)\.(\d+)", present.strip())
    if not (m and p):
        return False
    if m.group(2) != p.group(1):
        return True
    return m.group(1) == "^" and m.group(2) == "0" and m.group(3) != p.group(2)


def check_deps(items: list[Item], npm=None, root: Path | None = None) -> tuple[list[Finding], dict]:
    out, facts = [], {}
    npm = npm or npm_facts
    for it in items:
        for dep in (it.data.get("dependencies") or []) + (it.data.get("devDependencies") or []):
            f = npm(dep)
            name = re.sub(r"(?<=.)@[^/]*$", "", dep)
            declared = dep[len(name) + 1:] if len(dep) > len(name) else ""
            present = installed_version(root, name) if root and declared else None
            if present and major_conflict(declared, present):
                out.append(Finding("D7", "review", it.key,
                                   f"{name}: the item asks for {declared}, the project has {present} — "
                                   "installing it adds a second major or breaks the range"))
            if f is None or ("missing" in f and not f["missing"]):
                out.append(Finding("D6", "review", it.key, f"{name}: npm view failed"))
                continue
            if f.get("missing"):
                out.append(Finding("D1", "block", it.key, f"{name} is not on npm (typo, private or invented)"))
                continue
            facts[name] = {k: f.get(k) for k in ("license", "version", "created")}
            lic = str(f.get("license") or "none")
            if lic == "none" or LICENSE_BLOCK.search(lic):
                out.append(Finding("D2", "block", it.key, f"{name}: licence {lic}"))
            elif LICENSE_REVIEW.search(lic):
                out.append(Finding("D3", "review", it.key, f"{name}: licence {lic}"))
            hooks = [s for s in ("preinstall", "install", "postinstall") if s in (f.get("scripts") or {})]
            if hooks:
                out.append(Finding("D4", "block", it.key, f"{name}: runs {', '.join(hooks)}"))
            if f.get("reused"):
                g = f["reused"]
                known = KNOWN_REUSED.get(name)
                if known and known in (f.get("repository") or ""):
                    out.append(Finding("D8", "info", it.key, f"{name}: name reused ({g['before']} → {g['after']}); "
                                                             f"current owner checked: {known}"))
                else:
                    out.append(Finding("D8", "review", it.key,
                                       f"{name}: name reused — last release {g['before']}, then {g['after']}; "
                                       f"the package behind it is not the one that name used to be. Repository now: "
                                       f"{f.get('repository') or 'none'}"))
            created = f.get("created")
            if created:
                age = dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(created.replace("Z", "+00:00"))
                if age.days < 30:
                    out.append(Finding("D5", "review", it.key, f"{name}: current release line first published "
                                                               f"{age.days} days ago"))
    return out, facts


@dataclass
class Report:
    root_item: str
    tier: str
    items: list[dict]
    findings: list[Finding]
    deps: dict

    @property
    def exit_code(self) -> int:
        if any(f.level == "block" for f in self.findings):
            return 1
        return 3 if self.tier == "high" or any(f.level == "review" for f in self.findings) else 0


def review(spec: str, root: Path, npm=None, allowlist_only: bool = False,
           extra: dict[str, str] | None = None) -> tuple[Report, list[Item]]:
    """`extra` resolves namespaces that are not allowlisted yet, so a registry can be reviewed
    before deciding to allow it. approve never passes it."""
    lock = load_lock(root)
    registries = known_registries(root, lock) if not allowlist_only else \
        {ns: r["url"] for ns, r in ((lock or {}).get("registries") or {}).items()}
    registries = {**(extra or {}), **registries}
    items = closure(spec, root, registries)
    # the root item's own namespace is the one under decision; R1 is about the closure reaching
    # into a *different* registry nobody chose
    allowed = set(((lock or {}).get("registries") or {})) | {ns_of(items[0].key)}
    eve_keys = eve_tool_keys(root)
    findings: list[Finding] = []
    high = False
    for it in items:
        fs, h = check_files(it, root, eve_keys)
        findings += fs
        high = high or h
        if it is not items[0]:
            if ns_of(it.key) not in allowed:
                findings.append(Finding("R1", "block", it.key, f"pulled in by the closure, but {ns_of(it.key)} is not allowlisted"))
    dep_findings, deps = check_deps(items, npm or npm_facts, root)
    findings += dep_findings
    if any(f.code == "T1" for f in findings):
        high = True
    rep = Report(spec, "high" if high else "low",
                 [{"key": i.key, "source": i.source, "type": i.data.get("type"), "files": [target_of(f) for f in i.data.get("files") or []],
                   "requires": i.requires, "first_party": i.first_party} for i in items], findings, deps)
    return rep, items


def print_report(rep: Report, diffs: dict[str, str]) -> None:
    verdict = {0: "clean", 3: "needs a human approval", 1: "BLOCKED"}[rep.exit_code]
    print(f"{rep.root_item} · tier {rep.tier} · {verdict}")
    for i in rep.items:
        print(f"  {i['key']}  ({i['type']})")
        for t in i["files"]:
            print(f"    + {t}")
        if i["first_party"]:
            print(f"    shadcn: {', '.join(i['first_party'])}")
    if rep.deps:
        print("  npm: " + ", ".join(f"{n}@{d['version']} ({d['license']})" for n, d in rep.deps.items()))
    for f in rep.findings:
        mark = {"block": "✗", "review": "!", "info": "·"}[f.level]
        print(f"  {mark} {f.code} {f.item}: {f.message}" + (f"  [{f.where}]" if f.where and f.where not in f.message else ""))
    for key, d in diffs.items():
        print(f"\n--- changes since the approved snapshot of {key}\n{d or '  (identical)'}")


# ---------------------------------------------------------------------------------------------
# snapshot + lock


def snapshot_rel(key: str) -> str:
    safe = key.lstrip("@") if key.startswith("@") else re.sub(r"[^\w.-]+", "_", key.split("://")[-1])
    safe = re.sub(r"\.json$", "", safe)
    return f"{VENDOR}/{safe}.json"


def local_dep(dep: str, items_by_source_key: dict[str, str]) -> str:
    return "./" + snapshot_rel(items_by_source_key[dep]) if dep in items_by_source_key else dep


def diff_against_snapshot(root: Path, lock: dict | None, items: list[Item]) -> dict[str, str]:
    out = {}
    for it in items:
        entry = ((lock or {}).get("items") or {}).get(it.key)
        if not entry:
            continue
        old = json.loads((root / entry["snapshot"]).read_text()) if (root / entry["snapshot"]).exists() else {}
        old_files = {target_of(f): f.get("content", "") for f in old.get("files") or []}
        chunks = []
        for f in it.data.get("files") or []:
            t = target_of(f)
            chunks += difflib.unified_diff(old_files.pop(t, "").splitlines(), (f.get("content") or "").splitlines(),
                                           f"a/{t}", f"b/{t}", lineterm="", n=2)
        chunks += [f"- removed {t}" for t in old_files]
        meta_old = {k: v for k, v in old.items() if k not in ("files", "registryDependencies")}
        meta_new = {k: v for k, v in it.data.items() if k not in ("files", "registryDependencies")}
        if meta_old != meta_new:
            chunks.append(f"~ item fields: {json.dumps(meta_old, sort_keys=True)} → {json.dumps(meta_new, sort_keys=True)}")
        out[it.key] = "\n".join(chunks)
    return out


def lint_caps(root: Path) -> dict[str, int]:
    caps = {}
    for pkg in [root / "package.json", *sorted(root.glob("apps/*/package.json")), *sorted(root.glob("packages/*/package.json"))]:
        if pkg.exists():
            m = re.search(r"--max-warnings[ =](\d+)", (json.loads(pkg.read_text()).get("scripts") or {}).get("lint", ""))
            if m:
                caps[pkg.parent.relative_to(root).as_posix() or "."] = int(m.group(1))
    return caps


def cmd_approve(args) -> int:
    root = args.root.resolve()
    lock = load_lock(root)
    if lock is None:
        print(f"no {LOCK} — run `registry_intake.py setup {root}` first", file=sys.stderr)
        return 1
    rep, items = review(args.item, root, allowlist_only=True)
    diffs = diff_against_snapshot(root, lock, items)
    print_report(rep, diffs)
    if ns_of(items[0].key) not in (lock.get("registries") or {}):
        print(f"\nrefused: {items[0].key} is not from an allowlisted registry", file=sys.stderr)
        return 1
    accepted = dict(a.split("=", 1) for a in args.accept or [] if "=" in a)
    if any("=" not in a or not a.split("=", 1)[1].strip() for a in args.accept or []):
        print("\nrefused: every --accept needs a reason, CODE=why", file=sys.stderr)
        return 1
    blocking = sorted({f.code for f in rep.findings if f.level == "block"})
    missing = [c for c in blocking if c not in accepted]
    if missing:
        print(f"\nrefused: blocking findings {', '.join(missing)} — fix upstream, port by hand "
              "(eve-registry-porting), or accept each with `--accept CODE=reason`", file=sys.stderr)
        return 1

    by_source_key = {}
    for it in items:
        for dep in it.data.get("registryDependencies") or []:
            if not is_bare(dep):
                by_source_key[dep] = resolve(dep, root, known_registries(root, lock))[0] if (split_ns(dep) or "://" in dep) else dep
    stamp = now()
    for it in items:
        snap = dict(it.data)
        if snap.get("registryDependencies"):
            snap["registryDependencies"] = [local_dep(d, by_source_key) for d in snap["registryDependencies"]]
        rel = snapshot_rel(it.key)
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(json.dumps(snap, indent=2) + "\n")
        mine = [f for f in rep.findings if f.item == it.key]
        lock.setdefault("items", {})[it.key] = {
            "source": it.source if "://" in it.source else Path(it.source).relative_to(root).as_posix() if Path(it.source).is_relative_to(root) else it.source,
            "snapshot": rel,
            "sha256": sha256(root / rel),
            "tier": rep.tier,
            "reviewed_at": stamp,
            "findings": [f"{f.level}:{f.code}" for f in mine],
            "accepted": {c: accepted[c] for c in sorted({f.code for f in mine}) if c in accepted},
            "approved_by": args.by,
            "approved_at": stamp,
            "note": args.note or "",
            "via": None if it is items[0] else items[0].key,
            "requires": it.requires,
            "dependencies": {n: d for n, d in rep.deps.items()
                             if n in [re.sub(r"(?<=.)@[^/]*$", "", x) for x in (it.data.get("dependencies") or []) + (it.data.get("devDependencies") or [])]},
            "installed_at": (((lock.get("items") or {}).get(it.key)) or {}).get("installed_at"),
        }
    save_lock(root, lock)
    print(f"\napproved {len(items)} item(s) → {VENDOR}/ · {LOCK} updated")
    print(f"next: registry_intake.py install {root} {items[0].key}")
    return 0


# ---------------------------------------------------------------------------------------------
# install / check / setup


def verify_entry(root: Path, key: str, lock: dict) -> str | None:
    entry = (lock.get("items") or {}).get(key)
    if not entry:
        return f"{key} is not approved"
    snap = root / entry["snapshot"]
    if not snap.exists():
        return f"{key}: snapshot {entry['snapshot']} is missing"
    if sha256(snap) != entry["sha256"]:
        return f"{key}: snapshot {entry['snapshot']} changed after approval"
    for dep in entry.get("requires") or []:
        if err := verify_entry(root, dep, lock):
            return err
    return None


def cmd_install(args) -> int:
    root = args.root.resolve()
    lock = load_lock(root)
    if lock is None:
        print(f"no {LOCK} — run setup first", file=sys.stderr)
        return 1
    key = args.item
    if key not in (lock.get("items") or {}):
        key = resolve(args.item, root, known_registries(root, lock))[0]
    if err := verify_entry(root, key, lock):
        print(f"refused: {err} — run `registry_intake.py approve`", file=sys.stderr)
        return 1
    entry = lock["items"][key]
    before = lint_caps(root)
    # registryDependencies in a snapshot are root-relative ("./vendor/registry/..."), and the shadcn
    # CLI resolves local paths against its process working directory — so it always runs from the
    # lock's root, and a monorepo target (packages/ui) is reached with --cwd.
    cmd = ["npx", "--yes", f"shadcn@{lock.get('shadcn', SHADCN_VERSION)}", "add", "./" + entry["snapshot"], *args.shadcn_args]
    if args.cwd:
        cmd += ["--cwd", str((root / args.cwd).resolve())]
    print("$ " + " ".join(cmd), flush=True)
    r = subprocess.run(cmd, cwd=root, check=False)
    if r.returncode:
        return r.returncode
    stamp = now()
    for k in [key, *all_requires(key, lock)]:
        lock["items"][k]["installed_at"] = stamp
    after = lint_caps(root)
    lock["design_lint_caps"] = {**(lock.get("design_lint_caps") or {}), **{k: min(v, before.get(k, v)) for k, v in after.items()}}
    save_lock(root, lock)
    print(f"\ninstalled {key}. Now run the gates the imported code has to pass, not the other way round:")
    print("  typecheck · the capped lint (a raised --max-warnings fails `check`) · `eve build` if agent/ changed · tests")
    return 0


def all_requires(key: str, lock: dict) -> list[str]:
    out = []
    for d in (lock["items"].get(key) or {}).get("requires") or []:
        out += [d, *all_requires(d, lock)]
    return out


def hook_installed(root: Path) -> bool:
    p = root / ".claude" / "settings.json"
    if not p.exists():
        return False
    try:
        pre = (json.loads(p.read_text()).get("hooks") or {}).get("PreToolUse") or []
    except json.JSONDecodeError:
        return False
    return (root / HOOK_COPY).exists() and any(h.get("command") == HOOK_COMMAND for m in pre for h in m.get("hooks") or [])


def check(root: Path) -> tuple[bool, list[str]]:
    lock = load_lock(root)
    if lock is None:
        return False, [f"no {LOCK}: registry intake is not set up"]
    problems = []
    allowed = lock.get("registries") or {}
    for ns, (url, p) in registries_in_components(root).items():
        if ns not in allowed:
            problems.append(f"{p.relative_to(root)} declares {ns} ({url}), which is not allowlisted")
        elif allowed[ns]["url"] != url:
            problems.append(f"{p.relative_to(root)} points {ns} at {url}, the allowlist says {allowed[ns]['url']}")
    snapshots = set()
    for key, entry in (lock.get("items") or {}).items():
        snapshots.add(entry["snapshot"])
        snap = root / entry["snapshot"]
        if not snap.exists():
            problems.append(f"{key}: snapshot {entry['snapshot']} is missing")
        elif sha256(snap) != entry["sha256"]:
            problems.append(f"{key}: {entry['snapshot']} was edited after approval")
    vendor = root / VENDOR
    if vendor.exists():
        for f in sorted(vendor.rglob("*.json")):
            if f.relative_to(root).as_posix() not in snapshots:
                problems.append(f"{f.relative_to(root)} is in {VENDOR}/ but not in the lock")
    for unit, cap in lint_caps(root).items():
        base = (lock.get("design_lint_caps") or {}).get(unit)
        if base is not None and cap > base:
            problems.append(f"{unit}: lint --max-warnings rose {base} → {cap}; fix the new warnings, or record why "
                            "with `registry_intake.py caps <root> --reason ...`")
    if not hook_installed(root):
        problems.append(f".claude/settings.json has no registry-intake PreToolUse hook running {HOOK_COPY}")
    else:
        here, copy = Path(__file__).resolve(), (root / HOOK_COPY).resolve()
        if here != copy and copy.read_bytes() != here.read_bytes():
            problems.append(f"{HOOK_COPY} differs from the installed skill — rerun `registry_intake.py setup`")
    return not problems, problems


def cmd_caps(args) -> int:
    root = args.root.resolve()
    lock = load_lock(root)
    if lock is None:
        print(f"no {LOCK}", file=sys.stderr)
        return 1
    caps = lint_caps(root)
    lock.setdefault("cap_changes", []).append({"at": now(), "from": lock.get("design_lint_caps") or {}, "to": caps, "reason": args.reason})
    lock["design_lint_caps"] = caps
    save_lock(root, lock)
    print(f"design-lint caps recorded: {caps}")
    return 0


HOOK_COPY = ".claude/hooks/registry_intake.py"
HOOK_COMMAND = f'python3 "$CLAUDE_PROJECT_DIR/{HOOK_COPY}" hook'


def wire_hook(root: Path) -> bool:
    """Vendor this script into the project and point the hook at it through $CLAUDE_PROJECT_DIR.
    An absolute path to wherever the skill is installed would be committed with the settings and
    break on every other machine — and python3 on a missing file exits 2, which Claude Code reads
    as "block", so every Bash call would be refused."""
    changed = False
    copy = root / HOOK_COPY
    here = Path(__file__).resolve()
    if here != copy.resolve() and (not copy.exists() or copy.read_bytes() != here.read_bytes()):
        copy.parent.mkdir(parents=True, exist_ok=True)
        copy.write_bytes(here.read_bytes())
        changed = True
    p = root / ".claude" / "settings.json"
    data = json.loads(p.read_text()) if p.exists() else {}
    pre = data.setdefault("hooks", {}).setdefault("PreToolUse", [])
    ours = [m for m in pre for h in m.get("hooks") or [] if "registry_intake.py" in (h.get("command") or "")]
    if len(ours) == 1 and [h.get("command") for h in ours[0]["hooks"]] == [HOOK_COMMAND]:
        return changed
    data["hooks"]["PreToolUse"] = [m for m in pre if m not in ours] + [
        {"matcher": "Bash", "hooks": [{"type": "command", "command": HOOK_COMMAND}]}]
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2) + "\n")
    return True


AGENTS_BLOCK = f"""{SETUP_MARK[0]}
## Third-party registries

Items from a shadcn-format registry other than shadcn's own (`@ns/item`, a registry URL) are not
installed with `shadcn add` directly — a hook refuses it. They go through registry intake:

1. `registry_intake.py review . @ns/item` — read-only report of files, npm deps, env vars and findings
2. **Stop and ask the user**, always, even for a clean review or when in a hurry: a new registry needs
   their yes before `registry_intake.py allow . @ns <url> --reason "..." --by <them>`, and the item needs
   their yes before `registry_intake.py approve . @ns/item --by <them>`. `--by` is the person who said
   yes, never the agent or the OS login. The hook asks them to confirm both commands.
3. `registry_intake.py install . @ns/item` — installs the snapshot, never the live URL

Blocking findings are
fixed, ported by hand, or accepted one by one with a written reason. Imported code has to pass the
capped design lint; raising `--max-warnings` fails `registry_intake.py check`.
{SETUP_MARK[1]}
"""


def cmd_setup(args) -> int:
    root = args.root.resolve()
    lock = load_lock(root)
    created = lock is None
    lock = lock or {"version": 1, "shadcn": SHADCN_VERSION, "registries": {}, "items": {}, "design_lint_caps": {}}
    ui = stack_ui(root)
    for ns, (url, p) in registries_in_components(root).items():
        # the registry of the UI system the project chose (stack.ui = coss → @coss) installs live;
        # anything else found in components.json is allowlisted but still goes through snapshots
        live = ui is not None and ns == f"@{ui}" and ns in LIVE_UI_REGISTRIES
        lock["registries"].setdefault(ns, {
            "url": url, "trust": "live" if live else "snapshot",
            "reason": f"stack.ui = {ui}: the project's component system" if live
            else f"already in {p.relative_to(root)} when intake was set up",
            "allowed_by": "setup", "allowed_at": now()})
    caps = lint_caps(root)
    lock["design_lint_caps"] = {**caps, **{k: min(v, caps.get(k, v)) for k, v in (lock.get("design_lint_caps") or {}).items()}}
    save_lock(root, lock)
    hooked = wire_hook(root)
    agents = root / "AGENTS.md"
    text = agents.read_text() if agents.exists() else ""
    if SETUP_MARK[0] in text:
        text = re.sub(re.escape(SETUP_MARK[0]) + r".*?" + re.escape(SETUP_MARK[1]) + r"\n?", AGENTS_BLOCK, text, flags=re.S)
    else:
        text = (text.rstrip() + "\n\n" if text.strip() else "") + AGENTS_BLOCK
    agents.write_text(text)
    record(root, "enforced")
    print(f"{'created' if created else 'updated'} {LOCK} · registries allowlisted: {', '.join(lock['registries']) or 'none'}")
    print(f"hook: {'wired in' if hooked else 'already in'} .claude/settings.json · AGENTS.md section written")
    print(f"design-lint caps baseline: {lock['design_lint_caps'] or 'none'}")
    ok, problems = check(root)
    for pr in problems:
        print(f"  ✗ {pr}")
    return 0 if ok else 1


def stack_ui(root: Path) -> str | None:
    meta = root / ".workflow" / "meta.json"
    if not meta.exists():
        return None
    stack = json.loads(meta.read_text()).get("stack") or {}
    return stack.get("ui") or ((stack.get("monorepo") or {}).get("web") or {}).get("ui")


def record(root: Path, value: str) -> None:
    meta = root / ".workflow" / "meta.json"
    if not meta.exists():
        return
    d = json.loads(meta.read_text())
    d.setdefault("stack", {})["registry_intake"] = value
    meta.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")


def cmd_allow(args) -> int:
    root = args.root.resolve()
    lock = load_lock(root)
    if lock is None:
        print(f"no {LOCK} — run setup first", file=sys.stderr)
        return 1
    if not args.ns.startswith("@") or "{name}" not in args.url or not args.url.startswith("https://"):
        print("usage: allow <root> @ns https://host/r/{name}.json --reason ...", file=sys.stderr)
        return 1
    if args.trust == "live" and args.ns not in LIVE_UI_REGISTRIES:
        print(f"refused: only a chosen UI system's registry ({', '.join(sorted(LIVE_UI_REGISTRIES))}) can install live; "
              f"{args.ns} goes through snapshots", file=sys.stderr)
        return 1
    lock["registries"][args.ns] = {"url": args.url, "trust": args.trust, "reason": args.reason,
                                   "allowed_by": args.by, "allowed_at": now()}
    save_lock(root, lock)
    print(f"allowlisted {args.ns} → {args.url}")
    print("components.json is not changed: installs go through the snapshot, so the CLI never needs the live namespace.")
    return 0


def cmd_deny(args) -> int:
    root = args.root.resolve()
    lock = load_lock(root)
    if lock is None or args.ns not in (lock.get("registries") or {}):
        print(f"{args.ns} is not allowlisted", file=sys.stderr)
        return 1
    del lock["registries"][args.ns]
    save_lock(root, lock)
    left = [k for k in lock.get("items") or {} if k.startswith(args.ns + "/")]
    print(f"removed {args.ns}" + (f" — {len(left)} approved item(s) stay locked: {', '.join(left)}" if left else ""))
    return 0


# ---------------------------------------------------------------------------------------------
# hook


RUNNERS = {"npx", "pnpx", "bunx", "dlx", "exec"}


def governed_adds(command: str) -> list[tuple[str, list[str], str | None, bool]]:
    """[(tool, items, --cwd, read_only)] for every `shadcn add` / `eve add` / `eve registry add`."""
    out = []
    for seg in re.split(r"&&|\|\||;|\||\n", command):
        try:
            toks = shlex.split(seg)
        except ValueError:
            toks = seg.split()
        for i, t in enumerate(toks):
            base = t.split("/")[-1]
            tool = "shadcn" if re.match(r"^shadcn(@[\w.-]+)?$", base) else "eve" if re.match(r"^eve(@[\w.-]+)?$", base) else None
            if not tool:
                continue
            rest = toks[i + 1:]
            if tool == "eve" and rest[:2] == ["registry", "add"]:
                out.append(("eve-registry", [a for a in rest[2:] if not a.startswith("-")], None, False))
                break
            if not rest or rest[0] != "add":
                break
            items, cwd, ro, j = [], None, False, 1
            while j < len(rest):
                a = rest[j]
                if a in ("-c", "--cwd", "-p", "--path"):
                    if a in ("-c", "--cwd") and j + 1 < len(rest):
                        cwd = rest[j + 1]
                    j += 2
                    continue
                if a.startswith("--cwd="):
                    cwd = a.split("=", 1)[1]
                elif a in ("--dry-run", "--view", "--diff") or a.startswith(("--view=", "--diff=")):
                    ro = True
                elif not a.startswith("-"):
                    items.append(a)
                j += 1
            out.append((tool, items, cwd, ro))
            break
    return out


def hook_decision(payload: dict) -> str | None:
    """None to allow, or the reason to deny."""
    if payload.get("tool_name") != "Bash":
        return None
    command = (payload.get("tool_input") or {}).get("command") or ""
    if "shadcn" not in command and "eve" not in command:
        return None
    adds = governed_adds(command)
    if not adds:
        return None
    cwd = Path(payload.get("cwd") or ".").resolve()
    root = find_root(cwd)
    lock = load_lock(root) if root else None
    how = "Use registry intake: `registry_intake.py review|approve|install <root> <item>` (see AGENTS.md)."
    for tool, items, add_cwd, read_only in adds:
        where = (cwd / add_cwd).resolve() if add_cwd else cwd
        if tool == "eve-registry":
            for a in items:
                ns = a.split("=", 1)[0]
                if lock is None or ns not in (lock.get("registries") or {}):
                    return f"`eve registry add {a}`: {ns} is not in the registry-intake allowlist. {how}"
            continue
        for it in items:
            if tool == "eve" and not it.startswith("@") and "://" not in it:
                continue  # eve's official catalog: `eve add connection/x`
            if tool == "shadcn" and is_bare(it):
                continue  # shadcn's own registry
            if read_only:
                continue  # --dry-run / --view / --diff write nothing
            ns = ns_of(it)
            if lock and ((lock.get("registries") or {}).get(ns) or {}).get("trust") == "live":
                continue  # the project's own UI system, allowlisted as live with its reason
            if lock is None:
                return (f"`{tool} add {it}` installs third-party source and this project has no {LOCK}. "
                        f"Set up intake first (`registry_intake.py setup <root>`), then review and approve the item.")
            if it.endswith(".json") and "://" not in it:
                target = (where / it).resolve()
                for key, entry in (lock.get("items") or {}).items():
                    if (root / entry["snapshot"]).resolve() == target:
                        err = verify_entry(root, key, lock)
                        if err:
                            return f"`{tool} add {it}`: {err}. {how}"
                        break
                else:
                    return f"`{tool} add {it}`: this file is not an approved snapshot in {LOCK}. {how}"
                continue
            return (f"`{tool} add {it}` fetches live third-party source and skips review and the snapshot. "
                    f"{how}")
    return None


# `registry_intake.py allow|approve`, called by path or through a variable holding it (`python3 $S approve`)
DECISION_CALL = re.compile(r"""(?:\S*registry_intake\.py["']?|["']?\$\{?\w+\}?["']?)\s+(allow|approve)\s+(?:\S+\s+)?(\S+)""")


def hook_ask(payload: dict) -> str | None:
    """None, or what the user is asked to confirm: allowlisting a registry and approving an item are
    their decisions, and an agent that skipped the question still meets the prompt."""
    if payload.get("tool_name") != "Bash":
        return None
    command = (payload.get("tool_input") or {}).get("command") or ""
    if "registry_intake" not in command:
        return None
    asks = []
    for verb, target in DECISION_CALL.findall(command):
        by = re.search(r"--by[= ]+(\"[^\"]*\"|'[^']*'|\S+)", command)
        who = by.group(1).strip("\"'") if by else "nobody named"
        what = f"allowlist the registry {target}" if verb == "allow" else f"approve {target} into a snapshot"
        asks.append(f"{what}, recorded as decided by {who}")
    if not asks:
        return None
    return ("registry intake: the agent wants to " + "; and to ".join(asks) +
            ". Confirm only if you said yes to this — the lock will say you did.")


def cmd_hook(_args) -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return 0
    reason = hook_decision(payload)
    if reason:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                                 "permissionDecisionReason": reason}}))
        return 0
    ask = hook_ask(payload)
    if ask:
        # "ask": the reason is shown to the user, not to Claude (hooks docs, PreToolUse decision control)
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask",
                                                 "permissionDecisionReason": ask}}))
    return 0


# ---------------------------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("setup"); s.add_argument("root", type=Path)
    s = sub.add_parser("allow"); s.add_argument("root", type=Path); s.add_argument("ns"); s.add_argument("url")
    s.add_argument("--reason", required=True); s.add_argument("--by", default="unknown")
    s.add_argument("--trust", choices=["snapshot", "live"], default="snapshot")
    s = sub.add_parser("deny"); s.add_argument("root", type=Path); s.add_argument("ns")
    s = sub.add_parser("review"); s.add_argument("root", type=Path); s.add_argument("item"); s.add_argument("--json", action="store_true")
    s.add_argument("--registry", action="append", default=[], metavar="@ns=URL",
                   help="resolve a namespace that is not allowlisted yet (review only)")
    s = sub.add_parser("approve"); s.add_argument("root", type=Path); s.add_argument("item"); s.add_argument("--by", required=True)
    s.add_argument("--accept", action="append"); s.add_argument("--note")
    s = sub.add_parser("install"); s.add_argument("root", type=Path); s.add_argument("item"); s.add_argument("--cwd")
    s.add_argument("shadcn_args", nargs=argparse.REMAINDER)
    s = sub.add_parser("check"); s.add_argument("root", type=Path)
    s = sub.add_parser("caps"); s.add_argument("root", type=Path); s.add_argument("--reason", required=True)
    sub.add_parser("hook")
    args = ap.parse_args(argv)
    if getattr(args, "shadcn_args", None) and args.shadcn_args[:1] == ["--"]:
        args.shadcn_args = args.shadcn_args[1:]

    if args.cmd == "review":
        root = args.root.resolve()
        extra = dict(r.split("=", 1) for r in args.registry if "=" in r)
        rep, items = review(args.item, root, extra=extra)
        if args.json:
            print(json.dumps({**asdict(rep), "exit": rep.exit_code,
                              "diffs": diff_against_snapshot(root, load_lock(root), items)}, indent=2))
        else:
            print_report(rep, diff_against_snapshot(root, load_lock(root), items))
        return rep.exit_code
    if args.cmd == "check":
        ok, problems = check(args.root.resolve())
        print("✓ registry intake enforced" if ok else "✗ registry intake:\n" + "\n".join(f"  {p}" for p in problems))
        return 0 if ok else 1
    return {"setup": cmd_setup, "allow": cmd_allow, "deny": cmd_deny, "approve": cmd_approve,
            "install": cmd_install, "caps": cmd_caps, "hook": cmd_hook}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
