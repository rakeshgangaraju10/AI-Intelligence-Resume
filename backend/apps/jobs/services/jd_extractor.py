"""
Suggest required / preferred skills from a pasted job description (pure Python).

Rules
-----
* Skills are found with the same dictionary matcher used for resumes
  (unambiguous aliases only — "Go" or "R" in prose is too risky).
* Lines under a "nice to have / preferred / bonus" heading, or a line that itself
  says "preferred", "nice to have", "a plus" ..., are PREFERRED.
* Everything else is REQUIRED (job descriptions rarely label requirements
  consistently, and the user reviews and edits every suggestion).
* A skill seen as both keeps "required".
"""
import re
from dataclasses import dataclass

from apps.skills.dictionary import SkillDictionary

REQUIRED = "required"
PREFERRED = "preferred"

_PREFERRED_HEADING = re.compile(
    r"^\W*(nice[\s-]to[\s-]haves?|good[\s-]to[\s-]haves?|preferred(\s+(qualifications|skills|experience))?|"
    r"bonus(\s+points)?|desirable|pluses|additional\s+(skills|qualifications)|it'?s\s+a\s+plus)\W*$",
    re.IGNORECASE,
)
_REQUIRED_HEADING = re.compile(
    r"^\W*(requirements?|required(\s+(skills|qualifications))?|must[\s-]haves?|qualifications|"
    r"minimum\s+qualifications|basic\s+qualifications|what\s+you('|’)?ll\s+need|what\s+we('|’)?re\s+looking\s+for|"
    r"skills(\s+required)?|tech(nical)?\s+(stack|skills)|responsibilities|you\s+have)\W*$",
    re.IGNORECASE,
)
_PREFERRED_INLINE = re.compile(
    r"\b(preferred|nice[\s-]to[\s-]have|good[\s-]to[\s-]have|a\s+plus|is\s+a\s+bonus|bonus|desirable|optional|familiarity\s+with)\b",
    re.IGNORECASE,
)
MAX_EVIDENCE_CHARS = 300


@dataclass(frozen=True)
class SuggestedRequirement:
    name: str
    kind: str
    evidence: str  # the job-description line it came from


def extract_job_skills(description: str, dictionary: SkillDictionary) -> list[SuggestedRequirement]:
    found: dict[str, SuggestedRequirement] = {}
    in_preferred_block = False
    for raw in description.splitlines():
        line = raw.strip()
        if not line:
            continue
        if _PREFERRED_HEADING.match(line):
            in_preferred_block = True
            continue
        if _REQUIRED_HEADING.match(line):
            in_preferred_block = False
            continue
        kind = PREFERRED if in_preferred_block or _PREFERRED_INLINE.search(line) else REQUIRED
        for match in dictionary.find(line):
            existing = found.get(match.skill_name)
            if existing is None or (existing.kind == PREFERRED and kind == REQUIRED):
                found[match.skill_name] = SuggestedRequirement(
                    match.skill_name, kind, " ".join(line.split())[:MAX_EVIDENCE_CHARS]
                )
    return list(found.values())
