"""
Pipeline entry point: raw resume text -> ParsedResume.

Runs each extractor on its section, de-duplicates and trims values, and
records warnings describing what could not be extracted, so the review UI can
tell the user exactly what to check. It never fills a missing field.
"""
from apps.skills.dictionary import SkillDictionary

from .certification_extractor import extract_certifications
from .contact_extractor import extract_contact
from .education_extractor import extract_education
from .experience_extractor import extract_experience
from .project_extractor import extract_projects
from .section_extractor import split_sections
from .skill_extractor import extract_skills
from .text_utils import non_empty_lines
from .types import ParsedResume

MAX_SUMMARY_CHARS = 2000

# Field length limits mirror the database columns so parser output always saves.
FIELD_LIMITS = {
    "institution": 200, "degree": 200, "field_of_study": 200, "start_date": 30,
    "end_date": 30, "grade": 50, "title": 200, "company": 200, "location": 120,
    "name": 200, "url": 300, "issuer": 200, "issue_date": 30, "credential_url": 300,
    "full_name": 150, "email": 254, "phone": 30,
}


def _truncate(obj) -> None:
    for field, limit in FIELD_LIMITS.items():
        value = getattr(obj, field, None)
        if isinstance(value, str) and len(value) > limit:
            setattr(obj, field, value[:limit].rstrip())


def parse_resume_text(text: str, dictionary: SkillDictionary) -> ParsedResume:
    sectioned = split_sections(text)
    warnings: list[str] = []

    contact = extract_contact(sectioned.header, text)
    summary = "\n".join(non_empty_lines(sectioned.get("summary"))).strip()[:MAX_SUMMARY_CHARS]
    skills = extract_skills(sectioned, dictionary)
    education = extract_education(sectioned.get("education"))
    experience = extract_experience(sectioned.get("experience"))
    projects = extract_projects(sectioned.get("projects"), dictionary)
    certifications = extract_certifications(sectioned.get("certifications"))

    for key in ("skills", "education", "experience", "projects"):
        if key not in sectioned.sections:
            warnings.append(f"section_not_found:{key}")
    if not skills:
        warnings.append("no_skills_detected")
    if non_empty_lines(sectioned.get("experience")) and not experience:
        warnings.append("experience_unstructured")
    if non_empty_lines(sectioned.get("education")) and not education:
        warnings.append("education_unstructured")
    if non_empty_lines(sectioned.get("projects")) and not projects:
        warnings.append("projects_unstructured")
    if not contact.email:
        warnings.append("email_not_found")
    if not contact.full_name:
        warnings.append("name_not_found")

    _truncate(contact)
    for entry in [*education, *experience, *projects, *certifications]:
        _truncate(entry)

    return ParsedResume(
        contact=contact,
        summary=summary,
        skills=skills,
        education=education,
        experience=experience,
        projects=projects,
        certifications=certifications,
        sections_found=list(sectioned.headings_found),
        warnings=warnings,
    )
