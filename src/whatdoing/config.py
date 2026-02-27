"""Configuration loading and path resolution for whatdoing.

Handles cross-device path detection (satellite rclone mount vs jeffrey direct),
config file loading, and first-run setup.
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
    overview_dir: str = "v1/dev-system/04 projects"
    editor: str = ""
    status_presets: list[str] = field(default_factory=lambda: [
        "Active", "Paused", "Backlog", "IN PROGRESS",
        "BLOCKED", "STUCK", "READY", "RUNNING",
    ])
    priority_presets: list[str] = field(default_factory=lambda: [
        "High", "Medium", "Low",
    ])

    @property
    def projects_path(self) -> Path:
        """Returns the path to the projects directory."""
        return Path(self.base_path) / self.overview_dir

    @property
    def resolved_editor(self) -> str:
        """Retrieve the resolved editor for the current environment.
        
        This property checks the value of the editor attribute. If the editor is not
        set  or starts with a dollar sign, it is ignored. The function then attempts to
        return  "micro" if it is available on the system. If "micro" is not found, it
        falls back  to the value of the EDITOR environment variable, defaulting to
        "nano" if neither  is set.
        """
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
    """Return the path to the state.json file."""
    return whatdoing_home() / "state.json"


def journal_dir() -> Path:
    """Create and return the path to the journal directory."""
    d = whatdoing_home() / "journal"
    d.mkdir(parents=True, exist_ok=True)
    return d


def scratchpad_path() -> Path:
    """Return the path to the scratchpad file."""
    return whatdoing_home() / "scratchpad.md"


def detect_base_path() -> str:
    """Auto-detect the project base path for the current machine."""
    candidates = [
        Path("/home/ash/server"),       # satellite (laptop, rclone mount)
        Path("/home/ashes"),            # jeffrey (server, direct)
        Path.home() / "server",         # generic fallback
    ]
    for path in candidates:
        if (path / "homelab").is_dir() or (path / "v1").is_dir():
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
