"""
Unit tests for the rule-based parsing pipeline. Pure Python: no database needed.
The skill dictionary is built from the same seed file the migration loads.
"""
import json
from pathlib import Path

from apps.resumes.services.parsing.certification_extractor import extract_certifications
from apps.resumes.services.parsing.contact_extractor import extract_contact
from apps.resumes.services.parsing.education_extractor import extract_education
from apps.resumes.services.parsing.experience_extractor import extract_experience
from apps.resumes.services.parsing.project_extractor import extract_projects
from apps.resumes.services.parsing.resume_normalizer import parse_resume_text
from apps.resumes.services.parsing.section_extractor import split_sections
from apps.resumes.services.parsing.skill_extractor import extract_skills
from apps.skills.dictionary import AliasEntry, SkillDictionary

SEED = Path(__file__).resolve().parent.parent / "apps" / "skills" / "data" / "skills_seed.json"


def build_dictionary() -> SkillDictionary:
    entries = []
    for skill in json.loads(SEED.read_text(encoding="utf-8")):
        ambiguous = set(skill["ambiguous"])
        for alias in [skill["name"], *skill["aliases"]]:
            entries.append(AliasEntry(alias, skill["name"], alias in ambiguous))
    return SkillDictionary(entries)


DICTIONARY = build_dictionary()

SAMPLE = """PRIYA SHARMA
Bengaluru, India | priya.sharma@example.com | +91 98765 43210
linkedin.com/in/priya-example | github.com/priya-example

PROFESSIONAL SUMMARY
Computer Science graduate focused on backend development.

TECHNICAL SKILLS
Languages: Python, JavaScript, C, SQL
Frameworks: Django, DRF, React.js
Tools: Git, Docker, Postgres

EXPERIENCE
Software Engineering Intern | Acme Analytics | Hyderabad
Jun 2024 - Aug 2024
• Built REST APIs with Django REST Framework for internal dashboards.
• Wrote pytest suites and set up GitHub Actions
for continuous integration.
Teaching Assistant, Example Institute of Technology   Jan 2023 – Present
• Ran weekly lab sessions.

EDUCATION
B.Tech in Computer Science and Engineering, Example Institute of Technology   2021 - 2025
CGPA: 8.6/10
Class XII, Sunrise Senior Secondary School, 2021 | 92.4%

PROJECTS
CareerForge - Resume intelligence platform
• Django REST API with PostgreSQL and a React + TypeScript frontend.
• Source: github.com/priya-example/careerforge
Movie Recommender
• Content-based recommender using Pandas and scikit-learn.

CERTIFICATIONS
• AWS Certified Cloud Practitioner - Amazon Web Services (2024)
• Python for Everybody | Coursera | Mar 2023

ACHIEVEMENTS
• Winner, college hackathon 2023 (Go team!)
"""


def names(matches) -> list[str]:
    return [m.skill_name for m in matches]


# --- Skill dictionary -----------------------------------------------------------


def test_aliases_normalise_to_canonical_names():
    found = names(DICTIONARY.find("JS, Postgres, ReactJS, sklearn, K8s"))
    assert found == ["JavaScript", "PostgreSQL", "React", "scikit-learn", "Kubernetes"]


def test_no_substring_matches_inside_other_words():
    assert names(DICTIONARY.find("Javadoc, Googled, reactive, gopher, Rustic, scalable")) == []


def test_longest_alias_wins():
    assert names(DICTIONARY.find("Java and JavaScript")) == ["Java", "JavaScript"]
    assert names(DICTIONARY.find("C++ and C# and ASP.NET")) == ["C++", "C#", ".NET"]
    assert names(DICTIONARY.find("Spring Boot", allow_ambiguous=True)) == ["Spring Boot"]
    assert names(DICTIONARY.find("Node.js")) == ["Node.js"]


def test_ambiguous_aliases_need_explicit_permission_and_exact_case():
    text = "C, R, Go, Excel"
    assert names(DICTIONARY.find(text)) == []
    assert names(DICTIONARY.find(text, allow_ambiguous=True)) == ["C", "R", "Go", "Microsoft Excel"]
    assert names(DICTIONARY.find("go, excel", allow_ambiguous=True)) == []
    assert names(DICTIONARY.find("R&D, C-suite", allow_ambiguous=True)) == []


def test_resolve_is_exact_and_case_insensitive():
    assert DICTIONARY.resolve("postgres") == "PostgreSQL"
    assert DICTIONARY.resolve("  js ") == "JavaScript"
    assert DICTIONARY.resolve("Postgres database") is None


# --- Sections ---------------------------------------------------------------------


def test_sections_are_detected_with_synonyms_and_inline_skills():
    sectioned = split_sections(SAMPLE)
    assert sectioned.headings_found == [
        "summary", "skills", "experience", "education", "projects",
        "certifications", "other:achievements",
    ]
    assert sectioned.header[0] == "PRIYA SHARMA"
    inline = split_sections("Technical Skills: Python, Django\nEXPERIENCE\nx")
    assert inline.get("skills") == ["Python, Django"]


def test_label_lines_inside_skills_do_not_open_sections():
    sectioned = split_sections("SKILLS\nLanguages: Python\nExperience: 2 years")
    assert sectioned.headings_found == ["skills"]
    assert len(sectioned.get("skills")) == 2


def test_missing_sections_do_not_crash():
    parsed = parse_resume_text("Just a name\nand a line of text", DICTIONARY)
    assert parsed.education == [] and parsed.experience == [] and parsed.projects == []
    assert "section_not_found:skills" in parsed.warnings
    assert "no_skills_detected" in parsed.warnings


