import pytest
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.accounts.models import User

from .pdf_factory import make_pdf

TEST_PASSWORD = "Correct-Horse-Battery-42"


@pytest.fixture(autouse=True)
def _clear_cache():
    """Throttle counters live in the cache; isolate them per test."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def user(db) -> User:
    return User.objects.create_user(
        email="alex@example.com", password=TEST_PASSWORD, full_name="Alex Example"
    )


@pytest.fixture
def other_user(db) -> User:
    return User.objects.create_user(
        email="blake@example.com", password=TEST_PASSWORD, full_name="Blake Example"
    )


@pytest.fixture
def auth_client(user) -> APIClient:
    client = APIClient()
    client.force_login(user)
    return client


@pytest.fixture
def other_client(other_user) -> APIClient:
    client = APIClient()
    client.force_login(other_user)
    return client


def pdf_upload(
    data: bytes | None = None,
    name: str = "resume.pdf",
    content_type: str = "application/pdf",
) -> SimpleUploadedFile:
    return SimpleUploadedFile(name, make_pdf() if data is None else data, content_type=content_type)
