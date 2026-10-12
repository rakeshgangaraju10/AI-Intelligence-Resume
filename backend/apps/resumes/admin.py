from django.contrib import admin

from .models import Resume


@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    """
    Operational view of processing records. The resume file and its full text
    are deliberately excluded so routine administration doesn't expose
    candidates' personal data.
    """

    list_display = ["id", "owner", "title", "status", "error_code", "page_count", "file_size", "created_at"]
    list_filter = ["status", "created_at"]
    search_fields = ["owner__email", "title"]
    list_select_related = ["owner"]
    fields = [
        "id", "owner", "title", "original_filename", "status", "error_code",
        "page_count", "file_size", "sha256", "created_at", "updated_at",
    ]
    readonly_fields = fields

    def has_add_permission(self, request) -> bool:
        return False  # resumes are only created through the validated upload API
