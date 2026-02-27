"""Project drill-in screen — full view with overview, live data, and actions.

Interaction model:
- Status, priority, and next action are clickable inline-editable fields
- Select widget for status/priority (dropdown-style, only active when editing)
- Input widget for free-text fields (next action, work log)
- 'e' opens the full file in micro (suspends TUI, resumes after)
- Projects without _OVERVIEW.md offer to create one
"""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll, Horizontal
from textual.message import Message
from textual.screen import Screen
from textual.widgets import (
    Footer, Label, Markdown, Static, Input, Select, Button,
)
from rich.text import Text

from whatdoing.models import Project
from whatdoing.parser import parse_document
from whatdoing.services import git, docker, files
from whatdoing.services.journal import log_work


STATUS_OPTIONS = [
    ("Active", "Active"),
    ("Paused", "Paused"),
    ("Backlog", "Backlog"),
    ("IN PROGRESS", "IN PROGRESS"),
    ("BLOCKED", "BLOCKED"),
    ("STUCK", "STUCK"),
    ("READY", "READY"),
    ("RUNNING", "RUNNING"),
]

PRIORITY_OPTIONS = [
    ("High", "High"),
    ("Medium", "Medium"),
    ("Low", "Low"),
]

OVERVIEW_TEMPLATE = """\
---
Status: Backlog
Priority: Low
Type:
Next_action:
Energy_required:
Time_estimate:
code_path:
docker_name:
Tags:
---

# {name}

## What is this?


## Blockers

None
"""


