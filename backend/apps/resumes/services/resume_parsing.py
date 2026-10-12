"""
Run the rule-based parser on a resume's extracted text and store the result.

Re-parsing rules (so user work is never lost):
  * the profile is overwritten only while `user_edited` is False;
  * parser rows that are still unverified are replaced;
  * user-created rows and verified rows are kept, and a parsed entry that
    duplicates a kept row is skipped.
"""
import logging
from collections.abc import Callable, Iterable
from dataclasses import asdict

from django.db import transaction
from django.db.models import Max, Model
from django.utils import timezone

from apps.skills.dictionary import SkillDictionary
from apps.skills.models import Skill
from apps.skills.services import load_skill_dictionary

from ..models import (
    EntrySource,
    Resume,
    ResumeCertification,
    ResumeEducation,
    ResumeExperience,
    ResumeProfile,
    ResumeProject,
    ResumeSkill,
)
from .parsing.resume_normalizer import parse_resume_text
from .parsing.types import ParsedResume

logger = logging.getLogger(__name__)


def _key(*values: str) -> tuple[str, ...]:
    return tuple(" ".join((v or "").split()).lower() for v in values)


def _replace_entries(
    resume: Resume,
    model: type[Model],
    parsed_rows: Iterable[dict],
    key_fields: tuple[str, ...],
    extra: Callable[[dict], dict] | None = None,
) -> None:
    model.objects.filter(resume=resume, source=EntrySource.PARSER, is_verified=False).delete()
    kept = model.objects.filter(resume=resume)
    existing_keys = {_key(*(getattr(row, f) for f in key_fields)) for row in kept}
    next_position = (kept.aggregate(m=Max("position"))["m"] or 0) + 1

    new_rows = []
    for data in parsed_rows:
        key = _key(*(data.get(f, "") for f in key_fields))
        if key in existing_keys:
            continue
        existing_keys.add(key)
        values = {**data, **(extra(data) if extra else {})}
        new_rows.append(
            model(resume=resume, source=EntrySource.PARSER, is_verified=False, position=next_position, **values)
        )
        next_position += 1
    model.objects.bulk_create(new_rows)


def store_parsed_resume(resume: Resume, parsed: ParsedResume) -> None:
    with transaction.atomic():
        profile, _ = ResumeProfile.objects.select_for_update().get_or_create(resume=resume)
        if not profile.user_edited:
            contact = parsed.contact
            profile.full_name = contact.full_name
            profile.email = contact.email
            profile.phone = contact.phone
            profile.location = contact.location
            profile.links = contact.links[:10]
            profile.summary = parsed.summary
            profile.save()

        skill_ids = dict(
            Skill.objects.filter(name__in=[s.name for s in parsed.skills]).values_list("name", "id")
        )
        _replace_entries(
            resume,
            ResumeSkill,
            [{"name": s.name, "section": s.section[:60], "evidence": s.evidence} for s in parsed.skills],
            key_fields=("name",),
            extra=lambda d: {"skill_id": skill_ids.get(d["name"])},
        )
        _replace_entries(resume, ResumeEducation, [asdict(e) for e in parsed.education], ("institution", "degree"))
        _replace_entries(resume, ResumeExperience, [asdict(e) for e in parsed.experience], ("title", "company"))
        _replace_entries(resume, ResumeProject, [asdict(e) for e in parsed.projects], ("name",))
        _replace_entries(resume, ResumeCertification, [asdict(e) for e in parsed.certifications], ("name",))

        resume.status = Resume.Status.PARSED
        resume.error_code = ""
        resume.parse_warnings = parsed.warnings
        resume.parsed_at = timezone.now()
        resume.save(update_fields=["status", "error_code", "parse_warnings", "parsed_at", "updated_at"])


def parse_and_store(resume: Resume, dictionary: SkillDictionary | None = None) -> ParsedResume:
    parsed = parse_resume_text(resume.extracted_text, dictionary or load_skill_dictionary())
    store_parsed_resume(resume, parsed)
    logger.info(
        "Resume parsed id=%s skills=%s education=%s experience=%s projects=%s certifications=%s warnings=%s",
        resume.id, len(parsed.skills), len(parsed.education), len(parsed.experience),
        len(parsed.projects), len(parsed.certifications), len(parsed.warnings),
    )
    return parsed


def try_parse_and_store(resume: Resume) -> bool:
    """
    Parse after upload. A parser bug must not lose the upload: on failure the
    resume keeps its extracted text, gets error_code="parse_failed", and the user
    can retry via the reparse endpoint or enter data manually.
    """
    try:
        parse_and_store(resume)
        return True
    except Exception:  # noqa: BLE001 - see docstring
        logger.exception("Resume parsing failed id=%s", resume.id)
        Resume.objects.filter(pk=resume.pk).update(error_code="parse_failed")
        resume.error_code = "parse_failed"
        return False
