"""
Work experience entries.

Each entry is anchored on a line containing a date range ("Jun 2024 - Present").
The anchor line plus at most one preceding non-bullet header line form the
entry header (title / company / location); following lines up to the next
entry's header are the description.

If the section has text but no date ranges, no entries are invented: the
caller records an "experience_unstructured" warning and the user adds entries
manually (the raw text remains available).
"""
import re

from .text_utils import (
    DATE_RANGE_RE,
    HEADER_SPLIT_RE,
    PRESENT_RE,
    clean,
    is_bullet,
    non_empty_lines,
    strip_bullet,
)
from .types import ExperienceEntry

MAX_HEADER_CHARS = 120
_AT_RE = re.compile(r"\s+(?:at|@)\s+", re.IGNORECASE)


def _is_header_candidate(line: str) -> bool:
    text = line.strip()
    return (
        bool(text)
        and not is_bullet(text)
        and len(text) <= MAX_HEADER_CHARS
        and not text.endswith(".")
        and not DATE_RANGE_RE.search(text)
    )


def _parse_header(header: str, entry: ExperienceEntry) -> None:
    parts = [clean(p) for p in HEADER_SPLIT_RE.split(header) if clean(p)]
    if len(parts) == 1 and _AT_RE.search(parts[0]):
        parts = [clean(p) for p in _AT_RE.split(parts[0], maxsplit=1)]
    if len(parts) == 1:
        # "Software Intern, Acme Corp" -> split on the first comma only.
        title, sep, rest = parts[0].partition(",")
        parts = [clean(title), clean(rest)] if sep else parts
    if parts:
        entry.title = parts[0]
    if len(parts) > 1:
        entry.company = parts[1]
    if len(parts) > 2:
        entry.location = ", ".join(parts[2:])


def extract_experience(lines: list[str]) -> list[ExperienceEntry]:
    rows = non_empty_lines(lines)
    anchors = [i for i, ln in enumerate(rows) if DATE_RANGE_RE.search(ln)]
    if not anchors:
        return []

    # Header start for each anchor: include one preceding header-like line,
    # but never reach back into the previous anchor line.
    starts: list[int] = []
    for n, a in enumerate(anchors):
        floor = anchors[n - 1] + 1 if n else 0
        start = a
        if a - 1 >= floor and _is_header_candidate(rows[a - 1]):
            start = a - 1
        starts.append(start)

    entries: list[ExperienceEntry] = []
    for n, a in enumerate(anchors):
        end = starts[n + 1] if n + 1 < len(anchors) else len(rows)
        entry = ExperienceEntry()

        date_match = DATE_RANGE_RE.search(rows[a])
        entry.start_date = clean(date_match.group("start"))
        end_text = clean(date_match.group("end"))
        entry.is_current = bool(PRESENT_RE.match(end_text))
        entry.end_date = "" if entry.is_current else end_text

        anchor_rest = clean(rows[a].replace(date_match.group(0), " "))
        header_bits = [clean(rows[i]) for i in range(starts[n], a)]
        if anchor_rest:
            header_bits.append(anchor_rest)
        _parse_header(" | ".join(header_bits), entry)

        description: list[str] = []
        for line in rows[a + 1:end]:
            text = strip_bullet(line)
            if description and not is_bullet(line) and text[:1].islower():
                description[-1] = f"{description[-1]} {text}"  # wrapped line
            else:
                description.append(text)
        entry.description = "\n".join(d for d in description if d)
        if entry.title or entry.company or entry.description:
            entries.append(entry)
    return entries