def test_empty_text():
    parsed = parse_resume_text("", DICTIONARY)
    assert parsed.skills == []
    assert parsed.contact.full_name == ""


# --- Contact ----------------------------------------------------------------------


def test_contact_details_come_from_text_only():
    sectioned = split_sections(SAMPLE)
    contact = extract_contact(sectioned.header, SAMPLE)
    assert contact.full_name == "Priya Sharma"
    assert contact.email == "priya.sharma@example.com"
    assert contact.phone == "+91 98765 43210"
    assert contact.links == ["linkedin.com/in/priya-example", "github.com/priya-example"]
    assert contact.location == ""  # not guessed


def test_year_ranges_are_not_phone_numbers():
    contact = extract_contact(["Alex Example", "2019 - 2023"], "")
    assert contact.phone == ""


# --- Skills -----------------------------------------------------------------------


def test_skills_have_section_and_evidence_and_ignore_urls():
    sectioned = split_sections(SAMPLE)
    hits = {h.name: h for h in extract_skills(sectioned, DICTIONARY)}
    assert hits["C"].section == "skills"  # ambiguous alias allowed in Skills section
    assert hits["Django REST Framework"].section == "skills"  # "DRF" in skills
    assert hits["PostgreSQL"].evidence == "Tools: Git, Docker, Postgres"
    assert hits["pytest"].section == "experience"
    assert "GitHub" not in hits  # only appears inside URLs
    assert "Go" not in hits  # "Go team!" outside the Skills section


def test_each_skill_reported_once():
    sectioned = split_sections("SKILLS\nPython, python3, Python\nPROJECTS\nApp\n• Python app")
    hits = extract_skills(sectioned, DICTIONARY)
    assert [h.name for h in hits] == ["Python"]


# --- Education --------------------------------------------------------------------


def test_education_entries():
    entries = extract_education(split_sections(SAMPLE).get("education"))
    assert len(entries) == 2
    btech, school = entries
    assert btech.degree == "B.Tech"
    assert btech.field_of_study == "Computer Science and Engineering"
    assert btech.institution == "Example Institute of Technology"
    assert (btech.start_date, btech.end_date) == ("2021", "2025")
    assert btech.grade == "CGPA: 8.6/10"
    assert school.degree == "Class XII"
    assert school.institution == "Sunrise Senior Secondary School"
    assert school.end_date == "2021"
    assert school.grade == "92.4%"


def test_education_without_recognisable_degree_or_institution_is_not_invented():
    assert extract_education(["Studied many things", "2019"]) == []


# --- Experience -------------------------------------------------------------------


def test_experience_entries():
    entries = extract_experience(split_sections(SAMPLE).get("experience"))
    assert len(entries) == 2
    intern, ta = entries
    assert intern.title == "Software Engineering Intern"
    assert intern.company == "Acme Analytics"
    assert intern.location == "Hyderabad"
    assert (intern.start_date, intern.end_date, intern.is_current) == ("Jun 2024", "Aug 2024", False)
    assert intern.description.splitlines()[1] == (
        "Wrote pytest suites and set up GitHub Actions for continuous integration."
    )
    assert ta.title == "Teaching Assistant"
    assert ta.company == "Example Institute of Technology"
    assert ta.is_current is True and ta.end_date == ""


def test_experience_without_dates_is_not_structured():
    parsed = parse_resume_text("EXPERIENCE\nDid some freelance work for clients\n", DICTIONARY)
    assert parsed.experience == []
    assert "experience_unstructured" in parsed.warnings


# --- Projects ---------------------------------------------------------------------


def test_project_entries_with_explicit_technologies():
    projects = extract_projects(split_sections(SAMPLE).get("projects"), DICTIONARY)
    assert [p.name for p in projects] == ["CareerForge", "Movie Recommender"]
    careerforge, recommender = projects
    assert careerforge.description.startswith("Resume intelligence platform")
    assert careerforge.url == "github.com/priya-example/careerforge"
    assert careerforge.technologies == ["Django", "REST APIs", "PostgreSQL", "React", "TypeScript"]
    assert recommender.technologies == ["Pandas", "scikit-learn"]


# --- Certifications ---------------------------------------------------------------


def test_certification_entries():
    certs = extract_certifications(split_sections(SAMPLE).get("certifications"))
    assert [(c.name, c.issuer, c.issue_date) for c in certs] == [
        ("AWS Certified Cloud Practitioner", "Amazon Web Services", "2024"),
        ("Python for Everybody", "Coursera", "Mar 2023"),
    ]


# --- Whole pipeline ---------------------------------------------------------------


def test_full_pipeline_has_no_warnings_for_complete_resume():
    parsed = parse_resume_text(SAMPLE, DICTIONARY)
    assert parsed.warnings == []
    assert len(parsed.education) == 2
    assert len(parsed.experience) == 2
    assert len(parsed.projects) == 2
    assert len(parsed.certifications) == 2


def test_long_values_are_truncated_to_column_limits():
    parsed = parse_resume_text("PROJECTS\n" + "X" * 99 + "\n• " + "word " * 10, DICTIONARY)
    assert all(len(p.name) <= 200 for p in parsed.projects)


def test_one_line_projects_with_inline_descriptions():
    lines = [
        "Inventory Tracker - built a Django API with PostgreSQL.",
        "Chat App: real-time chat with WebSockets.",
        "• Used Redis for presence.",
    ]
    projects = extract_projects(lines, DICTIONARY)
    assert [(p.name, p.technologies) for p in projects] == [
        ("Inventory Tracker", ["Django", "PostgreSQL"]),
        ("Chat App", ["WebSockets", "Redis"]),
    ]
    assert projects[1].description == "real-time chat with WebSockets.\nUsed Redis for presence."
