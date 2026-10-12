from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("skills", "0002_seed_skills"),
    ]

    operations = [
        migrations.CreateModel(
            name="SkillGroup",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100, unique=True)),
                (
                    "description",
                    models.CharField(help_text="Shown to users, e.g. 'relational databases'.", max_length=200),
                ),
                ("skills", models.ManyToManyField(related_name="groups", to="skills.skill")),
            ],
            options={
                "ordering": ["name"],
            },
        ),
    ]
