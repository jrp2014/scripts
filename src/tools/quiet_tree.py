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
import subprocess
import sys
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


def cloud_sync_hint(root: Path) -> str | None:
    """Explain why directory mtimes under ``root`` may change without a local write.

    iCloud Drive's "Desktop & Documents" sync rewrites the modification time
    of every directory whose contents it has just synchronised, with
    whole-second values, a moment after the change. A tree under
    ``~/Documents`` or ``~/Desktop`` with that service active therefore sees
    directory mtimes move on its own; file mtimes are unaffected. Returns a
    one-line explanation when that applies, else None.
    """
    if sys.platform != "darwin":
        return None
    home = Path.home()
    try:
        resolved = root.resolve()
        under_synced_folder = any(
            resolved.is_relative_to(home / name) for name in ("Documents", "Desktop")
        )
    except OSError:
        return None
    if not under_synced_folder:
        return None
    try:
        completed = subprocess.run(
            ["/usr/bin/defaults", "read", "MobileMeAccounts"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if "CLOUDDESKTOP" not in completed.stdout:
        return None
    return (
        f"{resolved} is under iCloud Drive's Desktop & Documents sync, whose agent rewrites "
        "directory modification times after every change; directory-only findings are "
        "reported but cannot be attributed to the tests"
    )
