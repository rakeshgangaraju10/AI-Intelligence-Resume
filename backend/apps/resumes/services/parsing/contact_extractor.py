"""
Contact details from the resume header (text before the first section heading).

Only values that literally appear in the text are returned; nothing is guessed
beyond choosing which header line is most likely the candidate's name.
"""
import re

from .text_utils import URL_RE, clean
from .types import ContactInfo

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# International or local numbers with 10-15 digits and common separators.
PHONE_RE = re.compile(r"(?<!\w)(\+?\d[\d\s().-]{8,18}\d)(?!\w)")
_NAME_WORD = re.compile(r"^[A-Za-z][A-Za-z.'-]*$")


def _digits(value: str) -> int:
    return sum(ch.isdigit() for ch in value)


def _is_name_line(line: str) -> bool:
    words = line.split()
    return (
        2 <= len(words) <= 4
        and all(_NAME_WORD.match(w) for w in words)
        and len(line) <= 50
    )


def extract_contact(header_lines: list[str], full_text: str) -> ContactInfo:
    info = ContactInfo()
    # Email/phone/links are searched in the header first, then in the full text
    # (some templates place contact details in a footer or side column).
    header = "\n".join(header_lines)
    for source in (header, full_text):
        if not info.email and (m := EMAIL_RE.search(source)):
            info.email = m.group(0)
        if not info.phone:
            for m in PHONE_RE.finditer(source):
                if 10 <= _digits(m.group(1)) <= 15 and not re.fullmatch(r"(?:19|20)\d{2}\s*[-–]\s*(?:19|20)\d{2}", m.group(1).strip()):
                    info.phone = clean(m.group(1))
                    break

    seen: set[str] = set()
    for m in URL_RE.finditer(header):
        url = m.group(0).rstrip(".")
        if url.lower() not in seen and "@" not in url:
            seen.add(url.lower())
            info.links.append(url)

    for line in header_lines:
        candidate = clean(line)
        if candidate and _is_name_line(candidate) and not EMAIL_RE.search(candidate):
            info.full_name = candidate if not candidate.isupper() else candidate.title()
            break
    return info
