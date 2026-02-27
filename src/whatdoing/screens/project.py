"""Project drill-in screen — full view with overview, live data, and actions.

Interaction model:
- Status, priority, and next action are clickable inline-editable fields
- Each ## section in the overview is rendered as an EditableSection widget
- Click a section (or press Enter) to edit its raw markdown in a TextArea
- Ctrl+S saves the section, Esc cancels
- 'e' opens the full file in micro (suspends TUI, resumes after)
- 'a' adds a new ## section at the end
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
    Footer, Label, Markdown, Static, Input, Select, Button, TextArea,
)
from rich.text import Text

from whatdoing.models import Project
from whatdoing.parser import parse_document, write_section
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

ADD_NEW_SENTINEL = "__add_new__"


def _build_status_options(config) -> list[tuple[str, str]]:
    """Build status Select options from config presets, with '+ Add new...' at the end."""
    opts = [(s, s) for s in config.status_presets]
    opts.append(("+ Add new...", ADD_NEW_SENTINEL))
    return opts


def _build_priority_options(config) -> list[tuple[str, str]]:
    """Build priority Select options from config presets, with '+ Add new...' at the end."""
    opts = [(p, p) for p in config.priority_presets]
    opts.append(("+ Add new...", ADD_NEW_SENTINEL))
    return opts


def _normalize_status(value: str, config=None) -> str:
    """Normalize status to match SELECT options (case-insensitive lookup)."""
    if not value:
        return ""
    presets = config.status_presets if config else [s for _, s in STATUS_OPTIONS]
    for option_value in presets:
        if value.lower() == option_value.lower():
            return option_value
    return value  # Fallback to original if no match


def _normalize_priority(value: str, config=None) -> str:
    """Normalize priority to match SELECT options (case-insensitive lookup)."""
    if not value:
        return ""
    presets = config.priority_presets if config else [p for _, p in PRIORITY_OPTIONS]
    for option_value in presets:
        if value.lower() == option_value.lower():
            return option_value
    return value  # Fallback to original if no match

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


# ── Custom widgets ──────────────────────────────────────────────


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


class SectionTextArea(TextArea):
    """TextArea that emits save/cancel messages on Ctrl+S / Escape."""

    BINDINGS = [
        Binding("ctrl+s", "save_section", "Save", show=False),
        Binding("escape", "cancel_section", "Cancel", show=False),
    ]

    class SaveRequested(Message):
        pass

    class CancelRequested(Message):
        pass

    def action_save_section(self) -> None:
        self.post_message(self.SaveRequested())

    def action_cancel_section(self) -> None:
        self.post_message(self.CancelRequested())


class EditableSection(Vertical):
    """A ## section that toggles between Markdown display and TextArea edit.

    Display mode: heading label + rendered Markdown content (clickable)
    Edit mode: TextArea with raw markdown, Ctrl+S saves, Esc cancels
    """

    class Saved(Message):
        """Posted when a section is saved."""
        def __init__(self, heading: str, content: str) -> None:
            super().__init__()
            self.heading = heading
            self.content = content

    def __init__(
        self, heading: str, content: str, is_blocker: bool = False, **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.heading = heading
        self.section_content = content
        self.is_blocker = is_blocker
        self._in_edit = False
        self.can_focus = True

    def compose(self) -> ComposeResult:
        yield Static(self._heading_markup(), classes="section-heading")
        yield Markdown(self.section_content, classes="section-display")
        yield SectionTextArea("", classes="section-editor")

    def on_mount(self) -> None:
        self.query_one(".section-editor", SectionTextArea).display = False
        self._apply_blocker_style()

    def _heading_markup(self) -> str:
        if self.is_blocker:
            return "[bold red]  \u25a0 BLOCKERS[/]  [dim]\u270e[/]"
        return f"[bold]  {self.heading}[/]  [dim]\u270e[/]"

    def _apply_blocker_style(self) -> None:
        if self.is_blocker:
            trimmed = self.section_content.strip()
            if trimmed and not trimmed.lower().startswith("none"):
                self.add_class("has-blockers")
            else:
                self.remove_class("has-blockers")

    def _enter_edit(self) -> None:
        if self._in_edit:
            return
        self._in_edit = True
        self.add_class("editing")
        display = self.query_one(".section-display", Markdown)
        editor = self.query_one(".section-editor", SectionTextArea)
        display.display = False
        editor.text = self.section_content
        editor.display = True
        editor.focus()

    def _exit_edit(self, save: bool = False) -> None:
        if not self._in_edit:
            return
        self._in_edit = False
        self.remove_class("editing")
        display = self.query_one(".section-display", Markdown)
        editor = self.query_one(".section-editor", SectionTextArea)

        if save:
            self.section_content = editor.text
            display.update(self.section_content)
            self._apply_blocker_style()
            self.post_message(self.Saved(self.heading, self.section_content))

        editor.display = False
        display.display = True

    def on_click(self, event) -> None:
        if not self._in_edit:
            self._enter_edit()

    def on_key(self, event) -> None:
        if not self._in_edit and event.key == "enter":
            self._enter_edit()
            event.stop()

    def on_section_text_area_save_requested(self, event: SectionTextArea.SaveRequested) -> None:
        self._exit_edit(save=True)
        event.stop()

    def on_section_text_area_cancel_requested(self, event: SectionTextArea.CancelRequested) -> None:
        self._exit_edit(save=False)
        event.stop()


# ── Project Screen ──────────────────────────────────────────────


class ProjectScreen(Screen):
    """Full drill-in view for a single project."""

    BINDINGS = [
        Binding("b", "go_back", "Back", show=True),
        Binding("escape", "cancel_or_back", "Back", show=False),
        Binding("e", "edit_file", "Edit File", show=True),
        Binding("u", "edit_status", "Status", show=True),
        Binding("p", "edit_priority", "Priority", show=True),
        Binding("n", "edit_next", "Next", show=True),
        Binding("a", "add_section", "Add Section", show=True),
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
        self._adding_new: str = ""  # Which field is getting a new custom option

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

        # Custom new option input (hidden, shown when "+ Add new..." is selected)
        yield Input(placeholder="Type new value...", id="input-new-option")

        # Clickable next action
        yield ClickableField("", field_id="next_action", id="field-next")
        yield Input(placeholder="New next action...", id="input-next")

        with VerticalScroll(id="project-body"):
            # Dynamic per-section editable blocks
            yield Vertical(id="sections-container")

            # PROJECT.md extra content
            yield Static("", id="project-extra")

            # Live data panel
            yield Static("", id="live-header")
            yield Static("", id="live-modified")
            yield Static("", id="live-git")
            yield Static("", id="live-docker")

        # Add-section input (hidden)
        yield Input(placeholder="New section name...", id="input-add-section")
        # Work log input
        yield Input(placeholder="What did you work on?...", id="input-worklog")
        yield Footer()

    def on_mount(self) -> None:
        # CRITICAL: Hide ALL inline editors before anything else
        # This prevents Select.Changed from firing with default values
        self.query_one("#select-status", Select).display = False
        self.query_one("#select-priority", Select).display = False
        self.query_one("#input-new-option", Input).display = False
        self.query_one("#input-next", Input).display = False
        self.query_one("#input-add-section", Input).display = False
        self.query_one("#input-worklog", Input).display = False

        # Build Select options from config presets
        config = self.app.config
        self.query_one("#select-status", Select).set_options(_build_status_options(config))
        self.query_one("#select-priority", Select).set_options(_build_priority_options(config))

        if self.project and self.project.has_overview:
            self._render_project()
            self._fetch_live_data()
        elif self.project and not self.project.has_overview:
            self._render_empty_project()

    def on_screen_resume(self) -> None:
        """Refresh project data when returning from another screen."""
        if self.project:
            self.project = Project.from_directory(self.project.dir_path)
            if self.project.has_overview:
                self._render_project()
                self._fetch_live_data()

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

        container = self.query_one("#sections-container", Vertical)
        container.remove_children()
        container.mount(
            Markdown(
                f"## No `_OVERVIEW.md` found\n\n"
                f"This project directory exists but has no overview file.\n\n"
                f"Press **e** to create one and open it in your editor."
            )
        )

    def _render_project(self) -> None:
        """Full render — metadata + sections."""
        self._render_metadata()
        self._render_sections()

    def _render_metadata(self) -> None:
        """Update header, status row, and next action display."""
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

    def _render_sections(self) -> None:
        """Build per-section editable widgets from the parsed document."""
        p = self.project
        if not p or not p.doc:
            return

        container = self.query_one("#sections-container", Vertical)
        container.remove_children()

        doc = p.doc

        # Preamble: content between # Title and first ## section
        preamble = self._get_preamble(doc.body)
        if preamble.strip():
            container.mount(Markdown(preamble, classes="section-preamble"))

        # Editable sections
        for heading, content in doc.sections.items():
            is_blocker = heading.lower() == "blockers"
            section = EditableSection(
                heading=heading,
                content=content,
                is_blocker=is_blocker,
                classes="editable-section",
            )
            container.mount(section)

        # Merge PROJECT.md extra sections (read-only)
        extra_widget = self.query_one("#project-extra", Static)
        extra_widget.update("")
        if p.code_path:
            project_md = Path(p.code_path) / "PROJECT.md"
            if project_md.exists():
                secondary = parse_document(project_md)
                primary_headings = set(doc.sections.keys())
                extra_parts = []
                for heading, content in secondary.sections.items():
                    if heading not in primary_headings and content.strip():
                        extra_parts.append(f"## {heading}\n{content}")
                if extra_parts:
                    extra_widget.update(
                        "[dim]\u2500\u2500 from PROJECT.md \u2500\u2500[/]"
                    )
                    # Mount extra sections as read-only Markdown
                    container.mount(
                        Markdown("\n\n".join(extra_parts), classes="extra-sections")
                    )

    @staticmethod
    def _get_preamble(body: str) -> str:
        """Get content between # Title and first ## section."""
        lines = body.split("\n")
        result: list[str] = []
        past_title = False
        for line in lines:
            if line.startswith("# ") and not line.startswith("## "):
                past_title = True
                continue
            if line.startswith("## "):
                break
            if past_title:
                result.append(line)
        return "\n".join(result).strip()

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

        docker_host = getattr(self.app.config, "docker_host", "")
        dock_info = await docker.container_status(docker_name, remote_host=docker_host)
        self.query_one("#live-docker", Static).update(
            f"  [bold white]DOCKER[/]          {dock_info}"
        )

    # -- Inline editing (status / priority / next action) --

    def _show_editor(self, field: str) -> None:
        """Show the appropriate inline editor for a field."""
        self._editing = field

        if field == "status":
            sel = self.query_one("#select-status", Select)
            # Set value BEFORE showing to prevent spurious Changed events
            if self.project and self.project.status:
                sel.value = _normalize_status(self.project.status, self.app.config)
            sel.display = True
            sel.focus()

        elif field == "priority":
            sel = self.query_one("#select-priority", Select)
            if self.project and self.project.priority:
                sel.value = _normalize_priority(self.project.priority, self.app.config)
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

        elif field == "add_section":
            inp = self.query_one("#input-add-section", Input)
            inp.value = ""
            inp.display = True
            inp.focus()

    def _hide_editors(self) -> None:
        """Hide all inline editors."""
        self._editing = ""
        self._adding_new = ""
        self.query_one("#select-status", Select).display = False
        self.query_one("#select-priority", Select).display = False
        self.query_one("#input-new-option", Input).display = False
        self.query_one("#input-next", Input).display = False
        self.query_one("#input-add-section", Input).display = False
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

    def action_add_section(self) -> None:
        if self.project and self.project.has_overview:
            self._show_editor("add_section")

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

    def on_editable_section_saved(self, event: EditableSection.Saved) -> None:
        """Handle section save — write updated content to disk."""
        if not self.project:
            return
        overview = self.project.dir_path / "_OVERVIEW.md"
        write_section(overview, event.heading, event.content)

        # Reload the parsed document so future edits see fresh data
        self.project = Project.from_directory(self.project.dir_path)
        self.notify(f"Saved: {event.heading}")
        event.stop()

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle selection from inline Select widget.

        CRITICAL: Only process when we're actively editing that field.
        The Select widget fires Changed on mount/value-set — we must ignore those.
        """
        if event.value is None or event.value == Select.BLANK:
            return

        value = str(event.value)

        if value == ADD_NEW_SENTINEL:
            if event.select.id == "select-status" and self._editing == "status":
                self._adding_new = "status"
                event.select.display = False
                inp = self.query_one("#input-new-option", Input)
                inp.placeholder = "New status name..."
                inp.value = ""
                inp.display = True
                inp.focus()
                return
            elif event.select.id == "select-priority" and self._editing == "priority":
                self._adding_new = "priority"
                event.select.display = False
                inp = self.query_one("#input-new-option", Input)
                inp.placeholder = "New priority name..."
                inp.value = ""
                inp.display = True
                inp.focus()
                return

        if event.select.id == "select-status" and self._editing == "status":
            if self.project:
                self._write_yaml("Status", value)
                self.project.status = value
                self.notify(f"Status \u2192 {value}")
                self._hide_editors()
                self._render_metadata()

        elif event.select.id == "select-priority" and self._editing == "priority":
            if self.project:
                self._write_yaml("Priority", value)
                self.project.priority = value
                self.notify(f"Priority \u2192 {value}")
                self._hide_editors()
                self._render_metadata()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter in an inline Input widget."""
        value = event.value.strip()

        if event.input.id == "input-next" and self._editing == "next_action":
            if self.project and value:
                self._write_yaml("Next_action", value)
                self.project.next_action = value
                self.notify("Next action updated")
                self._hide_editors()
                self._render_metadata()
            else:
                self._hide_editors()

        elif event.input.id == "input-add-section" and self._editing == "add_section":
            if self.project and value:
                overview = self.project.dir_path / "_OVERVIEW.md"
                write_section(overview, value, "")
                self.project = Project.from_directory(self.project.dir_path)
                self._render_sections()
                self.notify(f"Added: ## {value}")
            self._hide_editors()

        elif event.input.id == "input-new-option" and self._adding_new:
            if value:
                from whatdoing.config import save_config
                config = self.app.config
                if self._adding_new == "status":
                    if value not in config.status_presets:
                        config.status_presets.append(value)
                        save_config(config)
                    self._write_yaml("Status", value)
                    self.project.status = value
                    self.query_one("#select-status", Select).set_options(_build_status_options(config))
                    self.notify(f"Status \u2192 {value} (added to presets)")
                elif self._adding_new == "priority":
                    if value not in config.priority_presets:
                        config.priority_presets.append(value)
                        save_config(config)
                    self._write_yaml("Priority", value)
                    self.project.priority = value
                    self.query_one("#select-priority", Select).set_options(_build_priority_options(config))
                    self.notify(f"Priority \u2192 {value} (added to presets)")
                self._adding_new = ""
                self._hide_editors()
                self._render_metadata()
            else:
                self._adding_new = ""
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
