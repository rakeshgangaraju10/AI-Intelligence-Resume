from .dictionary import AliasEntry, SkillDictionary
from .models import Skill, SkillAlias, SkillGroup


def load_skill_dictionary() -> SkillDictionary:
    """
    Build the matcher from the database (a couple of hundred rows; built per
    parse so admin edits take effect immediately without cache invalidation).
    Canonical names without an explicit alias row are still matchable.
    """
    entries = [
        AliasEntry(alias=a.alias, skill_name=a.skill.name, is_ambiguous=a.is_ambiguous)
        for a in SkillAlias.objects.select_related("skill")
    ]
    covered = {e.alias.lower() for e in entries}
    entries += [
        AliasEntry(alias=name, skill_name=name)
        for name in Skill.objects.values_list("name", flat=True)
        if name.lower() not in covered
    ]
    return SkillDictionary(entries)


def load_skill_groups() -> list[tuple[str, frozenset[str]]]:
    """[(description, {skill names})] for related-skill explanations."""
    return [
        (group.description, frozenset(s.name for s in group.skills.all()))
        for group in SkillGroup.objects.prefetch_related("skills")
    ]
