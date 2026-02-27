# User Customization & UX Enhancements — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add custom dashboard columns, button links, color theming with background images, interactive checkboxes, and custom dropdown options to whatdoing.

**Architecture:** Expand `config.py` to hold all new settings. Build a `themes.py` module for theme registration. Modify `dashboard.py` for columns + buttons, `project.py` for checkboxes + dropdown add-new. Use Textual's native Theme system and `textual-image` for background images.

**Tech Stack:** Python 3.9+, Textual 0.86+, PyYAML, textual-image (optional)

---

## Task 1: Expand Config System

**Files:**
- Modify: `src/whatdoing/config.py`

**Step 1: Add new fields to Config dataclass**

Add these fields to the `Config` class at `config.py:16-30`:

```python
@dataclass
class Config:
    """Application configuration."""

    base_path: str = ""
    overview_dir: str = ""
    editor: str = ""
    docker_host: str = ""
    status_presets: list[str] = field(default_factory=lambda: [
        "Active", "Paused", "Backlog", "IN PROGRESS",
        "BLOCKED", "STUCK", "READY", "RUNNING",
    ])
    priority_presets: list[str] = field(default_factory=lambda: [
        "High", "Medium", "Low",
    ])
    # NEW fields
    dashboard_columns: list[str] = field(default_factory=lambda: [
        "status", "priority", "project", "type", "next_action",
    ])
    buttons: dict = field(default_factory=lambda: {
        "placement": "top",
        "items": [
            {"label": "Scratch", "action": "screen:scratchpad"},
            {"label": "Journal", "action": "screen:journal"},
            {"label": "Guide", "action": "screen:guide"},
            {"label": "+ New", "action": "new_project"},
        ],
    })
    theme: dict = field(default_factory=lambda: {
        "name": "default",
    })
```

**Step 2: Load new fields in `load_config()`**

After line 109 (after priority-presets loading), add:

```python
        if "dashboard-columns" in data and isinstance(data["dashboard-columns"], list):
            cfg.dashboard_columns = data["dashboard-columns"]
        if "buttons" in data and isinstance(data["buttons"], dict):
            cfg.buttons = data["buttons"]
        if "theme" in data and isinstance(data["theme"], dict):
            cfg.theme = data["theme"]
```

**Step 3: Add `save_config()` function**

Add a new function to write config back to disk (needed for custom dropdown options and column picker):

```python
def save_config(cfg: Config) -> None:
    """Save config back to ~/.whatdoing/config.yaml."""
    config_file = whatdoing_home() / "config.yaml"
    data = {}

    # Preserve existing file data if present
    if config_file.exists():
        try:
            with open(config_file) as f:
                data = yaml.safe_load(f) or {}
        except Exception:
            data = {}

    data["base_path"] = cfg.base_path
    data["overview_dir"] = cfg.overview_dir
    data["editor"] = cfg.editor
    data["docker_host"] = cfg.docker_host
    data["status-presets"] = cfg.status_presets
    data["priority-presets"] = cfg.priority_presets
    data["dashboard-columns"] = cfg.dashboard_columns
    data["buttons"] = cfg.buttons
    data["theme"] = cfg.theme

    config_file.parent.mkdir(parents=True, exist_ok=True)
    with open(config_file, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)
```

**Step 4: Verify**

Run: `cd /home/ash/dev/whatdoing && python -c "from whatdoing.config import load_config; c = load_config(); print(c.dashboard_columns, c.theme)"`

Expected: prints default column list and theme dict.

**Step 5: Commit**

```bash
git add src/whatdoing/config.py
git commit -m "feat: expand config with dashboard columns, buttons, and theme settings"
```

---

## Task 2: Create Themes Module

**Files:**
- Create: `src/whatdoing/themes.py`

**Step 1: Create `themes.py` with preset definitions and theme builder**

