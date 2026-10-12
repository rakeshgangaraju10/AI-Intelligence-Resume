"""Seed curated related-skill groups from apps/skills/data/skill_groups_seed.json (idempotent)."""
import json
from pathlib import Path

from django.db import migrations

SEED_FILE = Path(__file__).resolve().parent.parent / "data" / "skill_groups_seed.json"


def seed_groups(apps, schema_editor):
    Skill = apps.get_model("skills", "Skill")
    SkillGroup = apps.get_model("skills", "SkillGroup")
    for entry in json.loads(SEED_FILE.read_text(encoding="utf-8")):
        group, _ = SkillGroup.objects.get_or_create(
            name=entry["name"], defaults={"description": entry["description"]}
        )
        group.skills.add(*Skill.objects.filter(name__in=entry["skills"]))


def unseed_groups(apps, schema_editor):
    SkillGroup = apps.get_model("skills", "SkillGroup")
    names = [e["name"] for e in json.loads(SEED_FILE.read_text(encoding="utf-8"))]
    SkillGroup.objects.filter(name__in=names).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("skills", "0003_skillgroup"),
    ]

    operations = [
        migrations.RunPython(seed_groups, unseed_groups),
    ]
