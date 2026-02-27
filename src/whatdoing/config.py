"""Configuration loading and path resolution for whatdoing.

Handles cross-device path detection, config file loading, and first-run setup.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class Config:
    """Application configuration."""

    base_path: str = ""
    overview_dir: str = ""
    editor: str = ""
    docker_host: str = ""  # SSH host for remote docker checks (e.g., "myserver")
    status_presets: list[str] = field(default_factory=lambda: [
        "Active", "Paused", "Backlog", "IN PROGRESS",
        "BLOCKED", "STUCK", "READY", "RUNNING",
    ])
    priority_presets: list[str] = field(default_factory=lambda: [
        "High", "Medium", "Low",
    ])

    @property
    def projects_path(self) -> Path:
        return Path(self.base_path) / self.overview_dir

    @property
    def resolved_editor(self) -> str:
        editor = self.editor
        # Ignore bash-style expressions from v1 config (e.g., "${EDITOR:-nano}")
        if not editor or editor.startswith("$"):
            editor = ""
        # Default to micro. $EDITOR is a fallback if explicitly set to something real.
        if not editor:
            import shutil
            if shutil.which("micro"):
                return "micro"
            return os.environ.get("EDITOR", "nano")
        return editor


def whatdoing_home() -> Path:
    """Return the whatdoing home directory."""
    env = os.environ.get("WHATDOING_HOME")
    if env:
        return Path(env)
    return Path.home() / ".whatdoing"


def state_path() -> Path:
    return whatdoing_home() / "state.json"


def journal_dir() -> Path:
    d = whatdoing_home() / "journal"
    d.mkdir(parents=True, exist_ok=True)
    return d


def scratchpad_path() -> Path:
    return whatdoing_home() / "scratchpad.md"


def detect_base_path() -> str:
    """Auto-detect the project base path for the current machine.

    Checks common locations for a projects directory.
    Returns empty string if nothing found (triggers first-run setup).
    """
    candidates = [
        Path.home() / "server",
        Path.home() / "projects",
    ]
    for path in candidates:
        if path.is_dir():
            return str(path)
    return ""


def load_config() -> Config:
    """Load config from ~/.whatdoing/config.yaml, with auto-detection fallbacks."""
    config_file = whatdoing_home() / "config.yaml"
    cfg = Config()

    if config_file.exists():
        try:
            with open(config_file) as f:
                data = yaml.safe_load(f) or {}
        except Exception:
            data = {}

        cfg.base_path = data.get("base_path", "")
        cfg.overview_dir = data.get("overview_dir", cfg.overview_dir)
        cfg.editor = data.get("editor", "")
        cfg.docker_host = data.get("docker_host", "")

        if "status-presets" in data and isinstance(data["status-presets"], list):
            cfg.status_presets = data["status-presets"]
        if "priority-presets" in data and isinstance(data["priority-presets"], list):
            cfg.priority_presets = data["priority-presets"]

    if not cfg.base_path:
        cfg.base_path = detect_base_path()

    return cfg


def load_state() -> dict:
    """Load persisted app state (last project, etc.)."""
    sp = state_path()
    if sp.exists():
        try:
            return json.loads(sp.read_text())
        except Exception:
            return {}
    return {}


def save_state(state: dict) -> None:
    """Save app state to disk."""
    sp = state_path()
    sp.parent.mkdir(parents=True, exist_ok=True)
    sp.write_text(json.dumps(state, indent=2))