```python
"""Theme definitions and dynamic theme builder for whatdoing."""

from __future__ import annotations

from textual.design import ColorSystem
from textual.app import App


# Preset color schemes
PRESETS: dict[str, dict[str, str]] = {
    "default": {
        "bg-color": "#1a1a2e",
        "accent-color": "#0f3460",
        "header-color": "#282840",
        "text-color": "#e0e0e0",
        "table-alt-color": "#1f1f3a",
        "primary": "#0f3460",
        "secondary": "#533483",
        "accent": "#e94560",
        "surface": "#16213e",
    },
    "ocean": {
        "bg-color": "#0a1628",
        "accent-color": "#1a6b8a",
        "header-color": "#0d2137",
        "text-color": "#c8e6f0",
        "table-alt-color": "#0d2a3a",
        "primary": "#1a6b8a",
        "secondary": "#2d9cbc",
        "accent": "#4fd1c5",
        "surface": "#0d2137",
    },
    "forest": {
        "bg-color": "#1a2e1a",
        "accent-color": "#2d5a27",
        "header-color": "#1e3a1e",
        "text-color": "#d4e8c8",
        "table-alt-color": "#1f3a1a",
        "primary": "#2d5a27",
        "secondary": "#8b6914",
        "accent": "#d4a017",
        "surface": "#1e3a1e",
    },
}


def build_theme_colors(theme_config: dict) -> dict[str, str]:
    """Merge user theme config with a preset base.

    Returns a flat dict of color keys.
    """
    preset_name = theme_config.get("name", "default")
    base = dict(PRESETS.get(preset_name, PRESETS["default"]))

    # User overrides from config
    for key in ("bg-color", "accent-color", "header-color", "text-color",
                "table-alt-color", "primary", "secondary", "accent", "surface"):
        if key in theme_config:
            base[key] = theme_config[key]

    return base


def get_header_color(theme_config: dict) -> str:
    """Get the header background color for Rich markup."""
    colors = build_theme_colors(theme_config)
    return colors.get("header-color", "#282840")


def get_status_color(theme_config: dict, status: str) -> str | None:
    """Get a custom status color override, if configured."""
    custom = theme_config.get("status-colors", {})
    if isinstance(custom, dict):
        return custom.get(status.lower())
    return None
```

**Step 2: Verify import**

Run: `python -c "from whatdoing.themes import PRESETS, build_theme_colors; print(list(PRESETS.keys()))"`

Expected: `['default', 'ocean', 'forest']`

**Step 3: Commit**

```bash
git add src/whatdoing/themes.py
git commit -m "feat: add themes module with 3 presets and dynamic color builder"
```

---

## Task 3: Apply Theme System to App

**Files:**
- Modify: `src/whatdoing/app.py`
- Modify: `src/whatdoing/app.tcss`

**Step 1: Register theme in `WhatDoingApp.__init__`**

In `app.py`, after `self.config = config or load_config()` (line 35), add theme registration. Import `build_theme_colors` from `themes.py`.

The approach: Textual's `App` class supports a `design` property and CSS variable overrides. We'll use `App.stylesheet` or dynamic CSS injection. The most reliable way in Textual 0.86+ is to override the `get_css_variables` method:

```python
from whatdoing.themes import build_theme_colors, get_header_color

class WhatDoingApp(App):
    # ... existing code ...

    def get_css_variables(self) -> dict[str, str]:
        """Override CSS variables with theme colors."""
        variables = super().get_css_variables()
        colors = build_theme_colors(self.config.theme)
        # Map our theme keys to Textual CSS variable names
        variables["background"] = colors.get("bg-color", variables.get("background", ""))
        variables["surface"] = colors.get("surface", variables.get("surface", ""))
        variables["primary"] = colors.get("primary", variables.get("primary", ""))
        variables["secondary"] = colors.get("secondary", variables.get("secondary", ""))
        variables["accent"] = colors.get("accent", variables.get("accent", ""))
        return variables
```

**Step 2: Replace hardcoded colors in `app.tcss`**

Replace all `rgb(40, 40, 60)` references with a CSS variable. Since Textual CSS variables don't directly map to arbitrary names easily, we'll use the `$surface` variable for headers (which is set by our theme):

- `#dashboard-header`: change `background: rgb(40, 40, 60)` to `background: $surface-darken-1`
- `#project-header`: same change
- `#scratch-header`: change `background: rgb(60, 40, 10)` to `background: $secondary`
- `#journal-header`: change `background: rgb(20, 40, 60)` to `background: $primary`
- `.has-blockers`: change `background: rgb(60, 20, 20)` to `background: $error-darken-3`