class ClickableField(Static):
    """A label that can be clicked to trigger editing."""

    class Clicked(Message):
        def __init__(self, field_id: str) -> None:
            super().__init__()
            self.field_id = field_id

    def __init__(self, *args, field_id: str = "", **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.field_id = field_id
        self.can_focus = True

    def on_click(self) -> None:
        self.post_message(self.Clicked(self.field_id))

    def on_key(self, event) -> None:
        if event.key == "enter":
            self.post_message(self.Clicked(self.field_id))
            event.stop()


class ProjectScreen(Screen):
    """Full drill-in view for a single project."""

    BINDINGS = [
        Binding("b", "go_back", "Back", show=True),
        Binding("escape", "cancel_or_back", "Back", show=False),
        Binding("e", "edit_file", "Edit File", show=True),
        Binding("u", "edit_status", "Status", show=True),
        Binding("p", "edit_priority", "Priority", show=True),
        Binding("n", "edit_next", "Next", show=True),
        Binding("w", "log_work", "Log Work", show=True),
        Binding("s", "open_scratchpad", "Scratch", show=True),
        Binding("l", "open_journal", "Journal", show=True),
        Binding("question_mark", "open_guide", "Help", show=True),
        Binding("q", "quit_app", "Quit", show=True),
    ]

    def __init__(self, project: Project | None = None) -> None:
        super().__init__()
        self.project = project
        self._editing: str = ""  # Which field is being edited ("status", "priority", etc.)

    def compose(self) -> ComposeResult:
        yield Static("", id="project-header")

        # Inline-editable status bar
        with Horizontal(id="status-row"):
            yield ClickableField("", field_id="status", id="field-status")
            yield ClickableField("", field_id="priority", id="field-priority")
            yield Static("", id="field-type")
            yield Static("", id="field-meta")

        # Inline editors (hidden, only shown when _editing is set)
        yield Select(STATUS_OPTIONS, id="select-status", allow_blank=False)
        yield Select(PRIORITY_OPTIONS, id="select-priority", allow_blank=False)

        # Clickable next action
        yield ClickableField("", field_id="next_action", id="field-next")
        yield Input(placeholder="New next action...", id="input-next")

        with VerticalScroll(id="project-body"):
            yield Static("", id="project-blockers")
            yield Markdown("", id="project-content")
            yield Static("", id="project-extra")

            # Live data panel
            yield Static("", id="live-header")
            yield Static("", id="live-modified")
            yield Static("", id="live-git")
            yield Static("", id="live-docker")

        # Work log input
        yield Input(placeholder="What did you work on?...", id="input-worklog")
        yield Footer()

    def on_mount(self) -> None:
        # CRITICAL: Hide ALL inline editors before anything else
        # This prevents Select.Changed from firing with default values
        self.query_one("#select-status", Select).display = False
        self.query_one("#select-priority", Select).display = False
        self.query_one("#input-next", Input).display = False
        self.query_one("#input-worklog", Input).display = False

        if self.project and self.project.has_overview:
            self._render_project()
            self._fetch_live_data()
        elif self.project and not self.project.has_overview:
            self._render_empty_project()

    def _render_empty_project(self) -> None:
        """Render a project that has no _OVERVIEW.md file."""
        self.query_one("#project-header", Static).update(
            f"[bold bright_white on rgb(40,40,60)]"
            f"  {self.project.name} "
            f"[/]"
        )
        self.query_one("#field-status", ClickableField).update(
            "  [dim italic]no overview file[/]"
        )
        self.query_one("#field-priority", ClickableField).update("")
        self.query_one("#field-type", Static).update("")
        self.query_one("#field-meta", Static).update("")
        self.query_one("#field-next", ClickableField).update("")
        self.query_one("#project-blockers", Static).display = False

        self.query_one("#project-content", Markdown).update(
            f"## No `_OVERVIEW.md` found\n\n"
            f"This project directory exists but has no overview file.\n\n"
            f"Press **e** to create one and open it in your editor."
        )

    def _render_project(self) -> None:
        p = self.project
        if not p or not p.doc:
            return

        # Header
        self.query_one("#project-header", Static).update(
            f"[bold bright_white on rgb(40,40,60)]"
            f"  {p.title or p.name} "
            f"[/]"
        )

        # Clickable status
        self.query_one("#field-status", ClickableField).update(
            f"  [bold {p.status_color}]{p.status}[/] [dim]\u270e[/]"
        )

        # Clickable priority
        self.query_one("#field-priority", ClickableField).update(
            f"  [{p.priority_color}]{p.priority}[/] [dim]\u270e[/]"
        )

        # Type
        type_w = self.query_one("#field-type", Static)
        type_w.update(f"  [dim]{p.project_type}[/]" if p.project_type else "")

        # Meta
        meta_parts = []
        if p.time_estimate:
            meta_parts.append(f"[bold]Time:[/] {p.time_estimate}")
        if p.energy:
            meta_parts.append(f"[dim]Energy:[/] {p.energy}")
        self.query_one("#field-meta", Static).update(
            "  " + "  ".join(meta_parts) if meta_parts else ""
        )

        # Clickable next action
        na = p.next_action or "[dim italic]no next action set[/]"
        self.query_one("#field-next", ClickableField).update(
            f"  [cyan]Next:[/] {na} [dim]\u270e[/]"
        )

        # Blockers
        blockers_widget = self.query_one("#project-blockers", Static)
        blockers = p.doc.get_section("Blockers")
        trimmed = blockers.strip() if blockers else ""
        if trimmed and not trimmed.lower().startswith("none"):
            blockers_widget.update(
                f"[bold red]  BLOCKERS[/]\n"
                f"[red]  {trimmed}[/]"
            )
            blockers_widget.display = True
        else:
            blockers_widget.display = False

        # Body (minus Blockers and title)
        body_text = p.doc.body_without("Blockers")
        body_lines = body_text.split("\n")
        body_lines = [ln for ln in body_lines if not (ln.startswith("# ") and not ln.startswith("## "))]
        body_text = "\n".join(body_lines).strip()

        # Merge PROJECT.md
        extra_widget = self.query_one("#project-extra", Static)
        extra_widget.update("")
        if p.code_path:
            project_md = Path(p.code_path) / "PROJECT.md"
            if project_md.exists():
                secondary = parse_document(project_md)
                primary_headings = set(p.doc.sections.keys())
                extra_sections = []
                for heading, content in secondary.sections.items():
                    if heading not in primary_headings and content.strip():
                        extra_sections.append(f"## {heading}\n{content}")
                if extra_sections:
                    extra_widget.update("[dim]\u2500\u2500 from PROJECT.md \u2500\u2500[/]")
                    body_text += "\n\n" + "\n\n".join(extra_sections)

        self.query_one("#project-content", Markdown).update(body_text)

    def _fetch_live_data(self) -> None:
        if not self.project:
            return

        code = self.project.code_path
        docker_name = self.project.docker_name or self.project.name

        self.query_one("#live-header", Static).update(
            "\n[dim]\u2500\u2500\u2500\u2500\u2500 [/][bold] Live [/][dim]\u2500\u2500\u2500\u2500\u2500[/]\n"
        )
        self.query_one("#live-modified", Static).update("  [bold white]LAST MODIFIED[/]   loading...")
        self.query_one("#live-git", Static).update("  [bold white]GIT[/]             loading...")
        self.query_one("#live-docker", Static).update("  [bold white]DOCKER[/]          loading...")

        self.run_worker(self._load_live_data(code, docker_name))

    async def _load_live_data(self, code_path: str, docker_name: str) -> None:
        mod_info = await asyncio.to_thread(files.last_modified, code_path)
        self.query_one("#live-modified", Static).update(
            f"  [bold white]LAST MODIFIED[/]   {mod_info}"
        )

        git_info = await git.recent_activity(code_path)
        self.query_one("#live-git", Static).update(
            f"  [bold white]GIT[/]             {git_info}"
        )

        dock_info = await docker.container_status(docker_name)
        self.query_one("#live-docker", Static).update(
            f"  [bold white]DOCKER[/]          {dock_info}"
        )

    # -- Inline editing --

    def _show_editor(self, field: str) -> None:
        """Show the appropriate inline editor for a field."""
        self._editing = field

        if field == "status":
            sel = self.query_one("#select-status", Select)
            # Set value BEFORE showing to prevent spurious Changed events
            if self.project and self.project.status:
                sel.value = self.project.status
            sel.display = True
            sel.focus()

        elif field == "priority":
            sel = self.query_one("#select-priority", Select)
            if self.project and self.project.priority:
                sel.value = self.project.priority
            sel.display = True
            sel.focus()

        elif field == "next_action":
            inp = self.query_one("#input-next", Input)
            inp.value = self.project.next_action if self.project else ""
            inp.display = True
            inp.focus()

        elif field == "log_work":
            inp = self.query_one("#input-worklog", Input)
            inp.value = ""
            inp.display = True
            inp.focus()

    def _hide_editors(self) -> None:
        """Hide all inline editors."""
        self._editing = ""
        self.query_one("#select-status", Select).display = False
        self.query_one("#select-priority", Select).display = False
        self.query_one("#input-next", Input).display = False
        self.query_one("#input-worklog", Input).display = False

    # -- Actions --

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_cancel_or_back(self) -> None:
        if self._editing:
            self._hide_editors()
        else:
            self.app.pop_screen()

    def action_edit_file(self) -> None:
        """Open the overview file in micro, suspending the TUI."""
        if not self.project:
            return

        overview = self.project.dir_path / "_OVERVIEW.md"

        # Create overview if it doesn't exist
        if not overview.exists():
            overview.write_text(OVERVIEW_TEMPLATE.format(name=self.project.name))
            self.notify("Created _OVERVIEW.md")

        editor = self.app.config.resolved_editor

        # Suspend the TUI, run editor, resume
        with self.app.suspend():
            subprocess.run([editor, str(overview)])

        # Reload project data after editing
        self.project = Project.from_directory(self.project.dir_path)
        if self.project.has_overview:
            self._render_project()
            self._fetch_live_data()
        self.notify("File reloaded")

    def action_edit_status(self) -> None:
        if self.project and self.project.has_overview:
            self._show_editor("status")

    def action_edit_priority(self) -> None:
        if self.project and self.project.has_overview:
            self._show_editor("priority")

    def action_edit_next(self) -> None:
        if self.project and self.project.has_overview:
            self._show_editor("next_action")

    def action_log_work(self) -> None:
        if self.project:
            self._show_editor("log_work")

    def action_open_scratchpad(self) -> None:
        self.app.push_screen("scratchpad")

    def action_open_journal(self) -> None:
        self.app.push_screen("journal")

    def action_open_guide(self) -> None:
        self.app.push_screen("guide")

    def action_quit_app(self) -> None:
        self.app.exit()

    # -- Event handlers --

    def on_clickable_field_clicked(self, event: ClickableField.Clicked) -> None:
        if self.project and self.project.has_overview:
            self._show_editor(event.field_id)

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle selection from inline Select widget.

        CRITICAL: Only process when we're actively editing that field.
        The Select widget fires Changed on mount/value-set — we must ignore those.
        """
        if event.value is None or event.value == Select.BLANK:
            return

        value = str(event.value)

        if event.select.id == "select-status" and self._editing == "status":
            if self.project:
                self._write_yaml("Status", value)
                self.project.status = value
                self.notify(f"Status \u2192 {value}")
                self._hide_editors()
                self._render_project()

        elif event.select.id == "select-priority" and self._editing == "priority":
            if self.project:
                self._write_yaml("Priority", value)
                self.project.priority = value
                self.notify(f"Priority \u2192 {value}")
                self._hide_editors()
                self._render_project()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter in an inline Input widget."""
        value = event.value.strip()

        if event.input.id == "input-next" and self._editing == "next_action":
            if self.project and value:
                self._write_yaml("Next_action", value)
                self.project.next_action = value
                self.notify("Next action updated")
                self._hide_editors()
                self._render_project()
            else:
                self._hide_editors()

        elif event.input.id == "input-worklog" and self._editing == "log_work":
            if self.project and value:
                log_work(self.project.name, value)
                self.notify("Logged to journal")
            self._hide_editors()

        else:
            self._hide_editors()

    def _write_yaml(self, key: str, value: str) -> None:
        """Update a YAML frontmatter value in the overview file.

        Handles all formats:
        - Standard: 'Key: value'
        - Quoted: 'Key: "value with spaces"'
        - Null: 'Key: null'
        - List format: 'Key:\\n- item' (replaces with scalar)
        - Missing key: appends before closing ---
        """
        if not self.project:
            return
        overview = self.project.dir_path / "_OVERVIEW.md"
        if not overview.exists():
            return

        text = overview.read_text()
        lines = text.split("\n")

        # Quote values with spaces
        if " " in value:
            formatted = f'{key}: "{value}"'
        else:
            formatted = f"{key}: {value}"

        in_frontmatter = False
        key_found = False
        key_line = -1
        frontmatter_end = -1

        for i, line in enumerate(lines):
            if line.strip() == "---":
                if not in_frontmatter:
                    in_frontmatter = True
                    continue
                else:
                    frontmatter_end = i
                    break
            if in_frontmatter and line.startswith(f"{key}:"):
                key_line = i
                key_found = True
                break

        if key_found:
            # Replace the key line
            lines[key_line] = formatted

            # Remove any list items that follow (handles "Key:\n- item" format)
            while (key_line + 1 < len(lines)
                   and lines[key_line + 1].startswith("- ")):
                lines.pop(key_line + 1)

        elif frontmatter_end > 0:
            # Key doesn't exist — add it before closing ---
            lines.insert(frontmatter_end, formatted)

        overview.write_text("\n".join(lines))
