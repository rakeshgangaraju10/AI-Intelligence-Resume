import logging

from django.db import connection
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


class HealthCheckView(APIView):
    """Liveness/readiness probe. Verifies the database answers a trivial query."""

    permission_classes = [AllowAny]
    authentication_classes: list = []

    @extend_schema(
        responses={
            200: inline_serializer(
                "HealthResponse",
                {"status": serializers.CharField(), "database": serializers.CharField()},
            )
        }
    )
    def get(self, request: Request) -> Response:
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except Exception:  # noqa: BLE001 - any DB failure means "not ready"
            logger.warning("Health check: database unavailable")
            return Response(
                {"status": "error", "database": "unavailable"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({"status": "ok", "database": "ok"})