**Step 3: Add theme cycling binding to dashboard**

In `dashboard.py`, add binding `Binding("t", "cycle_theme", "Theme", show=True)` and handler:

```python
def action_cycle_theme(self) -> None:
    """Cycle through available themes."""
    from whatdoing.themes import PRESETS
    from whatdoing.config import save_config
    names = list(PRESETS.keys())
    current = self.app.config.theme.get("name", "default")
    try:
        idx = names.index(current)
    except ValueError:
        idx = 0
    next_name = names[(idx + 1) % len(names)]
    self.app.config.theme["name"] = next_name
    save_config(self.app.config)
    # Force CSS refresh
    self.app.stylesheet.reparse()
    self.app.stylesheet.apply(self.app)
    self.notify(f"Theme: {next_name}")
```

**Step 4: Verify**

Run `whatdoing`, press `t` to cycle themes. Verify header and background colors change.

**Step 5: Commit**

```bash
git add src/whatdoing/app.py src/whatdoing/app.tcss src/whatdoing/screens/dashboard.py
git commit -m "feat: apply theme system with CSS variable overrides and theme cycling"
```

---

## Task 4: Custom Dashboard Columns

**Files:**
- Modify: `src/whatdoing/models.py`
- Modify: `src/whatdoing/screens/dashboard.py`

**Step 1: Expose raw frontmatter in Project model**

In `models.py`, the `Project` dataclass already stores `doc: ParsedDocument | None`. The `ParsedDocument.frontmatter` dict contains all raw keys. No model changes needed — we can access arbitrary frontmatter via `project.doc.get(key)` and sections via `project.doc.get_section(heading)`.

**Step 2: Make dashboard columns dynamic**

Replace `_setup_table()` in `dashboard.py:63-70`:

```python
# Column display config: maps config key -> (header_label, width_hint)
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


def _setup_table(self) -> None:
    table = self.query_one("#project-table", DataTable)
    table.cursor_type = "row"
    table.zebra_stripes = True

    columns = self.config.dashboard_columns
    for col_key in columns:
        label = COLUMN_LABELS.get(col_key, col_key.replace("_", " ").upper())
        if col_key.startswith("## "):
            label = col_key[3:].upper()
        table.add_column(label, key=col_key)
```

**Step 3: Update `_populate_table()` to use dynamic columns**

Replace the row-building logic. For each project, build cell values dynamically:

```python
def _get_cell_value(self, project: Project, col_key: str) -> Text:
    """Get the display value for a column."""
    if col_key == "status":
        if not project.has_overview:
            return Text("—", style="dim")
        return Text(project.status, style=f"bold {project.status_color}")
    elif col_key == "priority":
        if not project.has_overview:
            return Text("—", style="dim")
        return Text(project.priority, style=project.priority_color)
    elif col_key == "project":
        if not project.has_overview:
            return Text(project.name, style="dim italic")
        return Text(project.name)
    elif col_key == "type":
        return Text(project.project_type, style="dim")
    elif col_key == "next_action":
        if not project.has_overview:
            return Text("[no overview]", style="dim italic")
        na = project.next_action
        if len(na) > 40:
            na = na[:39] + "\u2026"
        return Text(na)
    elif col_key.startswith("## "):
        # Section content
        heading = col_key[3:]
        if project.doc:
            content = project.doc.get_section(heading).strip()
            if len(content) > 30:
                content = content[:29] + "\u2026"
            return Text(content or "—", style="dim")
        return Text("—", style="dim")
    else:
        # Arbitrary frontmatter key
        if project.doc:
            val = project.doc.get(col_key.replace("_", " ").title().replace(" ", "_"), "")
            if not val:
                # Try exact key match
                val = project.doc.get(col_key, "")
            if len(val) > 30:
                val = val[:29] + "\u2026"
            return Text(val or "—", style="dim")
        return Text("—", style="dim")
```

Then update `_populate_table()` to use it:

