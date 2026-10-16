import hashlib
import uuid
from pathlib import Path

import pytest
from django.conf import settings
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework.throttling import ScopedRateThrottle

from apps.resumes.models import Resume

from .conftest import pdf_upload
from .pdf_factory import make_blank_pdf, make_corrupt_pdf, make_encrypted_pdf, make_pdf

pytestmark = pytest.mark.django_db

LIST_URL = reverse("resume-list")


def detail_url(resume_id) -> str:
    return reverse("resume-detail", kwargs={"pk": str(resume_id)})


def upload(client: APIClient, file=None, **extra):
    data = {"file": file if file is not None else pdf_upload(), **extra}
    return client.post(LIST_URL, data, format="multipart")


def field_error_code(response, field: str = "file") -> str:
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    return body["error"]["fields"][field][0]["code"]


# --- Upload ---------------------------------------------------------------------


class TestUpload:
    def test_valid_pdf_is_stored_and_text_extracted(self, auth_client, user):
        data = make_pdf()
        response = upload(auth_client, pdf_upload(data, name="Alex Resume.pdf"))

        assert response.status_code == 201, response.content
        body = response.json()
        assert body["title"] == "Alex Resume"
        assert body["original_filename"] == "Alex Resume.pdf"
        assert body["page_count"] == 1
        assert body["status"] == "parsed"  # structured parsing runs right after upload
        assert "Django REST Framework" in body["extracted_text"]
        assert body["char_count"] == len(body["extracted_text"])

        resume = Resume.objects.get(pk=body["id"])
        assert resume.owner == user
        assert resume.file_size == len(data)
        assert resume.sha256 == hashlib.sha256(data).hexdigest()

    def test_file_is_stored_privately_with_server_generated_name(self, auth_client, user):
        response = upload(auth_client, pdf_upload(name="../../../etc/evil.pdf"))
        assert response.status_code == 201
        resume = Resume.objects.get(pk=response.json()["id"])

        stored = Path(resume.file.path).resolve()
        private_root = Path(settings.PRIVATE_MEDIA_ROOT).resolve()
        assert stored.is_relative_to(private_root / "resumes" / str(user.pk))
        assert "evil" not in stored.name
        assert stored.suffix == ".pdf"
        assert resume.original_filename == "evil.pdf"
        # No public URL can be generated for a private resume.
        with pytest.raises(ValueError):
            _ = resume.file.url
        # The API never exposes a storage path or URL.
        assert "file" not in response.json()

    def test_custom_title_is_used(self, auth_client):
        response = upload(auth_client, title="Backend roles v2")
        assert response.status_code == 201
        assert response.json()["title"] == "Backend roles v2"

    @pytest.mark.parametrize(
        ("file_factory", "expected_code"),
        [
            (lambda: pdf_upload(name="resume.docx"), "invalid_extension"),
            (lambda: pdf_upload(b"\x89PNG\r\n\x1a\n" + b"0" * 200), "invalid_signature"),
            (lambda: pdf_upload(make_corrupt_pdf()), "pdf_corrupt"),
            (lambda: pdf_upload(make_encrypted_pdf()), "pdf_encrypted"),
            (lambda: pdf_upload(make_blank_pdf()), "pdf_no_text"),
            (lambda: pdf_upload(b""), "empty_file"),
        ],
        ids=["extension", "signature", "corrupt", "encrypted", "scanned", "empty"],
    )
    def test_invalid_files_are_rejected_and_not_stored(self, auth_client, file_factory, expected_code):
        files_before = set(Path(settings.PRIVATE_MEDIA_ROOT).rglob("*.pdf"))

        response = upload(auth_client, file_factory())

        assert response.status_code == 400
        assert field_error_code(response) == expected_code
        assert Resume.objects.count() == 0
        assert set(Path(settings.PRIVATE_MEDIA_ROOT).rglob("*.pdf")) == files_before

    def test_oversized_file_is_rejected(self, auth_client, settings):
        settings.RESUME_MAX_UPLOAD_BYTES = 500
        response = upload(auth_client, pdf_upload(make_pdf()))  # generated PDF > 500 bytes
        assert response.status_code == 400
        assert field_error_code(response) == "file_too_large"

    def test_too_many_pages_is_rejected(self, auth_client, settings):
        settings.RESUME_MAX_PAGES = 1
        pdf = make_pdf([["Page one " * 10], ["Page two " * 10]])
        response = upload(auth_client, pdf_upload(pdf))
        assert response.status_code == 400
        assert field_error_code(response) == "pdf_too_many_pages"

    def test_missing_file_field(self, auth_client):
        response = auth_client.post(LIST_URL, {"title": "x"}, format="multipart")
        assert response.status_code == 400
        assert field_error_code(response) == "required"

    def test_json_body_cannot_upload(self, auth_client):
        response = auth_client.post(LIST_URL, {"file": "not-a-file"}, format="json")
        assert response.status_code == 400

    def test_upload_requires_authentication(self, api_client):
        response = upload(api_client)
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "not_authenticated"
        assert Resume.objects.count() == 0

    def test_upload_is_rate_limited(self, auth_client, monkeypatch):
        # DRF copies rates onto the throttle class at import time, so patch the class.
        monkeypatch.setattr(
            ScopedRateThrottle, "THROTTLE_RATES", {"auth": "1000/minute", "uploads": "2/minute"}
        )
        assert upload(auth_client).status_code == 201
        assert upload(auth_client).status_code == 201
        response = upload(auth_client)
        assert response.status_code == 429
        assert response.json()["error"]["code"] == "throttled"


