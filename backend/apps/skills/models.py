from django.db import models
from django.db.models.functions import Lower


class Skill(models.Model):
    """A canonical skill, e.g. "PostgreSQL". Managed by admins; seeded by migration."""

    class Category(models.TextChoices):
        LANGUAGE = "language", "Programming language"
        FRONTEND = "frontend", "Frontend"
        BACKEND = "backend", "Backend"
        DATABASE = "database", "Database"
        CLOUD_DEVOPS = "cloud_devops", "Cloud & DevOps"
        DATA_ML = "data_ml", "Data & ML"
        TESTING = "testing", "Testing"
        TOOL = "tool", "Tool"
        CONCEPT = "concept", "Concept / practice"

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    category = models.CharField(max_length=20, choices=Category.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class SkillAlias(models.Model):
    """
    A surface form that maps to a Skill (e.g. "JS" -> JavaScript).

    `is_ambiguous` marks aliases that are also ordinary words or letters
    ("Go", "R", "C", "Excel", "Spring"). Those are only matched case-sensitively
    inside a resume's Skills section, never in free text.
    """

    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="aliases")
    alias = models.CharField(max_length=100)
    is_ambiguous = models.BooleanField(default=False)

    class Meta:
        ordering = ["alias"]
        constraints = [
            models.UniqueConstraint(Lower("alias"), name="skill_alias_unique_ci"),
        ]
        verbose_name_plural = "skill aliases"

    def __str__(self) -> str:
        return f"{self.alias} -> {self.skill.name}"