```python
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
        row = [self._get_cell_value(project, col) for col in columns]
        table.add_row(*row)
        if project.name == self._last_project:
            highlight_row = i

    if highlight_row is not None and highlight_row < len(self.filtered_projects):
        table.move_cursor(row=highlight_row)

    self._update_stats()
```

**Step 4: Add column picker (press `c`)**

Add binding: `Binding("c", "edit_columns", "Columns", show=True)`

Implement as a simple modal approach — use `self.app.push_screen()` with a new `ColumnPickerScreen`:

Create a lightweight inner class or add to `dashboard.py`:

```python
from textual.widgets import Checkbox

class ColumnPickerScreen(Screen):
    """Modal for toggling dashboard columns."""

    BINDINGS = [
        Binding("escape", "close", "Close"),
    ]

    def __init__(self, config, available_columns: list[str]) -> None:
        super().__init__()
        self.config = config
        self.available_columns = available_columns

    def compose(self) -> ComposeResult:
        yield Static("[bold]Dashboard Columns[/] (Esc to close)\n", id="col-picker-header")
        with VerticalScroll():
            for col in self.available_columns:
                is_core = col in CORE_COLUMNS
                is_active = col in self.config.dashboard_columns
                label = COLUMN_LABELS.get(col, col)
                if is_core:
                    label += " (locked)"
                cb = Checkbox(label, value=is_active or is_core, id=f"col-{col}")
                cb.disabled = is_core
                yield cb

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        col_key = event.checkbox.id.replace("col-", "", 1)
        if col_key in CORE_COLUMNS:
            return
        if event.value and col_key not in self.config.dashboard_columns:
            self.config.dashboard_columns.append(col_key)
        elif not event.value and col_key in self.config.dashboard_columns:
            self.config.dashboard_columns.remove(col_key)
        save_config(self.config)

    def action_close(self) -> None:
        self.app.pop_screen()
```

The `action_edit_columns()` method in `DashboardScreen`:

```python
def action_edit_columns(self) -> None:
    """Open column picker."""
    # Build list of all available columns from scanned projects
    available = list(CORE_COLUMNS)
    seen = set(CORE_COLUMNS)
    # Add frontmatter keys from all projects
    for p in self.projects:
        if p.doc and p.doc.frontmatter:
            for key in p.doc.frontmatter:
                normalized = key.lower().replace(" ", "_")
                if normalized not in seen:
                    available.append(normalized)
                    seen.add(normalized)
        if p.doc and p.doc.sections:
            for heading in p.doc.sections:
                section_key = f"## {heading}"
                if section_key not in seen:
                    available.append(section_key)
                    seen.add(section_key)
    self.app.push_screen(ColumnPickerScreen(self.config, available))
```

After the picker closes, `on_screen_resume` already reloads and repopulates the table, which will pick up the new columns. However, since `_setup_table` only runs once (on mount), we need to rebuild the table when returning:

```python
def on_screen_resume(self) -> None:
    """Refresh project data when returning from another screen."""
    self._last_project = load_state().get("last_project", "")
    self._load_projects()
    # Rebuild table columns in case column config changed
    table = self.query_one("#project-table", DataTable)
    table.clear(columns=True)
    self._setup_table()
    self._populate_table()
    self.query_one("#project-table", DataTable).focus()
```

**Step 5: Verify**

Run `whatdoing`, press `c`, toggle a column, close, verify the table updates.

**Step 6: Commit**

```bash
git add src/whatdoing/screens/dashboard.py src/whatdoing/models.py
git commit -m "feat: dynamic dashboard columns with picker (press c)"
```

---

## Task 5: Button Links (Top Bar)

**Files:**
- Modify: `src/whatdoing/screens/dashboard.py`
- Modify: `src/whatdoing/app.tcss`

**Step 1: Add button bar to dashboard compose**

In `dashboard.py`, update `compose()` to add a button bar between header and filter:

```python
from textual.widgets import Button

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
        pass  # Context-sensitive buttons populated dynamically
    yield Static("", id="dashboard-stats")
    yield Footer()
```

**Step 2: Add button click handler**

