"""Create jobs and their requirements; suggest requirements from the description."""
from django.db import transaction

from apps.skills.dictionary import SkillDictionary
from apps.skills.models import Skill
from apps.skills.services import load_skill_dictionary

from ..models import JobDescription, JobRequirement
from .jd_extractor import extract_job_skills


def canonical_name(name: str, dictionary: SkillDictionary) -> str:
    cleaned = " ".join(name.split())
    return dictionary.resolve(cleaned) or cleaned


def add_suggested_requirements(job: JobDescription, dictionary: SkillDictionary | None = None) -> int:
    """
    Add skills found in the description that the job doesn't already list.
    Never removes or changes existing requirements. Returns how many were added.
    """
    dictionary = dictionary or load_skill_dictionary()
    existing = {n.lower() for n in job.requirements.values_list("name", flat=True)}
    suggestions = [s for s in extract_job_skills(job.description, dictionary) if s.name.lower() not in existing]
    skill_ids = dict(Skill.objects.filter(name__in=[s.name for s in suggestions]).values_list("name", "id"))
    JobRequirement.objects.bulk_create(
        JobRequirement(
            job=job,
            name=s.name,
            skill_id=skill_ids.get(s.name),
            kind=s.kind,
            weight=1,
            source=JobRequirement.Source.EXTRACTED,
            evidence=s.evidence,
        )
        for s in suggestions
    )
    return len(suggestions)


@transaction.atomic
def create_job(owner, *, fields: dict, required: list[dict], preferred: list[dict], auto_extract: bool) -> JobDescription:
    """
    `required` / `preferred` are [{"name", "weight"}] lists already validated and
    canonicalised by the serializer. Explicit lists win over extracted suggestions.
    """
    job = JobDescription.objects.create(owner=owner, **fields)
    explicit: dict[str, JobRequirement] = {}
    for kind, items in ((JobRequirement.Kind.REQUIRED, required), (JobRequirement.Kind.PREFERRED, preferred)):
        for item in items:
            key = item["name"].lower()
            if key in explicit:
                continue  # required was processed first, so it wins
            explicit[key] = JobRequirement(job=job, name=item["name"], kind=kind, weight=item["weight"])
    skill_ids = dict(Skill.objects.filter(name__in=[r.name for r in explicit.values()]).values_list("name", "id"))
    for req in explicit.values():
        req.skill_id = skill_ids.get(req.name)
    JobRequirement.objects.bulk_create(explicit.values())
    if auto_extract and job.description:
        add_suggested_requirements(job)
    return job
