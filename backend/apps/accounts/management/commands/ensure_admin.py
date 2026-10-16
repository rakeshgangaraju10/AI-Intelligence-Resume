"""
Create the admin account from environment variables (runs on every start).

Used on hosts without a shell (e.g. Render's free plan): set
DJANGO_SUPERUSER_EMAIL and DJANGO_SUPERUSER_PASSWORD (optionally
DJANGO_SUPERUSER_FULL_NAME), deploy, log in, then remove the password variable.

An existing account's password is only changed when
DJANGO_SUPERUSER_RESET_PASSWORD=true. Otherwise a password left in the
environment would undo every later password change each time the free server
wakes up or restarts. Does nothing when either variable is missing. Never
prints the password.
"""
import os

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create or update the admin account from DJANGO_SUPERUSER_* environment variables."

    def handle(self, *args, **options) -> None:
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "").strip()
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "")
        full_name = os.environ.get("DJANGO_SUPERUSER_FULL_NAME", "").strip() or "Admin"
        if not email or not password:
            self.stdout.write("Admin: DJANGO_SUPERUSER_EMAIL/PASSWORD not set; skipping.")
            return

        User = get_user_model()
        user = User.objects.filter(email__iexact=email).first()
        try:
            validate_password(password, user=user)
        except ValidationError as exc:
            raise CommandError("Admin password rejected: " + " ".join(exc.messages)) from exc

        if user is None:
            User.objects.create_superuser(email=email, password=password, full_name=full_name)
            self.stdout.write("Admin account created.")
            return
        reset = os.environ.get("DJANGO_SUPERUSER_RESET_PASSWORD", "").strip().lower() in {"1", "true", "yes"}
        if not reset:
            self.stdout.write(
                "Admin account exists; password left unchanged "
                "(set DJANGO_SUPERUSER_RESET_PASSWORD=true to reset it)."
            )
            return
        user.set_password(password)
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.save(update_fields=["password", "is_staff", "is_superuser", "is_active"])
        self.stdout.write("Admin account password updated.")
