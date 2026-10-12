from django.contrib import admin

from .models import Skill, SkillAlias


class SkillAliasInline(admin.TabularInline):
    model = SkillAlias
    extra = 1


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "alias_count"]
    list_filter = ["category"]
    search_fields = ["name", "aliases__alias"]
    prepopulated_fields = {"slug": ["name"]}
    inlines = [SkillAliasInline]

    def get_queryset(self, request):
        from django.db.models import Count

        return super().get_queryset(request).annotate(_alias_count=Count("aliases"))

    @admin.display(ordering="_alias_count", description="Aliases")
    def alias_count(self, obj: Skill) -> int:
        return obj._alias_count


@admin.register(SkillAlias)
class SkillAliasAdmin(admin.ModelAdmin):
    list_display = ["alias", "skill", "is_ambiguous"]
    list_filter = ["is_ambiguous", "skill__category"]
    search_fields = ["alias", "skill__name"]
    list_select_related = ["skill"]
    autocomplete_fields = ["skill"]
