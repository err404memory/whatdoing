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
        """def get(self, key: str, default: str = "") -> str:
        
        Retrieve a frontmatter value as a string.  This function attempts to fetch the
        value associated with the given  key from the frontmatter. If the value is None
        or the string "null",  it returns the specified default value. If the value is
        a list, it  returns the first element as a string, or the default if the list
        is  empty. Otherwise, it returns the trimmed string representation of the
        value or the default if the value is empty.
        """
        val = self.frontmatter.get(key, "")
        if val is None or val == "null":
            return default
        if isinstance(val, list):
            # Handle YAML lists stored as scalar (e.g., Status:\n- active)
            return str(val[0]) if val else default
        return str(val).strip() or default

    def get_section(self, heading: str) -> str:
        """Retrieve content under a specified heading."""
        return self.sections.get(heading, "")

    def body_without(self, *headings: str) -> str:
        """Return body with specified ## sections removed.
        
        This function processes the body of text by splitting it into lines and
        removing any lines that correspond to the specified headings. It checks  each
        line to determine if it starts with "## " and matches any of the  provided
        headings. Lines that do not match the headings are retained  and returned as a
        single string.
        
        Args:
            headings (str): The headings to be removed from the body.
        """
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
    
    This function reads a markdown file specified by the given path and processes
    it to extract both the frontmatter and the body content. It handles various
    scenarios, including files without frontmatter, malformed YAML, and horizontal
    rules. The function also ensures that any errors during file reading or YAML
    parsing do not disrupt the flow, returning a ParsedDocument object with the
    appropriate content.
    
    Args:
        path (Path): The path to the markdown file to be parsed.
    
    Returns:
        ParsedDocument: An object containing the parsed frontmatter and body of the document.
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
    """Extract title and sections from the body.
    
    This function processes the body of a ParsedDocument to extract the  title and
    sections. It identifies the title as the first level one  heading (starting
    with "# ") and captures all subsequent level two  headings (starting with "##
    ") as sections, storing them in the  `doc` object. The content under each
    section is collected until  the next section heading is encountered.
    
    Args:
        doc (ParsedDocument): The document from which to extract metadata.
    """
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


def merge_documents(primary: ParsedDocument, secondary: ParsedDocument) -> str:
    """Merge unique sections from secondary into primary body."""
    merged = primary.body
    primary_headings = set(primary.sections.keys())

    for heading, content in secondary.sections.items():
        if heading not in primary_headings and content.strip():
            merged += f"\n\n## {heading}\n{content}"

    return merged
