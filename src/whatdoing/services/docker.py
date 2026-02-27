"""Docker container status checks — local or via SSH to jeffrey.

Uses asyncio.create_subprocess_exec (safe, no shell injection)
with timeout handling for SSH connections.
"""

from __future__ import annotations

import asyncio
import socket


def _is_jeffrey() -> bool:
    """Check if we're running directly on jeffrey."""
    try:
        return socket.gethostname() == "jeffrey"
    except Exception:
        return False


async def container_status(name: str) -> str:
    """Get docker container status.

    If on jeffrey, runs docker directly.
    Otherwise, runs via ssh jeffrey.

    Returns: 'container-name  Up 43 hours (healthy)' or em-dash
    """
    if not name:
        return "\u2014"

    try:
        if _is_jeffrey():
            cmd = [
                "docker", "ps",
                "--filter", f"name=^{name}$",
                "--format", "{{.Names}}  {{.Status}}",
            ]
        else:
            # Build the docker command to run remotely
            remote_cmd = (
                f"docker ps --filter 'name=^{name}$' "
                "--format '{{.Names}}  {{.Status}}'"
            )
            cmd = ["ssh", "-o", "ConnectTimeout=3", "jeffrey", remote_cmd]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)

        if proc.returncode == 0 and stdout:
            return stdout.decode().strip()
    except (asyncio.TimeoutError, FileNotFoundError, Exception):
        pass

    return "\u2014"
