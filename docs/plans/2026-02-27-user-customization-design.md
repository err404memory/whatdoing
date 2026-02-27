# whatdoing v2.2.0 — User Customization & UX Enhancements

**Date:** 2026-02-27
**Status:** Approved
**Version target:** 2.2.0

## Context

whatdoing v2.1.3 has a solid foundation — project dashboard, drill-in views, inline editing, live data services. But everything is hardcoded: the dashboard columns, color scheme, dropdown options. Users need control over what they see and how the app looks. Additionally, markdown checkboxes in project files are display-only when they should be interactive.

This design adds five features that collectively transform whatdoing from a fixed-layout tool into a customizable workspace.

---

## Feature 1: Custom Dashboard Columns

### Problem
Dashboard has 5 hardcoded columns (STATUS, PRI, PROJECT, TYPE, NEXT ACTION). Users may want to see Energy, Time Estimate, Tags, or even section content at a glance.

### Design
- Scan all projects on load to build a union of available frontmatter keys and section headings.
- `dashboard-columns` config key defines visible columns and their order.
- Three core columns (STATUS, PRI, PROJECT) are always present and locked.
- Press `c` on dashboard to open a column picker overlay.

### Column Picker
- Modal overlay listing all available columns grouped: "Core (locked)" / "Frontmatter" / "Sections"
- Textual Checkbox widgets to toggle visibility
- Changes save to config immediately on close

### Display Rules
- Frontmatter values: display as-is, truncated to column width
- Section headings (prefixed with `##` in config): show first 30 chars of section content
- Tags: comma-separated, truncated
- Null/missing values: display `—`

### Config Format
```yaml
dashboard-columns:
  - status           # core, locked
  - priority         # core, locked
  - project          # core, locked
  - type             # frontmatter
  - next_action      # frontmatter
  # Additional options users can add:
  # - energy_required
  # - time_estimate
  # - tags
  # - "## Blockers"  # section heading
```

### Files Modified
- `config.py` — new `dashboard_columns` field, load/save
- `dashboard.py` — dynamic column setup, picker modal, populate logic
- `models.py` — expose raw frontmatter dict for arbitrary key access

---

## Feature 2: Button Links (Top Bar)

