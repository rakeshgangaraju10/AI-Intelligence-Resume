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


# Same policy nginx sends in the Docker Compose setup (frontend/nginx/spa-headers.conf).
SPA_CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
    "font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; "
    "form-action 'self'; frame-ancestors 'none'"
)


def spa_index(request, *args, **kwargs):
    """
    Single-service deployments: return the React app's index.html for client-side
    routes (/dashboard, /analyses/7, ...). Built assets are served by WhiteNoise.
    404 when SPA_DIST_DIR isn't configured (development, Docker Compose + nginx).
    """
    from pathlib import Path

    from django.conf import settings
    from django.http import Http404, HttpResponse

    if not settings.SPA_DIST_DIR:
        raise Http404("SPA not served by Django in this deployment.")
    index = Path(settings.SPA_DIST_DIR) / "index.html"
    try:
        body = index.read_bytes()
    except OSError as exc:
        raise Http404("SPA build not found.") from exc
    response = HttpResponse(body, content_type="text/html; charset=utf-8")
    response["Content-Security-Policy"] = SPA_CSP
    response["Cache-Control"] = "no-cache"
    response["Cross-Origin-Opener-Policy"] = "same-origin"
    return response
