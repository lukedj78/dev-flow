#!/usr/bin/env python3
"""
Scaffold lib/forms/ for a Next.js 16 App Router project.

Reads meta.json#stack.forms to pick the underlying library (TanStack Form
or react-hook-form), then writes the 7 toolkit files into <root>/lib/forms/
with the matching backend. Surface API is identical across both — only the
internals differ.

Idempotent: if lib/forms/index.ts already exists, prints a warning and exits
0 (no overwrite). Pass --force to overwrite.

Refuses to apply if:
- meta.json#stack.framework not in {"next", "monorepo"}
- meta.json#stack.nextjs_version != "16"
- pages/ directory exists (Pages Router) at the project root

After writing the files, appends a history entry to meta.json. Does NOT bump
phase (forms live inside the implementation phase).

Reference files used as source-of-truth for the wiring:
- forms/references/toolkit-tanstack.md  → stack.forms = "tanstack-form"
- forms/references/toolkit-rhf.md       → stack.forms = "react-hook-form"

Usage:
  python3 scaffold_lib_forms.py --root <project-root> [--force] [--monorepo-app web]

Notes:
- The script extracts code blocks marked with fenced code fence "```ts" or
  "```tsx" from the matching toolkit reference and writes them out by
  recognizing the file path mentioned in the section heading immediately
  above the fence (e.g. "## `lib/forms/useEditForm.ts`").
- The 7 expected files are: index.ts, useEditForm.ts, useCreateForm.ts,
  FormProvider.tsx, FormField.tsx, FormActions.tsx, mapFormError.ts
- After scaffolding, prints a checklist of remaining manual steps:
  * Install dependencies (npm install … or pnpm add …)
  * Mount <Toaster richColors position="top-right" /> in app/layout.tsx
  * Add the shadcn primitives (field input textarea select checkbox switch
    radio-group button label sonner) via `npx shadcn@latest add …`
  * Optionally adapt the error classes inside mapFormError.ts to your
    services layer (SessionExpiredError, ForbiddenError, ValidationProblem,
    ServerProblem are placeholders).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

EXPECTED_FILES = [
    "index.ts",
    "FormProvider.tsx",
    "useEditForm.ts",
    "useCreateForm.ts",
    "FormField.tsx",
    "FormActions.tsx",
    "mapFormError.ts",
]


def fail(msg: str, code: int = 1) -> None:
    print(f"✗ {msg}", file=sys.stderr)
    sys.exit(code)


def warn(msg: str) -> None:
    print(f"⚠ {msg}", file=sys.stderr)


def info(msg: str) -> None:
    print(f"  {msg}")


def find_skill_dir() -> Path:
    """The directory containing the toolkit reference markdown files."""
    # This script lives at <skills-root>/forms/scripts/scaffold_lib_forms.py
    # References at  <skills-root>/forms/references/toolkit-*.md
    here = Path(__file__).resolve().parent
    return here.parent  # …/forms


def read_meta(root: Path) -> dict:
    meta_path = root / ".workflow" / "meta.json"
    if not meta_path.exists():
        fail(
            f"No .workflow/meta.json at {root}. Run dev-flow's init_workflow.py first."
        )
    with meta_path.open() as f:
        return json.load(f)


def resolve_stack(meta: dict, monorepo_app: str | None) -> dict:
    """Return the effective stack section for the web target."""
    stack = meta.get("stack", {})
    framework = stack.get("framework")
    if framework == "next":
        return stack
    if framework == "monorepo":
        web = stack.get("monorepo", {}).get(monorepo_app or "web", {})
        # Inherit nextjs_version + forms if set on the web sub-stack
        merged = dict(stack)
        merged.update(web)
        return merged
    fail(
        f"meta.json#stack.framework={framework!r} — this skill only applies "
        "to 'next' or 'monorepo' targets."
    )


def check_app_router(root: Path) -> None:
    if (root / "pages").exists():
        fail(
            f"Found pages/ at {root} — this skill only applies to App Router "
            "projects. Migrate to app/ first."
        )
    if not (root / "app").exists():
        fail(
            f"No app/ directory at {root}. Initialize Next.js 16 App Router first."
        )


def parse_toolkit_md(md_path: Path) -> dict[str, str]:
    """Extract the 7 code blocks from a toolkit reference markdown file.

    Each section heading like `## \`lib/forms/<file>\`` is followed by a
    fenced code block. We capture the body of each fence and map it to the
    filename.
    """
    text = md_path.read_text()
    # Pattern: heading line `## ` lib/forms/<file> `, then any markdown, then
    # the next fenced code block whose body is captured.
    pattern = re.compile(
        r"^##\s+`lib/forms/(?P<file>[^`]+)`\s*\n"   # heading
        r"(?:.*?\n)*?"                              # any preamble lines
        r"```(?:ts|tsx)\n"                          # fence opening
        r"(?P<body>.*?)\n"                          # captured body
        r"```",                                     # fence closing
        re.MULTILINE | re.DOTALL,
    )
    extracted: dict[str, str] = {}
    for m in pattern.finditer(text):
        extracted[m.group("file")] = m.group("body")
    missing = [f for f in EXPECTED_FILES if f not in extracted]
    if missing:
        fail(
            f"Toolkit reference {md_path} is missing code blocks for: {missing}. "
            "Check section headings — they must look like '## `lib/forms/<file>`'."
        )
    return extracted


def write_files(target_dir: Path, files: dict[str, str], force: bool) -> list[str]:
    target_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for name, body in files.items():
        dest = target_dir / name
        if dest.exists() and not force:
            warn(f"{dest.relative_to(target_dir.parent.parent)} exists — skipping (use --force to overwrite)")
            continue
        dest.write_text(body + "\n")
        written.append(str(dest.relative_to(target_dir.parent.parent)))
        info(f"✓ {dest.relative_to(target_dir.parent.parent)}")
    return written


def append_history(
    meta_path: Path,
    library: str,
    written: list[str],
) -> None:
    with meta_path.open() as f:
        meta = json.load(f)
    history = meta.setdefault("history", [])
    history.append(
        {
            "skill": "forms",
            "ran_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "action": f"scaffold lib/forms/ ({library})",
            "outputs": written,
            "phase_before": meta.get("phase"),
            "phase_after": meta.get("phase"),
        }
    )
    meta["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    with meta_path.open("w") as f:
        json.dump(meta, f, indent=2)
        f.write("\n")


def print_next_steps(library: str) -> None:
    print()
    print("Next steps:")
    print()
    print("1. Install dependencies:")
    if library == "tanstack-form":
        print("     npm install @tanstack/react-form zod sonner")
    else:
        print("     npm install react-hook-form @hookform/resolvers zod sonner")
    print()
    print("2. Install shadcn primitives:")
    print(
        "     npx shadcn@latest add field input textarea select "
        "checkbox switch radio-group button label sonner"
    )
    print()
    print("3. Mount the Toaster in app/layout.tsx:")
    print("     import { Toaster } from \"sonner\";")
    print("     <Toaster richColors position=\"top-right\" />")
    print()
    print("4. Adapt the error classes inside lib/forms/mapFormError.ts to")
    print("   match your services layer (SessionExpiredError, ForbiddenError,")
    print("   ValidationProblem, ServerProblem are placeholders).")
    print()
    print("5. Optionally swap inline strings for your i18n keys.")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path, help="Project root containing .workflow/")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files in lib/forms/",
    )
    parser.add_argument(
        "--monorepo-app",
        default="web",
        help="For monorepo projects: which app to scaffold into (default: web)",
    )
    parser.add_argument(
        "--library",
        choices=["tanstack-form", "react-hook-form"],
        help="Override meta.json#stack.forms (rarely needed)",
    )
    args = parser.parse_args()

    root: Path = args.root.resolve()
    if not root.is_dir():
        fail(f"--root {root} is not a directory.")

    meta = read_meta(root)
    stack = resolve_stack(meta, args.monorepo_app)

    nextjs_version = str(stack.get("nextjs_version", ""))
    if nextjs_version != "16":
        fail(
            f"meta.json#stack.nextjs_version={nextjs_version!r} — this skill "
            "only applies to Next.js 16. Pages Router and pre-16 are out of scope."
        )

    check_app_router(root)

    library = args.library or stack.get("forms")
    if not library:
        fail(
            "meta.json#stack.forms is not set. Run prd-from-idea Q8 first, or "
            "pass --library tanstack-form|react-hook-form."
        )
    if library not in ("tanstack-form", "react-hook-form"):
        fail(f"Unknown library {library!r}. Expected tanstack-form or react-hook-form.")

    skill_dir = find_skill_dir()
    md_name = "toolkit-tanstack.md" if library == "tanstack-form" else "toolkit-rhf.md"
    md_path = skill_dir / "references" / md_name
    if not md_path.exists():
        fail(f"Missing toolkit reference {md_path}.")

    print(f"→ Scaffolding lib/forms/ ({library}) at {root}")
    files = parse_toolkit_md(md_path)
    target_dir = root / "lib" / "forms"
    written = write_files(target_dir, files, args.force)
    if not written:
        print()
        print("Nothing written (all files already exist). Use --force to overwrite.")
        sys.exit(0)

    meta_path = root / ".workflow" / "meta.json"
    append_history(meta_path, library, written)
    print()
    print(f"✓ Wrote {len(written)} file(s) into lib/forms/")
    print(f"✓ Appended history entry to {meta_path.relative_to(root)}")
    print_next_steps(library)


if __name__ == "__main__":
    main()
