"""Git operations for live data display.

Uses asyncio.create_subprocess_exec (safe, no shell injection)
to fetch git info without blocking the TUI.
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path


def _relative_time(seconds: int) -> str:
    """Convert seconds-ago to human-readable string."""
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


async def recent_activity(code_path: str) -> str:
    """Get the most recent git commit with relative time.

    Returns: 'abc1234 commit message (2d ago)' or 'no repo' or 'no commits'
    """
    if not code_path:
        return "\u2014"

    path = Path(code_path)
    if not (path / ".git").is_dir():
        return "no repo"

    try:
        proc = await asyncio.create_subprocess_exec(
            "git", "-C", str(path), "log", "--oneline", "-1",
            "--format=%h %s%n%ct",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await proc.communicate()
        if proc.returncode != 0 or not stdout:
            return "no commits"

        lines = stdout.decode().strip().split("\n")
        if len(lines) < 2:
            return "no commits"

        summary = lines[0]
        try:
            epoch = int(lines[1])
            ago = int(time.time()) - epoch
            return f"{summary}  ({_relative_time(ago)})"
        except (ValueError, IndexError):
            return summary

    except FileNotFoundError:
        return "git not found"
    except Exception:
        return "\u2014"


async def branch_name(code_path: str) -> str:
    """Get current git branch name."""
    if not code_path:
        return ""

    try:
        proc = await asyncio.create_subprocess_exec(
            "git", "-C", code_path, "rev-parse", "--abbrev-ref", "HEAD",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await proc.communicate()
        if proc.returncode == 0 and stdout:
            return stdout.decode().strip()
    except Exception:
        pass
    return ""
