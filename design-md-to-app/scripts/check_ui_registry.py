#!/usr/bin/env python3
"""Checks for a UI SDK design-system registry installed into a monorepo's packages/ui (G1).

Every rule here was a failure measured on 2026-11-26, installing ui-agent's registry (981 items, UI SDK
0.1.0-beta.17) into a shadcn monorepo on pnpm with `moduleResolution: Bundler`
(`references/ui-sdk-registry-monorepo.md` has the account).

  check_ui_registry.py items   <base-url> <name>... --version 0.1.0-beta.17 [--json]
      Before installing: the items and everything they pull in, read from the registry. Exit 1 on a stop,
      3 when only warnings need a person, 0 clean.
  check_ui_registry.py project <root> [--ui-package packages/ui] [--app apps/web] [--json]
      After installing: what the install left in the monorepo. Same exit codes.

Standard library only; `items` fetches over HTTP(S), `project` reads files.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urljoin, urlparse

BEHAVIOUR_LIBS = ("@shadcn/react", "radix-ui", "@base-ui/react")
LAYER_ORDER = "@layer ui-sdk, theme, base, components, utilities;"
CLIENT_SIGNS = re.compile(r"\b(on[A-Z][A-Za-z]+=\{|use(State|Effect|Ref|Reducer|Context|Callback|Memo|LayoutEffect)\()")
ALIAS_IMPORT = re.compile(r"""from\s+['"](@/(?:components/ui|lib)/[^'"]+)['"]""")


def finding(code: str, level: str, where: str, what: str) -> dict:
    return {"code": code, "level": level, "where": where, "what": what}


def dep_name_version(dep: str) -> tuple[str, str | None]:
    m = re.match(r"^(@?[^@]+)@(.+)$", dep)
    return (m.group(1), m.group(2)) if m else (dep, None)


def fetch(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=20) as r:  # noqa: S310 — the registry URL the user named
        return json.loads(r.read())


def item_url(base: str, name: str) -> str:
    return name if "://" in name else urljoin(base.rstrip("/") + "/", f"{name}.json")


def check_items(base: str, names: list[str], version: str, get=fetch) -> list[dict]:
    """The items and their registryDependencies, transitively, each read once."""
    out: list[dict] = []
    seen: set[str] = set()
    local_origins: dict[str, int] = {}
    queue = [item_url(base, n) for n in names]
    while queue:
        url = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)
        item = get(url)
        name = item.get("name", url)
        for dep in item.get("registryDependencies", []):
            host = urlparse(dep).hostname if "://" in dep else None
            if host in ("localhost", "127.0.0.1", "::1"):
                origin = f"{urlparse(dep).scheme}://{urlparse(dep).netloc}"
                local_origins[origin] = local_origins.get(origin, 0) + 1
            queue.append(dep if "://" in dep else item_url(base, dep))
        for dep in item.get("dependencies", []):
            pkg, ver = dep_name_version(dep)
            if pkg in ("@ui-sdk/core", "@ui-sdk/react") and ver != version:
                out.append(finding("U1", "stop", name, f"{pkg}@{ver} — the project pins {version} exactly: regenerate the registry"))
            if pkg in BEHAVIOUR_LIBS or pkg.startswith("@radix-ui/"):
                out.append(finding("U2", "stop", name, f"depends on {pkg}: a second behaviour library beside UI SDK (golden rule 3) — fix the item or record an exception"))
            if ver is None:
                out.append(finding("U4", "warn", name, f"{pkg} has no version: pin it in the registry"))
            elif ver[0] in "^~":
                out.append(finding("U4", "warn", name, f"{dep}: a range, not an exact version"))
        for f in item.get("files", []):
            path, ftype, content = f.get("path", ""), f.get("type", ""), f.get("content", "")
            if path.endswith(".css") and item.get("type") != "registry:theme":
                out.append(finding("U3", "warn", name, f"{path}: CSS outside a theme item — tokens belong in globals.css"))
            if ftype == "registry:file" and ALIAS_IMPORT.search(content):
                alias = ALIAS_IMPORT.search(content).group(1)
                out.append(finding("U5", "stop", name, f"{path} is registry:file, copied as is: its import {alias} is not rewritten and does not exist in a monorepo — type it registry:component"))
            if path.endswith(".tsx") and CLIENT_SIGNS.search(content) and not re.match(r"""\s*['"]use client['"]""", content):
                out.append(finding("U7", "warn", name, f"{path} uses handlers or hooks without 'use client': it breaks a server page's prerender"))
    for origin, n in local_origins.items():
        out.append(finding("U6", "stop", origin, f"{n} registryDependencies point at {origin}: the registry was built for a local origin — rebuild it with its public one"))
    return out


