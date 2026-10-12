"""
Project entries.

A project starts at a non-bullet, title-like line (short, not ending with a
period, not a wrapped continuation). "Name - description" / "Name | stack" /
"Name: description" headers are split. Bullets and sentences that follow form
the description. Technologies are the dictionary skills explicitly mentioned
inside that project's own text; nothing is inferred from the project name.
"""
import re

from apps.skills.dictionary import SkillDictionary

from .text_utils import (
    DATE_RANGE_RE,
    URL_RE,
    clean,
    is_bullet,
    looks_like_continuation,
    non_empty_lines,
    strip_bullet,
)
from .types import ProjectEntry

MAX_TITLE_CHARS = 100
_TITLE_SPLIT_RE = re.compile(r"\s+[-–—|]\s+|\s*\|\s*|:\s+")
_TECH_PREFIX_RE = re.compile(r"^(?:tech(?:nologies)?(?:\s+used)?|tech\s*stack|stack|tools|built\s+with)\s*:\s*", re.IGNORECASE)


MAX_INLINE_NAME_WORDS = 8


def _has_inline_name(text: str) -> bool:
    """'Inventory Tracker - built a Django API.' : a short name before a separator."""
    parts = _TITLE_SPLIT_RE.split(text, maxsplit=1)
    return len(parts) == 2 and 0 < len(parts[0].split()) <= MAX_INLINE_NAME_WORDS


def _is_title_line(line: str) -> bool:
    text = line.strip()
    if not text or is_bullet(text) or looks_like_continuation(text) or _TECH_PREFIX_RE.match(text):
        return False
    if _has_inline_name(text):
        return True
    return len(text) <= MAX_TITLE_CHARS and not text.endswith(".")


def extract_projects(lines: list[str], dictionary: SkillDictionary) -> list[ProjectEntry]:
    rows = non_empty_lines(lines)
    groups: list[list[str]] = []
    for line in rows:
        # A title line starts a new project once the current project has content
        # (a description line, or a description inline in its own title line).
        # Otherwise it is treated as the current project's subtitle.
        current_has_content = bool(groups) and (len(groups[-1]) > 1 or _has_inline_name(groups[-1][0]))
        if _is_title_line(line) and (not groups or current_has_content):
            groups.append([line])
        elif groups:
            groups[-1].append(line)
        else:
            groups.append([line])  # section starts with a bullet: untitled project

    projects: list[ProjectEntry] = []
    for group in groups:
        title_line = group[0] if _is_title_line(group[0]) else ""
        body = group[1:] if title_line else group
        entry = ProjectEntry()

        if title_line:
            title = DATE_RANGE_RE.sub(" ", title_line)
            name, *rest = _TITLE_SPLIT_RE.split(title, maxsplit=1)
            entry.name = clean(name)
            if rest and clean(rest[0]):
                body = [rest[0], *body]

        description: list[str] = []
        for line in body:
            text = strip_bullet(line)
            if description and not is_bullet(line) and looks_like_continuation(text):
                description[-1] = f"{description[-1]} {text}"
            else:
                description.append(text)
        entry.description = "\n".join(clean(d) if _TECH_PREFIX_RE.match(d) else d.strip() for d in description if d.strip())

        full_text = "\n".join(group)
        if m := URL_RE.search(full_text):
            entry.url = m.group(0).rstrip(".")
        seen: list[str] = []
        for match in dictionary.find(URL_RE.sub(" ", full_text)):
            if match.skill_name not in seen:
                seen.append(match.skill_name)
        entry.technologies = seen

        if entry.name or entry.description:
            projects.append(entry)
    return projects
