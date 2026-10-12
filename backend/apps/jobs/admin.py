from django.contrib import admin

from .models import JobDescription, JobRequirement


class JobRequirementInline(admin.TabularInline):
    model = JobRequirement
    extra = 0
    fields = ["name", "kind", "weight", "source", "skill"]
    autocomplete_fields = ["skill"]


@admin.register(JobDescription)
class JobDescriptionAdmin(admin.ModelAdmin):
    list_display = ["title", "company", "experience_level", "owner", "created_at"]
    list_filter = ["experience_level", "created_at"]
    search_fields = ["title", "company", "owner__email"]
    list_select_related = ["owner"]
    inlines = [JobRequirementInline]
