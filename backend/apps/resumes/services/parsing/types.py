"""Plain data containers produced by the parsers (serialisable with dataclasses.asdict)."""
from dataclasses import dataclass, field


@dataclass
class ContactInfo:
    full_name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    links: list[str] = field(default_factory=list)


@dataclass
class SkillHit:
    name: str          # canonical skill name
    section: str       # section where it was first seen ("skills", "projects", ...)
    evidence: str      # the resume line containing the mention (trimmed)


@dataclass
class EducationEntry:
    institution: str = ""
    degree: str = ""
    field_of_study: str = ""
    start_date: str = ""
    end_date: str = ""
    grade: str = ""
    description: str = ""


@dataclass
class ExperienceEntry:
    title: str = ""
    company: str = ""
    location: str = ""
    start_date: str = ""
    end_date: str = ""
    is_current: bool = False
    description: str = ""


@dataclass
class ProjectEntry:
    name: str = ""
    description: str = ""
    technologies: list[str] = field(default_factory=list)
    url: str = ""


@dataclass
class CertificationEntry:
    name: str = ""
    issuer: str = ""
    issue_date: str = ""
    credential_url: str = ""


@dataclass
class ParsedResume:
    contact: ContactInfo
    summary: str
    skills: list[SkillHit]
    education: list[EducationEntry]
    experience: list[ExperienceEntry]
    projects: list[ProjectEntry]
    certifications: list[CertificationEntry]
    sections_found: list[str]
    warnings: list[str]
