"""
Consistent API error envelope.

Every error response has the shape:

    {
      "error": {
        "code": "validation_error",          # machine-readable
        "message": "Human readable summary.",
        "fields": {                           # only for validation errors
          "file": [{"code": "pdf_encrypted", "message": "..."}]
        }
      }
    }

Unhandled exceptions become a generic 500 without stack traces or internals.
"""
import logging
from typing import Any

from django.core.exceptions import PermissionDenied
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


def _flatten_field_errors(detail: Any) -> dict[str, list[dict[str, str]]]:
    """Convert DRF's nested ErrorDetail structure into {field: [{code, message}]}."""

    def to_items(value: Any) -> list[dict[str, str]]:
        if isinstance(value, list):
            items: list[dict[str, str]] = []
            for v in value:
                items.extend(to_items(v))
            return items
        if isinstance(value, dict):
            # Nested serializer errors: keep them flat but prefixed.
            items = []
            for key, v in value.items():
                for item in to_items(v):
                    items.append({**item, "message": f"{key}: {item['message']}"})
            return items
        code = getattr(value, "code", "invalid")
        return [{"code": str(code), "message": str(value)}]

    if isinstance(detail, dict):
        return {str(field): to_items(errors) for field, errors in detail.items()}
    return {"non_field_errors": to_items(detail)}


def api_exception_handler(exc: Exception, context: dict) -> Response:
    # Normalise Django exceptions into DRF ones (DRF does this too, but we need
    # to know the final class to pick the code).
    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, PermissionDenied):
        exc = exceptions.PermissionDenied()

    response = drf_exception_handler(exc, context)

    if response is None:
        # Unexpected error: log it server-side (no request body), return a safe message.
        view = context.get("view")
        logger.error(
            "Unhandled API error in %s", view.__class__.__name__ if view else "?", exc_info=exc
        )
        return Response(
            {"error": {"code": "server_error", "message": "An unexpected error occurred."}},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if isinstance(exc, exceptions.ValidationError):
        fields = _flatten_field_errors(exc.detail)
        first_message = next(
            (items[0]["message"] for items in fields.values() if items),
            "Invalid input.",
        )
        response.data = {
            "error": {
                "code": "validation_error",
                "message": first_message,
                "fields": fields,
            }
        }
        return response

    if isinstance(exc, exceptions.APIException):
        detail = exc.detail
        message = str(detail) if not isinstance(detail, (list, dict)) else "Request failed."
        response.data = {
            "error": {
                "code": str(getattr(detail, "code", exc.default_code)),
                "message": message,
            }
        }
    return response
