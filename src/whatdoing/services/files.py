"""File system operations — last modified file, directory scanning."""

from __future__ import annotations

import os
import time
from pathlib import Path

# Directories to skip when scanning for recently modified files
SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".next", "build",
    "dist", ".dart_tool", ".gradle", ".venv", "venv", ".tox",
    ".mypy_cache", ".pytest_cache",
}

SKIP_EXTENSIONS = {".pyc", ".pyo", ".DS_Store"}


def last_modified(code_path: str) -> str:
    """Find the most recently modified file in a directory.

    Returns: '2d ago  (filename.ext)' or '\u2014'
    """
    if not code_path:
        return "\u2014"

    path = Path(code_path)
    if not path.is_dir():
        return "\u2014"

    newest_time = 0.0
    newest_name = ""

    try:
        for root, dirs, files in os.walk(path):
            # Prune skipped directories in-place
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

            for fname in files:
                if Path(fname).suffix in SKIP_EXTENSIONS:
                    continue
                filepath = os.path.join(root, fname)
                try:
                    mtime = os.path.getmtime(filepath)
                    if mtime > newest_time:
                        newest_time = mtime
                        newest_name = fname
                except OSError:
                    continue
    except OSError:
        return "\u2014"

    if not newest_name:
        return "\u2014"

    ago = int(time.time() - newest_time)
    return f"{_relative_time(ago)}  ({newest_name})"


def _relative_time(seconds: int) -> str:
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        return f"{seconds // 60}m ago"
    if seconds < 86400:
        return f"{seconds // 3600}h ago"
    if seconds < 604800:
        return f"{seconds // 86400}d ago"
    if seconds < 2592000:
        return f"{seconds // 604800}w ago"
    return f"{seconds // 2592000}mo ago"
