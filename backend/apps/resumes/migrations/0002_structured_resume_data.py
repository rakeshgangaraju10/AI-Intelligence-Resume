import django.db.models.deletion
import django.db.models.functions.text
from django.db import migrations, models

SOURCE_CHOICES = [("parser", "Extracted by parser"), ("user", "Added by user")]


def entry_fields():
    """Fields inherited from the abstract ResumeEntry model."""
    return [
        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
        ("source", models.CharField(choices=SOURCE_CHOICES, default="parser", max_length=10)),
        ("is_verified", models.BooleanField(default=False)),
        ("position", models.PositiveIntegerField(default=0)),
        ("created_at", models.DateTimeField(auto_now_add=True)),
        ("updated_at", models.DateTimeField(auto_now=True)),
    ]


def resume_fk(related_name):
    return (
        "resume",
        models.ForeignKey(
            on_delete=django.db.models.deletion.CASCADE,
            related_name=related_name,
            to="resumes.resume",
        ),
    )


class Migration(migrations.Migration):

    dependencies = [
        ("resumes", "0001_initial"),
        ("skills", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="resume",
            name="parse_warnings",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="resume",
            name="parsed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="ResumeProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("full_name", models.CharField(blank=True, max_length=150)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("phone", models.CharField(blank=True, max_length=30)),
                ("location", models.CharField(blank=True, max_length=120)),
                ("links", models.JSONField(blank=True, default=list)),
                ("summary", models.TextField(blank=True)),
                ("user_edited", models.BooleanField(default=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "resume",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="profile",
                        to="resumes.resume",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ResumeSkill",
            fields=[
                *entry_fields(),
                ("name", models.CharField(max_length=100)),
                ("section", models.CharField(blank=True, help_text="Section where the parser found it.", max_length=60)),
                ("evidence", models.CharField(blank=True, help_text="Resume line containing the mention.", max_length=300)),
                resume_fk("skills"),
                (
                    "skill",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="resume_skills",
                        to="skills.skill",
                    ),
                ),
            ],
            options={
                "ordering": ["position", "id"],
                "abstract": False,
                "constraints": [
                    models.UniqueConstraint(
                        models.F("resume"),
                        django.db.models.functions.text.Lower("name"),
                        name="resume_skill_unique_name_ci",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="ResumeEducation",
            fields=[
                *entry_fields(),
                ("institution", models.CharField(blank=True, max_length=200)),
                ("degree", models.CharField(blank=True, max_length=200)),
                ("field_of_study", models.CharField(blank=True, max_length=200)),
                ("start_date", models.CharField(blank=True, max_length=30)),
                ("end_date", models.CharField(blank=True, max_length=30)),
                ("grade", models.CharField(blank=True, max_length=50)),
                ("description", models.TextField(blank=True)),
                resume_fk("education"),
            ],
            options={
                "verbose_name_plural": "resume education",
                "ordering": ["position", "id"],
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="ResumeExperience",
            fields=[
                *entry_fields(),
                ("title", models.CharField(blank=True, max_length=200)),
                ("company", models.CharField(blank=True, max_length=200)),
                ("location", models.CharField(blank=True, max_length=120)),
                ("start_date", models.CharField(blank=True, max_length=30)),
                ("end_date", models.CharField(blank=True, max_length=30)),
                ("is_current", models.BooleanField(default=False)),
                ("description", models.TextField(blank=True)),
                resume_fk("experience"),
            ],
            options={
                "verbose_name_plural": "resume experience",
                "ordering": ["position", "id"],
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="ResumeProject",
            fields=[
                *entry_fields(),
                ("name", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True)),
                ("technologies", models.JSONField(blank=True, default=list)),
                ("url", models.CharField(blank=True, max_length=300)),
                resume_fk("projects"),
            ],
            options={
                "ordering": ["position", "id"],
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="ResumeCertification",
            fields=[
                *entry_fields(),
                ("name", models.CharField(max_length=200)),
                ("issuer", models.CharField(blank=True, max_length=200)),
                ("issue_date", models.CharField(blank=True, max_length=30)),
                ("credential_url", models.CharField(blank=True, max_length=300)),
                resume_fk("certifications"),
            ],
            options={
                "ordering": ["position", "id"],
                "abstract": False,
            },
        ),
    ]