```python
def on_button_pressed(self, event: Button.Pressed) -> None:
    """Handle button bar clicks."""
    btn_id = event.button.id or ""
    action = btn_id.replace("btn-", "", 1)

    if action.startswith("screen:"):
        screen_name = action.split(":", 1)[1]
        self.app.push_screen(screen_name)
    elif action == "new_project":
        self._create_new_project()
    elif action.startswith("open_url:"):
        self._open_project_url(action.split(":", 1)[1])


def _create_new_project(self) -> None:
    """Create a new project directory with template."""
    # Show input for project name
    inp = self.query_one("#filter-input", Input)
    inp.placeholder = "New project name (Enter to create, Esc to cancel)..."
    inp.value = ""
    inp.focus()
    self._creating_project = True


def _open_project_url(self, frontmatter_key: str) -> None:
    """Open a URL from the selected project's frontmatter."""
    import webbrowser
    table = self.query_one("#project-table", DataTable)
    if table.cursor_row is not None and table.cursor_row < len(self.filtered_projects):
        project = self.filtered_projects[table.cursor_row]
        if project.doc:
            url = project.doc.get(frontmatter_key, "")
            if url:
                webbrowser.open(url)
                self.notify(f"Opened {frontmatter_key}")
            else:
                self.notify(f"No {frontmatter_key} URL for this project", severity="warning")
```

**Step 3: Update context-sensitive buttons on row cursor change**

```python
def on_data_table_cursor_changed(self, event) -> None:
    """Update context buttons when table cursor moves."""
    context_bar = self.query_one("#context-bar", Horizontal)
    context_bar.remove_children()

    if event.cursor_row is not None and event.cursor_row < len(self.filtered_projects):
        project = self.filtered_projects[event.cursor_row]
        if project.doc:
            for item in self.config.buttons.get("items", []):
                if not item.get("context"):
                    continue
                key = item["action"].split(":", 1)[1] if ":" in item["action"] else ""
                val = project.doc.get(key, "")
                if val:
                    btn = Button(item["label"], id=f"btn-{item['action']}", classes="ctx-button")
                    context_bar.mount(btn)
```

**Step 4: Add button bar CSS to `app.tcss`**

```css
/* ── Button Bar ── */

#button-bar {
    dock: top;
    height: 3;
    padding: 0 1;
    background: $surface;
}

.bar-button {
    margin: 0 1 0 0;
    min-width: 10;
    height: 3;
}

#context-bar {
    height: auto;
    max-height: 3;
    padding: 0 1;
}

.ctx-button {
    margin: 0 1 0 0;
    min-width: 8;
    height: 3;
    border: round $accent;
}
```

**Step 5: Verify**

Run `whatdoing`, verify buttons appear below header, click Scratch/Journal/Guide buttons work.

**Step 6: Commit**

```bash
git add src/whatdoing/screens/dashboard.py src/whatdoing/app.tcss
git commit -m "feat: add configurable button bar to dashboard with context-sensitive project links"
```

---

## Task 6: Custom Dropdown Options

**Files:**
- Modify: `src/whatdoing/screens/project.py`
- Modify: `src/whatdoing/config.py` (already has `save_config` from Task 1)

**Step 1: Build options dynamically from config presets**

Replace the hardcoded `STATUS_OPTIONS` and `PRIORITY_OPTIONS` at `project.py:35-50` with functions that build options from config:

```python
ADD_NEW_SENTINEL = "__add_new__"


def _build_status_options(config) -> list[tuple[str, str]]:
    """Build status Select options from config presets."""
    opts = [(s, s) for s in config.status_presets]
    opts.append(("+ Add new...", ADD_NEW_SENTINEL))
    return opts


def _build_priority_options(config) -> list[tuple[str, str]]:
    """Build priority Select options from config presets."""
    opts = [(p, p) for p in config.priority_presets]
    opts.append(("+ Add new...", ADD_NEW_SENTINEL))
    return opts
```

Keep `STATUS_OPTIONS` and `PRIORITY_OPTIONS` as module-level defaults for the normalization functions (they still need a reference list). Update the normalization functions to accept a config parameter:

