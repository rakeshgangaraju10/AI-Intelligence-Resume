"""
Password reset by email ("Forgot password?").

- Request: always answers the same way, whether or not the email has an account,
  so the endpoint can't be used to discover who is registered.
- Link: /reset-password/<uid>/<token> on the same site. Tokens come from Django's
  PasswordResetTokenGenerator: they expire (PASSWORD_RESET_TIMEOUT) and stop
  working once the password changes, so each link works once.
- Logs contain user ids only; never emails, links or tokens.
"""
import logging

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from .models import User

logger = logging.getLogger(__name__)


def build_reset_link(request, user: User) -> str:
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    path = f"/reset-password/{uid}/{token}"
    base = getattr(settings, "PASSWORD_RESET_BASE_URL", "").rstrip("/")
    return f"{base}{path}" if base else request.build_absolute_uri(path)


def send_reset_email(request, email: str) -> None:
    user = User.objects.filter(email__iexact=email.strip(), is_active=True).first()
    if user is None or not user.has_usable_password():
        return
    if settings.EMAIL_BACKEND.endswith("dummy.EmailBackend"):
        logger.warning("Password reset requested but no email provider is configured (EMAIL_BACKEND).")
        return
    link = build_reset_link(request, user)
    minutes = settings.PASSWORD_RESET_TIMEOUT // 60
    body = (
        f"Hi {user.full_name or 'there'},\n\n"
        "Someone (hopefully you) asked to reset your CareerForge password.\n"
        f"Open this link within {minutes} minutes to choose a new password:\n\n"
        f"{link}\n\n"
        "If you didn't ask for this, ignore this email; your password stays the same.\n\n"
        "— CareerForge"
    )
    try:
        send_mail("Reset your CareerForge password", body, None, [user.email], fail_silently=False)
        logger.info("Password reset email sent user=%s", user.pk)
    except Exception:
        # The response stays generic either way; the failure is visible in logs.
        logger.exception("Password reset email could not be sent user=%s", user.pk)


def user_from_token(uidb64: str, token: str) -> User | None:
    try:
        pk = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=pk, is_active=True)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return None
    return user if default_token_generator.check_token(user, token) else None
