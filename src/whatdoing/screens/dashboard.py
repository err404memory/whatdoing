"""Dashboard screen — main project list with color-coded table."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, Horizontal
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Input, Label, Static
from rich.text import Text

from whatdoing.config import load_config, load_state, save_state
from whatdoing.models import Project, scan_projects
from whatdoing.screens.project import ProjectScreen


class DashboardScreen(Screen):
    """Main screen showing all projects in a color-coded table."""

    BINDINGS = [
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("enter", "select_project", "Open", show=True),
        Binding("/", "focus_filter", "Filter", show=True),
        Binding("s", "open_scratchpad", "Scratch", show=True),
        Binding("l", "open_journal", "Journal", show=True),
        Binding("question_mark", "open_guide", "Help", show=True),
        Binding("q", "quit_app", "Quit", show=True),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.projects: list[Project] = []
        self.filtered_projects: list[Project] = []
        self.config = load_config()
        self._last_project = load_state().get("last_project", "")

    def compose(self) -> ComposeResult:
        yield Static("", id="dashboard-header")
        yield Input(placeholder="Type to filter projects...", id="filter-input")
        yield DataTable(id="project-table")
        yield Static("", id="dashboard-stats")
        yield Footer()

    def on_mount(self) -> None:
        self._load_projects()
        self._setup_table()
        self._populate_table()
        self._update_header()
        self.query_one("#project-table", DataTable).focus()

    def on_screen_resume(self) -> None:
        """Refresh project data when returning from another screen."""
        self._last_project = load_state().get("last_project", "")
        self._load_projects()
        self._populate_table()
        self.query_one("#project-table", DataTable).focus()

    def _load_projects(self) -> None:
        self.projects = scan_projects(self.config.projects_path)
        self.filtered_projects = list(self.projects)

    def _setup_table(self) -> None:
        table = self.query_one("#project-table", DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True

        table.add_columns(
            "STATUS", "PRI", "PROJECT", "TYPE", "NEXT ACTION",
        )

    def _populate_table(self, filter_text: str = "") -> None:
        table = self.query_one("#project-table", DataTable)
        table.clear()

        if filter_text:
            ft = filter_text.lower()
            self.filtered_projects = [
                p for p in self.projects
                if ft in p.name.lower() or ft in p.next_action.lower()
                or ft in p.status.lower() or ft in p.project_type.lower()
            ]
        else:
            self.filtered_projects = list(self.projects)

        highlight_row = None
        for i, project in enumerate(self.filtered_projects):
            if not project.has_overview:
                # Dimmed row for projects without _OVERVIEW.md
                table.add_row(
                    Text("\u2014", style="dim"),
                    Text("\u2014", style="dim"),
                    Text(project.name, style="dim italic"),
                    Text("\u2014", style="dim"),
                    Text("[no overview]", style="dim italic"),
                )
            else:
                status_text = Text(project.status, style=f"bold {project.status_color}")
                pri_text = Text(project.priority, style=project.priority_color)
                name_text = Text(project.name)
                type_text = Text(project.project_type, style="dim")

                # Truncate next action to reasonable length
                na = project.next_action
                if len(na) > 40:
                    na = na[:39] + "\u2026"
                action_text = Text(na)

                table.add_row(status_text, pri_text, name_text, type_text, action_text)

            if project.name == self._last_project:
                highlight_row = i

        # Highlight last-viewed project
        if highlight_row is not None and highlight_row < len(self.filtered_projects):
            table.move_cursor(row=highlight_row)

        self._update_stats()

    def _update_header(self) -> None:
        header = self.query_one("#dashboard-header", Static)
        header.update(
            "[bold bright_white on rgb(40,40,60)]"
            "  \u2588\u2588 whatdoing "
            "[/]"
        )

    def _update_stats(self) -> None:
        stats = self.query_one("#dashboard-stats", Static)
        total = len(self.projects)
        active = sum(1 for p in self.projects if p.status.lower() in ("active", "in progress", "running"))
        blocked = sum(1 for p in self.projects if p.status.lower() in ("blocked", "stuck"))
        paused = sum(1 for p in self.projects if p.status.lower() == "paused")
        no_overview = sum(1 for p in self.projects if not p.has_overview)

        stats.update(
            f"[dim]{total} projects[/]  "
            f"[green]{active} active[/]  "
            f"[red]{blocked} blocked[/]  "
            f"[yellow]{paused} paused[/]  "
            f"[dim italic]{no_overview} missing overview[/]"
        )

    # -- Actions --

    def action_select_project(self) -> None:
        table = self.query_one("#project-table", DataTable)
        if table.cursor_row is not None and table.cursor_row < len(self.filtered_projects):
            project = self.filtered_projects[table.cursor_row]
            # Save as last-viewed
            save_state({"last_project": project.name})
            self.app.push_screen(ProjectScreen(project=project))

    def action_cursor_down(self) -> None:
        self.query_one("#project-table", DataTable).action_cursor_down()

    def action_cursor_up(self) -> None:
        self.query_one("#project-table", DataTable).action_cursor_up()

    def action_focus_filter(self) -> None:
        self.query_one("#filter-input", Input).focus()

    def action_open_scratchpad(self) -> None:
        self.app.push_screen("scratchpad")

    def action_open_journal(self) -> None:
        self.app.push_screen("journal")

    def action_open_guide(self) -> None:
        self.app.push_screen("guide")

    def action_quit_app(self) -> None:
        self.app.exit()

    # -- Event handlers --

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "filter-input":
            self._populate_table(event.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "filter-input":
            # Return focus to table after filtering
            self.query_one("#project-table", DataTable).focus()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self.action_select_project()
