"""Settings for the automated test-suite (pytest). Uses a real PostgreSQL database."""
import os
import tempfile
from pathlib import Path

# Sensible defaults so tests run without a .env file (CI sets DATABASE_URL explicitly).
os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-insecure-secret-key-not-for-production")
os.environ.setdefault(
    "DATABASE_URL", "postgres://careerforge:careerforge@localhost:5432/careerforge"
)

from .base import *  # noqa: E402,F401,F403
from .base import REST_FRAMEWORK  # noqa: E402

DEBUG = False
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]  # speed only

# Each test session writes uploads to a throwaway directory.
PRIVATE_MEDIA_ROOT = Path(tempfile.mkdtemp(prefix="careerforge-test-media-"))

RESUME_MAX_UPLOAD_BYTES = 1024 * 1024  # 1 MB keeps size tests fast
RESUME_MAX_PAGES = 5

# High limits so ordinary tests are never throttled; throttle tests override these.
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_THROTTLE_RATES": {"auth": "1000/minute", "uploads": "1000/minute", "analyses": "1000/minute"},
}

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
