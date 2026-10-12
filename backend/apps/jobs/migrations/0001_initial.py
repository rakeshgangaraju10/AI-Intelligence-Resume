import django.core.validators
import django.db.models.deletion
import django.db.models.functions.text
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("skills", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="JobDescription",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=200)),
                ("company", models.CharField(blank=True, max_length=200)),
                (
                    "experience_level",
                    models.CharField(
                        choices=[
                            ("unspecified", "Not specified"),
                            ("internship", "Internship"),
                            ("entry", "Entry level / fresher"),
                            ("mid", "Mid level"),
                            ("senior", "Senior"),
                        ],
                        default="unspecified",
                        max_length=20,
                    ),
                ),
                ("description", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="jobs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [models.Index(fields=["owner", "-created_at"], name="job_owner_created_idx")],
            },
        ),
        migrations.CreateModel(
            name="JobRequirement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                (
                    "kind",
                    models.CharField(
                        choices=[("required", "Required"), ("preferred", "Preferred")],
                        default="required",
                        max_length=10,
                    ),
                ),
                (
                    "weight",
                    models.PositiveSmallIntegerField(
                        default=1,
                        help_text="Relative importance, 1 (normal) to 5 (critical).",
                        validators=[
                            django.core.validators.MinValueValidator(1),
                            django.core.validators.MaxValueValidator(5),
                        ],
                    ),
                ),
                (
                    "source",
                    models.CharField(
                        choices=[("extracted", "Suggested from the description"), ("user", "Added by user")],
                        default="user",
                        max_length=10,
                    ),
                ),
                (
                    "evidence",
                    models.CharField(blank=True, help_text="Description line it was suggested from.", max_length=300),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "job",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="requirements",
                        to="jobs.jobdescription",
                    ),
                ),
                (
                    "skill",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="job_requirements",
                        to="skills.skill",
                    ),
                ),
            ],
            options={
                "ordering": ["-kind", "-weight", "id"],
                "constraints": [
                    models.UniqueConstraint(
                        models.F("job"),
                        django.db.models.functions.text.Lower("name"),
                        name="job_requirement_unique_name_ci",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(("weight__gte", 1), ("weight__lte", 5)),
                        name="job_requirement_weight_1_5",
                    ),
                ],
            },
        ),
    ]
