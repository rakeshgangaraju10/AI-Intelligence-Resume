from unittest import mock

import pytest
from django.db import OperationalError
from django.urls import reverse
from rest_framework import exceptions

from apps.core.exceptions import api_exception_handler


@pytest.mark.django_db
class TestHealthCheck:
    def test_healthy(self, api_client):
        response = api_client.get(reverse("health"))
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "database": "ok"}

    def test_database_down_returns_503(self, api_client):
        with mock.patch("apps.core.views.connection.cursor", side_effect=OperationalError("down")):
            response = api_client.get(reverse("health"))
        assert response.status_code == 503
        assert response.json()["database"] == "unavailable"


class TestExceptionHandler:
    def test_unhandled_exception_returns_generic_500_without_details(self):
        response = api_exception_handler(RuntimeError("secret internal detail"), {"view": None})
        assert response.status_code == 500
        assert response.data == {
            "error": {"code": "server_error", "message": "An unexpected error occurred."}
        }

    def test_validation_error_envelope(self):
        exc = exceptions.ValidationError({"email": ["Enter a valid email address."]})
        response = api_exception_handler(exc, {"view": None})
        assert response.status_code == 400
        assert response.data["error"]["code"] == "validation_error"
        assert response.data["error"]["message"] == "Enter a valid email address."
        assert response.data["error"]["fields"]["email"][0]["message"] == "Enter a valid email address."

    def test_not_found_envelope(self):
        response = api_exception_handler(exceptions.NotFound(), {"view": None})
        assert response.status_code == 404
        assert response.data["error"]["code"] == "not_found"


@pytest.mark.django_db
def test_openapi_schema_is_generated(api_client, user):
    api_client.force_login(user)
    response = api_client.get(reverse("schema"))
    assert response.status_code == 200
    content = response.content.decode()
    for path in ["/api/v1/resumes/", "/api/v1/auth/login/", "/api/v1/health/", "/api/v1/analyses/compare/",
                 "/api/v1/analyses/{id}/report/", "text/markdown"]:
        assert path in content


@pytest.mark.django_db
class TestSecurityHeaders:
    def test_api_responses_are_locked_down(self, api_client):
        response = api_client.get(reverse("health"))
        assert response["Content-Security-Policy"] == "default-src 'none'; frame-ancestors 'none'"
        assert "camera=()" in response["Permissions-Policy"]
        assert response["X-Content-Type-Options"] == "nosniff"

    def test_html_pages_keep_their_own_policy(self, api_client, user):
        api_client.force_login(user)
        response = api_client.get(reverse("swagger-ui"))
        assert response.status_code == 200
        assert "Content-Security-Policy" not in response
        assert "Permissions-Policy" in response


def test_static_files_are_world_readable_but_uploads_stay_private(settings):
    from django.contrib.staticfiles.storage import staticfiles_storage

    # nginx (a different OS user) must read collected static files...
    assert staticfiles_storage.file_permissions_mode == 0o644
    assert staticfiles_storage.directory_permissions_mode == 0o755
    # ...while the global upload modes stay private.
    assert settings.FILE_UPLOAD_PERMISSIONS == 0o600
    assert settings.FILE_UPLOAD_DIRECTORY_PERMISSIONS == 0o700
