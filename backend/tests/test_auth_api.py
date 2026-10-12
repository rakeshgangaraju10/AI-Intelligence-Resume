import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework.throttling import ScopedRateThrottle

from apps.accounts.models import User

from .conftest import TEST_PASSWORD

pytestmark = pytest.mark.django_db

REGISTER = reverse("auth-register")
LOGIN = reverse("auth-login")
LOGOUT = reverse("auth-logout")
ME = reverse("auth-me")
CSRF = reverse("auth-csrf")


def field_codes(response, field: str) -> list[str]:
    return [item["code"] for item in response.json()["error"]["fields"][field]]


class TestRegister:
    payload = {"full_name": "Casey Example", "email": "Casey@Example.com", "password": TEST_PASSWORD}

    def test_register_creates_user_with_hashed_password_and_logs_in(self, api_client):
        response = api_client.post(REGISTER, self.payload)

        assert response.status_code == 201, response.content
        body = response.json()
        assert body["email"] == "casey@example.com"  # normalised to lower case
        assert "password" not in body
        user = User.objects.get(email="casey@example.com")
        assert user.password != TEST_PASSWORD
        assert user.check_password(TEST_PASSWORD)
        assert api_client.get(ME).status_code == 200  # session established

    def test_duplicate_email_is_rejected_case_insensitively(self, api_client, user):
        response = api_client.post(REGISTER, {**self.payload, "email": "ALEX@example.com"})
        assert response.status_code == 400
        assert field_codes(response, "email") == ["email_taken"]

    @pytest.mark.parametrize("password", ["short", "1234567890123", "password123"])
    def test_weak_passwords_are_rejected(self, api_client, password):
        response = api_client.post(REGISTER, {**self.payload, "password": password})
        assert response.status_code == 400
        assert "password" in response.json()["error"]["fields"]
        assert not User.objects.exists()

    def test_missing_fields_are_reported_per_field(self, api_client):
        response = api_client.post(REGISTER, {})
        assert response.status_code == 400
        fields = response.json()["error"]["fields"]
        assert set(fields) == {"full_name", "email", "password"}

    def test_client_cannot_grant_itself_admin(self, api_client):
        response = api_client.post(
            REGISTER, {**self.payload, "is_staff": True, "is_superuser": True}
        )
        assert response.status_code == 201
        user = User.objects.get(email="casey@example.com")
        assert not user.is_staff
        assert not user.is_superuser


class TestLoginLogout:
    def test_login_with_valid_credentials(self, api_client, user):
        response = api_client.post(LOGIN, {"email": "ALEX@example.com", "password": TEST_PASSWORD})
        assert response.status_code == 200
        assert response.json()["email"] == user.email
        assert response.cookies["sessionid"]["httponly"]
        assert api_client.get(ME).json()["email"] == user.email

    @pytest.mark.parametrize(
        "credentials",
        [
            {"email": "alex@example.com", "password": "wrong-password-123"},
            {"email": "nobody@example.com", "password": TEST_PASSWORD},
        ],
    )
    def test_invalid_credentials_give_identical_generic_error(self, api_client, user, credentials):
        response = api_client.post(LOGIN, credentials)
        assert response.status_code == 400
        assert response.json()["error"]["fields"]["non_field_errors"][0] == {
            "code": "invalid_credentials",
            "message": "Invalid email or password.",
        }

    def test_logout_ends_session(self, api_client, user):
        api_client.post(LOGIN, {"email": user.email, "password": TEST_PASSWORD})
        assert api_client.post(LOGOUT).status_code == 204
        assert api_client.get(ME).status_code == 403

    def test_me_requires_authentication(self, api_client):
        response = api_client.get(ME)
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "not_authenticated"

    def test_login_is_rate_limited(self, api_client, user, monkeypatch):
        monkeypatch.setattr(
            ScopedRateThrottle, "THROTTLE_RATES", {"auth": "3/minute", "uploads": "1000/minute"}
        )
        for _ in range(3):
            api_client.post(LOGIN, {"email": user.email, "password": "wrong-password-123"})
        response = api_client.post(LOGIN, {"email": user.email, "password": TEST_PASSWORD})
        assert response.status_code == 429


