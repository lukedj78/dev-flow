#!/usr/bin/env python3
"""flags_check.py — is the Flags SDK really wired? One verdict per piece.

    python3 flags_check.py <project-root> [--provider launchdarkly] [--json]

The provider comes from `meta.json#stack.flags`, or `meta.json#release.flag_provider`, or `--provider`.

Statuses, the same four the other module checkers use:

- `ok` — verified from the project's own files.
- `found` — missing or wrong. Exit 1.
- `not checked` — it cannot see the answer (a value that lives only in the deployment's environment,
  a declaration behind a spread). **Never a pass**: an env var this script cannot read may still be
  unset in production, and saying "ok" there would be a lie with a tick next to it.
- `not applicable` — not a web surface (the Flags SDK is web; React Native uses the provider's SDK).

What it checks, and why each one is here rather than being assumed:

1. **`flags` and the adapter are in `package.json`.** v4 ships no adapters, so the second one is a
   separate dependency and a project can easily have one without the other.
2. **`FLAGS_SECRET` is named, and 32 bytes where a literal is readable.** The shipped code throws
   *"it must be a 256-bit key (32 bytes)"*, and `precompute`/`serialize` need it too — so a missing
   secret is not "no explorer", it is a crash or a statically-served page that stopped being one.
3. **The provider's own variables.** Read from the shipped adapters' `assertEnv` calls, which throw
   on a missing value. LaunchDarkly's is `EXPERIMENTATION_CONFIG`, which contains no hint of the word.
   **Vercel Flags has none** — `vercelAdapter()` uses the deployment's OIDC token — so for the default
   provider this check has nothing to say, which is the point of choosing it.
4. **`lib/flags.ts` exists, declares a flag, and every flag has an explicit `defaultValue`** — the
   value every user gets when the provider is unreachable.
5. **No flag is declared in a `"use client"` file.** A flag evaluated client-side ships its
   configuration, and with the wrong adapter a credential, into the bundle.
6. **The sub-processor register names the provider.** A hosted flag provider is on the request path
   and receives whatever `identify` passes it.

Stdlib only, like every script the skills ship.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from base64 import urlsafe_b64decode
from dataclasses import asdict, dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import surfaces as sf  # noqa: E402 — vendored copy of dev-flow/scripts/surfaces.py; lint_skills.py keeps it identical

CODE = (".ts", ".tsx", ".js", ".jsx", ".mjs")
SKIP = {"node_modules", ".next", ".git", "dist", "build", "out", ".verification",
        ".eve", ".output", ".vercel", ".turbo", ".data"}
ENV_FILES = (".env.example", ".env.local", ".env.development.local", ".env.production",
             ".env.production.local", ".env")

#: Read from each adapter's shipped `dist` on 2026-11-06 — the literal strings it passes to its own
#: `assertEnv`, which throws when the value is missing. Not from any quickstart.
PROVIDER_ENV: dict[str, tuple[str, ...]] = {
    # The default for our stack, and its empty tuple is the whole argument: `vercelAdapter()`
    # authenticates with the OIDC token the platform injects, so there is nothing to set, nothing to
    # leak and nothing to forget. Verified by grepping its shipped dist for process.env / assertEnv
    # on 2026-11-07: zero hits.
    "vercel": (),
    "launchdarkly": ("EXPERIMENTATION_CONFIG", "LAUNCHDARKLY_CLIENT_SIDE_ID", "LAUNCHDARKLY_PROJECT_SLUG"),
    "edge-config": ("EDGE_CONFIG",),
    "posthog": ("POSTHOG_PROJECT_API_KEY", "POSTHOG_HOST"),
    "openfeature": (),
    "statsig": (),
    "growthbook": (),
    "hypertune": (),
    "optimizely": (),
    "split": (),
}

PROVIDER_PACKAGE = {p: f"@flags-sdk/{p}" for p in PROVIDER_ENV}

FLAG_DECL = re.compile(r"\bflag\s*(?:<[^>]*>)?\s*\(")
DEFAULT_VALUE = re.compile(r"\bdefaultValue\s*:")
USE_CLIENT = re.compile(r'^\s*["\']use client["\']')


@dataclass
class Finding:
    check: str
    status: str   # ok | found | not checked | not applicable
    detail: str


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _files(base: Path) -> dict[Path, str]:
    out: dict[Path, str] = {}
    for d, dirs, names in os.walk(base):
        dirs[:] = sorted(x for x in dirs if x not in SKIP)
        for n in sorted(names):
            p = Path(d) / n
            if p.suffix in CODE:
                out[p] = _read(p)
    return out


def _first(base: Path, *names: str) -> Path | None:
    for n in names:
        for prefix in ("", "src/"):
            p = base / f"{prefix}{n}"
            if p.is_file():
                return p
    return None


def env_values(base: Path) -> dict[str, str]:
    """Every NAME=value pair written in the project's env files. Values here are examples or local
    development ones; a production value lives in the deployment and this script cannot see it."""
    out: dict[str, str] = {}
    for name in ENV_FILES:
        p = base / name
        if not p.is_file():
            continue
        for line in _read(p).splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            out.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    return out


def read_meta(root: Path) -> dict:
    try:
        data = json.loads((root / ".workflow" / "meta.json").read_text())
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def resolve_provider(meta: dict, override: str | None) -> str | None:
    if override:
        return override
    stack = meta.get("stack") or {}
    if isinstance(stack.get("flags"), str):
        return stack["flags"]
    rel = meta.get("release")
    if isinstance(rel, dict) and isinstance(rel.get("flag_provider"), str):
        return rel["flag_provider"]
    return None


def _deps(base: Path) -> dict[str, str]:
    try:
        pkg = json.loads(_read(base / "package.json") or "{}")
    except ValueError:
        return {}
    out: dict[str, str] = {}
    for key in ("dependencies", "devDependencies", "peerDependencies"):
        section = pkg.get(key)
        if isinstance(section, dict):
            out.update({k: str(v) for k, v in section.items()})
    return out


def check_secret(values: dict[str, str], findings: list[Finding]) -> None:
    raw = values.get("FLAGS_SECRET")
    if raw is None:
        findings.append(Finding("flags-secret", "found",
                                "FLAGS_SECRET is in no env file — `precompute`/`serialize` throw without it, "
                                "so a flagged page either crashes or stops being statically served. "
                                "Generate one: node -e \"console.log(require('crypto')"
                                ".randomBytes(32).toString('base64url'))\""))
        return
    if not raw or raw.startswith("$") or raw in ("", "changeme", "replace-me"):
        findings.append(Finding("flags-secret", "not checked",
                                "FLAGS_SECRET is named but has no readable value here (a placeholder, or it "
                                "lives only in the deployment) — its length could not be verified"))
        return
    try:
        padded = raw + "=" * (-len(raw) % 4)
        decoded = urlsafe_b64decode(padded)
    except Exception:  # noqa: BLE001 — any decode failure is the same finding
        findings.append(Finding("flags-secret", "found",
                                "FLAGS_SECRET is not base64url: the SDK decodes it and throws "
                                '"Invalid secret, it must be a 256-bit key (32 bytes)"'))
        return
    if len(decoded) != 32:
        findings.append(Finding("flags-secret", "found",
                                f"FLAGS_SECRET decodes to {len(decoded)} bytes, not 32 — the SDK throws "
                                '"it must be a 256-bit key (32 bytes)"'))
        return
    findings.append(Finding("flags-secret", "ok", "FLAGS_SECRET is present and decodes to 32 bytes"))


def check(root: Path, provider: str | None = None) -> list[Finding]:
    findings: list[Finding] = []
    web = [s for s in sf.surfaces(root) if s.kind == "web"]
    if not web:
        return [Finding("surface", "not applicable",
                        "no web surface: the Flags SDK is web — React Native uses the provider's own SDK")]
    # Surface.path is a string relative to the project root, "." for the root — not a Path.
    base = (root / web[0].path).resolve()
    meta = read_meta(root)
    provider = resolve_provider(meta, provider)

    if provider is None:
        findings.append(Finding("provider", "found",
                                "no flag provider recorded (meta.json#stack.flags or "
                                "#release.flag_provider) and none passed with --provider"))
    elif provider not in PROVIDER_ENV:
        findings.append(Finding("provider", "not checked",
                                f"provider {provider!r} is not one this script knows "
                                f"({', '.join(sorted(PROVIDER_ENV))}): its env vars were not checked"))
    else:
        findings.append(Finding("provider", "ok", f"provider: {provider}"))

    deps = _deps(base)
    if "flags" in deps:
        findings.append(Finding("package", "ok", f"flags {deps['flags']}"))
    else:
        findings.append(Finding("package", "found", "`flags` is not a dependency — pnpm add flags"))

    if provider in PROVIDER_PACKAGE:
        pkg = PROVIDER_PACKAGE[provider]
        if pkg in deps:
            findings.append(Finding("adapter-package", "ok", f"{pkg} {deps[pkg]}"))
        else:
            findings.append(Finding("adapter-package", "found",
                                    f"{pkg} is not a dependency — flags v4 ships no adapters, "
                                    f"so the provider is a separate install"))

    values = env_values(base)
    check_secret(values, findings)

    for name in PROVIDER_ENV.get(provider or "", ()):  # type: ignore[arg-type]
        if name not in values:
            findings.append(Finding(f"env:{name}", "found",
                                    f"{name} is in no env file — the adapter calls assertEnv({name!r}) "
                                    f"and throws when it is missing"))
        elif not values[name] or values[name].startswith("$"):
            findings.append(Finding(f"env:{name}", "not checked",
                                    f"{name} is named with no readable value (it may be set only in the "
                                    f"deployment)"))
        else:
            findings.append(Finding(f"env:{name}", "ok", f"{name} is set"))

    decl = _first(base, "lib/flags.ts", "lib/flags.tsx", "lib/flags.js")
    if decl is None:
        findings.append(Finding("declaration-file", "found",
                                "no lib/flags.ts — the project has no flag declaration file "
                                "(module-add/references/module-flags.md Step 4)"))
    else:
        text = _read(decl)
        rel = decl.relative_to(base)
        n = len(FLAG_DECL.findall(text))
        if n == 0:
            findings.append(Finding("declaration-file", "found",
                                    f"{rel} exists but declares no flag()"))
        else:
            findings.append(Finding("declaration-file", "ok", f"{rel}: {n} flag(s) declared"))
            if len(DEFAULT_VALUE.findall(text)) < n:
                findings.append(Finding("default-value", "found",
                                        f"{rel}: {n} flag(s) but "
                                        f"{len(DEFAULT_VALUE.findall(text))} defaultValue — the default is what "
                                        f"EVERY user gets when the provider is unreachable, so it is written "
                                        f"explicitly and chosen to fall back to the previous behaviour"))
            else:
                findings.append(Finding("default-value", "ok", "every declared flag has an explicit defaultValue"))

    client = []
    for p, text in _files(base).items():
        if FLAG_DECL.search(text) and USE_CLIENT.search(text) and "flags/next" in text:
            client.append(str(p.relative_to(base)))
    if client:
        findings.append(Finding("client-declaration", "found",
                                "a flag is declared in a \"use client\" file, which ships its configuration "
                                "(and with some adapters a credential) into the bundle: "
                                + ", ".join(sorted(client)[:5])))
    else:
        findings.append(Finding("client-declaration", "ok", "no flag declared in a client component"))

    reg = root / "docs" / "compliance" / "subprocessors.md"
    # Vercel Flags and Edge Config are the platform the project already deploys to: same vendor, same
    # DPA, no new processor to register. Every other provider is a third party on the request path.
    SAME_PLATFORM = ("vercel", "edge-config")
    if provider is None or provider in SAME_PLATFORM:
        findings.append(Finding("subprocessor", "not applicable",
                                f"{provider} is the platform this project already deploys to: "
                                "no new sub-processor" if provider in SAME_PLATFORM
                                else "no provider to register"))
    elif not reg.is_file():
        findings.append(Finding("subprocessor", "found",
                                "docs/compliance/subprocessors.md does not exist — a hosted flag provider is on "
                                "the request path and receives whatever identify() passes it "
                                "(dev-flow/references/eu-data-sovereignty.md)"))
    elif provider.lower() not in _read(reg).lower():
        findings.append(Finding("subprocessor", "found",
                                f"{provider} is not named in docs/compliance/subprocessors.md"))
    else:
        findings.append(Finding("subprocessor", "ok", f"{provider} is in the sub-processor register"))

    return findings


def render(findings: list[Finding]) -> str:
    mark = {"ok": "✓", "found": "✗", "not checked": "?", "not applicable": "–"}
    lines = [f"  {mark.get(f.status, '?')} [{f.status:14}] {f.check}: {f.detail}" for f in findings]
    bad = sum(1 for f in findings if f.status == "found")
    unknown = sum(1 for f in findings if f.status == "not checked")
    head = ("flags: wired" if not bad and not unknown else
            f"flags: {bad} to fix" + (f", {unknown} not checked" if unknown else ""))
    tail = ["", "`not checked` is never a pass: a value this script cannot read may still be unset in "
                "production."] if unknown else []
    return "\n".join([head, *lines, *tail])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("project_root", type=Path)
    ap.add_argument("--provider", default=None, help="override meta.json#stack.flags")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if not a.project_root.is_dir():
        print(f"not a directory: {a.project_root}", file=sys.stderr)
        return 2
    findings = check(a.project_root.resolve(), a.provider)
    print(json.dumps([asdict(f) for f in findings], indent=2) if a.json else render(findings))
    return 1 if any(f.status == "found" for f in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
