"""
Split resume text into sections by detecting heading lines.

A line is a heading when, after removing decoration (":" "—" "#" etc.), it
matches a known heading synonym. Headings of sections we don't parse
("Achievements", "Hobbies", ...) are recognised too and kept under
"other:<heading>", so their text is not wrongly attached to the previous section.
A Skills heading may carry inline content: "Skills: Python, Django".

Generic ALL-CAPS detection is deliberately NOT used: project and company names
are often written in capitals and would be mistaken for headings.
"""
import re
from dataclasses import dataclass, field

SECTION_SYNONYMS: dict[str, tuple[str, ...]] = {
    "summary": (
        "summary", "professional summary", "profile", "professional profile",
        "career objective", "objective", "about me", "about", "career summary",
    ),
    "skills": (
        "skills", "technical skills", "key skills", "core skills", "skill set", "skillset",
        "core competencies", "technologies", "tech stack", "technical proficiency",
        "tools and technologies", "tools & technologies", "programming skills",
    ),
    "experience": (
        "experience", "work experience", "professional experience", "employment",
        "employment history", "work history", "internships", "internship",
        "internship experience", "relevant experience",
    ),
    "education": (
        "education", "academic background", "academic qualifications",
        "educational qualifications", "education and training", "academics",
    ),
    "projects": (
        "projects", "academic projects", "personal projects", "key projects",
        "project experience", "selected projects", "major projects",
    ),
    "certifications": (
        "certifications", "certification", "certificates", "licenses and certifications",
        "licenses & certifications", "courses and certifications",
        "courses & certifications", "courses",
    ),
}

OTHER_HEADINGS = (
    "achievements", "awards", "awards and achievements", "honors and awards",
    "accomplishments", "languages", "languages known", "hobbies", "interests",
    "hobbies and interests", "extracurricular activities", "extra-curricular activities",
    "co-curricular activities", "activities", "publications", "volunteering",
    "volunteer experience", "references", "declaration", "personal details",
    "personal information", "strengths", "positions of responsibility",
    "leadership", "training", "workshops", "soft skills",
)

_LOOKUP = {syn: key for key, syns in SECTION_SYNONYMS.items() for syn in syns}
_LOOKUP.update({h: f"other:{h}" for h in OTHER_HEADINGS})
_DECORATION = re.compile(r"^[\s#*=_\-–—:|•]+|[\s#*=_\-–—:|•]+$")
MAX_HEADING_CHARS = 45


@dataclass
class SectionedText:
    header: list[str] = field(default_factory=list)  # lines before the first heading
    sections: dict[str, list[str]] = field(default_factory=dict)
    headings_found: list[str] = field(default_factory=list)

    def get(self, name: str) -> list[str]:
        return self.sections.get(name, [])

    def text(self, name: str) -> str:
        return "\n".join(self.get(name))


def _normalise_heading(line: str) -> str:
    return re.sub(r"\s+", " ", _DECORATION.sub("", line)).strip()


def classify_heading(line: str) -> tuple[str, str] | None:
    """
    Return (section_key, inline_content) if the line is a heading, else None.
    Unparsed sections get the key "other:<heading>".
    """
    candidate = _normalise_heading(line)
    if not candidate:
        return None
    if len(candidate) <= MAX_HEADING_CHARS:
        key = _LOOKUP.get(candidate.lower())
        if key:
            return key, ""
    # Inline form, only for skills ("Technical Skills: Python, Django"). Other
    # "Label: value" lines (e.g. "Languages: Python, C" inside a skills block,
    # "Experience: 2 years" in a summary) must not open a new section.
    head, sep, rest = candidate.partition(":")
    if sep and rest.strip() and _LOOKUP.get(head.strip().lower()) == "skills":
        return "skills", rest.strip()
    return None


def split_sections(text: str) -> SectionedText:
    result = SectionedText()
    current: str | None = None
    for raw in text.splitlines():
        line = raw.rstrip()
        heading = classify_heading(line) if line.strip() else None
        if heading:
            key, inline = heading
            current = key
            result.sections.setdefault(key, [])
            if key not in result.headings_found:
                result.headings_found.append(key)
            if inline:
                result.sections[key].append(inline)
            continue
        if current is None:
            result.header.append(line)
        else:
            result.sections[current].append(line)
    return result
