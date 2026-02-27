"""Dashboard screen — main project list with color-coded table."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen, ModalScreen
from textual.widgets import Button, Checkbox, DataTable, Footer, Input, Label, Static
from rich.text import Text

from whatdoing.config import load_config, load_state, save_state, save_config
from whatdoing.models import Project, scan_projects
from whatdoing.screens.project import ProjectScreen


CORE_COLUMNS = {"status", "priority", "project"}

COLUMN_LABELS = {
    "status": "STATUS",
    "priority": "PRI",
    "project": "PROJECT",
    "type": "TYPE",
    "next_action": "NEXT ACTION",
    "energy_required": "ENERGY",
    "time_estimate": "TIME",
    "tags": "TAGS",
}


class ColumnPickerScreen(ModalScreen):
    """Modal screen for choosing which columns appear on the dashboard."""

    BINDINGS = [
        Binding("escape", "close", "Close", show=True),
    ]

    DEFAULT_CSS = """
    ColumnPickerScreen {
        align: center middle;
    }
    #column-picker-container {
        width: 50;
        max-height: 80%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }
    #column-picker-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }
    """

    def __init__(self, available_columns: list[str], active_columns: list[str], config) -> None:
        super().__init__()
        self.available_columns = available_columns
        self.active_columns = active_columns
        self.config = config

    def compose(self) -> ComposeResult:
        with Vertical(id="column-picker-container"):
            yield Label("Dashboard Columns", id="column-picker-title")
            with VerticalScroll():
                for col_key in self.available_columns:
                    is_core = col_key in CORE_COLUMNS
                    is_active = col_key in self.active_columns
                    label = COLUMN_LABELS.get(col_key, col_key.replace("_", " ").title())
                    if col_key.startswith("## "):
                        label = f"[section] {col_key[3:]}"
                    if is_core:
                        label = f"{label} (core)"
                    yield Checkbox(
                        label,
                        value=is_active or is_core,
                        disabled=is_core,
                        id=f"col-{col_key.replace(' ', '_').replace('#', 'h')}",
                        name=col_key,
                    )

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        col_key = event.checkbox.name
        if col_key in CORE_COLUMNS:
            return

        if event.value and col_key not in self.config.dashboard_columns:
            self.config.dashboard_columns.append(col_key)
        elif not event.value and col_key in self.config.dashboard_columns:
            self.config.dashboard_columns.remove(col_key)

        save_config(self.config)

    def action_close(self) -> None:
        self.dismiss()


class DashboardScreen(Screen):
    """Main screen showing all projects in a color-coded table."""

    BINDINGS = [
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("enter", "select_project", "Open", show=True),
        Binding("/", "focus_filter", "Filter", show=True),
        Binding("s", "open_scratchpad", "Scratch", show=True),
        Binding("l", "open_journal", "Journal", show=True),
        Binding("c", "edit_columns", "Columns", show=True),
        Binding("question_mark", "open_guide", "Help", show=True),
        Binding("q", "quit_app", "Quit", show=True),
        Binding("t", "cycle_theme", "Theme", show=True),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.projects: list[Project] = []
        self.filtered_projects: list[Project] = []
        self.config = load_config()
        self._last_project = load_state().get("last_project", "")

    def compose(self) -> ComposeResult:
        yield Static("", id="dashboard-header")
        with Horizontal(id="button-bar"):
            for item in self.config.buttons.get("items", []):
                if item.get("context"):
                    continue  # Context buttons added dynamically
                yield Button(item["label"], id=f"btn-{item['action']}", classes="bar-button")
        yield Input(placeholder="Type to filter projects...", id="filter-input")
        yield DataTable(id="project-table")
        with Horizontal(id="context-bar"):
            pass
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
        self.config = load_config()
        self._load_projects()
        table = self.query_one("#project-table", DataTable)
        table.clear(columns=True)
        self._setup_table()
        self._populate_table()
        table.focus()

    def _load_projects(self) -> None:
        self.projects = scan_projects(self.config.projects_path)
        self.filtered_projects = list(self.projects)

    def _setup_table(self) -> None:
        table = self.query_one("#project-table", DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True

        for col_key in self.config.dashboard_columns:
            if col_key.startswith("## "):
                label = col_key[3:]
            else:
                label = COLUMN_LABELS.get(col_key, col_key.replace("_", " ").title())
            table.add_column(label, key=col_key)

    def _get_cell_value(self, project: Project, col_key: str) -> Text:
        """Return a styled Text object for any column key."""
        if not project.has_overview:
            if col_key == "project":
                return Text(project.name, style="dim italic")
            return Text("—", style="dim")

        if col_key == "status":
            return Text(project.status, style=f"bold {project.status_color}")
        elif col_key == "priority":
            return Text(project.priority, style=project.priority_color)
        elif col_key == "project":
            return Text(project.name)
        elif col_key == "next_action":
            na = project.next_action
            if len(na) > 40:
                na = na[:39] + "\u2026"
            return Text(na)
        elif col_key == "type":
            return Text(project.project_type, style="dim")
        elif col_key == "tags":
            return Text(", ".join(project.tags) if project.tags else "—", style="dim")
        elif col_key.startswith("## "):
            heading = col_key[3:]
            if project.doc:
                content = project.doc.get_section(heading)
                if content:
                    content = content.strip().split("\n")[0][:30]
                    return Text(content)
            return Text("—", style="dim")
        else:
            # Try frontmatter lookup: as-is, then title-cased
            if project.doc:
                val = project.doc.frontmatter.get(col_key, "")
                if not val:
                    val = project.doc.frontmatter.get(col_key.title(), "")
                if not val:
                    # Try with underscores converted to title case
                    title_key = col_key.replace("_", " ").title().replace(" ", "_")
                    val = project.doc.frontmatter.get(title_key, "")
                if val:
                    if isinstance(val, list):
                        return Text(", ".join(str(v) for v in val), style="dim")
                    return Text(str(val).strip(), style="dim")
            return Text("—", style="dim")

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

        columns = self.config.dashboard_columns
        highlight_row = None
        for i, project in enumerate(self.filtered_projects):
            row = [self._get_cell_value(project, col_key) for col_key in columns]
            table.add_row(*row)

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

    def action_edit_columns(self) -> None:
        """Open the column picker modal."""
        # Build available columns from known labels + frontmatter/sections across all projects
        available = list(COLUMN_LABELS.keys())

        for project in self.projects:
            if project.doc:
                # Add frontmatter keys
                for key in project.doc.frontmatter:
                    normalized = key.lower().replace(" ", "_")
                    if normalized not in available and normalized not in COLUMN_LABELS:
                        available.append(normalized)
                # Add section headings
                for heading in project.doc.sections:
                    section_key = f"## {heading}"
                    if section_key not in available:
                        available.append(section_key)

        self.app.push_screen(
            ColumnPickerScreen(available, list(self.config.dashboard_columns), self.config)
        )

    def action_quit_app(self) -> None:
        self.app.exit()

    def action_cycle_theme(self) -> None:
        """Cycle through available themes."""
        from whatdoing.themes import PRESETS
        names = list(PRESETS.keys())
        current = self.app.config.theme.get("name", "default")
        try:
            idx = names.index(current)
        except ValueError:
            idx = 0
        next_name = names[(idx + 1) % len(names)]
        self.app.config.theme["name"] = next_name
        save_config(self.app.config)
        self.app.refresh_css()
        self.notify(f"Theme: {next_name}")

    # -- Event handlers --

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        action = btn_id.replace("btn-", "", 1)

        if action.startswith("screen:"):
            screen_name = action.split(":", 1)[1]
            self.app.push_screen(screen_name)
        elif action == "new_project":
            self.notify("Use 'a' in any project to add sections, or create a directory in your projects folder")
        elif action.startswith("open_url:"):
            import webbrowser
            key = action.split(":", 1)[1]
            table = self.query_one("#project-table", DataTable)
            if table.cursor_row is not None and table.cursor_row < len(self.filtered_projects):
                project = self.filtered_projects[table.cursor_row]
                if project.doc:
                    url = project.doc.get(key, "")
                    if url:
                        webbrowser.open(url)
                        self.notify(f"Opened {key}")
                    else:
                        self.notify(f"No {key} for this project", severity="warning")

    def on_data_table_cursor_changed(self, event) -> None:
        """Update context buttons when cursor moves."""
        context_bar = self.query_one("#context-bar", Horizontal)
        context_bar.remove_children()

        table = self.query_one("#project-table", DataTable)
        if table.cursor_row is not None and table.cursor_row < len(self.filtered_projects):
            project = self.filtered_projects[table.cursor_row]
            if project.doc:
                for item in self.config.buttons.get("items", []):
                    if not item.get("context"):
                        continue
                    action = item.get("action", "")
                    key = action.split(":", 1)[1] if ":" in action else ""
                    val = project.doc.get(key, "")
                    if val:
                        btn = Button(item["label"], id=f"btn-{action}", classes="ctx-button")
                        context_bar.mount(btn)

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "filter-input":
            self._populate_table(event.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "filter-input":
            # Return focus to table after filtering
            self.query_one("#project-table", DataTable).focus()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self.action_select_project()
