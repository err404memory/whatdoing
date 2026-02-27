# whatdoing

Terminal dashboard for tracking what you're working on. Shows all your projects at a glance, lets you drill into any one, and surfaces live data (git activity, Docker status, last modified file) without leaving the terminal.

Built for ADHD brains managing dozens of unfinished projects across multiple devices.

## Install

```bash
pipx install whatdoing
```

Or with pip:

```bash
pip install whatdoing
```

## Setup

whatdoing needs a directory where each subdirectory is a project. The structure looks like:

```
~/projects/
  my-app/
    _OVERVIEW.md
  website/
    _OVERVIEW.md
  side-project/
```

### 1. Create the config

```bash
mkdir -p ~/.whatdoing
```

Create `~/.whatdoing/config.yaml`:

```yaml
# Required: path to the directory containing your project folders
base_path: ~/projects

# Optional: subdirectory within base_path where projects live
# (leave blank if projects are directly inside base_path)
overview_dir:

# Optional: preferred text editor (defaults to micro, then $EDITOR, then nano)
editor: nano

# Optional: SSH host for remote docker status checks
docker_host: myserver
```

### 2. Add a project

Create a directory with an `_OVERVIEW.md` file:

```bash
mkdir -p ~/projects/my-app
cat > ~/projects/my-app/_OVERVIEW.md << 'EOF'
---
Status: Active
Priority: High
Next_action: Build the thing
Type: app
---

# My App

## What is this?

Description of the project.

## Blockers

None
EOF
```

### 3. Launch

```bash
whatdoing
```

Projects without an `_OVERVIEW.md` still appear in the dashboard (dimmed) and you can create one from inside the app.

## Usage

```
whatdoing                 Dashboard - show all projects
whatdoing <name>          Jump to a project (fuzzy match)
whatdoing scratch         Open scratchpad
whatdoing journal         Open journal
whatdoing guide           User guide
whatdoing --help          This message
```

## Keyboard Shortcuts

### Dashboard

| Key | Action |
|-----|--------|
| `Enter` | Open selected project |
| `/` | Filter projects by name |
| `s` | Open scratchpad |
| `l` | Open journal |
| `?` | Help |
| `q` | Quit |

### Project View

| Key | Action |
|-----|--------|
| Click / `Enter` on section | Edit section inline |
| `Ctrl+S` (in editor) | Save section |
| `Esc` (in editor) | Cancel edit |
| `a` | Add new section |
| `e` | Open full file in text editor |
| `u` | Edit status |
| `p` | Edit priority |
| `n` | Edit next action |
| `w` | Log work to journal |
| `b` | Back to dashboard |

## YAML Frontmatter

Each `_OVERVIEW.md` supports these frontmatter fields:

```yaml
---
Status: Active          # Shown color-coded in dashboard
Priority: High          # High / Medium / Low
Next_action: Do thing   # Shown in dashboard and project view
Type: app               # Free text label
Energy_required: high   # Shown in project view
Time_estimate: 2h       # Shown in project view
code_path: /path/to/src # For git status checks
docker_name: my-container  # For docker status checks
Tags:
  - tag1
  - tag2
---
```

## File Locations

| What | Where |
|------|-------|
| Config | `~/.whatdoing/config.yaml` |
| Scratchpad | `~/.whatdoing/scratchpad.md` |
| Journal | `~/.whatdoing/journal/YYYY-MM-DD.md` |
| Session state | `~/.whatdoing/state.json` |

Override the config directory with `WHATDOING_HOME` env var.

## License

MIT
