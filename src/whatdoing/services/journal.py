"""Journal service — daily work log read/write/search."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from whatdoing.config import journal_dir


def today_file() -> Path:
    """Get path to today's journal file."""
    return journal_dir() / f"{datetime.now().strftime('%Y-%m-%d')}.md"


def log_work(project_name: str, note: str) -> None:
    """Add a timestamped work entry for a project."""
    path = today_file()
    timestamp = datetime.now().strftime("%H:%M")

    entry = f"\n## {timestamp} \u2014 {project_name}\n{note}\n"

    if not path.exists():
        header = f"# Journal \u2014 {datetime.now().strftime('%Y-%m-%d')}\n"
        path.write_text(header + entry)
    else:
        with open(path, "a") as f:
            f.write(entry)


def recent_entries(limit: int = 20) -> list[dict]:
    """Get recent journal entries across all days.

    Returns list of dicts: {date, time, project, note, file}
    """
    jdir = journal_dir()
    entries = []

    # Read journal files newest first
    files = sorted(jdir.glob("*.md"), reverse=True)
    for jfile in files[:7]:  # Last 7 days max
        try:
            text = jfile.read_text()
        except Exception:
            continue

        date = jfile.stem  # e.g. 2026-02-26
        current_time = ""
        current_project = ""
        current_lines: list[str] = []

        for line in text.split("\n"):
            if line.startswith("## ") and "\u2014" in line:
                # Flush previous entry
                if current_time and current_project:
                    entries.append({
                        "date": date,
                        "time": current_time,
                        "project": current_project,
                        "note": "\n".join(current_lines).strip(),
                        "file": str(jfile),
                    })

                # Parse new entry header: ## 14:32 — project-name
                header = line[3:].strip()
                parts = header.split("\u2014", 1)
                current_time = parts[0].strip()
                current_project = parts[1].strip() if len(parts) > 1 else ""
                current_lines = []
            elif current_time:
                current_lines.append(line)

        # Flush last entry
        if current_time and current_project:
            entries.append({
                "date": date,
                "time": current_time,
                "project": current_project,
                "note": "\n".join(current_lines).strip(),
                "file": str(jfile),
            })

        if len(entries) >= limit:
            break

    return entries[:limit]


def search_journal(query: str) -> list[dict]:
    """Search all journal entries for a query string."""
    all_entries = recent_entries(limit=100)
    q = query.lower()
    return [
        e for e in all_entries
        if q in e["project"].lower() or q in e["note"].lower()
    ]
