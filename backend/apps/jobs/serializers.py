from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.skills.models import Skill
from apps.skills.services import load_skill_dictionary

from .models import MAX_DESCRIPTION_CHARS, JobDescription, JobRequirement
from .services.job_service import canonical_name, create_job

MAX_SKILLS_PER_LIST = 50


@extend_schema_field({
    "oneOf": [
        {"type": "string", "example": "Docker"},
        {
            "type": "object",
            "properties": {
                "name": {"type": "string", "maxLength": 100},
                "weight": {"type": "integer", "minimum": 1, "maximum": 5, "default": 1},
            },
            "required": ["name"],
        },
    ]
})
class RequirementInputField(serializers.Field):
    """Accepts "Docker" or {"name": "Docker", "weight": 3}."""

    default_error_messages = {
        "invalid": "Each skill must be a name or an object with 'name' and optional 'weight' (1-5).",
    }

    def to_internal_value(self, data) -> dict:
        if isinstance(data, str):
            name, weight = data, 1
        elif isinstance(data, dict) and isinstance(data.get("name"), str):
            name, weight = data["name"], data.get("weight", 1)
        else:
            self.fail("invalid")
        name = " ".join(name.split())
        if not name or len(name) > 100:
            raise serializers.ValidationError("Skill names must be 1-100 characters.", code="invalid_skill_name")
        if not isinstance(weight, int) or isinstance(weight, bool) or not 1 <= weight <= 5:
            raise serializers.ValidationError("Weight must be an integer from 1 to 5.", code="invalid_weight")
        return {"name": name, "weight": weight}

    def to_representation(self, value):  # write-only in practice
        return value


class JobRequirementSerializer(serializers.ModelSerializer):
    canonical = serializers.SerializerMethodField()

    class Meta:
        model = JobRequirement
        fields = ["id", "name", "kind", "weight", "canonical", "source", "evidence", "created_at"]
        read_only_fields = ["id", "source", "evidence", "created_at"]

    def get_canonical(self, obj: JobRequirement) -> bool:
        return obj.skill_id is not None

    def validate_name(self, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise serializers.ValidationError("Skill name cannot be blank.", code="blank")
        return canonical_name(value, load_skill_dictionary())

    def validate(self, attrs: dict) -> dict:
        name = attrs.get("name")
        if name is not None:
            job: JobDescription = self.context["job"]
            duplicates = JobRequirement.objects.filter(job=job, name__iexact=name)
            if self.instance is not None:
                duplicates = duplicates.exclude(pk=self.instance.pk)
            if duplicates.exists():
                raise serializers.ValidationError(
                    {"name": [serializers.ErrorDetail(f"'{name}' is already listed for this job.", code="duplicate_skill")]}
                )
            attrs["skill"] = Skill.objects.filter(name=name).first()
        return attrs


class JobListSerializer(serializers.ModelSerializer):
    required_count = serializers.IntegerField(read_only=True)
    preferred_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = JobDescription
        fields = ["id", "title", "company", "experience_level", "required_count", "preferred_count",
                  "created_at", "updated_at"]
        read_only_fields = fields


class JobDetailSerializer(serializers.ModelSerializer):
    requirements = JobRequirementSerializer(many=True, read_only=True)

    class Meta:
        model = JobDescription
        fields = ["id", "title", "company", "experience_level", "description", "requirements",
                  "created_at", "updated_at"]
        read_only_fields = ["id", "requirements", "created_at", "updated_at"]

    def validate_title(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Title cannot be blank.", code="blank")
        return value.strip()

    def validate_description(self, value: str) -> str:
        if len(value) > MAX_DESCRIPTION_CHARS:
            raise serializers.ValidationError(
                f"The description is longer than {MAX_DESCRIPTION_CHARS:,} characters.", code="too_long"
            )
        return value.strip()


class JobCreateSerializer(JobDetailSerializer):
    """
    POST /jobs/: job fields plus optional skill lists. With `auto_extract`
    (default true), skills found in the description are added as suggestions
    marked source="extracted" for the user to review.
    """

    required_skills = serializers.ListField(
        child=RequirementInputField(), required=False, max_length=MAX_SKILLS_PER_LIST, write_only=True
    )
    preferred_skills = serializers.ListField(
        child=RequirementInputField(), required=False, max_length=MAX_SKILLS_PER_LIST, write_only=True
    )
    auto_extract = serializers.BooleanField(required=False, default=True, write_only=True)

    class Meta(JobDetailSerializer.Meta):
        fields = JobDetailSerializer.Meta.fields + ["required_skills", "preferred_skills", "auto_extract"]

    def validate(self, attrs: dict) -> dict:
        dictionary = load_skill_dictionary()
        for key in ("required_skills", "preferred_skills"):
            attrs[key] = [
                {"name": canonical_name(item["name"], dictionary), "weight": item["weight"]}
                for item in attrs.get(key, [])
            ]
        if not attrs.get("description") and not attrs["required_skills"] and not attrs["preferred_skills"]:
            raise serializers.ValidationError(
                "Paste a job description or list at least one required or preferred skill.", code="empty_job"
            )
        return attrs

    def create(self, validated_data: dict) -> JobDescription:
        required = validated_data.pop("required_skills")
        preferred = validated_data.pop("preferred_skills")
        auto_extract = validated_data.pop("auto_extract")
        return create_job(
            self.context["request"].user,
            fields=validated_data,
            required=required,
            preferred=preferred,
            auto_extract=auto_extract,
        )

    def to_representation(self, instance: JobDescription) -> dict:
        return JobDetailSerializer(instance, context=self.context).data
