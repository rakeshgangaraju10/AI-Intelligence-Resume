from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.functions import Lower

MAX_DESCRIPTION_CHARS = 20_000


class JobDescription(models.Model):
    """A job posting the user wants to compare resumes against. Saved for reuse."""

    class ExperienceLevel(models.TextChoices):
        UNSPECIFIED = "unspecified", "Not specified"
        INTERNSHIP = "internship", "Internship"
        ENTRY = "entry", "Entry level / fresher"
        MID = "mid", "Mid level"
        SENIOR = "senior", "Senior"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="jobs")
    title = models.CharField(max_length=200)
    company = models.CharField(max_length=200, blank=True)
    experience_level = models.CharField(
        max_length=20, choices=ExperienceLevel.choices, default=ExperienceLevel.UNSPECIFIED
    )
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["owner", "-created_at"], name="job_owner_created_idx")]

    def __str__(self) -> str:
        return f"{self.title} @ {self.company}" if self.company else self.title


class JobRequirement(models.Model):
    """One skill the job asks for, with its importance."""

    class Kind(models.TextChoices):
        REQUIRED = "required", "Required"
        PREFERRED = "preferred", "Preferred"

    class Source(models.TextChoices):
        EXTRACTED = "extracted", "Suggested from the description"
        USER = "user", "Added by user"

    job = models.ForeignKey(JobDescription, on_delete=models.CASCADE, related_name="requirements")
    skill = models.ForeignKey(
        "skills.Skill", on_delete=models.SET_NULL, null=True, blank=True, related_name="job_requirements"
    )
    name = models.CharField(max_length=100)
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.REQUIRED)
    weight = models.PositiveSmallIntegerField(
        default=1, validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Relative importance, 1 (normal) to 5 (critical).",
    )
    source = models.CharField(max_length=10, choices=Source.choices, default=Source.USER)
    evidence = models.CharField(max_length=300, blank=True, help_text="Description line it was suggested from.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-kind", "-weight", "id"]  # required before preferred
        constraints = [
            models.UniqueConstraint("job", Lower("name"), name="job_requirement_unique_name_ci"),
            models.CheckConstraint(
                condition=models.Q(weight__gte=1) & models.Q(weight__lte=5), name="job_requirement_weight_1_5"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.kind}, w{self.weight})"