def deps_of(pkg_json: Path) -> set[str]:
    p = json.loads(pkg_json.read_text())
    return {*p.get("dependencies", {}), *p.get("devDependencies", {}), *p.get("peerDependencies", {})}


# Real module specifiers only: `import … from "x"`, `export … from "x"`, `import "x"` at the start of a statement, and
# `import("x")`. A looser pattern read SQL as imports — `select … from "user"` in a test became a package `user` (P4
# false positive, measured on Agentic Factory's apps/web, 2026-11-26).
STATIC_IMPORT = re.compile(r"""^\s*(?:import|export)\s(?:[^;'"]*?\sfrom\s*)?['"]([^'"]+)['"]""", re.M)
DYNAMIC_IMPORT = re.compile(r"""\bimport\(\s*['"]([^'"]+)['"]\s*\)""")


def import_specs(text: str) -> list[str]:
    return STATIC_IMPORT.findall(text) + DYNAMIC_IMPORT.findall(text)


def package_of(spec: str) -> str | None:
    if spec.startswith((".", "/", "@/", "~/", "node:")):
        return None
    parts = spec.split("/")
    return "/".join(parts[:2]) if spec.startswith("@") else parts[0]


def check_project(root: Path, ui_pkg: str = "packages/ui", app: str = "apps/web") -> list[dict]:
    out: list[dict] = []
    ui_dir, app_dir = root / ui_pkg, root / app
    ui_name = json.loads((ui_dir / "package.json").read_text())["name"]
    cj = json.loads((app_dir / "components.json").read_text())
    lib = cj.get("aliases", {}).get("lib")
    if lib != f"{ui_name}/lib":
        out.append(finding("P1", "stop", f"{app}/components.json", f'aliases.lib is {lib!r}: registry:lib items land in the app while packages/ui imports them from {ui_name}/lib — set it to "{ui_name}/lib"'))
    css_path = ui_dir / json.loads((ui_dir / "components.json").read_text())["tailwind"]["css"]
    css = css_path.read_text()
    imp = re.search(r"""@import\s+['"]tailwindcss['"]""", css)
    order = css.find(LAYER_ORDER)
    if imp and (order == -1 or order > imp.start()):
        out.append(finding("P2", "stop", str(css_path.relative_to(root)), f"`{LAYER_ORDER}` must come before @import \"tailwindcss\": without it ui-sdk's layer lands after utilities, and a utility cannot override a component"))
    lock = root / "pnpm-lock.yaml"
    if lock.exists():
        versions = set(re.findall(r"^\s{2}'?@ui-sdk/core@([^:'(\s]+)", lock.read_text(), re.M))
        if len(versions) > 1:
            out.append(finding("P3", "stop", "pnpm-lock.yaml", f"@ui-sdk/core at {sorted(versions)}: one copy only (pnpm.overrides)"))
    # With pnpm a package sees only its own dependencies (and the workspace root's): packages/ui's are not the app's.
    app_deps = deps_of(app_dir / "package.json") | deps_of(root / "package.json") | {ui_name}
    for f in sorted(app_dir.rglob("*.ts*")):
        if "node_modules" in f.parts or ".next" in f.parts:
            continue
        text = f.read_text(errors="ignore")
        for spec in import_specs(text):
            m = ALIAS_IMPORT.search(f"from '{spec}'")
            if m:
                out.append(finding("P5", "stop", str(f.relative_to(root)), f"imports {spec}: it does not exist in the monorepo — the item was copied without rewriting (U5)"))
            pkg = package_of(spec)
            if pkg and pkg not in app_deps:
                out.append(finding("P4", "stop", str(f.relative_to(root)), f"imports {pkg}, which is not a dependency of {app}: with pnpm the app cannot see packages/ui's dependencies — add it to {app}/package.json"))
    return out


def report(findings: list[dict], as_json: bool) -> int:
    if as_json:
        print(json.dumps(findings, indent=2))
    else:
        for f in findings:
            print(f"{f['level'].upper():5} {f['code']} {f['where']}: {f['what']}")
        print("clean" if not findings else f"{len(findings)} finding(s)")
    if any(f["level"] == "stop" for f in findings):
        return 1
    return 3 if findings else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("items")
    a.add_argument("base")
    a.add_argument("names", nargs="+")
    a.add_argument("--version", required=True)
    a.add_argument("--json", action="store_true")
    b = sub.add_parser("project")
    b.add_argument("root", type=Path)
    b.add_argument("--ui-package", default="packages/ui")
    b.add_argument("--app", default="apps/web")
    b.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if args.cmd == "items":
        return report(check_items(args.base, args.names, args.version), args.json)
    return report(check_project(args.root.resolve(), args.ui_package, args.app), args.json)


if __name__ == "__main__":
    sys.exit(main())
