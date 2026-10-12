"""
Skill extraction: dictionary matching over the whole resume.

* The Skills section allows ambiguous aliases ("C", "R", "Go"), because there
  a bare token is clearly a skill. Everywhere else only unambiguous aliases count.
* Every hit carries the line it came from as evidence, so the UI and the
  matching engine can show *why* a skill was detected.
* Each canonical skill appears once; the first sighting wins, with the Skills
  section checked first.
"""
from apps.skills.dictionary import SkillDictionary

from .section_extractor import SectionedText
from .text_utils import URL_RE, clean
from .types import SkillHit

MAX_EVIDENCE_CHARS = 300
_SECTION_ORDER = ("skills", "experience", "projects", "certifications", "summary", "education")


def extract_skills(sectioned: SectionedText, dictionary: SkillDictionary) -> list[SkillHit]:
    hits: dict[str, SkillHit] = {}
    ordered = [s for s in _SECTION_ORDER if s in sectioned.sections]
    ordered += [s for s in sectioned.sections if s not in ordered]

    blocks: list[tuple[str, list[str]]] = [(s, sectioned.get(s)) for s in ordered]
    blocks.append(("header", sectioned.header))

    for section, lines in blocks:
        allow_ambiguous = section == "skills"
        for line in lines:
            # URLs are not skill claims ("github.com/..." is not "GitHub").
            searchable = URL_RE.sub(" ", line)
            for match in dictionary.find(searchable, allow_ambiguous=allow_ambiguous):
                if match.skill_name not in hits:
                    hits[match.skill_name] = SkillHit(
                        name=match.skill_name,
                        section=section,
                        evidence=clean(line)[:MAX_EVIDENCE_CHARS],
                    )
    return list(hits.values())
