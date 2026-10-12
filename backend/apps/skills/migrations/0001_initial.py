import django.db.models.deletion
import django.db.models.functions.text
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Skill",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100, unique=True)),
                ("slug", models.SlugField(max_length=100, unique=True)),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("language", "Programming language"),
                            ("frontend", "Frontend"),
                            ("backend", "Backend"),
                            ("database", "Database"),
                            ("cloud_devops", "Cloud & DevOps"),
                            ("data_ml", "Data & ML"),
                            ("testing", "Testing"),
                            ("tool", "Tool"),
                            ("concept", "Concept / practice"),
                        ],
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="SkillAlias",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("alias", models.CharField(max_length=100)),
                ("is_ambiguous", models.BooleanField(default=False)),
                (
                    "skill",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="aliases",
                        to="skills.skill",
                    ),
                ),
            ],
            options={
                "verbose_name_plural": "skill aliases",
                "ordering": ["alias"],
                "constraints": [
                    models.UniqueConstraint(
                        django.db.models.functions.text.Lower("alias"), name="skill_alias_unique_ci"
                    )
                ],
            },
        ),
    ]
