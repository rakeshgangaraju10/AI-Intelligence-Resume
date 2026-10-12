from django.db.models import Max, Prefetch, QuerySet
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .models import (
    EntrySource,
    Resume,
    ResumeCertification,
    ResumeEducation,
    ResumeExperience,
    ResumeProfile,
    ResumeProject,
    ResumeSkill,
)
from .serializers import (
    ResumeDetailSerializer,
    ResumeListSerializer,
    ResumeUpdateSerializer,
    ResumeUploadSerializer,
)
from .services.resume_parsing import parse_and_store
from .structured_serializers import (
    ResumeCertificationSerializer,
    ResumeEducationSerializer,
    ResumeExperienceSerializer,
    ResumeExtractionSerializer,
    ResumeProfileSerializer,
    ResumeProjectSerializer,
    ResumeSkillSerializer,
)


def extraction_queryset(owner) -> QuerySet[Resume]:
    """Resume + all structured data in a fixed number of queries (no N+1)."""
    return (
        Resume.objects.filter(owner=owner)
        .select_related("profile")
        .prefetch_related(
            Prefetch("skills", queryset=ResumeSkill.objects.order_by("position", "id")),
            "education",
            "experience",
            "projects",
            "certifications",
        )
    )


class ResumeViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    Upload, list, view, rename and delete the authenticated user's resumes.

    Ownership is enforced in get_queryset(): another user's resume id simply
    does not exist from this user's point of view (404, not 403, so ids are not
    confirmed to exist).
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, JSONParser]
    lookup_value_regex = r"[0-9a-fA-F-]{36}"
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self) -> QuerySet[Resume]:
        if getattr(self, "swagger_fake_view", False):  # OpenAPI generation, no real user
            return Resume.objects.none()
        if self.action in ("extraction", "reparse"):
            return extraction_queryset(self.request.user)
        qs = Resume.objects.filter(owner=self.request.user)
        if self.action == "list":
            qs = qs.defer("extracted_text")  # don't load full text for list pages
        return qs

    def get_serializer_class(self):
        if self.action == "create":
            return ResumeUploadSerializer
        if self.action == "list":
            return ResumeListSerializer
        if self.action == "partial_update":
            return ResumeUpdateSerializer
        if self.action in ("extraction", "reparse"):
            return ResumeExtractionSerializer
        return ResumeDetailSerializer

    def get_throttles(self):
        # Upload and re-parse are the expensive operations.
        if self.action in ("create", "reparse"):
            self.throttle_scope = "uploads"
            return [ScopedRateThrottle()]
        return []

    @extend_schema(
        request={"multipart/form-data": ResumeUploadSerializer},
        responses={201: ResumeDetailSerializer},
    )
    def create(self, request: Request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        resume = serializer.save()
        return Response(serializer.to_representation(resume), status=status.HTTP_201_CREATED)

    @extend_schema(request=ResumeUpdateSerializer, responses={200: ResumeDetailSerializer})
    def partial_update(self, request: Request, *args, **kwargs) -> Response:
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(responses={200: ResumeExtractionSerializer})
    @action(detail=True, methods=["get"])
    def extraction(self, request: Request, pk=None) -> Response:
        """Structured data for the review page: profile + every section + parser warnings."""
        return Response(self.get_serializer(self.get_object()).data)

    @extend_schema(request=None, responses={200: ResumeExtractionSerializer})
    @action(detail=True, methods=["post"])
    def reparse(self, request: Request, pk=None) -> Response:
        """
        Run the parser again. Unverified parser rows are replaced; user-added or
        verified rows and a user-edited profile are kept.
        """
        resume = self.get_object()
        parse_and_store(resume)
        fresh = extraction_queryset(request.user).get(pk=resume.pk)
        return Response(self.get_serializer(fresh).data)


class ResumeProfileView(APIView):
    """GET/PATCH /resumes/{resume_pk}/profile/"""

    permission_classes = [IsAuthenticated]

    def _profile(self, request: Request, resume_pk) -> ResumeProfile:
        resume = get_object_or_404(Resume, pk=resume_pk, owner=request.user)
        profile, _ = ResumeProfile.objects.get_or_create(resume=resume)
        return profile

    @extend_schema(responses={200: ResumeProfileSerializer})
    def get(self, request: Request, resume_pk) -> Response:
        return Response(ResumeProfileSerializer(self._profile(request, resume_pk)).data)

    @extend_schema(request=ResumeProfileSerializer, responses={200: ResumeProfileSerializer})
    def patch(self, request: Request, resume_pk) -> Response:
        profile = self._profile(request, resume_pk)
        serializer = ResumeProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(user_edited=True)
        return Response(serializer.data)


class ResumeEntryViewSet(viewsets.ModelViewSet):
    """
    CRUD for one list-type section of a resume, nested under /resumes/{resume_pk}/.

    * Entries are only reachable through a resume the user owns (404 otherwise).
    * Created entries are source="user" and verified.
    * Editing a parser entry marks it verified unless the client explicitly
      sends is_verified=false.
    """

    permission_classes = [IsAuthenticated]
    pagination_class = None  # a resume has a handful of entries per section
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    model = None  # set by subclasses

    def get_resume(self) -> Resume:
        if not hasattr(self, "_resume"):
            self._resume = get_object_or_404(Resume, pk=self.kwargs["resume_pk"], owner=self.request.user)
        return self._resume

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.model.objects.none()
        return self.model.objects.filter(resume=self.get_resume())

    def get_serializer_context(self) -> dict:
        context = super().get_serializer_context()
        if not getattr(self, "swagger_fake_view", False):
            context["resume"] = self.get_resume()
        return context

    def perform_create(self, serializer) -> None:
        resume = self.get_resume()
        last = self.model.objects.filter(resume=resume).aggregate(m=Max("position"))["m"] or 0
        serializer.save(resume=resume, source=EntrySource.USER, is_verified=True, position=last + 1)

    def perform_update(self, serializer) -> None:
        verified = serializer.validated_data.get("is_verified", True)
        serializer.save(is_verified=verified)


class ResumeSkillViewSet(ResumeEntryViewSet):
    model = ResumeSkill
    serializer_class = ResumeSkillSerializer


class ResumeEducationViewSet(ResumeEntryViewSet):
    model = ResumeEducation
    serializer_class = ResumeEducationSerializer


class ResumeExperienceViewSet(ResumeEntryViewSet):
    model = ResumeExperience
    serializer_class = ResumeExperienceSerializer


class ResumeProjectViewSet(ResumeEntryViewSet):
    model = ResumeProject
    serializer_class = ResumeProjectSerializer


class ResumeCertificationViewSet(ResumeEntryViewSet):
    model = ResumeCertification
    serializer_class = ResumeCertificationSerializer