```python
def _normalize_status(value: str, config=None) -> str:
    """Normalize status to match SELECT options (case-insensitive lookup)."""
    if not value:
        return ""
    presets = config.status_presets if config else [s for _, s in STATUS_OPTIONS]
    for option_value in presets:
        if value.lower() == option_value.lower():
            return option_value
    return value


def _normalize_priority(value: str, config=None) -> str:
    """Normalize priority to match SELECT options (case-insensitive lookup)."""
    if not value:
        return ""
    presets = config.priority_presets if config else [p for _, p in PRIORITY_OPTIONS]
    for option_value in presets:
        if value.lower() == option_value.lower():
            return option_value
    return value
```

**Step 2: Update ProjectScreen to build Select options from config**

In `ProjectScreen.__init__`, store config. In `compose()`, build Select with dynamic options:

```python
def __init__(self, project: Project | None = None) -> None:
    super().__init__()
    self.project = project
    self._editing: str = ""
    self._adding_new: str = ""  # "status" or "priority" when adding new option

def compose(self) -> ComposeResult:
    # ... existing code up to Select widgets ...
    config = self.app.config if hasattr(self, 'app') and self.app else load_config()
    yield Select(_build_status_options(config), id="select-status", allow_blank=False)
    yield Select(_build_priority_options(config), id="select-priority", allow_blank=False)
    # Add a hidden input for "add new" values
    yield Input(placeholder="Type new value...", id="input-new-option")
    # ... rest of compose ...
```

Note: `self.app` may not be available in `compose()`. Instead, we can use `on_mount()` to call `set_options()` on the Select widgets:

```python
def on_mount(self) -> None:
    # ... existing hide logic ...
    # Set options from config
    config = self.app.config
    self.query_one("#select-status", Select).set_options(_build_status_options(config))
    self.query_one("#select-priority", Select).set_options(_build_priority_options(config))
    self.query_one("#input-new-option", Input).display = False
    # ... rest of on_mount ...
```

**Step 3: Handle "+ Add new..." selection**

Update `on_select_changed()`:

```python
def on_select_changed(self, event: Select.Changed) -> None:
    if event.value is None or event.value == Select.BLANK:
        return

    value = str(event.value)

    # Handle "Add new..." sentinel
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

    # ... existing status/priority handling ...
```

**Step 4: Handle new option input submission**

Add to `on_input_submitted()`:

```python
        elif event.input.id == "input-new-option" and self._adding_new:
            if value:
                from whatdoing.config import save_config
                config = self.app.config

                if self._adding_new == "status":
                    # Add to config presets if not already there
                    if value not in config.status_presets:
                        config.status_presets.append(value)
                        save_config(config)
                    # Apply to project
                    self._write_yaml("Status", value)
                    self.project.status = value
                    # Rebuild Select options
                    self.query_one("#select-status", Select).set_options(
                        _build_status_options(config)
                    )
                    self.notify(f"Status → {value} (added to presets)")

                elif self._adding_new == "priority":
                    if value not in config.priority_presets:
                        config.priority_presets.append(value)
                        save_config(config)
                    self._write_yaml("Priority", value)
                    self.project.priority = value
                    self.query_one("#select-priority", Select).set_options(
                        _build_priority_options(config)
                    )
                    self.notify(f"Priority → {value} (added to presets)")

                self._adding_new = ""
                self._hide_editors()
                self._render_metadata()
            else:
                self._adding_new = ""
                self._hide_editors()
```

Also update `_hide_editors()` to hide the new input and clear `_adding_new`:

```python
def _hide_editors(self) -> None:
    """Hide all inline editors."""
    self._editing = ""
    self._adding_new = ""
    self.query_one("#select-status", Select).display = False
    self.query_one("#select-priority", Select).display = False
    self.query_one("#input-next", Input).display = False
    self.query_one("#input-add-section", Input).display = False
    self.query_one("#input-worklog", Input).display = False
    self.query_one("#input-new-option", Input).display = False
```

**Step 5: Verify**

Open a project, press `u` for status, select "+ Add new...", type "Review", press Enter. Verify it saves to project file and appears in dropdown next time.

**Step 6: Commit**

```bash
git add src/whatdoing/screens/project.py
git commit -m "feat: custom dropdown options with '+ Add new...' for status and priority"
```

