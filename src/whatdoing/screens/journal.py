"""Journal screen — view and search work log entries."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Input, Static

from whatdoing.services.journal import recent_entries, search_journal


class JournalScreen(Screen):
    """View recent journal entries with search."""

    BINDINGS = [
        Binding("escape", "go_back", "Back", show=True),
        Binding("/", "focus_search", "Search", show=True),
    ]

    def compose(self) -> ComposeResult:
        yield Static(
            "[bold bright_white on rgb(40,40,60)]  Journal [/]",
            id="journal-header",
        )
        yield Input(placeholder="Search journal entries...", id="journal-search")
        with VerticalScroll(id="journal-entries"):
            yield Static("", id="journal-content")
        yield Footer()

    def on_mount(self) -> None:
        self._render_entries(recent_entries())
        self.query_one("#journal-entries").focus()

    def on_screen_resume(self) -> None:
        """Refresh entries when returning to this screen."""
        self._render_entries(recent_entries())
        self.query_one("#journal-search", Input).value = ""

    def _render_entries(self, entries: list[dict]) -> None:
        content = self.query_one("#journal-content", Static)
        if not entries:
            content.update("[dim italic]No journal entries yet. Use [bold]w[/bold] in project view to log work.[/]")
            return

        lines = []
        current_date = ""
        for entry in entries:
            if entry["date"] != current_date:
                current_date = entry["date"]
                lines.append(f"\n[bold dim]\u2500\u2500 {current_date} \u2500\u2500[/]")

            lines.append(
                f"  [bold cyan]{entry['time']}[/]  "
                f"[bold]{entry['project']}[/]\n"
                f"  [dim]{entry['note']}[/]"
            )

        content.update("\n".join(lines))

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_focus_search(self) -> None:
        self.query_one("#journal-search", Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "journal-search":
            query = event.value.strip()
            if query:
                self._render_entries(search_journal(query))
            else:
                self._render_entries(recent_entries())

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.query_one("#journal-entries").focus()
