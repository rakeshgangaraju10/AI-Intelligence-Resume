from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from .models import Resume
from .serializers import (
    ResumeDetailSerializer,
    ResumeListSerializer,
    ResumeUploadSerializer,
)


class ResumeViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    Upload, list, view and delete the authenticated user's resumes.

    Ownership is enforced in get_queryset(): another user's resume id simply
    does not exist from this user's point of view (404, not 403, so ids are not
    confirmed to exist).
    """

    permission_classes = [IsAuthenticated]
    # Uploads are multipart; JSON stays available for later PATCH endpoints.
    parser_classes = [MultiPartParser, JSONParser]
    lookup_value_regex = r"[0-9a-fA-F-]{36}"

    def get_queryset(self) -> QuerySet[Resume]:
        if getattr(self, "swagger_fake_view", False):  # OpenAPI generation, no real user
            return Resume.objects.none()
        qs = Resume.objects.filter(owner=self.request.user)
        if self.action == "list":
            qs = qs.defer("extracted_text")  # don't load full text for list pages
        return qs

    def get_serializer_class(self):
        if self.action == "create":
            return ResumeUploadSerializer
        if self.action == "list":
            return ResumeListSerializer
        return ResumeDetailSerializer

    def get_throttles(self):
        # Only uploads are rate-limited (they are the expensive operation).
        if self.action == "create":
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
