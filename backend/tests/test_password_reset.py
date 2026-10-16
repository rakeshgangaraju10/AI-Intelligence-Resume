"""Forgot password: request email, confirm with the link, Brevo email backend."""
import json
import re
from unittest import mock

import pytest
from django.core import mail
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework.throttling import ScopedRateThrottle

from apps.accounts.models import User

from .conftest import TEST_PASSWORD

REQUEST = reverse("auth-password-reset")
CONFIRM = reverse("auth-password-reset-confirm")
LOGIN = reverse("auth-login")
NEW_PASSWORD = "Brand-New-Secret-77"

pytestmark = pytest.mark.django_db


def link_parts(message) -> tuple[str, str]:
    match = re.search(r"https?://[^/\s]+/reset-password/([^/\s]+)/([^/\s]+)", message.body)
    assert match, message.body
    return match.group(1), match.group(2)


def request_reset(client, email):
    return client.post(REQUEST, {"email": email})


class TestRequest:
    def test_sends_one_email_with_a_link_to_this_site(self, api_client, user, settings):
        settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
        response = request_reset(api_client, "ALEX@example.com")
        assert response.status_code == 200
        assert "If an account exists" in response.json()["detail"]
        assert len(mail.outbox) == 1
        message = mail.outbox[0]
        assert message.to == [user.email]
        assert message.subject == "Reset your CareerForge password"
        assert "http://testserver/reset-password/" in message.body
        assert "60 minutes" in message.body

    def test_unknown_email_gets_the_same_answer_and_no_email(self, api_client, user, settings):
        settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
        known = request_reset(api_client, user.email).json()
        mail.outbox.clear()
        unknown = request_reset(api_client, "nobody@example.com")
        assert unknown.status_code == 200 and unknown.json() == known
        assert mail.outbox == []

    def test_inactive_user_gets_no_email(self, api_client, user, settings):
        settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
        user.is_active = False
        user.save()
        assert request_reset(api_client, user.email).status_code == 200
        assert mail.outbox == []

    def test_configured_base_url_is_used(self, api_client, user, settings):
        settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
        settings.PASSWORD_RESET_BASE_URL = "https://careerforge.example.com/"
        request_reset(api_client, user.email)
        assert "https://careerforge.example.com/reset-password/" in mail.outbox[0].body

    def test_without_email_provider_nothing_is_sent_or_logged(self, api_client, user, settings, caplog):
        settings.EMAIL_BACKEND = "django.core.mail.backends.dummy.EmailBackend"
        response = request_reset(api_client, user.email)
        assert response.status_code == 200
        assert "no email provider" in caplog.text
        assert "reset-password/" not in caplog.text

    def test_send_failure_still_returns_generic_answer(self, api_client, user, settings):
        settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
        with mock.patch("apps.accounts.password_reset.send_mail", side_effect=RuntimeError("down")):
            response = request_reset(api_client, user.email)
        assert response.status_code == 200

    def test_invalid_email_is_a_validation_error(self, api_client):
        response = request_reset(api_client, "not-an-email")
        assert response.status_code == 400
        assert "email" in response.json()["error"]["fields"]

    def test_requires_csrf(self, user):
        client = APIClient(enforce_csrf_checks=True)
        assert client.post(REQUEST, {"email": user.email}).status_code == 403

    def test_rate_limited(self, api_client, user, monkeypatch, settings):
        settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
        monkeypatch.setattr(ScopedRateThrottle, "THROTTLE_RATES", {"password_reset": "2/hour", "auth": "1000/minute"})
        assert request_reset(api_client, user.email).status_code == 200
        assert request_reset(api_client, user.email).status_code == 200
        response = request_reset(api_client, user.email)
        assert response.status_code == 429
        assert response.json()["error"]["code"] == "throttled"


