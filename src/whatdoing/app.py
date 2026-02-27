"""whatdoing — terminal dashboard for tracking what you're working on.

Main entry point. Launches the Textual TUI app.
"""

from __future__ import annotations

import sys
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding

from whatdoing.config import load_config, Config
from whatdoing.models import resolve_project
from whatdoing.themes import build_theme_colors
from whatdoing.screens.dashboard import DashboardScreen
from whatdoing.screens.project import ProjectScreen
from whatdoing.screens.scratchpad import ScratchpadScreen
from whatdoing.screens.journal import JournalScreen
from whatdoing.screens.guide import GuideScreen


class WhatDoingApp(App):
    """The main whatdoing application."""

    TITLE = "whatdoing"
    CSS_PATH = "app.tcss"

    BINDINGS = [
        Binding("ctrl+n", "quick_capture", "Quick Note", show=False, priority=True),
    ]

    def get_css_variables(self) -> dict[str, str]:
        """Override CSS variables with theme colors."""
        variables = super().get_css_variables()
        # get_css_variables is called during super().__init__(), before
        # self.config is assigned — fall back to defaults in that case.
        if hasattr(self, "config"):
            colors = build_theme_colors(self.config.theme)
            variables["background"] = colors.get("bg-color", variables.get("background", ""))
            variables["surface"] = colors.get("surface", variables.get("surface", ""))
            variables["primary"] = colors.get("primary", variables.get("primary", ""))
            variables["secondary"] = colors.get("secondary", variables.get("secondary", ""))
            variables["accent"] = colors.get("accent", variables.get("accent", ""))
        return variables

    def __init__(self, config: Config | None = None, target: str = "") -> None:
        super().__init__()
        self.config = config or load_config()
        self._target = target

    def on_mount(self) -> None:
        # Install named screens for navigation
        self.install_screen(ScratchpadScreen(), name="scratchpad")
        self.install_screen(JournalScreen(), name="journal")
        self.install_screen(GuideScreen(), name="guide")

        if self._target == "scratch":
            self.push_screen("scratchpad")
        elif self._target == "journal":
            self.push_screen("journal")
        elif self._target == "guide":
            self.push_screen("guide")
        elif self._target:
            # Direct project target
            project = resolve_project(self.config.projects_path, self._target)
            if project:
                self.push_screen(ProjectScreen(project=project))
            else:
                self.notify(f"Project '{self._target}' not found", severity="error")
                self.push_screen(DashboardScreen())
        else:
            self.push_screen(DashboardScreen())

    def action_quick_capture(self) -> None:
        """Quick note capture from any screen."""
        self.push_screen("scratchpad")


def main() -> None:
    """CLI entry point."""
    config = load_config()

    # Check if projects path exists
    if not config.projects_path.exists():
        print(f"Warning: Projects directory not found: {config.projects_path}")
        print(f"Base path: {config.base_path}")
        print(f"Run 'whatdoing guide' for setup help.")
        # Still launch — guide screen will help

    target = sys.argv[1] if len(sys.argv) > 1 else ""

    if target == "--help":
        print("whatdoing — terminal dashboard for tracking what you're working on")
        print()
        print("Usage: whatdoing [command|project-name]")
        print()
        print("Commands:")
        print("  (no args)     Dashboard — show all projects")
        print("  <name>        Jump to a project (fuzzy match)")
        print("  scratch       Open scratchpad")
        print("  journal       Open journal")
        print("  guide         User guide")
        print("  --help        This message")
        print("  --version     Show version")
        return

    if target == "--version":
        from whatdoing import __version__
        print(f"whatdoing {__version__}")
        return

    app = WhatDoingApp(config=config, target=target)
    app.run()


if __name__ == "__main__":
    main()
