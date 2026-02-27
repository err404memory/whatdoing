"""Docker container status checks — local or via SSH to a remote host.

Uses asyncio.create_subprocess_exec (safe, no shell injection)
with timeout handling for SSH connections.
"""

from __future__ import annotations

import asyncio
import os


def _docker_ssh_host() -> str:
    """Get the SSH host for remote docker checks.

    Set WHATDOING_DOCKER_HOST env var, or configure docker_host in config.yaml.
    Returns empty string if no remote host configured (local-only mode).
    """
    return os.environ.get("WHATDOING_DOCKER_HOST", "")


def _is_local_docker() -> bool:
    """Check if docker is available locally."""
    import shutil
    return shutil.which("docker") is not None


async def container_status(name: str, remote_host: str = "") -> str:
    """Get docker container status.

    If docker is available locally, runs docker directly.
    If a remote_host is configured, runs via SSH.

    Returns: 'container-name  Up 43 hours (healthy)' or em-dash
    """
    if not name:
        return "\u2014"

    host = remote_host or _docker_ssh_host()

    try:
        if not host and _is_local_docker():
            cmd = [
                "docker", "ps",
                "--filter", f"name=^{name}$",
                "--format", "{{.Names}}  {{.Status}}",
            ]
        elif host:
            # Build the docker command to run remotely
            remote_cmd = (
                f"docker ps --filter 'name=^{name}$' "
                "--format '{{.Names}}  {{.Status}}'"
            )
            cmd = ["ssh", "-o", "ConnectTimeout=3", host, remote_cmd]
        else:
            return "\u2014"

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
