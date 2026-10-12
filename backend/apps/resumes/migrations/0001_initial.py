import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import apps.resumes.storage


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Resume",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("title", models.CharField(max_length=150)),
                ("original_filename", models.CharField(max_length=255)),
                (
                    "file",
                    models.FileField(
                        max_length=255,
                        storage=apps.resumes.storage.private_resume_storage,
                        upload_to=apps.resumes.storage.resume_upload_path,
                    ),
                ),
                ("file_size", models.PositiveIntegerField(help_text="Size in bytes.")),
                ("sha256", models.CharField(help_text="Hex digest of the uploaded bytes.", max_length=64)),
                ("page_count", models.PositiveSmallIntegerField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("text_extracted", "Text extracted"),
                            ("parsed", "Parsed"),
                            ("failed", "Failed"),
                        ],
                        default="text_extracted",
                        max_length=20,
                    ),
                ),
                ("error_code", models.CharField(blank=True, max_length=50)),
                ("extracted_text", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="resumes",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["owner", "-created_at"], name="resume_owner_created_idx"),
                    models.Index(fields=["owner", "sha256"], name="resume_owner_sha256_idx"),
                ],
                "constraints": [
                    models.CheckConstraint(condition=models.Q(("file_size__gt", 0)), name="resume_file_size_positive"),
                    models.CheckConstraint(condition=models.Q(("page_count__gt", 0)), name="resume_page_count_positive"),
                ],
            },
        ),
    ]
