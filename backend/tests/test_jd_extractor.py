"""Unit tests for job-description skill suggestions (pure Python, no database)."""
from apps.jobs.services.jd_extractor import PREFERRED, REQUIRED, extract_job_skills

from .test_parsing import DICTIONARY

JD = """Junior Backend Developer (Python)

About the role
You will build REST APIs for our analytics product.

Requirements
- 0-2 years of experience with Python and Django
- Solid SQL skills; we use PostgreSQL
- Git and code review experience
- Experience with Docker is a plus

Nice to have
- AWS or GCP
- React for occasional frontend work
- Python scripting for automation
"""


def kinds(items):
    return {i.name: i.kind for i in items}


def test_required_and_preferred_sections_and_inline_markers():
    result = kinds(extract_job_skills(JD, DICTIONARY))
    assert result["Python"] == REQUIRED          # required wins over later preferred mention
    assert result["Django"] == REQUIRED
    assert result["PostgreSQL"] == REQUIRED
    assert result["SQL"] == REQUIRED
    assert result["Git"] == REQUIRED
    assert result["REST APIs"] == REQUIRED
    assert result["Docker"] == PREFERRED         # "is a plus" on the line
    assert result["AWS"] == PREFERRED            # under "Nice to have"
    assert result["Google Cloud Platform"] == PREFERRED
    assert result["React"] == PREFERRED


def test_evidence_is_the_source_line():
    items = {i.name: i for i in extract_job_skills(JD, DICTIONARY)}
    assert items["PostgreSQL"].evidence == "- Solid SQL skills; we use PostgreSQL"


def test_ambiguous_aliases_are_not_extracted_from_prose():
    names = kinds(extract_job_skills("We go above and beyond. R&D team. Excel at teamwork.", DICTIONARY))
    assert names == {}


def test_empty_description():
    assert extract_job_skills("", DICTIONARY) == []
