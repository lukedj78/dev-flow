"""Safe writes for `.workflow/meta.json`: atomic replace, plus a lock around read-modify-write.

Every script in this folder that changes meta.json goes through here. It used to be a plain
`write_text` with no lock, and that failed in two ways (AUDIT.md §6.2):

- Two writers in parallel each read the old file, and the second save erased the first one's
  change. Twenty `append-history` runs kept 11 to 15 entries, and every process exited 0.
- `write_text` truncates first and writes second, so a reader in between saw an empty file. If a
  crash landed there, it left the empty file behind, and every script then failed on it.

Usage:

    with meta_io.locked(root / ".workflow"):
        meta = meta_io.load_or_exit(meta_path)   # refuses an invalid file with exit 2, changes nothing
        ...                                      # change meta
        meta_io.write_json(meta_path, meta)

The lock is `flock` on the `.workflow` directory itself, not on meta.json. `os.replace` swaps
meta.json's inode, so a process waiting on the old file would wake up holding a lock on a file
nobody reads. Locking the directory also leaves no lock file in a folder that projects commit.
The lock is advisory: a writer that does not take it can still clobber. Where `fcntl` is
missing (Windows), the lock does nothing, and the write is still atomic.

Standard library only, like every script the skills ship.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

try:
    import fcntl
except ImportError:  # Windows
    fcntl = None  # type: ignore[assignment]


# The contract version a meta.json conforms to, recorded in it as `contract_version` on every write. Bump it
# only with a breaking contract change, together with the migration that brings older files up to it. A file
# without the field predates it and is version 1-compatible. A script never rewrites a file whose version is
# higher than the one it knows: it would save back fields whose meaning it does not have.
CONTRACT_VERSION = 1


class InvalidMeta(ValueError):
    """meta.json is not something a script can safely read or rewrite."""


# The containers scripts read with .get(), .append() and .items(). When one held the wrong type, some
# scripts crashed on it and others saved it back unchanged (AUDIT.md §6.2). `phase` is not checked here:
# a wrong phase is refused by update_meta.py and repaired with `set-phase --allow-regress`, and that
# repair needs the file to load. A missing container is fine; `null` is not, because `setdefault` keeps it.
CONTAINERS = {"history": list, "artifacts": dict, "stack": dict, "stack_config": dict}
_JSON_TYPES = {dict: "an object", list: "an array", str: "a string", int: "a number", float: "a number",
               bool: "a boolean", type(None): "null"}


def read_meta(path: Path) -> dict[str, Any]:
    """Parse meta.json and check its structure; raise InvalidMeta saying what is wrong."""
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        raise InvalidMeta(f"it is not UTF-8 text ({e.reason})") from None
    if not text.strip():
        raise InvalidMeta("the file is empty")
    try:
        meta = json.loads(text)
    except json.JSONDecodeError as e:
        raise InvalidMeta(f"it is not valid JSON ({e.msg}, line {e.lineno} column {e.colno})") from None
    if not isinstance(meta, dict):
        raise InvalidMeta(f"its top level is {_JSON_TYPES.get(type(meta), type(meta).__name__)}, not an object")
    for key, kind in CONTAINERS.items():
        if key in meta and not isinstance(meta[key], kind):
            raise InvalidMeta(f"`{key}` is {_JSON_TYPES.get(type(meta[key]), type(meta[key]).__name__)}, "
                              f"not {_JSON_TYPES[kind]}")
    version = meta.get("contract_version")
    if "contract_version" in meta and (not isinstance(version, int) or isinstance(version, bool) or version < 1):
        raise InvalidMeta(f"`contract_version` is {version!r}, not a positive integer")
    for key, entry in (meta.get("artifacts") or {}).items():
        if not isinstance(entry, dict):
            raise InvalidMeta(f"artifact `{key}` is {_JSON_TYPES.get(type(entry), type(entry).__name__)}, "
                              "not an object")
    return meta


def load_or_exit(path: Path) -> dict[str, Any]:
    """read_meta for a command-line script: on an invalid file, say why and exit 2, having changed nothing."""
    try:
        return read_meta(path)
    except InvalidMeta as e:
        sys.stderr.write(
            f"{path} is not a valid meta.json: {e}.\n"
            "  Nothing was changed. Fix it by hand, or restore the last committed version with\n"
            f"  git checkout -- {path}\n"
        )
        sys.exit(2)


@contextmanager
def locked(workflow_dir: Path) -> Iterator[None]:
    """Hold an exclusive lock on `workflow_dir` for the duration of the block.

    If the folder does not exist, this does nothing. The caller reports the missing meta.json
    itself, and a lock must not create the folder as a side effect.
    """
    if fcntl is None or not workflow_dir.is_dir():
        yield
        return
    fd = os.open(workflow_dir, os.O_RDONLY)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)  # closing the descriptor releases the lock


def write_text(path: Path, text: str) -> None:
    """Replace `path` with `text` atomically: readers see the old file or the new one, never a mix."""
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        if path.exists():
            os.chmod(tmp, path.stat().st_mode & 0o777)
        else:
            # mkstemp creates the file 0600; a new meta.json gets the usual 0644 minus the umask.
            umask = os.umask(0)
            os.umask(umask)
            os.chmod(tmp, 0o666 & ~umask)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise


def write_json(path: Path, data: Any) -> None:
    """Write `data` in meta.json's usual layout (2-space indent, UTF-8, trailing newline), atomically,
    stamped with CONTRACT_VERSION. A file written under a newer contract is refused with exit 2, untouched."""
    if isinstance(data, dict):
        version = data.get("contract_version")
        if isinstance(version, int) and not isinstance(version, bool) and version > CONTRACT_VERSION:
            sys.stderr.write(
                f"{path} was written under a newer dev-flow contract (version {version}; this script knows "
                f"{CONTRACT_VERSION}).\n  Nothing was changed. Update the dev-flow skills, then run this again.\n")
            sys.exit(2)
        data["contract_version"] = CONTRACT_VERSION
    write_text(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")
