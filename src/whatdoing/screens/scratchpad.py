"""Scratchpad screen — quick notes with auto-save."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Static, TextArea

from whatdoing.config import scratchpad_path

DEFAULT_SCRATCHPAD = """\
# Scratchpad

Quick notes and reminders.

## Install Notes


## Config Paths


## Commands to Remember


## Misc

"""


class ScratchpadScreen(Screen):
    """Quick notes editor with auto-save on exit."""

    BINDINGS = [
        Binding("escape", "go_back", "Back (auto-saves)", show=True),
        Binding("ctrl+s", "save", "Save", show=True),
    ]

    def compose(self) -> ComposeResult:
        yield Static(
            "[bold bright_white on rgb(40,40,60)]  Scratchpad [/]",
            id="scratch-header",
        )
        yield TextArea(id="scratch-editor")
        yield Footer()

    def on_mount(self) -> None:
        path = scratchpad_path()
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(DEFAULT_SCRATCHPAD)

        editor = self.query_one("#scratch-editor", TextArea)
        editor.load_text(path.read_text())
        editor.focus()

    def _save(self) -> None:
        editor = self.query_one("#scratch-editor", TextArea)
        path = scratchpad_path()
        path.write_text(editor.text)

    def action_save(self) -> None:
        self._save()
        self.notify("Saved")

    def action_go_back(self) -> None:
        self._save()
        self.app.pop_screen()
