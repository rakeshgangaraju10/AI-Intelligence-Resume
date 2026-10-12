"""
Education entries from the Education section.

An entry starts at a line mentioning a degree (B.Tech, Bachelor of ..., 12th, ...)
or an institution (University, College, Institute, School, IIT ...) once the
current entry already has that kind of value. Fields are filled only from text
present in the entry; unknown fields stay empty.
"""
import re

from .text_utils import DATE_RANGE_RE, YEAR_RE, clean, non_empty_lines, strip_bullet
from .types import EducationEntry

DEGREE_RE = re.compile(
    r"\b(?:"
    r"B\.?\s?Tech|M\.?\s?Tech|B\.?\s?E\.?|M\.?\s?E\.?|B\.?\s?Sc\.?|M\.?\s?Sc\.?|"
    r"B\.?\s?C\.?\s?A|M\.?\s?C\.?\s?A|B\.?\s?Com|M\.?\s?Com|B\.?\s?A\.|M\.?\s?A\.|"
    r"MBA|BBA|Ph\.?\s?D|B\.?\s?S\.?|M\.?\s?S\.?|"
    r"Bachelor(?:'s)?(?:\s+of\s+[A-Z][\w&]*(?:\s+[A-Z][\w&]*)*)?|"
    r"Master(?:'s)?(?:\s+of\s+[A-Z][\w&]*(?:\s+[A-Z][\w&]*)*)?|"
    r"Doctor(?:ate)?\s+of\s+\w+|Associate(?:'s)?\s+Degree|Diploma|"
    r"Higher\s+Secondary|Senior\s+Secondary|Secondary\s+School|HSC|SSC|"
    r"Intermediate|Class\s+(?:X|XII|10|12)(?:th)?|(?:10|12)th(?:\s+(?:Grade|Standard|Class))?"
    r")(?![A-Za-z])",
)
INSTITUTION_RE = re.compile(
    r"\b(?:University|College|Institute|School|Academy|Polytechnic|Vidyalaya|"
    r"IIT|NIT|IIIT|BITS)\b",
    re.IGNORECASE,
)
GRADE_RE = re.compile(
    r"(?:CGPA|GPA|CPI|SGPA|Grade|Percentage|Score)\s*[:\-]?\s*\d{1,2}(?:\.\d{1,2})?\s*(?:/\s*\d{1,3}(?:\.\d+)?)?"
    r"|\b\d{2}(?:\.\d{1,2})?\s*%",
    re.IGNORECASE,
)
FIELD_IN_RE = re.compile(r"\bin\s+([A-Z][^,|]{1,80})")
PAREN_RE = re.compile(r"\(([^)]{2,80})\)")


def _field_of_study(part: str, degree_match: re.Match) -> str:
    """Only from explicit text: "... in X", text after the degree, or "(X)"."""
    if m := FIELD_IN_RE.search(part):
        return clean(m.group(1))
    remainder = clean(part[degree_match.end():])
    if remainder and remainder[0].isupper() and not INSTITUTION_RE.search(remainder):
        return remainder
    if m := PAREN_RE.search(part):
        return clean(m.group(1))
    return ""


def _split_parts(line: str) -> list[str]:
    # Commas inside parentheses (e.g. "(AI, ML)") must not split a part.
    parts, depth, buf = [], 0, ""
    for ch in line:
        depth += (ch == "(") - (ch == ")")
        if depth <= 0 and ch in "|,–—":
            parts.append(buf)
            buf = ""
        else:
            buf += ch
    parts.append(buf)
    out: list[str] = []
    for p in parts:
        out.extend(re.split(r"\s+-\s+", p))
    return [clean(p) for p in out if clean(p)]


def _apply_line(entry: EducationEntry, line: str, extras: list[str]) -> None:
    text = line
    if not entry.grade and (g := GRADE_RE.search(text)):
        entry.grade = clean(g.group(0))
        text = text.replace(g.group(0), " ")

    if (r := DATE_RANGE_RE.search(text)) and not entry.start_date:
        entry.start_date, entry.end_date = clean(r.group("start")), clean(r.group("end"))
        text = text.replace(r.group(0), " ")
    elif not entry.end_date:
        years = YEAR_RE.findall(text)
        if years:
            entry.end_date = years[-1]  # a single year on an education line is the completion year
            for y in years:
                text = text.replace(y, " ")

    used = False
    for part in _split_parts(text):
        if not entry.degree and (d := DEGREE_RE.search(part)):
            entry.degree = part
            if (m := FIELD_IN_RE.search(part)) and m.start() > d.start():
                entry.degree = clean(part[: m.start()])  # "B.Tech in CSE" -> degree "B.Tech"
            if not entry.field_of_study:
                entry.field_of_study = _field_of_study(part, d)
            used = True
        elif not entry.institution and INSTITUTION_RE.search(part):
            entry.institution = part
            used = True
    if not used and clean(text):
        extras.append(clean(text))


def extract_education(lines: list[str]) -> list[EducationEntry]:
    entries: list[EducationEntry] = []
    current: EducationEntry | None = None
    extras: list[str] = []

    def flush() -> None:
        if current and (current.degree or current.institution):
            current.description = "\n".join(extras)
            entries.append(current)

    for raw in non_empty_lines(lines):
        line = strip_bullet(raw)
        has_degree = bool(DEGREE_RE.search(line))
        has_institution = bool(INSTITUTION_RE.search(line))
        starts_new = current is None or (
            (has_degree and current.degree) or (has_institution and current.institution and not has_degree)
        )
        if (has_degree or has_institution) and starts_new:
            flush()
            current, extras = EducationEntry(), []
        if current is None:
            continue  # stray text before the first recognisable entry
        _apply_line(current, line, extras)
    flush()
    return entries