# --- List / retrieve / delete ------------------------------------------------------


class TestReadAndDelete:
    def test_list_returns_only_own_resumes_paginated(self, auth_client, other_client):
        upload(auth_client)
        upload(auth_client)
        upload(other_client)

        response = auth_client.get(LIST_URL)

        assert response.status_code == 200
        body = response.json()
        assert body["count"] == 2
        assert len(body["results"]) == 2
        assert "extracted_text" not in body["results"][0]  # list is lightweight

    def test_list_query_count_is_constant(self, auth_client, django_assert_max_num_queries):
        for _ in range(3):
            upload(auth_client)
        # session + user + count + page; must not grow with the number of rows.
        with django_assert_max_num_queries(5):
            assert auth_client.get(LIST_URL).status_code == 200

    def test_retrieve_own_resume(self, auth_client):
        resume_id = upload(auth_client).json()["id"]
        response = auth_client.get(detail_url(resume_id))
        assert response.status_code == 200
        assert response.json()["id"] == resume_id
        assert "extracted_text" in response.json()

    def test_cannot_retrieve_another_users_resume(self, auth_client, other_client):
        resume_id = upload(auth_client).json()["id"]
        response = other_client.get(detail_url(resume_id))
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"

    def test_cannot_delete_another_users_resume(self, auth_client, other_client):
        resume_id = upload(auth_client).json()["id"]
        response = other_client.delete(detail_url(resume_id))
        assert response.status_code == 404
        assert Resume.objects.filter(pk=resume_id).exists()

    def test_unknown_and_malformed_ids_return_404(self, auth_client):
        assert auth_client.get(detail_url(uuid.uuid4())).status_code == 404
        assert auth_client.get(f"{LIST_URL}not-a-uuid/").status_code == 404

    def test_delete_removes_row_and_file(self, auth_client, django_capture_on_commit_callbacks):
        resume_id = upload(auth_client).json()["id"]
        file_path = Path(Resume.objects.get(pk=resume_id).file.path)
        assert file_path.exists()

        with django_capture_on_commit_callbacks(execute=True):
            response = auth_client.delete(detail_url(resume_id))

        assert response.status_code == 204
        assert not Resume.objects.filter(pk=resume_id).exists()
        assert not file_path.exists()

    def test_deleting_user_removes_their_files(self, auth_client, user, django_capture_on_commit_callbacks):
        resume_id = upload(auth_client).json()["id"]
        file_path = Path(Resume.objects.get(pk=resume_id).file.path)

        with django_capture_on_commit_callbacks(execute=True):
            user.delete()

        assert not Resume.objects.filter(pk=resume_id).exists()
        assert not file_path.exists()

    def test_read_endpoints_require_authentication(self, api_client, auth_client):
        resume_id = upload(auth_client).json()["id"]
        assert api_client.get(LIST_URL).status_code == 403
        assert api_client.get(detail_url(resume_id)).status_code == 403
        assert api_client.delete(detail_url(resume_id)).status_code == 403

    def test_rename_resume(self, auth_client):
        resume_id = upload(auth_client).json()["id"]
        response = auth_client.patch(detail_url(resume_id), {"title": "  Backend v3  "}, format="json")
        assert response.status_code == 200
        assert response.json()["title"] == "Backend v3"

    def test_rename_rejects_blank_title_and_ignores_other_fields(self, auth_client):
        resume_id = upload(auth_client).json()["id"]
        response = auth_client.patch(detail_url(resume_id), {"title": "   "}, format="json")
        assert response.status_code == 400
        response = auth_client.patch(
            detail_url(resume_id), {"title": "ok", "extracted_text": "hacked", "status": "failed"}, format="json"
        )
        assert response.status_code == 200
        resume = Resume.objects.get(pk=resume_id)
        assert resume.extracted_text != "hacked" and resume.status == "parsed"

    def test_put_is_not_allowed(self, auth_client):
        resume_id = upload(auth_client).json()["id"]
        assert auth_client.put(detail_url(resume_id), {"title": "x"}, format="json").status_code == 405

    def test_cannot_rename_another_users_resume(self, auth_client, other_client):
        resume_id = upload(auth_client).json()["id"]
        assert other_client.patch(detail_url(resume_id), {"title": "x"}, format="json").status_code == 404


# --- Deployments that keep no PDF files (RESUME_STORE_FILES=False) ----------------


def test_resume_without_stored_file_still_parses_reparses_and_deletes(auth_client, settings, tmp_path):
    settings.RESUME_STORE_FILES = False
    settings.PRIVATE_MEDIA_ROOT = tmp_path  # nothing may be written here
    response = upload(auth_client)
    assert response.status_code == 201, response.content
    resume = Resume.objects.get(pk=response.json()["id"])
    assert not resume.file
    assert resume.extracted_text
    assert not any(tmp_path.rglob("*.pdf"))

    skills = auth_client.get(reverse("resume-skills-list", kwargs={"resume_pk": resume.pk})).json()
    names = {s["name"] for s in (skills["results"] if isinstance(skills, dict) else skills)}
    assert "Python" in names
    assert auth_client.post(reverse("resume-reparse", kwargs={"pk": resume.pk})).status_code == 200
    assert auth_client.delete(reverse("resume-detail", kwargs={"pk": resume.pk})).status_code == 204
    assert not Resume.objects.filter(pk=resume.pk).exists()
