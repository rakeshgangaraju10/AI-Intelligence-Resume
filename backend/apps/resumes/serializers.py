from rest_framework import serializers

from .models import Resume
from .services.errors import ResumeUploadError
from .services.resume_ingestion import create_resume, inspect_resume_upload


class ResumeListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resume
        fields = [
            "id", "title", "original_filename", "file_size", "page_count",
            "status", "created_at", "updated_at",
        ]
        read_only_fields = fields


class ResumeDetailSerializer(ResumeListSerializer):
    char_count = serializers.SerializerMethodField()

    class Meta(ResumeListSerializer.Meta):
        fields = ResumeListSerializer.Meta.fields + [
            "error_code", "parse_warnings", "parsed_at", "char_count", "extracted_text",
        ]
        read_only_fields = fields

    def get_char_count(self, obj: Resume) -> int:
        return len(obj.extracted_text)


class ResumeUpdateSerializer(serializers.ModelSerializer):
    """PATCH /resumes/{id}/ — only the user-facing label is editable."""

    class Meta:
        model = Resume
        fields = ["title"]

    def validate_title(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Title cannot be blank.", code="blank")
        return value

    def to_representation(self, instance: Resume) -> dict:
        return ResumeDetailSerializer(instance, context=self.context).data


class ResumeUploadSerializer(serializers.Serializer):
    """
    multipart/form-data: `file` (required PDF), `title` (optional label).
    Validation includes opening the PDF, because an unreadable file is invalid input.
    """

    file = serializers.FileField(write_only=True, allow_empty_file=True, use_url=False)
    title = serializers.CharField(max_length=150, required=False, allow_blank=True, write_only=True)

    def validate_file(self, uploaded_file):
        try:
            self._inspected = inspect_resume_upload(uploaded_file)
        except ResumeUploadError as exc:
            raise serializers.ValidationError(exc.message, code=exc.code) from exc
        return uploaded_file

    def create(self, validated_data: dict) -> Resume:
        return create_resume(
            owner=self.context["request"].user,
            inspected=self._inspected,
            title=validated_data.get("title"),
        )

    def to_representation(self, instance: Resume) -> dict:
        return ResumeDetailSerializer(instance, context=self.context).data
