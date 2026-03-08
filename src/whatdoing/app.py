"""whatdoing — terminal dashboard for tracking what you're working on.

Main entry point. Launches the Textual TUI app.
"""

from __future__ import annotations

import argparse
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
        if hasattr(self, "config"):  # guard for edge cases during init
            colors = build_theme_colors(self.config.theme)
            variables["background"] = colors.get(
                "bg-color", variables.get("background", "")
            )
            variables["surface"] = colors.get("surface", variables.get("surface", ""))
            variables["primary"] = colors.get("primary", variables.get("primary", ""))
            variables["secondary"] = colors.get(
                "secondary", variables.get("secondary", "")
            )
            variables["accent"] = colors.get("accent", variables.get("accent", ""))
        return variables

    def compose(self) -> ComposeResult:
        """Compose the main app. Optionally adds background image."""
        bg_image = self.config.theme.get("background-image", "")
        if bg_image:
            if Path(bg_image).exists():
                try:
                    from textual_image.widget import Image

                    yield Image(bg_image, id="bg-image")
                except ImportError:
                    pass  # textual-image not installed, skip gracefully

    def __init__(self, config: Config | None = None, target: str = "") -> None:
        self.config = config or load_config()
        self._target = target
        super().__init__()

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
    args = parse_args()

    if args.version:
        from whatdoing import __version__

        print(f"whatdoing {__version__}")
        return

    config = load_config()

    # Check if projects path exists
    if not config.projects_path.exists():
        print(f"Warning: Projects directory not found: {config.projects_path}")
        print(f"Base path: {config.base_path}")
        print(f"Run 'whatdoing guide' for setup help.")
        # Still launch — guide screen will help

    app = WhatDoingApp(config=config, target=args.target)
    app.run()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI args for command/project targets."""
    parser = argparse.ArgumentParser(
        prog="whatdoing",
        description="terminal dashboard for tracking what you're working on",
    )
    parser.add_argument("target", nargs="?", default="", help="command or project name")
    parser.add_argument("--version", action="store_true", help="show version")

    args, extras = parser.parse_known_args(argv)
    if not args.target and extras:
        args.target = extras[0]
    return args


if __name__ == "__main__":
    main()
