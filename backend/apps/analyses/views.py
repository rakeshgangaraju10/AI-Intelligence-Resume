from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count, Q, QuerySet
from django.http import HttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from .models import Analysis, AnalysisSkillResult
from .serializers import (
    AnalysisCompareQuerySerializer,
    AnalysisComparisonSerializer,
    AnalysisCreateSerializer,
    AnalysisDetailSerializer,
    AnalysisListSerializer,
)
from .services.comparison import SkillRow, compare_skill_results, comparison_basis
from .services.report import render_markdown


class AnalysisViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    Run and review resume-to-job analyses. Only the owner's analyses are
    visible. List filters: `?resume=<uuid>` and `?job=<id>`.
    """

    permission_classes = [IsAuthenticated]
    throttle_scope = "analyses"

    def get_throttles(self):
        # Running an analysis does real work; reading history does not.
        return [ScopedRateThrottle()] if self.action == "create" else []

    def get_queryset(self) -> QuerySet[Analysis]:
        if getattr(self, "swagger_fake_view", False):
            return Analysis.objects.none()
        qs = Analysis.objects.filter(owner=self.request.user)
        if self.action == "list":
            qs = qs.annotate(
                matched_count=Count("skill_results", filter=Q(skill_results__status=AnalysisSkillResult.Status.MATCHED)),
                missing_count=Count("skill_results", filter=~Q(skill_results__status=AnalysisSkillResult.Status.MATCHED)),
            ).defer("breakdown", "strengths", "improvements", "suggestions").order_by("-created_at", "-id")
            # (aggregation queries ignore Meta.ordering, so order explicitly for stable pagination)
            params = self.request.query_params
            try:
                if params.get("resume"):
                    qs = qs.filter(resume_id=params["resume"])
                if params.get("job"):
                    qs = qs.filter(job_id=int(params["job"]))
            except (ValueError, TypeError, DjangoValidationError) as exc:
                raise ValidationError({"filter": ["Invalid resume or job filter."]}) from exc
        else:
            qs = qs.prefetch_related("skill_results")
        return qs

    def get_serializer_class(self):
        if self.action == "create":
            return AnalysisCreateSerializer
        if self.action == "list":
            return AnalysisListSerializer
        return AnalysisDetailSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter("resume", str, description="Filter by resume id (uuid)"),
            OpenApiParameter("job", int, description="Filter by job id"),
        ]
    )
    def list(self, request: Request, *args, **kwargs) -> Response:
        return super().list(request, *args, **kwargs)

    @extend_schema(request=AnalysisCreateSerializer, responses={201: AnalysisDetailSerializer})
    def create(self, request: Request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        analysis = serializer.save()
        analysis = Analysis.objects.prefetch_related("skill_results").get(pk=analysis.pk)
        return Response(AnalysisDetailSerializer(analysis).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        parameters=[
            OpenApiParameter("a", int, required=True, description="Id of the earlier/baseline analysis"),
            OpenApiParameter("b", int, required=True, description="Id of the analysis to compare against it"),
        ],
        responses={200: AnalysisComparisonSerializer},
    )
    @action(detail=False, methods=["get"])
    def compare(self, request: Request) -> Response:
        """
        Compare two of your analyses skill by skill. 404 if either is not yours.
        `score_delta` is b minus a; `basis` says whether they share a resume or job.
        """
        query = AnalysisCompareQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        ids = (query.validated_data["a"], query.validated_data["b"])
        found = {obj.pk: obj for obj in self.get_queryset().filter(pk__in=ids)}
        if len(found) != 2:
            raise NotFound("Analysis not found.")
        a, b = found[ids[0]], found[ids[1]]

        def rows(analysis: Analysis) -> list[SkillRow]:
            return [SkillRow(r.skill_name, r.kind, r.weight, r.status) for r in analysis.skill_results.all()]

        # Pass model instances: the nested AnalysisDetailSerializer serializes them
        # (passing already-serialized dicts breaks its related-field handling).
        payload = {
            "a": a,
            "b": b,
            "score_delta": round(float(b.score) - float(a.score), 1),
            "basis": comparison_basis(str(a.resume_id), str(b.resume_id), a.job_id, b.job_id),
            "skills": [vars(c) for c in compare_skill_results(rows(a), rows(b))],
        }
        return Response(AnalysisComparisonSerializer(payload).data)

    @extend_schema(responses={(200, "text/markdown"): OpenApiTypes.STR})
    @action(detail=True, methods=["get"])
    def report(self, request: Request, pk: str | None = None) -> HttpResponse:
        """Download the analysis as a Markdown report (same content as the detail view)."""
        analysis = self.get_object()
        body = render_markdown(AnalysisDetailSerializer(analysis).data)
        response = HttpResponse(body, content_type="text/markdown; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="careerforge-analysis-{analysis.pk}.md"'
        response["Cache-Control"] = "no-store"
        return response
