"""
Connects stored resume/job data to the pure matching engine and saves the result.

Evidence gathering: for every skill we look for concrete places it appears —
the Skills section line, project texts/technology lists, experience bullets,
certification names — so a match can point at "Project: CareerForge" rather
than just "it's somewhere in the PDF".
"""
from decimal import Decimal

from django.conf import settings
from django.db import transaction

from apps.jobs.models import JobDescription
from apps.resumes.models import EntrySource, Resume
from apps.skills.dictionary import SkillDictionary
from apps.skills.services import load_skill_dictionary, load_skill_groups

from ..models import Analysis, AnalysisSkillResult
from .matching import (
    SKILLS_SECTION,
    Evidence,
    Requirement,
    ResumeSkill,
    match_resume_to_job,
)

MAX_EVIDENCE_PER_SKILL = 3
SECTION_LABELS = {
    "skills": SKILLS_SECTION,
    "experience": "Experience section",
    "projects": "Projects section",
    "certifications": "Certifications section",
    "summary": "Summary",
    "education": "Education section",
    "header": "Resume header",
}


def _line_with(text: str, start: int) -> str:
    """The line of `text` containing character offset `start`."""
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", start)
    return text[line_start: line_end if line_end != -1 else len(text)].strip()


def _scan(dictionary: SkillDictionary, text: str) -> dict[str, str]:
    """{skill_name: line mentioning it} for one block of text."""
    hits: dict[str, str] = {}
    for match in dictionary.find(text):
        hits.setdefault(match.skill_name, _line_with(text, match.start))
    return hits


def build_resume_skills(resume: Resume, dictionary: SkillDictionary) -> list[ResumeSkill]:
    # Keyed by lower-cased skill name; display names kept separately.
    usage: dict[str, list[Evidence]] = {}
    display: dict[str, str] = {}
    verified_by_usage: dict[str, bool] = {}

    def add(name: str, evidence: Evidence, verified: bool) -> None:
        key = name.lower()
        display.setdefault(key, name)
        bucket = usage.setdefault(key, [])
        if evidence not in bucket:
            bucket.append(evidence)
        verified_by_usage[key] = verified_by_usage.get(key, False) or verified

    for project in resume.projects.all():
        label = f"Project: {project.name}" if project.name else "Projects section"
        text = f"{project.name}\n{project.description}"
        for name, line in _scan(dictionary, text).items():
            add(name, Evidence(label, line), project.is_verified)
        for tech in project.technologies:
            canonical = dictionary.resolve(tech) or tech
            add(canonical, Evidence(label, f"Technologies: {', '.join(project.technologies)}"), project.is_verified)

    for job in resume.experience.all():
        who = " at ".join(p for p in (job.title, job.company) if p) or "entry"
        for name, line in _scan(dictionary, f"{job.title}\n{job.description}").items():
            add(name, Evidence(f"Experience: {who}", line), job.is_verified)

    for cert in resume.certifications.all():
        for name, line in _scan(dictionary, cert.name).items():
            add(name, Evidence(f"Certification: {cert.name}", line), cert.is_verified)

    skills: dict[str, ResumeSkill] = {}
    for row in resume.skills.all():
        evidence: list[Evidence] = []
        if row.section == "skills" and row.evidence:
            evidence.append(Evidence(SKILLS_SECTION, row.evidence))
        evidence += usage.get(row.name.lower(), [])
        if not evidence and row.evidence:
            evidence.append(Evidence(SECTION_LABELS.get(row.section, "Resume"), row.evidence))
        user_added = row.source == EntrySource.USER
        skills[row.name.lower()] = ResumeSkill(
            name=row.name,
            evidence=evidence[:MAX_EVIDENCE_PER_SKILL],
            verified=row.is_verified or user_added,
            user_added=user_added,
        )

    # Skills that only appear inside project/experience entries still count:
    # the user can see and edit those entries on the review page.
    for key, evidence in usage.items():
        if key not in skills:
            skills[key] = ResumeSkill(
                name=display[key], evidence=evidence[:MAX_EVIDENCE_PER_SKILL], verified=verified_by_usage[key]
            )
    return list(skills.values())


def _decimal(value: float | None) -> Decimal | None:
    return None if value is None else Decimal(str(value))


def run_analysis(owner, resume: Resume, job: JobDescription) -> Analysis:
    """Compute and store an analysis. Raises matching.MatchingError for unusable jobs."""
    dictionary = load_skill_dictionary()
    resume = (
        Resume.objects.filter(pk=resume.pk)
        .prefetch_related("skills", "projects", "experience", "certifications")
        .get()
    )
    requirements = [Requirement(r.name, r.kind, r.weight) for r in job.requirements.all()]
    result = match_resume_to_job(
        build_resume_skills(resume, dictionary),
        requirements,
        load_skill_groups(),
        required_share=settings.MATCHING_REQUIRED_SHARE,
    )

    with transaction.atomic():
        analysis = Analysis.objects.create(
            owner=owner,
            resume=resume,
            job=job,
            resume_title=resume.title,
            job_title=str(job)[:200],
            score=_decimal(result.score),
            required_coverage=_decimal(result.required_coverage),
            preferred_coverage=_decimal(result.preferred_coverage),
            required_share=Decimal(str(result.required_share)),
            algorithm_version=result.algorithm_version,
            breakdown=result.breakdown,
            strengths=result.strengths,
            improvements=result.improvements,
            suggestions=result.suggestions,
        )
        AnalysisSkillResult.objects.bulk_create(
            AnalysisSkillResult(
                analysis=analysis,
                skill_name=r.name[:100],
                kind=r.kind,
                weight=r.weight,
                status=r.status,
                evidence=[{"location": e.location, "text": e.text} for e in r.evidence],
                related_to=r.related_to,
                related_reason=r.related_reason[:200],
                explanation=r.explanation,
                position=i,
            )
            for i, r in enumerate(result.results)
        )
    return analysis