class TestConfirm:
    def _link(self, client, user, settings):
        settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
        request_reset(client, user.email)
        return link_parts(mail.outbox[-1])

    def test_full_flow_changes_password_and_link_works_once(self, api_client, user, settings):
        uid, token = self._link(api_client, user, settings)
        response = api_client.post(CONFIRM, {"uid": uid, "token": token, "new_password": NEW_PASSWORD})
        assert response.status_code == 200, response.content
        user.refresh_from_db()
        assert user.check_password(NEW_PASSWORD)
        assert api_client.post(LOGIN, {"email": user.email, "password": NEW_PASSWORD}).status_code == 200

        again = api_client.post(CONFIRM, {"uid": uid, "token": token, "new_password": "Another-Secret-88"})
        assert again.status_code == 400
        assert again.json()["error"]["fields"]["token"][0]["code"] == "invalid_token"

    def test_old_sessions_are_logged_out(self, user, settings):
        logged_in = APIClient()
        logged_in.force_login(user)
        assert logged_in.get(reverse("auth-me")).status_code == 200
        uid, token = self._link(APIClient(), user, settings)
        APIClient().post(CONFIRM, {"uid": uid, "token": token, "new_password": NEW_PASSWORD})
        assert logged_in.get(reverse("auth-me")).status_code == 403

    @pytest.mark.parametrize("uid,token", [("bad", "bad"), ("", "x"), ("MQ", "1-abc")])
    def test_invalid_links_are_rejected(self, api_client, user, uid, token):
        response = api_client.post(CONFIRM, {"uid": uid or "x", "token": token, "new_password": NEW_PASSWORD})
        assert response.status_code == 400
        user.refresh_from_db()
        assert user.check_password(TEST_PASSWORD)

    def test_expired_link_is_rejected(self, api_client, user, settings):
        uid, token = self._link(api_client, user, settings)
        settings.PASSWORD_RESET_TIMEOUT = -1
        response = api_client.post(CONFIRM, {"uid": uid, "token": token, "new_password": NEW_PASSWORD})
        assert response.status_code == 400

    def test_weak_password_is_rejected_and_link_still_works(self, api_client, user, settings):
        uid, token = self._link(api_client, user, settings)
        weak = api_client.post(CONFIRM, {"uid": uid, "token": token, "new_password": "12345"})
        assert weak.status_code == 400 and "new_password" in weak.json()["error"]["fields"]
        ok = api_client.post(CONFIRM, {"uid": uid, "token": token, "new_password": NEW_PASSWORD})
        assert ok.status_code == 200


class TestBrevoBackend:
    def _send(self, settings, **overrides):
        from django.core.mail import EmailMultiAlternatives

        settings.EMAIL_BACKEND = "apps.core.email_backends.BrevoAPIBackend"
        settings.BREVO_API_KEY = overrides.get("key", "test-key")
        settings.DEFAULT_FROM_EMAIL = "CareerForge <owner@example.com>"
        msg = EmailMultiAlternatives("Subject", "Plain body", None, ["Someone <someone@example.com>"])
        msg.attach_alternative("<p>HTML</p>", "text/html")
        return msg.send()

    def test_posts_json_to_brevo(self, settings):
        response = mock.MagicMock(status=201)
        response.__enter__.return_value = response
        with mock.patch("apps.core.email_backends.urllib.request.urlopen", return_value=response) as urlopen:
            assert self._send(settings) == 1
        request = urlopen.call_args.args[0]
        assert request.full_url == "https://api.brevo.com/v3/smtp/email"
        assert request.get_header("Api-key") == "test-key"
        body = json.loads(request.data)
        assert body["sender"] == {"email": "owner@example.com", "name": "CareerForge"}
        assert body["to"] == [{"email": "someone@example.com"}]
        assert body["subject"] == "Subject" and body["textContent"] == "Plain body"
        assert body["htmlContent"] == "<p>HTML</p>"

    def test_missing_key_raises(self, settings):
        with pytest.raises(RuntimeError, match="BREVO_API_KEY"):
            self._send(settings, key="")

    def test_http_error_raises(self, settings):
        import urllib.error

        error = urllib.error.HTTPError("https://api.brevo.com", 401, "Unauthorized", {}, None)
        with mock.patch("apps.core.email_backends.urllib.request.urlopen", side_effect=error):
            with pytest.raises(RuntimeError, match="401"):
                self._send(settings)
