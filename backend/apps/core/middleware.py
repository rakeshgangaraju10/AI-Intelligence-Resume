"""Response headers that Django's SecurityMiddleware doesn't set."""
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

# API responses are data, never documents: nothing may load, run or frame them.
API_CSP = "default-src 'none'; frame-ancestors 'none'"
PERMISSIONS_POLICY = "camera=(), microphone=(), geolocation=(), payment=()"


class SecurityHeadersMiddleware:
    """
    - Permissions-Policy on every response.
    - A deny-all Content-Security-Policy on non-HTML responses (JSON, Markdown
      reports). HTML pages (Django admin, Swagger UI) are left alone because
      they need their own scripts and styles.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        response.setdefault("Permissions-Policy", PERMISSIONS_POLICY)
        if not response.get("Content-Type", "").startswith("text/html"):
            response.setdefault("Content-Security-Policy", API_CSP)
        return response
