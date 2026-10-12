"""
Serializers for reviewing and editing structured resume data.

All writes are validated here (lengths come from the model fields). `source`,
`section` and `evidence` are read-only: they describe where data came from and
must not be forged by the client.
"""
import re

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.skills.models import Skill
from apps.skills.services import load_skill_dictionary

from .models import (
    Resume,
    ResumeCertification,
    ResumeEducation,
    ResumeExperience,
    ResumeProfile,
    ResumeProject,
    ResumeSkill,
)

ENTRY_READ_ONLY = ["id", "source", "position", "created_at", "updated_at"]
MAX_LINKS = 10
MAX_TECHNOLOGIES = 30
_NO_SPACE_RE = re.compile(r"^\S+$")


def _strip_strings(attrs: dict) -> dict:
    return {k: v.strip() if isinstance(v, str) else v for k, v in attrs.items()}


class ResumeProfileSerializer(serializers.ModelSerializer):
    links = serializers.ListField(
        child=serializers.CharField(max_length=300), max_length=MAX_LINKS, required=False
    )

    class Meta:
        model = ResumeProfile
        fields = ["full_name", "email", "phone", "location", "links", "summary", "user_edited", "updated_at"]
        read_only_fields = ["user_edited", "updated_at"]

    def validate_links(self, value: list[str]) -> list[str]:
        cleaned = []
        for link in value:
            link = link.strip()
            if not link:
                continue
            if not _NO_SPACE_RE.match(link):
                raise serializers.ValidationError("Links cannot contain spaces.", code="invalid_link")
            cleaned.append(link)
        return cleaned

    def validate(self, attrs: dict) -> dict:
        return _strip_strings(attrs)


class ResumeSkillSerializer(serializers.ModelSerializer):
    canonical = serializers.SerializerMethodField(
        help_text="True when the name matches a skill in the dictionary."
    )

    class Meta:
        model = ResumeSkill
        fields = ["id", "name", "canonical", "source", "is_verified", "section", "evidence",
                  "position", "created_at", "updated_at"]
        read_only_fields = [*ENTRY_READ_ONLY, "section", "evidence"]

    def get_canonical(self, obj: ResumeSkill) -> bool:
        return obj.skill_id is not None

    def validate_name(self, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise serializers.ValidationError("Skill name cannot be blank.", code="blank")
        # Map aliases to the canonical name ("JS" -> "JavaScript") when known.
        canonical = load_skill_dictionary().resolve(value)
        return canonical or value

    def validate(self, attrs: dict) -> dict:
        name = attrs.get("name")
        if name is not None:
            resume: Resume = self.context["resume"]
            duplicates = ResumeSkill.objects.filter(resume=resume, name__iexact=name)
            if self.instance is not None:
                duplicates = duplicates.exclude(pk=self.instance.pk)
            if duplicates.exists():
                raise serializers.ValidationError(
                    {"name": [serializers.ErrorDetail(f"'{name}' is already in this resume.", code="duplicate_skill")]}
                )
            attrs["skill"] = Skill.objects.filter(name=name).first()
        return attrs


class ResumeEducationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResumeEducation
        fields = ["id", "institution", "degree", "field_of_study", "start_date", "end_date",
                  "grade", "description", "source", "is_verified", "position", "created_at", "updated_at"]
        read_only_fields = ENTRY_READ_ONLY

    def validate(self, attrs: dict) -> dict:
        attrs = _strip_strings(attrs)
        institution = attrs.get("institution", getattr(self.instance, "institution", ""))
        degree = attrs.get("degree", getattr(self.instance, "degree", ""))
        if not institution and not degree:
            raise serializers.ValidationError(
                "Provide at least an institution or a degree.", code="incomplete_entry"
            )
        return attrs


class ResumeExperienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResumeExperience
        fields = ["id", "title", "company", "location", "start_date", "end_date", "is_current",
                  "description", "source", "is_verified", "position", "created_at", "updated_at"]
        read_only_fields = ENTRY_READ_ONLY

    def validate(self, attrs: dict) -> dict:
        attrs = _strip_strings(attrs)
        title = attrs.get("title", getattr(self.instance, "title", ""))
        company = attrs.get("company", getattr(self.instance, "company", ""))
        if not title and not company:
            raise serializers.ValidationError(
                "Provide at least a job title or a company.", code="incomplete_entry"
            )
        is_current = attrs.get("is_current", getattr(self.instance, "is_current", False))
        end_date = attrs.get("end_date", getattr(self.instance, "end_date", ""))
        if is_current and end_date:
            raise serializers.ValidationError(
                {"end_date": [serializers.ErrorDetail(
                    "Leave the end date empty for a current position.", code="current_with_end_date"
                )]}
            )
        return attrs


class ResumeProjectSerializer(serializers.ModelSerializer):
    technologies = serializers.ListField(
        child=serializers.CharField(max_length=100), max_length=MAX_TECHNOLOGIES, required=False
    )

    class Meta:
        model = ResumeProject
        fields = ["id", "name", "description", "technologies", "url", "source", "is_verified",
                  "position", "created_at", "updated_at"]
        read_only_fields = ENTRY_READ_ONLY

    def validate_technologies(self, value: list[str]) -> list[str]:
        dictionary = load_skill_dictionary()
        result: list[str] = []
        for item in value:
            item = " ".join(item.split())
            if item:
                name = dictionary.resolve(item) or item
                if name.lower() not in {r.lower() for r in result}:
                    result.append(name)
        return result

    def validate(self, attrs: dict) -> dict:
        attrs = _strip_strings(attrs)
        if "name" in attrs and not attrs["name"]:
            raise serializers.ValidationError({"name": [serializers.ErrorDetail("Project name cannot be blank.", code="blank")]})
        return attrs


class ResumeCertificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResumeCertification
        fields = ["id", "name", "issuer", "issue_date", "credential_url", "source", "is_verified",
                  "position", "created_at", "updated_at"]
        read_only_fields = ENTRY_READ_ONLY

    def validate(self, attrs: dict) -> dict:
        attrs = _strip_strings(attrs)
        if "name" in attrs and not attrs["name"]:
            raise serializers.ValidationError(
                {"name": [serializers.ErrorDetail("Certification name cannot be blank.", code="blank")]}
            )
        return attrs


class ResumeExtractionSerializer(serializers.ModelSerializer):
    """Everything the review page needs in one response."""

    profile = serializers.SerializerMethodField()
    skills = ResumeSkillSerializer(many=True, read_only=True)
    education = ResumeEducationSerializer(many=True, read_only=True)
    experience = ResumeExperienceSerializer(many=True, read_only=True)
    projects = ResumeProjectSerializer(many=True, read_only=True)
    certifications = ResumeCertificationSerializer(many=True, read_only=True)

    class Meta:
        model = Resume
        fields = ["id", "title", "status", "error_code", "parse_warnings", "parsed_at",
                  "profile", "skills", "education", "experience", "projects", "certifications"]
        read_only_fields = fields

    @extend_schema_field(ResumeProfileSerializer(allow_null=True))
    def get_profile(self, obj: Resume):
        profile = getattr(obj, "profile", None)
        return ResumeProfileSerializer(profile).data if profile else None