---

## Task 7: Interactive Checkboxes

**Files:**
- Modify: `src/whatdoing/screens/project.py` (EditableSection)
- Modify: `src/whatdoing/parser.py`

**Step 1: Add checkbox detection helper to `parser.py`**

```python
import re

CHECKBOX_RE = re.compile(r'^(\s*)- \[([ xX])\] (.+)$')


def parse_checkboxes(content: str) -> list[dict]:
    """Parse markdown checkbox lines from content.

    Returns list of dicts: {line_idx, indent, checked, text, raw_line}
    """
    results = []
    for i, line in enumerate(content.split("\n")):
        m = CHECKBOX_RE.match(line)
        if m:
            results.append({
                "line_idx": i,
                "indent": len(m.group(1)),
                "checked": m.group(2) in ("x", "X"),
                "text": m.group(3),
                "raw_line": line,
            })
    return results


def toggle_checkbox(content: str, line_idx: int) -> str:
    """Toggle a checkbox on a specific line in content.

    Flips `- [ ]` to `- [x]` and vice versa.
    """
    lines = content.split("\n")
    if line_idx < 0 or line_idx >= len(lines):
        return content
    line = lines[line_idx]
    if "- [ ]" in line:
        lines[line_idx] = line.replace("- [ ]", "- [x]", 1)
    elif "- [x]" in line or "- [X]" in line:
        lines[line_idx] = re.sub(r'- \[[xX]\]', '- [ ]', line, count=1)
    return "\n".join(lines)
```

**Step 2: Modify EditableSection to render checkboxes**

In `EditableSection.compose()`, replace the simple Markdown display with a container that can hold checkboxes. The approach: keep Markdown for display, but add a post-mount step that replaces checkbox lines with actual Checkbox widgets.

Better approach for simplicity: Override the display rendering. When the section content contains checkboxes, render a mix of Static/Checkbox widgets instead of Markdown:

```python
from textual.widgets import Checkbox
from whatdoing.parser import parse_checkboxes, toggle_checkbox


class EditableSection(Vertical):
    # ... existing Saved message, __init__ ...

    def compose(self) -> ComposeResult:
        yield Static(self._heading_markup(), classes="section-heading")
        yield Vertical(id=f"section-display-{id(self)}", classes="section-display")
        yield SectionTextArea("", classes="section-editor")

    def on_mount(self) -> None:
        self.query_one(".section-editor", SectionTextArea).display = False
        self._apply_blocker_style()
        self._render_display()

    def _render_display(self) -> None:
        """Render section content with interactive checkboxes."""
        display = self.query_one(f"#section-display-{id(self)}", Vertical)
        display.remove_children()

        checks = parse_checkboxes(self.section_content)
        if not checks:
            # No checkboxes — render as plain Markdown
            display.mount(Markdown(self.section_content))
            return

        # Split content into chunks: non-checkbox text + checkbox widgets
        lines = self.section_content.split("\n")
        check_indices = {c["line_idx"] for c in checks}
        buffer = []

        for i, line in enumerate(lines):
            if i in check_indices:
                # Flush any buffered text
                if buffer:
                    display.mount(Markdown("\n".join(buffer)))
                    buffer = []
                # Add checkbox widget
                check = next(c for c in checks if c["line_idx"] == i)
                cb = Checkbox(
                    check["text"],
                    value=check["checked"],
                    id=f"check-{id(self)}-{i}",
                )
                display.mount(cb)
            else:
                buffer.append(line)

        if buffer:
            display.mount(Markdown("\n".join(buffer)))

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Toggle checkbox in content and write to disk."""
        cb_id = event.checkbox.id or ""
        if not cb_id.startswith(f"check-{id(self)}-"):
            return

        line_idx = int(cb_id.split("-")[-1])
        self.section_content = toggle_checkbox(self.section_content, line_idx)
        # Post save message to write to disk
        self.post_message(self.Saved(self.heading, self.section_content))
        event.stop()
```

Note: The `section-display` container is now a `Vertical` with an `id` instead of just a `Markdown`. Update the `_enter_edit` and `_exit_edit` methods to query by class instead:

