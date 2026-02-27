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
| `b` / `Esc` | Back to dashboard |
| `e` | Edit overview file in editor |
| `u` | Edit status (inline selector) |
| `p` | Edit priority (inline selector) |
| `n` | Edit next action (inline input) |
| `w` | Log work to journal |
| `s` | Open scratchpad |
| `l` | Open journal |
| **click** | Click status, priority, or next action to edit inline |
| `Esc` | Cancel edit / go back |

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

1. Create a directory in your projects folder
2. Add an `_OVERVIEW.md` file with YAML frontmatter:

```yaml
---
Status: Active
Priority: High
Next_action: What to do next
Type: app
code_path: /path/to/code
docker_name: container-name
---

# Project Name

## What is this?
Description here.

## Blockers
- Any blockers listed here show in a red box.
```

3. The project appears automatically in the dashboard.

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

## Tips for ADHD Workflow

- **Always log work** (`w`) before switching projects — future-you will thank past-you
- **Use the scratchpad** for random thoughts that pop up mid-task
- **Check the dashboard** at the start of each session — the last-viewed project is highlighted
- **Update status honestly** — "STUCK" and "BLOCKED" are valid statuses, not failures
- **Keep next actions small** — "Fix the bug" is better than "Finish the project"

## AI Integration

All whatdoing data is plain markdown + YAML. You can ask an AI assistant to:
- Read your project overviews to understand current state
- Help update _OVERVIEW.md files
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