class TestCsrf:
    def test_login_without_csrf_token_is_rejected(self, user):
        client = APIClient(enforce_csrf_checks=True)
        response = client.post(LOGIN, {"email": user.email, "password": TEST_PASSWORD})
        assert response.status_code == 403
        assert "CSRF" in response.json()["error"]["message"]

    def test_login_with_csrf_token_succeeds(self, user):
        client = APIClient(enforce_csrf_checks=True)
        csrf_response = client.get(CSRF)
        assert csrf_response.status_code == 204
        token = csrf_response.cookies["csrftoken"].value
        response = client.post(
            LOGIN,
            {"email": user.email, "password": TEST_PASSWORD},
            HTTP_X_CSRFTOKEN=token,
        )
        assert response.status_code == 200

    def test_authenticated_unsafe_request_requires_csrf(self, user):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(user)
        response = client.post(LOGOUT)
        assert response.status_code == 403


class TestAccountSettings:
    CHANGE = reverse("auth-change-password")

    def test_update_full_name(self, user):
        client = APIClient()
        client.force_login(user)
        response = client.patch(ME, {"full_name": "  Alex Q. Example  ", "email": "hacker@example.com"})
        assert response.status_code == 200
        assert response.json()["full_name"] == "Alex Q. Example"
        user.refresh_from_db()
        assert user.email == "alex@example.com"  # email is not editable here
        assert client.patch(ME, {"full_name": "   "}).status_code == 400

    def test_change_password_keeps_current_session(self, api_client, user):
        api_client.post(LOGIN, {"email": user.email, "password": TEST_PASSWORD})
        new_password = "Brand-New-Passphrase-77"
        response = api_client.post(self.CHANGE, {"current_password": TEST_PASSWORD, "new_password": new_password})
        assert response.status_code == 204
        assert api_client.get(ME).status_code == 200  # still logged in
        user.refresh_from_db()
        assert user.check_password(new_password)

        other = APIClient()
        assert other.post(LOGIN, {"email": user.email, "password": TEST_PASSWORD}).status_code == 400
        assert other.post(LOGIN, {"email": user.email, "password": new_password}).status_code == 200

    @pytest.mark.parametrize(
        ("payload", "field", "code"),
        [
            ({"current_password": "wrong-one-123", "new_password": "Brand-New-Passphrase-77"}, "current_password", "wrong_password"),
            ({"current_password": TEST_PASSWORD, "new_password": TEST_PASSWORD}, "new_password", "password_unchanged"),
            ({"current_password": TEST_PASSWORD, "new_password": "short"}, "new_password", None),
        ],
    )
    def test_change_password_validation(self, user, payload, field, code):
        client = APIClient()
        client.force_login(user)
        response = client.post(self.CHANGE, payload)
        assert response.status_code == 400
        errors = response.json()["error"]["fields"][field]
        if code:
            assert errors[0]["code"] == code
        user.refresh_from_db()
        assert user.check_password(TEST_PASSWORD)

    def test_delete_account_requires_password_and_removes_data(self, user, django_capture_on_commit_callbacks):
        from apps.resumes.models import Resume

        from .conftest import pdf_upload

        client = APIClient()
        client.force_login(user)
        client.post(reverse("resume-list"), {"file": pdf_upload()}, format="multipart")
        assert Resume.objects.filter(owner=user).count() == 1

        assert client.delete(ME, {"password": "wrong-password-123"}).status_code == 400
        assert User.objects.filter(pk=user.pk).exists()

        with django_capture_on_commit_callbacks(execute=True):
            response = client.delete(ME, {"password": TEST_PASSWORD})
        assert response.status_code == 204
        assert not User.objects.filter(pk=user.pk).exists()
        assert not Resume.objects.filter(owner_id=user.pk).exists()
        assert client.get(ME).status_code == 403  # logged out

    def test_settings_endpoints_require_authentication(self, api_client):
        assert api_client.patch(ME, {"full_name": "x"}).status_code == 403
        assert api_client.post(self.CHANGE, {}).status_code == 403
        assert api_client.delete(ME, {"password": "x"}).status_code == 403