```python
def _enter_edit(self) -> None:
    if self._in_edit:
        return
    self._in_edit = True
    self.add_class("editing")
    display = self.query_one(".section-display")
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
    display = self.query_one(".section-display")
    editor = self.query_one(".section-editor", SectionTextArea)

    if save:
        self.section_content = editor.text
        self._render_display()  # Re-render with checkboxes
        self._apply_blocker_style()
        self.post_message(self.Saved(self.heading, self.section_content))

    editor.display = False
    display.display = True
```

**Step 3: Verify**

Create a project with checkbox content in a section:
```
## Tasks
- [ ] First thing
- [x] Done thing
- [ ] Another thing
```

Open the project, verify checkboxes render as interactive widgets. Toggle one, verify the file updates.

**Step 4: Commit**

```bash
git add src/whatdoing/parser.py src/whatdoing/screens/project.py
git commit -m "feat: interactive checkboxes in project sections with immediate write-back"
```

---

## Task 8: Background Images (Optional Dependency)

**Files:**
- Modify: `pyproject.toml`
- Modify: `src/whatdoing/app.py`
- Modify: `src/whatdoing/themes.py`

**Step 1: Add textual-image as optional dependency**

In `pyproject.toml`, add:

```toml
[project.optional-dependencies]
images = ["textual-image>=0.7.0"]
```

**Step 2: Add image background support to `themes.py`**

```python
def supports_image_background() -> bool:
    """Check if textual-image is installed and terminal supports it."""
    try:
        import textual_image  # noqa: F401
        return True
    except ImportError:
        return False
```

**Step 3: Add image background widget to app**

In `app.py`, if image background is configured and supported, add it as a background layer. The `textual-image` library provides a widget that can be composed.

This is the most experimental part — the exact API depends on `textual-image` version. The general approach:

```python
def compose(self) -> ComposeResult:
    # If background image is configured, try to add it
    bg_image = self.config.theme.get("background-image", "")
    if bg_image and Path(bg_image).exists():
        try:
            from textual_image.widget import Image
            yield Image(bg_image, id="bg-image")
        except ImportError:
            pass
```

With CSS to position it as a background layer:

```css
#bg-image {
    dock: top;
    width: 100%;
    height: 100%;
    opacity: 0.3;
    layer: background;
}
```

**Note:** This task is intentionally lighter on specifics because `textual-image` API may vary. The implementer should install it, check its actual API, and adapt. If it proves too finicky, skip and revisit later — the color theming from Task 3 is the primary styling feature.

**Step 4: Verify**

Set `background-image: /path/to/image.png` in config, run in Ghostty or Kitty, verify image appears behind content.

**Step 5: Commit**

```bash
git add pyproject.toml src/whatdoing/app.py src/whatdoing/themes.py
git commit -m "feat: optional background image support via textual-image"
```

---

## Task 9: Version Bump and Final Verification

**Files:**
- Modify: `pyproject.toml:7` — change `2.1.3` to `2.2.0`
- Modify: `src/whatdoing/__init__.py` — change `__version__` to `2.2.0`

**Step 1: Bump version**

**Step 2: Full verification checklist**

1. `whatdoing` — dashboard loads with default columns and button bar
2. Press `c` — column picker opens, toggle a column, verify table updates
3. Click Scratch button — scratchpad opens
4. Press `t` — theme cycles (default → ocean → forest)
5. Open a project with `- [ ]` items — checkboxes are interactive
6. Toggle checkbox — file updates on disk
7. Press `u` for status — select "+ Add new...", type "Review", verify saves
8. Restart app — all customizations persist
9. `whatdoing --version` — prints 2.2.0

**Step 3: Commit**

```bash
git add pyproject.toml src/whatdoing/__init__.py
git commit -m "release: whatdoing v2.2.0 — user customization and UX enhancements"
```

**Step 4: Sync to jeffrey and reinstall**

```bash
rsync -av /home/ash/dev/whatdoing/ ashes@jeffrey:/home/ashes/dev/whatdoing/
ssh jeffrey "TERM=xterm-256color pipx install -e /home/ashes/dev/whatdoing --force"
```
