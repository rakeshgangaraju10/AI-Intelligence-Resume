from django.conf import settings
from django.db import models


class Analysis(models.Model):
    """
    A point-in-time comparison of one resume version against one job.

    Results are stored (not recomputed) so history stays accurate even if the
    resume data or job requirements are edited later. Titles are snapshotted
    for the same reason.
    """

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="analyses")
    resume = models.ForeignKey("resumes.Resume", on_delete=models.CASCADE, related_name="analyses")
    job = models.ForeignKey("jobs.JobDescription", on_delete=models.CASCADE, related_name="analyses")
    resume_title = models.CharField(max_length=150)
    job_title = models.CharField(max_length=200)
    score = models.DecimalField(max_digits=4, decimal_places=1, help_text="Resume-to-job matching score, 0-100.")
    required_coverage = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    preferred_coverage = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    required_share = models.DecimalField(max_digits=3, decimal_places=2)
    algorithm_version = models.CharField(max_length=30)
    breakdown = models.JSONField(default=dict)
    strengths = models.JSONField(default=list)
    improvements = models.JSONField(default=list)
    suggestions = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "analyses"
        indexes = [models.Index(fields=["owner", "-created_at"], name="analysis_owner_created_idx")]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(score__gte=0) & models.Q(score__lte=100), name="analysis_score_0_100"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.resume_title} vs {self.job_title}: {self.score}"


class AnalysisSkillResult(models.Model):
    """One job requirement and how the resume did against it, with the reason."""

    class Status(models.TextChoices):
        MATCHED = "matched", "Matched"
        MISSING = "missing", "Missing"
        RELATED = "related", "Related skill found"

    class Kind(models.TextChoices):
        REQUIRED = "required", "Required"
        PREFERRED = "preferred", "Preferred"

    analysis = models.ForeignKey(Analysis, on_delete=models.CASCADE, related_name="skill_results")
    skill_name = models.CharField(max_length=100)
    kind = models.CharField(max_length=10, choices=Kind.choices)
    weight = models.PositiveSmallIntegerField()
    status = models.CharField(max_length=10, choices=Status.choices)
    evidence = models.JSONField(default=list, help_text='[{"location": ..., "text": ...}]')
    related_to = models.JSONField(default=list)
    related_reason = models.CharField(max_length=200, blank=True)
    explanation = models.TextField()
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["position", "id"]
        constraints = [
            models.UniqueConstraint(fields=["analysis", "skill_name"], name="analysis_result_unique_skill"),
        ]

    def __str__(self) -> str:
        return f"{self.skill_name}: {self.status}"
