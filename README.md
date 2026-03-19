# whatdoing

Terminal dashboard for tracking what you're working on. It shows your projects in one place, lets you drill into any one, and surfaces live data such as git activity, Docker status, and last modified files without leaving the terminal.

It is most useful when you are juggling several active projects across one or more machines.

## Uses

- tracking many active repos from one terminal dashboard
- keeping one lightweight project record per directory in plain Markdown
- checking status, next action, and project health without opening every repo
- maintaining a scratchpad and journal beside the dashboard
- staying oriented across frequent context switches

## Fit

Best for:

- a terminal-first project dashboard
- one overview file per project that you can still edit directly
- live project signals such as git state, container state, and file freshness
- a lighter-weight alternative to a full team PM system

Less useful for:

- a web app or GUI-first project tracker
- an issue tracker for large teams
- a system that hides its source files from you
- a single-project workflow with no need for cross-project overview

## Start

Install with `pipx`:

```bash
pipx install whatdoing
```

Or with `pip`:

```bash
pip install whatdoing
```

Create the smallest working setup:

```bash
mkdir -p ~/.whatdoing ~/projects
printf '%s\n' 'base_path: ~/projects' > ~/.whatdoing/config.yaml
```

Launch:

```bash
whatdoing
```

Success criteria:

- the dashboard opens in your terminal
- each subdirectory in `~/projects` appears as a project row
- dimmed rows are still valid; they just do not have an `overview.md` yet
- press `e` inside a project to open or create its overview file

## Compatibility

- **Tested:** Linux terminals
- **Likely works:** macOS and WSL
- **Windows native:** use WSL for the best current experience

No special shell is required (`bash`, `zsh`, and similar all work). `whatdoing` is a normal Python CLI app.

If your system is not the default target:

- if `pipx` is missing, install it first with `python3 -m pip install --user pipx`
- if your projects are not under `~/projects`, set `base_path` to the correct directory
- if `git` is missing, git widgets will simply show a fallback state
- if Docker is not installed or reachable, Docker widgets will also fall back cleanly

## Launch

whatdoing expects one base directory where each subdirectory is a project. A simple layout looks like:

```
~/projects/
  my-app/
  website/
  side-project/
```

You do not need to create `overview.md` files before launch. Project directories still appear in the dashboard without them, and you can create the overview from inside the app.

Legacy overview filenames `_OVERVIEW.md`, `PROJECT.md`, and `project.md` are still supported for reading.

The overview file is plain Markdown with YAML frontmatter. `whatdoing` reads it as the project record, and you can edit it in your normal editor.

## Config

Smallest config:

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
docker_host: myserver
```

## Format

If you prefer to create an `overview.md` yourself instead of creating it from inside the app:

```bash
mkdir -p ~/projects/my-app
cat > ~/projects/my-app/overview.md << 'EOF'
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

## Commands

```
whatdoing                 Dashboard - show all projects
whatdoing <name>          Jump to a project (fuzzy match)
whatdoing scratch         Open scratchpad
whatdoing journal         Open journal
whatdoing guide           User guide
whatdoing --help          This message
```

## Keys

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

## Fields

Each `overview.md` supports these frontmatter fields:

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

## Files

| What | Where |
|------|-------|
| Config | `~/.whatdoing/config.yaml` |
| Scratchpad | `~/.whatdoing/scratchpad.md` |
| Journal | `~/.whatdoing/journal/YYYY-MM-DD.md` |
| Session state | `~/.whatdoing/state.json` |

Override the config directory with `WHATDOING_HOME` env var.

## Support

This project is open-source and free to use.

If support or implementation help would be useful, open an issue titled `commercial support interest`.

## Audit

Run the repo audit before publishing or opening a PR:

```bash
./scripts/public-safety-audit.sh
```

If you want a local pre-commit guard for staged files:

```bash
./scripts/install-public-safety-hook.sh
```

The audit scans for generic home-path leaks, SSH/scp-style host references, obvious secret-key markers, and suspicious local artifact filenames such as transcript dumps. If a match is intentional, add a path glob to `.public-safety-allowlist`. If you want the audit to catch your own machine names or local path fragments, put custom regex patterns in `.public-safety-local-patterns` and keep that file local only.

## License

MIT
