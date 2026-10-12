"""Shared helpers for the rule-based resume parsers (pure Python)."""
import re

BULLET_CHARS = "•●▪■◦‣∙·*-–—►➢✓✔○"
_BULLET_RE = re.compile(rf"^\s*(?:[{re.escape(BULLET_CHARS)}]|\d{{1,2}}[.)])\s+")

MONTH = (
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|"
    r"Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?"
)
YEAR = r"(?:19|20)\d{2}"
DATE = rf"(?:{MONTH}\s*,?\s*{YEAR}|\d{{1,2}}\s*/\s*{YEAR}|{YEAR})"
PRESENT = r"(?:Present|Current|Now|Ongoing|Till\s+date|To\s+date)"
DATE_RANGE_RE = re.compile(
    rf"(?P<start>{DATE})\s*(?:-|–|—|to|until|till)\s*(?P<end>{DATE}|{PRESENT})",
    re.IGNORECASE,
)
SINGLE_DATE_RE = re.compile(DATE, re.IGNORECASE)
YEAR_RE = re.compile(rf"\b{YEAR}\b")
URL_RE = re.compile(r"(?:https?://|www\.)[^\s,;|)]+|(?:github\.com|linkedin\.com|gitlab\.com)/[^\s,;|)]+", re.IGNORECASE)
PRESENT_RE = re.compile(rf"^{PRESENT}$", re.IGNORECASE)

# Separators used inside entry header lines: "Title | Company", "Name - description".
HEADER_SPLIT_RE = re.compile(r"\s+[|•·–—]\s+|\s+-\s+|\s*\|\s*")


def is_bullet(line: str) -> bool:
    return bool(_BULLET_RE.match(line))


def strip_bullet(line: str) -> str:
    return _BULLET_RE.sub("", line, count=1).strip()


def clean(text: str) -> str:
    """Collapse whitespace and trim stray separators."""
    return re.sub(r"\s+", " ", text).strip(" \t,;|-–—:")


def non_empty_lines(lines: list[str]) -> list[str]:
    return [ln.rstrip() for ln in lines if ln.strip()]


def looks_like_continuation(line: str) -> bool:
    """A wrapped line that continues the previous sentence (starts lower-case or with punctuation)."""
    stripped = line.strip()
    return bool(stripped) and (stripped[0].islower() or stripped[0] in ",;:&(")
