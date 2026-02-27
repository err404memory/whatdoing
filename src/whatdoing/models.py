"""Data models for whatdoing projects, journal entries, and state."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from whatdoing.parser import ParsedDocument, parse_document


# Status sort rank: lower = higher priority in list
STATUS_RANK = {
    "active": 1, "in progress": 1, "running": 1,
    "ready": 2, "stuck": 2, "blocked": 2,
    "paused": 3,
    "backlog": 4,
}

PRIORITY_RANK = {"high": 1, "medium": 2, "med": 2, "low": 3}

# Status -> Rich color name for display
STATUS_COLORS = {
    "active": "green", "running": "green",
    "in progress": "dodger_blue1",
    "ready": "cyan",
    "paused": "yellow",
    "stuck": "magenta",
    "blocked": "red",
    "backlog": "dim",
}

PRIORITY_COLORS = {
    "high": "red", "medium": "yellow", "med": "yellow", "low": "dim",
}


@dataclass
class Project:
    """A project loaded from an _OVERVIEW.md file."""

    name: str
    dir_path: Path
    has_overview: bool = True
    status: str = "Unknown"
    priority: str = "Low"
    next_action: str = ""
    energy: str = ""
    time_estimate: str = ""
    project_type: str = ""
    code_path: str = ""
    docker_name: str = ""
    tags: list[str] = field(default_factory=list)
    title: str = ""  # from # heading in body
    doc: ParsedDocument | None = None

    @property
    def sort_key(self) -> tuple[int, int, str]:
        """Return a tuple of status rank, priority rank, and name."""
        s = STATUS_RANK.get(self.status.lower(), 5)
        p = PRIORITY_RANK.get(self.priority.lower(), 4)
        return (s, p, self.name.lower())

    @property
    def status_color(self) -> str:
        """Get the color associated with the current status."""
        return STATUS_COLORS.get(self.status.lower(), "white")

    @property
    def priority_color(self) -> str:
        """Return the priority color based on the priority level."""
        return PRIORITY_COLORS.get(self.priority.lower(), "white")

    @classmethod
    def from_directory(cls, dir_path: Path) -> Project:
        """Load a project from a directory containing _OVERVIEW.md.
        
        This class method initializes a Project instance by loading data from  a
        specified directory. It checks for the existence of the _OVERVIEW.md  file and
        parses its content if available. The method extracts various  project
        attributes such as name, status, priority, and tags, and  returns a Project
        instance with the gathered information.
        """
        overview = dir_path / "_OVERVIEW.md"
        name = dir_path.name

        if not overview.exists():
            return cls(name=name, dir_path=dir_path, has_overview=False)

        doc = parse_document(overview)

        tags_raw = doc.frontmatter.get("Tags", [])
        if isinstance(tags_raw, list):
            tags = [str(t) for t in tags_raw]
        else:
            tags = []

        return cls(
            name=name,
            dir_path=dir_path,
            has_overview=True,
            status=doc.get("Status", "Unknown"),
            priority=doc.get("Priority", "Low"),
            next_action=doc.get("Next_action", ""),
            energy=doc.get("Energy_required", ""),
            time_estimate=doc.get("Time_estimate", ""),
            project_type=doc.get("Type", ""),
            code_path=doc.get("code_path", ""),
            docker_name=doc.get("docker_name", ""),
            tags=tags,
            title=doc.title or name,
            doc=doc,
        )


def scan_projects(projects_path: Path) -> list[Project]:
    """Scan for all project directories and return a sorted list.
    
    This function iterates through the specified `projects_path`, checking each
    item to determine if it is a directory  and does not start with a dot or
    underscore. It collects valid project directories into a list, creating
    `Project` instances from each directory. The resulting list is then sorted,
    prioritizing projects with an  overview file before sorting by their defined
    sort key.
    """
    if not projects_path.exists():
        return []

    projects = []
    for item in sorted(projects_path.iterdir()):
        if item.is_dir() and not item.name.startswith((".", "_")):
            projects.append(Project.from_directory(item))

    projects.sort(key=lambda p: (0 if p.has_overview else 1, p.sort_key))
    return projects


def resolve_project(projects_path: Path, query: str) -> Project | None:
    """Find a project by exact or substring match."""
    if not projects_path.exists():
        return None

    # Exact match
    exact = projects_path / query
    if exact.is_dir():
        return Project.from_directory(exact)

    # Substring match
    for item in sorted(projects_path.iterdir()):
        if item.is_dir() and query.lower() in item.name.lower():
            return Project.from_directory(item)

    return None
