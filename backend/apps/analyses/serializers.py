from rest_framework import serializers

from apps.jobs.models import JobDescription
from apps.resumes.models import Resume

from .models import Analysis, AnalysisSkillResult
from .services.analysis_service import run_analysis
from .services.matching import MatchingError

SCORE_LABEL = (
    "Resume-to-job matching score: the weighted share of the job's skills found in "
    "your resume. It is not a probability of being hired."
)


class AnalysisSkillResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalysisSkillResult
        fields = ["skill_name", "kind", "weight", "status", "evidence", "related_to", "related_reason", "explanation"]
        read_only_fields = fields


class AnalysisListSerializer(serializers.ModelSerializer):
    matched_count = serializers.IntegerField(read_only=True)
    missing_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Analysis
        fields = ["id", "resume", "job", "resume_title", "job_title", "score", "required_coverage",
                  "preferred_coverage", "matched_count", "missing_count", "algorithm_version", "created_at"]
        read_only_fields = fields


class AnalysisDetailSerializer(serializers.ModelSerializer):
    score_label = serializers.SerializerMethodField()
    skill_results = AnalysisSkillResultSerializer(many=True, read_only=True)

    class Meta:
        model = Analysis
        fields = ["id", "resume", "job", "resume_title", "job_title", "score", "score_label",
                  "required_coverage", "preferred_coverage", "required_share", "algorithm_version",
                  "breakdown", "strengths", "improvements", "suggestions", "skill_results", "created_at"]
        read_only_fields = fields

    def get_score_label(self, obj: Analysis) -> str:
        return SCORE_LABEL


class AnalysisCreateSerializer(serializers.Serializer):
    """
    {"resume": "<resume uuid>", "job": <job id>}. Both must belong to the
    requesting user; anything else is reported as "does not exist" so ids of
    other users' objects are never confirmed.
    """

    # pk_field validates the UUID format first, so a malformed id is a 400, not a 500.
    resume = serializers.PrimaryKeyRelatedField(
        queryset=Resume.objects.none(), pk_field=serializers.UUIDField(format="hex_verbose")
    )
    job = serializers.PrimaryKeyRelatedField(queryset=JobDescription.objects.none())

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request is not None and request.user.is_authenticated:
            self.fields["resume"].queryset = Resume.objects.filter(owner=request.user)
            self.fields["job"].queryset = JobDescription.objects.filter(owner=request.user)

    def create(self, validated_data: dict) -> Analysis:
        try:
            return run_analysis(self.context["request"].user, validated_data["resume"], validated_data["job"])
        except MatchingError as exc:
            raise serializers.ValidationError({"job": [serializers.ErrorDetail(exc.message, code=exc.code)]}) from exc

    def to_representation(self, instance: Analysis) -> dict:
        return AnalysisDetailSerializer(instance, context=self.context).data


class AnalysisCompareQuerySerializer(serializers.Serializer):
    """Query string for GET /analyses/compare/?a=<id>&b=<id>."""

    a = serializers.IntegerField(min_value=1)
    b = serializers.IntegerField(min_value=1)

    def validate(self, attrs: dict) -> dict:
        if attrs["a"] == attrs["b"]:
            raise serializers.ValidationError(
                {"b": [serializers.ErrorDetail("Choose two different analyses to compare.", code="same_analysis")]}
            )
        return attrs


class SkillComparisonSerializer(serializers.Serializer):
    skill_name = serializers.CharField()
    kind_a = serializers.CharField(allow_null=True)
    kind_b = serializers.CharField(allow_null=True)
    status_a = serializers.CharField(allow_null=True)
    status_b = serializers.CharField(allow_null=True)
    change = serializers.ChoiceField(choices=["gained", "lost", "only_in_a", "only_in_b", "unchanged"])


class AnalysisComparisonSerializer(serializers.Serializer):
    a = AnalysisDetailSerializer()
    b = AnalysisDetailSerializer()
    score_delta = serializers.FloatField(help_text="b.score - a.score, in score points.")
    basis = serializers.ChoiceField(
        choices=["same_resume_and_job", "same_job", "same_resume", "different"],
        help_text="What the two analyses have in common. Only same_job comparisons are like-for-like.",
    )
    skills = SkillComparisonSerializer(many=True)