### Problem
Navigation relies entirely on keyboard shortcuts. Visual buttons add discoverability, UI diversity, and context-sensitive convenience (e.g., opening a project's GitHub repo).

### Design
- Horizontal container below header with compact styled Buttons.
- Default buttons: Scratchpad, Journal, Guide, New Project.
- Context-sensitive buttons: when a table row is highlighted, buttons for that project's URL fields (repo, permalink) appear.
- Configured in `config.yaml` under `buttons`.

### Layout
```
┌──────────────────────────────────────────┐
│  whatdoing                    [filter: /] │
├──────────────────────────────────────────┤
│ [Scratch] [Journal] [Guide] [+ New]      │
├──────────────────────────────────────────┤
│ STATUS  PRI  PROJECT  TYPE  NEXT ACTION  │
```

### Action Types
- `screen:<name>` — push named screen (scratchpad, journal, guide)
- `new_project` — create new project with template _OVERVIEW.md
- `open_url:<frontmatter_key>` — open URL from selected project's frontmatter via `webbrowser.open()`

### Config Format
```yaml
buttons:
  placement: top    # top | bottom | sidebar (future)
  items:
    - { label: "Scratch", action: "screen:scratchpad" }
    - { label: "Journal", action: "screen:journal" }
    - { label: "Guide", action: "screen:guide" }
    - { label: "+ New", action: "new_project" }
    - { label: "Repo", action: "open_url:repo", context: true }
```

### Files Modified
- `dashboard.py` — button bar compose, handlers, context-sensitive updates
- `config.py` — button config schema
- `app.tcss` — compact button styling

---

## Feature 3: Styling & Theming

### Problem
The app has a single hardcoded dark color scheme. Users want visual customization: colors, backgrounds, and the ability to make the tool feel personal.

### Design: Two Layers

#### Layer 1 — Color Theming (universal, all terminals)

- Use Textual's native `Theme` system with CSS variables.
- Ship 3 built-in presets:
  - **default** — current dark blue/grey
  - **ocean** — deep teals, aqua accents
  - **forest** — dark greens, amber accents
- Users can override any color via `theme` config section.
- At startup, register a custom Theme from config values.
- Press `t` on dashboard to cycle themes or open picker.
- All hardcoded colors in `app.tcss` replaced with CSS variables.

#### Layer 2 — Background Images (Kitty-protocol terminals)

- Add `textual-image` as optional dependency.
- If `theme.background-image` is set and terminal supports Kitty graphics protocol: render image as background with configurable opacity.
- Graceful fallback to solid `bg-color` on unsupported terminals.
- Detection via terminal capability probing at startup.

### Config Format
```yaml
theme:
  name: default
  bg-color: "#1a1a2e"
  accent-color: "#0f3460"
  header-color: "#16213e"
  text-color: "#e0e0e0"
  table-alt-color: "#1f1f3a"
  status-colors:
    active: "green"
    blocked: "red"
  background-image: ""       # path to image file
  image-opacity: 0.3         # 0.0-1.0
```

### Files Modified
- `app.py` — theme registration at startup
- `config.py` — theme config loading
- `app.tcss` — replace all hardcoded colors with CSS variables
- New `themes.py` — preset definitions, image background layer, theme builder

---

## Feature 4: Interactive Checkboxes

### Problem
Markdown checkboxes (`- [ ]` / `- [x]`) in project _OVERVIEW.md files render as plain text. Users expect to click them to toggle state.

### Design
- In project screen `EditableSection` display mode: parse content for checkbox patterns.
- Replace checkbox lines with Textual `Checkbox` widgets.
- Non-checkbox content renders as normal Markdown/Static.
- On `Checkbox.Changed`: immediately regex-replace `- [ ]` <-> `- [x]` in the file.
- Track by line number within the section.

### Edge Cases
- Nested checkboxes (indented): supported, tracked by line offset
- Mixed content: interleaved Static + Checkbox widgets
- Only match lines starting with `- [ ]` or `- [x]` (with optional leading whitespace)

### Files Modified
- `project.py` — EditableSection rendering logic, checkbox toggle handler
- `parser.py` — checkbox line detection helper

---

## Feature 5: Custom Dropdown Options

### Problem
Status and priority dropdowns have hardcoded options. Users can't add new statuses like "Review" or "Testing" without editing code.

### Design
- Add `("+ Add new...", "__add_new__")` as the final option in every Select dropdown.
- When selected: hide Select, show Input for new value.
- On submit:
  1. Apply value to current project (write to YAML frontmatter)
  2. Append to `status-presets` / `priority-presets` in config.yaml
  3. Rebuild Select options with `set_options()` to include new value
- Existing normalization handles case-insensitive matching.
- Any value in project frontmatter is auto-accepted even if not in presets.

### Files Modified
- `project.py` — Select handling, add-new input flow, options rebuild
- `config.py` — write presets back to config file

---

## New Dependencies

- `textual-image` (optional) — for Kitty-protocol background images

## Version Bump

- `pyproject.toml` and `__init__.py`: 2.1.3 -> 2.2.0

## Verification Plan

1. Run `whatdoing` — dashboard loads with default columns and button bar
2. Press `c` — column picker opens, toggle a column, verify it appears/disappears
3. Click a button — verify navigation works (Scratchpad, Journal, etc.)
4. Press `t` — cycle through themes, verify colors change
5. Set `background-image` in config — verify image renders (Ghostty/Kitty) or falls back gracefully
6. Open a project with `- [ ]` items — verify checkboxes are interactive and toggle persists to file
7. Edit status dropdown — select "+ Add new...", type "Review", verify it saves to project and config
8. Restart app — verify all customizations persist
