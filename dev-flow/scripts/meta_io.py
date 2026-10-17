"""Safe writes for `.workflow/meta.json`: atomic replace, plus a lock around read-modify-write.

Every script in this folder that changes meta.json goes through here. It used to be a plain
`write_text` with no lock, and that failed in two ways (AUDIT.md §6.2):

- Two writers in parallel each read the old file, and the second save erased the first one's
  change. Twenty `append-history` runs kept 11 to 15 entries, and every process exited 0.
- `write_text` truncates first and writes second, so a reader in between saw an empty file. If a
  crash landed there, it left the empty file behind, and every script then failed on it.

Usage:

    with meta_io.locked(root / ".workflow"):
        meta = json.loads(meta_path.read_text())
        ...                                   # change meta
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
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

try:
    import fcntl
except ImportError:  # Windows
    fcntl = None  # type: ignore[assignment]


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
    """Write `data` in meta.json's usual layout (2-space indent, UTF-8, trailing newline), atomically."""
    write_text(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")
