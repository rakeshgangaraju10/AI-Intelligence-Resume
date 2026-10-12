from django.db.models import Count, Q, QuerySet
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from .models import JobDescription, JobRequirement
from .serializers import (
    JobCreateSerializer,
    JobDetailSerializer,
    JobListSerializer,
    JobRequirementSerializer,
)
from .services.job_service import add_suggested_requirements


class JobViewSet(viewsets.ModelViewSet):
    """
    Saved job descriptions of the authenticated user. Other users' jobs are
    invisible (404). `?search=` filters by title or company.
    """

    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self) -> QuerySet[JobDescription]:
        if getattr(self, "swagger_fake_view", False):
            return JobDescription.objects.none()
        qs = JobDescription.objects.filter(owner=self.request.user)
        if self.action == "list":
            qs = qs.annotate(
                required_count=Count("requirements", filter=Q(requirements__kind=JobRequirement.Kind.REQUIRED)),
                preferred_count=Count("requirements", filter=Q(requirements__kind=JobRequirement.Kind.PREFERRED)),
            ).defer("description")
            search = self.request.query_params.get("search", "").strip()
            if search:
                qs = qs.filter(Q(title__icontains=search) | Q(company__icontains=search))
        else:
            qs = qs.prefetch_related("requirements")
        return qs

    def get_serializer_class(self):
        if self.action == "create":
            return JobCreateSerializer
        if self.action == "list":
            return JobListSerializer
        return JobDetailSerializer

    @extend_schema(parameters=[OpenApiParameter("search", str, description="Filter by title or company")])
    def list(self, request: Request, *args, **kwargs) -> Response:
        return super().list(request, *args, **kwargs)

    @extend_schema(request=JobCreateSerializer, responses={201: JobDetailSerializer})
    def create(self, request: Request, *args, **kwargs) -> Response:
        return super().create(request, *args, **kwargs)

    @extend_schema(
        request=None,
        responses={200: inline_serializer("SuggestRequirementsResponse", {
            "added": serializers.IntegerField(), "job": JobDetailSerializer(),
        })},
    )
    @action(detail=True, methods=["post"], url_path="suggest-requirements")
    def suggest_requirements(self, request: Request, pk=None) -> Response:
        """Add skills found in the description that aren't listed yet. Never removes anything."""
        job = self.get_object()
        added = add_suggested_requirements(job)
        job = JobDescription.objects.prefetch_related("requirements").get(pk=job.pk)
        return Response({"added": added, "job": JobDetailSerializer(job, context=self.get_serializer_context()).data})


class JobRequirementViewSet(viewsets.ModelViewSet):
    """CRUD for a job's skills, nested under /jobs/{job_pk}/requirements/."""

    permission_classes = [IsAuthenticated]
    serializer_class = JobRequirementSerializer
    pagination_class = None
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_job(self) -> JobDescription:
        if not hasattr(self, "_job"):
            self._job = get_object_or_404(JobDescription, pk=self.kwargs["job_pk"], owner=self.request.user)
        return self._job

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return JobRequirement.objects.none()
        return JobRequirement.objects.filter(job=self.get_job())

    def get_serializer_context(self) -> dict:
        context = super().get_serializer_context()
        if not getattr(self, "swagger_fake_view", False):
            context["job"] = self.get_job()
        return context

    def perform_create(self, serializer) -> None:
        serializer.save(job=self.get_job(), source=JobRequirement.Source.USER)
