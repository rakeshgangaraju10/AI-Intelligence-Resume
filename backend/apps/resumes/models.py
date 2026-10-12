import uuid

from django.conf import settings
from django.db import models

from .storage import private_resume_storage, resume_upload_path


class Resume(models.Model):
    """
    One uploaded resume file plus the raw text extracted from it.

    Structured data (skills, education, ...) is added in a later stage as
    separate related models; this table stays the immutable "source document".
    Each upload is its own row, which doubles as simple version history.
    """

    class Status(models.TextChoices):
        TEXT_EXTRACTED = "text_extracted", "Text extracted"
        PARSED = "parsed", "Parsed"            # set by the Stage 4 parsing pipeline
        FAILED = "failed", "Failed"            # set when a later processing step fails

    # UUIDs avoid exposing sequential, guessable ids (ownership is still enforced).
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="resumes"
    )
    title = models.CharField(max_length=150)
    original_filename = models.CharField(max_length=255)
    file = models.FileField(
        upload_to=resume_upload_path, storage=private_resume_storage, max_length=255
    )
    file_size = models.PositiveIntegerField(help_text="Size in bytes.")
    sha256 = models.CharField(max_length=64, help_text="Hex digest of the uploaded bytes.")
    page_count = models.PositiveSmallIntegerField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.TEXT_EXTRACTED
    )
    error_code = models.CharField(max_length=50, blank=True)
    extracted_text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["owner", "-created_at"], name="resume_owner_created_idx"),
            models.Index(fields=["owner", "sha256"], name="resume_owner_sha256_idx"),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(file_size__gt=0), name="resume_file_size_positive"),
            models.CheckConstraint(condition=models.Q(page_count__gt=0), name="resume_page_count_positive"),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.id})"
