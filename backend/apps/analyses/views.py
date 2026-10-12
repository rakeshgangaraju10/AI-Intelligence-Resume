from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count, Q, QuerySet
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from .models import Analysis, AnalysisSkillResult
from .serializers import (
    AnalysisCreateSerializer,
    AnalysisDetailSerializer,
    AnalysisListSerializer,
)


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

    def get_queryset(self) -> QuerySet[Analysis]:
        if getattr(self, "swagger_fake_view", False):
            return Analysis.objects.none()
        qs = Analysis.objects.filter(owner=self.request.user)
        if self.action == "list":
            qs = qs.annotate(
                matched_count=Count("skill_results", filter=Q(skill_results__status=AnalysisSkillResult.Status.MATCHED)),
                missing_count=Count("skill_results", filter=~Q(skill_results__status=AnalysisSkillResult.Status.MATCHED)),
            ).defer("breakdown", "strengths", "improvements", "suggestions")
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
