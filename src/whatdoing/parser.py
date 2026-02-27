"""Robust YAML frontmatter + markdown parser.

Handles malformed YAML gracefully — never crashes on bad input.
Designed to parse _OVERVIEW.md and PROJECT.md files.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class ParsedDocument:
    """A parsed markdown file with optional YAML frontmatter."""

    frontmatter: dict[str, str] = field(default_factory=dict)
    body: str = ""
    sections: dict[str, str] = field(default_factory=dict)
    title: str = ""

    def get(self, key: str, default: str = "") -> str:
        """Get a frontmatter value, always as a string."""
        val = self.frontmatter.get(key, "")
        if val is None or val == "null":
            return default
        if isinstance(val, list):
            # Handle YAML lists stored as scalar (e.g., Status:\n- active)
            return str(val[0]) if val else default
        return str(val).strip() or default

    def get_section(self, heading: str) -> str:
        """Get content under a ## heading."""
        return self.sections.get(heading, "")

    def body_without(self, *headings: str) -> str:
        """Return body with specified ## sections removed."""
        lines = self.body.split("\n")
        result = []
        skip = False
        for line in lines:
            if line.startswith("## "):
                heading = line[3:].strip()
                skip = heading in headings
                if skip:
                    continue
            if not skip:
                result.append(line)
        return "\n".join(result)


def parse_document(path: Path) -> ParsedDocument:
    """Parse a markdown file with optional YAML frontmatter.

    Handles:
    - Files with no frontmatter (just markdown)
    - Malformed YAML (returns empty dict, preserves body)
    - YAML values that are lists, null, or missing
    - Horizontal rules (---) in the body
    """
    doc = ParsedDocument()

    if not path.exists():
        return doc

    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return doc

    lines = text.split("\n")

    # Check for frontmatter
    if not lines or lines[0].strip() != "---":
        doc.body = text
        _extract_metadata(doc)
        return doc

    # Find closing ---
    end_idx = -1
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break

    if end_idx == -1:
        # No closing ---, treat entire file as body
        doc.body = text
        _extract_metadata(doc)
        return doc

    # Parse YAML frontmatter
    yaml_text = "\n".join(lines[1:end_idx])
    try:
        parsed = yaml.safe_load(yaml_text)
        if isinstance(parsed, dict):
            doc.frontmatter = parsed
        # If YAML parses to non-dict (e.g., a string), ignore it
    except yaml.YAMLError:
        # Malformed YAML — skip silently, preserve body
        pass

    # Body is everything after the closing ---
    doc.body = "\n".join(lines[end_idx + 1:])
    _extract_metadata(doc)
    return doc


def _extract_metadata(doc: ParsedDocument) -> None:
    """Extract title and sections from the body."""
    lines = doc.body.split("\n")

    # Find title (first # heading)
    for line in lines:
        if line.startswith("# ") and not line.startswith("## "):
            doc.title = line[2:].strip()
            break

    # Extract ## sections
    current_heading = ""
    current_content: list[str] = []

    for line in lines:
        if line.startswith("## "):
            if current_heading:
                doc.sections[current_heading] = "\n".join(current_content).strip()
            current_heading = line[3:].strip()
            current_content = []
        elif current_heading:
            current_content.append(line)

    if current_heading:
        doc.sections[current_heading] = "\n".join(current_content).strip()


def write_section(path: Path, heading: str, new_content: str) -> None:
    """Update a ## section's content in a markdown file.

    Finds the ## heading in the body (after frontmatter) and replaces
    everything between it and the next ## heading (or EOF) with new_content.
    If the heading doesn't exist, appends a new section at the end.
    """
    if not path.exists():
        return

    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")

    # Find body start (skip frontmatter)
    body_start = 0
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                body_start = i + 1
                break

    # Find the target section boundaries
    section_start = -1
    section_end = len(lines)

    for i in range(body_start, len(lines)):
        if lines[i].startswith("## "):
            if section_start >= 0:
                # Found the next section — this is our end boundary
                section_end = i
                break
            if lines[i][3:].strip() == heading:
                section_start = i

    if section_start >= 0:
        # Replace: keep heading line, replace content up to next section
        replacement = [lines[section_start], ""]  # ## Heading + blank line
        if new_content.strip():
            replacement.extend(new_content.split("\n"))
        replacement.append("")  # Blank line before next section

        result = lines[:section_start] + replacement + lines[section_end:]
        path.write_text("\n".join(result), encoding="utf-8")
    else:
        # Section doesn't exist — append at end
        if not text.endswith("\n"):
            text += "\n"
        text += f"\n## {heading}\n\n{new_content}\n"
        path.write_text(text, encoding="utf-8")


def merge_documents(primary: ParsedDocument, secondary: ParsedDocument) -> str:
    """Merge unique sections from secondary into primary body.

    Returns the merged body text. Sections in secondary that don't exist
    in primary are appended at the end.
    """
    merged = primary.body
    primary_headings = set(primary.sections.keys())

    for heading, content in secondary.sections.items():
        if heading not in primary_headings and content.strip():
            merged += f"\n\n## {heading}\n{content}"

    return merged
