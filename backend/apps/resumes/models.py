import uuid

from django.conf import settings
from django.db import models
from django.db.models.functions import Lower

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
        PARSED = "parsed", "Parsed"            # structured data extracted
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
    parse_warnings = models.JSONField(default=list, blank=True)
    parsed_at = models.DateTimeField(null=True, blank=True)
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


# --- Structured data extracted from a resume (Stage 4) ---------------------------


class EntrySource(models.TextChoices):
    PARSER = "parser", "Extracted by parser"
    USER = "user", "Added by user"


class ResumeProfile(models.Model):
    """Contact details and summary. One per resume."""

    resume = models.OneToOneField(Resume, on_delete=models.CASCADE, related_name="profile")
    full_name = models.CharField(max_length=150, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    location = models.CharField(max_length=120, blank=True)
    links = models.JSONField(default=list, blank=True)
    summary = models.TextField(blank=True)
    # Once the user edits the profile, re-parsing never overwrites it.
    user_edited = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Profile of resume {self.resume_id}"


class ResumeEntry(models.Model):
    """
    Common fields for list-type sections.

    source:      who created the row (parser or user).
    is_verified: the user has confirmed or edited it. Re-parsing replaces only
                 parser rows that are still unverified, so user work is never lost.
    """

    source = models.CharField(max_length=10, choices=EntrySource.choices, default=EntrySource.PARSER)
    is_verified = models.BooleanField(default=False)
    position = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["position", "id"]


class ResumeSkill(ResumeEntry):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name="skills")
    # Null for custom skills that are not in the dictionary.
    skill = models.ForeignKey(
        "skills.Skill", on_delete=models.SET_NULL, null=True, blank=True, related_name="resume_skills"
    )
    name = models.CharField(max_length=100)
    section = models.CharField(max_length=60, blank=True, help_text="Section where the parser found it.")
    evidence = models.CharField(max_length=300, blank=True, help_text="Resume line containing the mention.")

    class Meta(ResumeEntry.Meta):
        constraints = [
            models.UniqueConstraint("resume", Lower("name"), name="resume_skill_unique_name_ci"),
        ]

    def __str__(self) -> str:
        return self.name


class ResumeEducation(ResumeEntry):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name="education")
    institution = models.CharField(max_length=200, blank=True)
    degree = models.CharField(max_length=200, blank=True)
    field_of_study = models.CharField(max_length=200, blank=True)
    # Dates are free text ("Jun 2023", "2025"): resumes are inconsistent and we
    # never invent a day or month that isn't written.
    start_date = models.CharField(max_length=30, blank=True)
    end_date = models.CharField(max_length=30, blank=True)
    grade = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)

    class Meta(ResumeEntry.Meta):
        verbose_name_plural = "resume education"

    def __str__(self) -> str:
        return self.degree or self.institution


class ResumeExperience(ResumeEntry):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name="experience")
    title = models.CharField(max_length=200, blank=True)
    company = models.CharField(max_length=200, blank=True)
    location = models.CharField(max_length=120, blank=True)
    start_date = models.CharField(max_length=30, blank=True)
    end_date = models.CharField(max_length=30, blank=True)
    is_current = models.BooleanField(default=False)
    description = models.TextField(blank=True)

    class Meta(ResumeEntry.Meta):
        verbose_name_plural = "resume experience"

    def __str__(self) -> str:
        return f"{self.title} @ {self.company}".strip(" @")


class ResumeProject(ResumeEntry):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name="projects")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    technologies = models.JSONField(default=list, blank=True)
    url = models.CharField(max_length=300, blank=True)

    def __str__(self) -> str:
        return self.name


class ResumeCertification(ResumeEntry):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name="certifications")
    name = models.CharField(max_length=200)
    issuer = models.CharField(max_length=200, blank=True)
    issue_date = models.CharField(max_length=30, blank=True)
    credential_url = models.CharField(max_length=300, blank=True)

    def __str__(self) -> str:
        return self.name
