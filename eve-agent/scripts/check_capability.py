#!/usr/bin/env python3
"""check_capability.py — check one capability package (references/capability-package.md).

Usage:
    python scripts/check_capability.py <project-root> <capability-id> [--validate-cmd "<cmd with {file}>"]

Checks, from the files alone (no build, no network):
  - capabilities/<id>/package.json and capability.json exist; capability.json#id equals <id>;
  - runtime dependencies are limited to @<slug>/contracts, @<slug>/services, eve and zod;
  - no file under extension/ imports another workspace package (the database package above all);
  - every tool, skill and instructions module is wrapped in defineDynamic (activation per workspace);
  - the mount agent/extensions/<id_snake>.ts exists, and tool names stay within ^[a-z][a-z0-9_]*$ and
    64 characters once prefixed with the mount;
  - THIRD_PARTY_NOTICES exists when capability.json#thirdPartyCode is true;
  - capability.json passes the project's schema, when a validate command is passed with --validate-cmd,
    e.g. "pnpm --filter @acme/contracts exec validate-capability {file}". A command recorded in
    meta.json#stack_config.capability_validate_cmd is only PRINTED, never run: meta.json is a file in
    the repository, and running a command from it would run whoever last edited it.
Exit 0 when every check passes, 1 otherwise. Pure standard library.
"""
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_eve_state import find_agent_app  # noqa: E402

NAME = re.compile(r"^[a-z][a-z0-9_]*$")
IMPORT = re.compile(r"""(?:from\s+|import\s*\(\s*|require\s*\(\s*)["']([^"']+)["']""")
COMMENTS = re.compile(r"/\*.*?\*/|//[^\n]*", re.S)
GATED_EXPORT = re.compile(r"export\s+default\s+defineDynamic\s*\(")
GATED_DIRS = {"tools", "skills", "instructions"}


def load_json(path: Path, fails: list[str], root: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError) as exc:
        fails.append(f"{path.relative_to(root)} cannot be read as JSON: {exc}")
        return None


def main() -> int:
    args = sys.argv[1:]
    validate_cmd = None
    if "--validate-cmd" in args:
        i = args.index("--validate-cmd")
        validate_cmd = args[i + 1] if i + 1 < len(args) else None
        args = args[:i] + args[i + 2:]
    if len(args) != 2:
        print(__doc__.strip().splitlines()[2])
        return 2
    root = Path(args[0]).expanduser().resolve()
    cap_id = args[1]
    pkg_dir = root / "capabilities" / cap_id
    fails: list[str] = []
    notes: list[str] = []

    meta_path = root / ".workflow" / "meta.json"
    meta = (load_json(meta_path, fails, root) or {}) if meta_path.is_file() else {}
    recorded_cmd = (meta.get("stack_config") or {}).get("capability_validate_cmd")

    if not re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", cap_id):
        fails.append(f"id `{cap_id}` is not kebab-case")
    mount = cap_id.replace("-", "_")

    pkg_path = pkg_dir / "package.json"
    contract_path = pkg_dir / "capability.json"
    if not pkg_path.is_file():
        print(f"FAIL: {pkg_path.relative_to(root)} not found — scaffold it with `eve extension init` first.")
        return 1
    pkg = load_json(pkg_path, fails, root)
    if pkg is None:
        for f in fails:
            print(f"FAIL: {f}")
        return 1
    name = pkg.get("name", "")
    scope = name.split("/")[0] if name.startswith("@") and "/" in name else None
    if not scope:
        fails.append(f"package name `{name}` has no scope; expected @<slug>/capability-{cap_id}")

    # Dependencies: only the contract and service packages, eve and zod.
    allowed = {"eve", "zod"} | ({f"{scope}/contracts", f"{scope}/services"} if scope else set())
    for field in ("dependencies", "peerDependencies"):
        for dep in pkg.get(field, {}) or {}:
            if dep not in allowed:
                fails.append(f"{field} has `{dep}`: a capability depends only on {', '.join(sorted(allowed))}")

    # Imports under extension/: no other workspace package.
    src_dir = pkg_dir / "extension"
    for f in sorted(src_dir.rglob("*.ts")) if src_dir.is_dir() else []:
        text = f.read_text(encoding="utf-8")
        code = COMMENTS.sub("", text)
        for spec in IMPORT.findall(code):
            if scope and spec.startswith(scope + "/") and spec not in allowed:
                fails.append(f"{f.relative_to(root)} imports `{spec}`: go through {scope}/services instead")
        rel_parts = f.relative_to(src_dir).parts
        gated = bool(GATED_DIRS & set(rel_parts[:-1])) or f.name == "instructions.ts"
        if gated and not GATED_EXPORT.search(code):
            fails.append(f"{f.relative_to(root)}: the default export is not `defineDynamic(...)` — it would reach every workspace")
        if f.parent.name == "tools":
            tool = f.stem
            if not NAME.match(tool):
                fails.append(f"tool `{tool}` is not snake_case")
            if len(f"{mount}__{tool}") > 64:
                fails.append(f"`{mount}__{tool}` is longer than 64 characters")
    if not src_dir.is_dir():
        fails.append("no extension/ folder — not an eve extension package")

    # The contract.
    if not contract_path.is_file():
        fails.append("capability.json not found")
    else:
        contract = load_json(contract_path, fails, root) or {}
        if contract and contract.get("id") != cap_id:
            fails.append(f"capability.json#id is `{contract.get('id')}`, expected `{cap_id}`")
        if contract.get("thirdPartyCode") is True and not (pkg_dir / "THIRD_PARTY_NOTICES").is_file():
            fails.append("thirdPartyCode is true but THIRD_PARTY_NOTICES is missing")
        if validate_cmd:
            # No shell: the command is split into arguments and {file} becomes one argument.
            argv = [str(contract_path) if a == "{file}" else a for a in shlex.split(validate_cmd)]
            r = subprocess.run(argv, cwd=root, capture_output=True, text=True)
            if r.returncode != 0:
                fails.append(f"schema validation failed: {(r.stdout + r.stderr).strip()[:400]}")
        elif recorded_cmd:
            notes.append(f"capability.json not validated. meta.json records `{recorded_cmd}`; read it, then "
                         f"re-run with --validate-cmd \"{recorded_cmd}\" to execute it")
        else:
            notes.append("capability.json not validated against the schema: pass --validate-cmd")

    # The mount.
    if not NAME.match(mount):
        fails.append(f"mount name `{mount}` is not snake_case")
    app, _ = find_agent_app(root)
    if not app:
        fails.append("no agent found (apps/agent, apps/web or the root) to mount the capability into")
    else:
        mount_file = app / "agent" / "extensions" / f"{mount}.ts"
        if not mount_file.is_file():
            fails.append(f"mount {mount_file.relative_to(root)} is missing")
        elif name and name not in mount_file.read_text(encoding="utf-8"):
            fails.append(f"mount {mount_file.relative_to(root)} does not import `{name}`")

    for n in notes:
        print(f"NOTE: {n}")
    for f in fails:
        print(f"FAIL: {f}")
    if not fails:
        print(f"OK: capability `{cap_id}` passes the package checks. Still to run: the build, `eve build`, "
              "and the off/on test with a recording mock model (capability-package.md, Done when).")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
