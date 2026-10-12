import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("jobs", "0001_initial"),
        ("resumes", "0002_structured_resume_data"),
    ]

    operations = [
        migrations.CreateModel(
            name="Analysis",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("resume_title", models.CharField(max_length=150)),
                ("job_title", models.CharField(max_length=200)),
                (
                    "score",
                    models.DecimalField(decimal_places=1, help_text="Resume-to-job matching score, 0-100.", max_digits=4),
                ),
                ("required_coverage", models.DecimalField(blank=True, decimal_places=1, max_digits=4, null=True)),
                ("preferred_coverage", models.DecimalField(blank=True, decimal_places=1, max_digits=4, null=True)),
                ("required_share", models.DecimalField(decimal_places=2, max_digits=3)),
                ("algorithm_version", models.CharField(max_length=30)),
                ("breakdown", models.JSONField(default=dict)),
                ("strengths", models.JSONField(default=list)),
                ("improvements", models.JSONField(default=list)),
                ("suggestions", models.JSONField(default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "job",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="analyses",
                        to="jobs.jobdescription",
                    ),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="analyses",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "resume",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="analyses",
                        to="resumes.resume",
                    ),
                ),
            ],
            options={
                "verbose_name_plural": "analyses",
                "ordering": ["-created_at"],
                "indexes": [models.Index(fields=["owner", "-created_at"], name="analysis_owner_created_idx")],
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(("score__gte", 0), ("score__lte", 100)), name="analysis_score_0_100"
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="AnalysisSkillResult",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("skill_name", models.CharField(max_length=100)),
                (
                    "kind",
                    models.CharField(choices=[("required", "Required"), ("preferred", "Preferred")], max_length=10),
                ),
                ("weight", models.PositiveSmallIntegerField()),
                (
                    "status",
                    models.CharField(
                        choices=[("matched", "Matched"), ("missing", "Missing"), ("related", "Related skill found")],
                        max_length=10,
                    ),
                ),
                ("evidence", models.JSONField(default=list, help_text='[{"location": ..., "text": ...}]')),
                ("related_to", models.JSONField(default=list)),
                ("related_reason", models.CharField(blank=True, max_length=200)),
                ("explanation", models.TextField()),
                ("position", models.PositiveSmallIntegerField(default=0)),
                (
                    "analysis",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="skill_results",
                        to="analyses.analysis",
                    ),
                ),
            ],
            options={
                "ordering": ["position", "id"],
                "constraints": [
                    models.UniqueConstraint(fields=("analysis", "skill_name"), name="analysis_result_unique_skill")
                ],
            },
        ),
    ]
