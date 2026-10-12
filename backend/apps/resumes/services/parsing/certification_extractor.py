"""
Certifications: one entry per line/bullet in the Certifications section.

"Name - Issuer (2024)", "Name | Issuer | Mar 2024", "Name by Issuer, 2024" are
split into name / issuer / date. Wrapped continuation lines are joined.
"""
import re

from .text_utils import (
    SINGLE_DATE_RE,
    URL_RE,
    clean,
    is_bullet,
    looks_like_continuation,
    non_empty_lines,
    strip_bullet,
)
from .types import CertificationEntry

_ISSUER_SPLIT_RE = re.compile(r"\s+[-–—|]\s+|\s*\|\s*|\s+by\s+|\s+from\s+|,\s+", re.IGNORECASE)


def extract_certifications(lines: list[str]) -> list[CertificationEntry]:
    items: list[str] = []
    for line in non_empty_lines(lines):
        text = strip_bullet(line)
        if items and not is_bullet(line) and looks_like_continuation(text):
            items[-1] = f"{items[-1]} {text}"
        else:
            items.append(text)

    entries: list[CertificationEntry] = []
    for item in items:
        entry = CertificationEntry()
        text = item
        if m := URL_RE.search(text):
            entry.credential_url = m.group(0).rstrip(".")
            text = text.replace(m.group(0), " ")
        dates = list(SINGLE_DATE_RE.finditer(text))
        if dates:
            entry.issue_date = clean(dates[-1].group(0))
            text = text[: dates[-1].start()] + text[dates[-1].end():]
        text = re.sub(r"\(\s*\)", " ", text)
        parts = [clean(p) for p in _ISSUER_SPLIT_RE.split(text, maxsplit=1) if clean(p)]
        if not parts:
            continue
        entry.name = parts[0].strip("() ")
        if len(parts) > 1:
            entry.issuer = parts[1].strip("() ")
        entries.append(entry)
    return entries
