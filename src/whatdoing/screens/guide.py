"""Guide screen — built-in help and user guide."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Markdown

GUIDE_TEXT = """\
# whatdoing User Guide

## Quick Start

**whatdoing** is your project dashboard — a single place to see everything you're working on,
log what you did, and find your way back when you get lost.

### 1. Create the smallest working setup

```
mkdir -p ~/.whatdoing ~/projects
printf '%s\n' 'base_path: ~/projects' > ~/.whatdoing/config.yaml
```

### 2. Launch

```bash
whatdoing
```

### 3. Success looks like this

- The dashboard opens in your terminal
- Each subdirectory in `~/projects` appears as a project row
- Dimmed rows are still valid; they just do not have an `overview.md` yet
- Press `e` inside a project to open or create its overview file

## Will This Work On My System?

- **Tested:** Linux terminals
- **Likely works:** macOS and WSL
- **Windows native:** use WSL for the best current experience

No special shell is required (`bash`, `zsh`, etc.). `whatdoing` is a normal Python CLI app.

If your system is not the default target:

- If your projects are not under `~/projects`, change `base_path`
- If `git` is missing, git widgets fall back cleanly
- If Docker is not installed or reachable, Docker widgets also fall back cleanly

## Project Layout

Each subdirectory in your base path is a project:

```
~/projects/
  my-app/
  website/
  side-project/
```

Projects without an `overview.md` still appear dimmed, and you can create one from inside the app by pressing `e`.

Legacy names `_OVERVIEW.md`, `PROJECT.md`, and `project.md` are still read automatically.

You can also override the config directory with the `WHATDOING_HOME` env var.

## Config

The smallest config is:

```yaml
base_path: ~/projects
```

Optional keys:

```yaml
# Subdirectory within base_path where projects live
overview_dir:

# Preferred text editor (defaults to micro, then $EDITOR, then nano)
editor: nano

# SSH host for remote docker status checks
docker_host:
```

## Keyboard Shortcuts

### Dashboard
| Key | Action |
|-----|--------|
| `Enter` | Open selected project |
| `/` | Filter projects by name |
| `j` / `k` | Move cursor down / up |
| `s` | Open scratchpad |
| `l` | Open journal |
| `?` | This help screen |
| `q` | Quit |

### Project View
| Key | Action |
|-----|--------|
| **click** / `Enter` | Edit a section inline |
| `Ctrl+S` | Save section (while editing) |
| `Esc` | Cancel edit (while editing) |
| `a` | Add a new section |
| `e` | Open full file in text editor |
| `u` | Edit status |
| `p` | Edit priority |
| `n` | Edit next action |
| `w` | Log work to journal |
| `s` | Open scratchpad |
| `l` | Open journal |
| `b` / `Esc` | Back to dashboard |

### Scratchpad
| Key | Action |
|-----|--------|
| `Esc` | Save and go back |
| `Ctrl+S` | Save |

### Journal
| Key | Action |
|-----|--------|
| `/` | Search entries |
| `Esc` | Go back |

## Adding a Project

The easiest path is:

1. Create a directory in your projects folder
2. Launch `whatdoing`
3. Open the project row and press `e`

If you prefer to create `overview.md` manually, use this format:

```yaml
---
Status: Active
Priority: High
Next_action: What to do next
Type: app
Energy_required: high
Time_estimate: 2h
code_path: /path/to/code
docker_name: container-name
Tags:
  - web
  - python
---

# Project Name

## What is this?
Description here.

## Blockers
- Any blockers listed here show in a red box.

## Next Steps
- Step one
- Step two
```

3. The project appears automatically in the dashboard.

Compatibility: legacy overview filenames `_OVERVIEW.md`, `PROJECT.md`, and `project.md` are still supported for reading.

All frontmatter fields are optional. Only `Status` and `Priority` are
used for dashboard sorting and color-coding.

## File Locations

| What | Where |
|------|-------|
| Config | `~/.whatdoing/config.yaml` |
| Scratchpad | `~/.whatdoing/scratchpad.md` |
| Journal | `~/.whatdoing/journal/YYYY-MM-DD.md` |
| Session state | `~/.whatdoing/state.json` |
| Projects | Configured in config.yaml `base_path` + `overview_dir` |

## Journal

Press `w` in any project view to log what you worked on.
Entries are timestamped and saved to daily markdown files.
Search across all entries from the journal screen.

## Tips for Managing Many Projects

- **Always log work** (`w`) before switching projects — future-you will thank past-you
- **Use the scratchpad** for random thoughts that pop up mid-task
- **Check the dashboard** at the start of each session — the last-viewed project is highlighted
- **Update status honestly** — "STUCK" and "BLOCKED" are valid statuses, not failures
- **Keep next actions small** — "Fix the bug" is better than "Finish the project"

## AI Integration

All whatdoing data is plain markdown + YAML. You can ask an AI assistant to:
- Read your project overviews to understand current state
- Help update overview files
- Search journal entries for what you worked on
- Suggest next actions based on blockers and priorities

Just point the AI at `~/.whatdoing/` and your projects directory.
"""


class GuideScreen(Screen):
    """Built-in user guide accessible from any screen."""

    BINDINGS = [
        Binding("escape", "go_back", "Back", show=True),
        Binding("q", "go_back", "Back", show=False),
    ]

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="guide-scroll"):
            yield Markdown(GUIDE_TEXT, id="guide-content")
        yield Footer()

    def action_go_back(self) -> None:
        self.app.pop_screen()
