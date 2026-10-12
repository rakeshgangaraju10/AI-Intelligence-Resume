from django.contrib import admin

from .models import Analysis, AnalysisSkillResult


class AnalysisSkillResultInline(admin.TabularInline):
    model = AnalysisSkillResult
    extra = 0
    fields = ["skill_name", "kind", "weight", "status", "related_reason"]
    readonly_fields = fields
    can_delete = False


@admin.register(Analysis)
class AnalysisAdmin(admin.ModelAdmin):
    list_display = ["id", "owner", "resume_title", "job_title", "score", "algorithm_version", "created_at"]
    list_filter = ["algorithm_version", "created_at"]
    search_fields = ["owner__email", "resume_title", "job_title"]
    list_select_related = ["owner"]
    readonly_fields = [f.name for f in Analysis._meta.fields]
    inlines = [AnalysisSkillResultInline]

    def has_add_permission(self, request) -> bool:
        return False  # analyses are only produced by the matching engine
