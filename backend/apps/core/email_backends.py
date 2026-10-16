"""
Email backend that sends through Brevo's HTTPS API instead of SMTP.

Render's free web services can't reach SMTP ports (25/465/587), but HTTPS works.
Brevo's free plan sends up to 300 emails/day. Only the standard library is used.

Settings: EMAIL_BACKEND = "apps.core.email_backends.BrevoAPIBackend",
BREVO_API_KEY, DEFAULT_FROM_EMAIL (e.g. "CareerForge <you@gmail.com>").
"""
import json
import logging
import urllib.error
import urllib.request
from email.utils import parseaddr

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)

BREVO_SEND_URL = "https://api.brevo.com/v3/smtp/email"


class BrevoAPIBackend(BaseEmailBackend):
    def __init__(self, fail_silently: bool = False, **kwargs) -> None:
        super().__init__(fail_silently=fail_silently, **kwargs)
        self.api_key = getattr(settings, "BREVO_API_KEY", "")
        self.timeout = getattr(settings, "EMAIL_TIMEOUT", None) or 10

    def send_messages(self, email_messages) -> int:
        if not email_messages:
            return 0
        if not self.api_key:
            if self.fail_silently:
                return 0
            raise RuntimeError("BREVO_API_KEY is not set.")
        sent = 0
        for message in email_messages:
            try:
                self._send(message)
                sent += 1
            except Exception:
                # Never log message bodies (they contain reset links) or addresses.
                logger.exception("Brevo email send failed")
                if not self.fail_silently:
                    raise
        return sent

    def _send(self, message) -> None:
        sender_name, sender_email = parseaddr(message.from_email or settings.DEFAULT_FROM_EMAIL)
        payload = {
            "sender": {"email": sender_email, **({"name": sender_name} if sender_name else {})},
            "to": [{"email": parseaddr(addr)[1]} for addr in message.to],
            "subject": message.subject,
            "textContent": message.body,
        }
        for alternative, mimetype in getattr(message, "alternatives", []) or []:
            if mimetype == "text/html":
                payload["htmlContent"] = alternative
        request = urllib.request.Request(
            BREVO_SEND_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "api-key": self.api_key,
                "accept": "application/json",
                "content-type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:  # noqa: S310 (fixed https URL)
                if response.status >= 300:
                    raise RuntimeError(f"Brevo API returned HTTP {response.status}")
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"Brevo API returned HTTP {exc.code}") from exc
