"""Detect any change inside a directory tree since a point in time.

The quality gate scans ``src/`` with Skylos while the test suite runs, and
Skylos's dead-code grep verification aborts (``SKY-ANALYSIS-INCOMPLETE``)
when files appear or vanish under it. The suite therefore asserts that it
touched nothing under the package. A create-then-delete leaves no surviving
descendant to inspect, but it does bump the modification time of the
directory that held the entry — including the root itself — so directories
are checked as carefully as files.
"""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_IGNORED_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        ".skylos",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "__pycache__",
        "node_modules",
    }
)


def paths_modified_since(
    root: Path,
    since: float,
    *,
    ignored_dirs: frozenset[str] = DEFAULT_IGNORED_DIRS,
) -> list[Path]:
    """Return every path under ``root`` (root included) modified after ``since``.

    Directory modification times change whenever an entry is created, deleted
    or renamed inside them, so a transient file that no longer exists still
    shows up as its parent directory. Unreadable paths count as modified.
    """
    modified: list[Path] = []

    def _check(path: Path) -> None:
        try:
            if path.lstat().st_mtime > since:
                modified.append(path)
        except OSError:
            modified.append(path)

    _check(root)
    for current, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in ignored_dirs]
        for name in (*dirnames, *filenames):
            _check(Path(current) / name)
    return sorted(modified)
