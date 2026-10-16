from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="college_name",
            field=models.CharField(blank=True, max_length=200, verbose_name="college name"),
        ),
        migrations.AddField(
            model_name="user",
            name="graduation_year",
            field=models.PositiveSmallIntegerField(blank=True, null=True, verbose_name="year of passing out"),
        ),
    ]
