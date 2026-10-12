"""
Seed the canonical skills dictionary from apps/skills/data/skills_seed.json.

Every canonical name also gets an alias row so the matcher has a single source
of truth and an admin can flag a canonical name as ambiguous (e.g. "Go", "R").
Idempotent: existing skills/aliases are left untouched.
"""
import json
from pathlib import Path

from django.db import migrations

SEED_FILE = Path(__file__).resolve().parent.parent / "data" / "skills_seed.json"


def seed_skills(apps, schema_editor):
    from apps.skills.utils import skill_slug

    Skill = apps.get_model("skills", "Skill")
    SkillAlias = apps.get_model("skills", "SkillAlias")
    entries = json.loads(SEED_FILE.read_text(encoding="utf-8"))

    for entry in entries:
        skill, _ = Skill.objects.get_or_create(
            name=entry["name"],
            defaults={"slug": skill_slug(entry["name"]), "category": entry["category"]},
        )
        ambiguous = set(entry.get("ambiguous", []))
        for alias in [entry["name"], *entry.get("aliases", [])]:
            if not SkillAlias.objects.filter(alias__iexact=alias).exists():
                SkillAlias.objects.create(
                    skill=skill, alias=alias, is_ambiguous=alias in ambiguous
                )


def unseed_skills(apps, schema_editor):
    Skill = apps.get_model("skills", "Skill")
    names = [e["name"] for e in json.loads(SEED_FILE.read_text(encoding="utf-8"))]
    Skill.objects.filter(name__in=names).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("skills", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_skills, unseed_skills),
    ]
