import pytest
from django.urls import reverse

from apps.resumes.models import Resume, ResumeEducation, ResumeProfile, ResumeSkill
from apps.skills.models import Skill, SkillAlias

from .conftest import pdf_upload

pytestmark = pytest.mark.django_db


def upload_resume(client) -> str:
    response = client.post(reverse("resume-list"), {"file": pdf_upload()}, format="multipart")
    assert response.status_code == 201, response.content
    return response.json()["id"]


def extraction(client, resume_id):
    return client.get(reverse("resume-extraction", kwargs={"pk": resume_id}))


def section_url(resume_id, section, pk=None):
    if pk is None:
        return reverse(f"resume-{section}-list", kwargs={"resume_pk": resume_id})
    return reverse(f"resume-{section}-detail", kwargs={"resume_pk": resume_id, "pk": pk})


def first_error_code(response, field):
    return response.json()["error"]["fields"][field][0]["code"]


# --- Seed data -----------------------------------------------------------------------


def test_skill_dictionary_is_seeded_by_migration():
    assert Skill.objects.count() >= 100
    postgres = Skill.objects.get(name="PostgreSQL")
    assert SkillAlias.objects.filter(skill=postgres, alias__iexact="postgres").exists()
    assert SkillAlias.objects.get(alias="Go").is_ambiguous
    assert Skill.objects.get(name="C++").slug == "c-plus-plus"


# --- Extraction after upload ------------------------------------------------------


class TestExtraction:
    def test_upload_produces_structured_data_with_provenance(self, auth_client):
        resume_id = upload_resume(auth_client)
        response = extraction(auth_client, resume_id)

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "parsed"
        assert body["profile"]["full_name"] == "Alex Example"
        assert body["profile"]["email"] == "alex.example@example.com"
        assert body["profile"]["user_edited"] is False

        skills = {s["name"]: s for s in body["skills"]}
        assert {"Python", "Django REST Framework", "PostgreSQL", "React", "TypeScript"} <= set(skills)
        python = skills["Python"]
        assert python["source"] == "parser"
        assert python["is_verified"] is False
        assert python["canonical"] is True
        assert python["section"] == "skills"
        assert "Python" in python["evidence"]

        assert body["education"][0]["degree"] == "B.Tech"
        assert body["education"][0]["institution"] == "Example Institute of Technology"
        assert body["projects"][0]["name"] == "Inventory Tracker"
        assert "section_not_found:experience" in body["parse_warnings"]
        assert body["experience"] == []

    def test_extraction_query_count_is_bounded(self, auth_client, django_assert_max_num_queries):
        resume_id = upload_resume(auth_client)
        with django_assert_max_num_queries(10):
            assert extraction(auth_client, resume_id).status_code == 200

    def test_parser_failure_keeps_upload(self, auth_client, monkeypatch):
        def boom(*args, **kwargs):
            raise RuntimeError("parser bug")

        monkeypatch.setattr("apps.resumes.services.resume_parsing.parse_resume_text", boom)
        resume_id = upload_resume(auth_client)
        resume = Resume.objects.get(pk=resume_id)
        assert resume.status == Resume.Status.TEXT_EXTRACTED
        assert resume.error_code == "parse_failed"
        assert resume.extracted_text  # raw text still available for manual entry


# --- Editing -------------------------------------------------------------------------


class TestSkillEditing:
    def test_add_skill_normalises_alias_and_marks_user_source(self, auth_client):
        resume_id = upload_resume(auth_client)
        response = auth_client.post(section_url(resume_id, "skills"), {"name": "JS", "source": "parser"})
        assert response.status_code == 201, response.content
        body = response.json()
        assert body["name"] == "JavaScript"
        assert body["canonical"] is True
        assert body["source"] == "user"  # client cannot forge provenance
        assert body["is_verified"] is True
        assert body["evidence"] == ""

    def test_custom_skill_outside_dictionary_is_allowed(self, auth_client):
        resume_id = upload_resume(auth_client)
        response = auth_client.post(section_url(resume_id, "skills"), {"name": "Prompt  Engineering"})
        assert response.status_code == 201
        assert response.json()["name"] == "Prompt Engineering"
        assert response.json()["canonical"] is False

    @pytest.mark.parametrize("name", ["python", "PYTHON", "python3"])
    def test_duplicate_skill_is_rejected(self, auth_client, name):
        resume_id = upload_resume(auth_client)
        response = auth_client.post(section_url(resume_id, "skills"), {"name": name})
        assert response.status_code == 400
        assert first_error_code(response, "name") == "duplicate_skill"

    def test_blank_skill_is_rejected(self, auth_client):
        resume_id = upload_resume(auth_client)
        response = auth_client.post(section_url(resume_id, "skills"), {"name": "   "})
        assert response.status_code == 400

    def test_confirm_and_delete_parser_skill(self, auth_client):
        resume_id = upload_resume(auth_client)
        skill = ResumeSkill.objects.get(resume_id=resume_id, name="Python")

        response = auth_client.patch(section_url(resume_id, "skills", skill.pk), {"is_verified": True})
        assert response.status_code == 200
        assert response.json()["is_verified"] is True
        assert response.json()["source"] == "parser"

        assert auth_client.delete(section_url(resume_id, "skills", skill.pk)).status_code == 204
        assert not ResumeSkill.objects.filter(pk=skill.pk).exists()


class TestEntryEditing:
    def test_editing_a_parser_entry_marks_it_verified(self, auth_client):
        resume_id = upload_resume(auth_client)
        edu = ResumeEducation.objects.get(resume_id=resume_id)
        response = auth_client.patch(section_url(resume_id, "education", edu.pk), {"grade": "CGPA 8.9/10"})
        assert response.status_code == 200
        assert response.json()["grade"] == "CGPA 8.9/10"
        assert response.json()["is_verified"] is True

    def test_education_needs_institution_or_degree(self, auth_client):
        resume_id = upload_resume(auth_client)
        response = auth_client.post(section_url(resume_id, "education"), {"grade": "9.0"})
        assert response.status_code == 400
        assert first_error_code(response, "non_field_errors") == "incomplete_entry"

    def test_experience_validation(self, auth_client):
        resume_id = upload_resume(auth_client)
        url = section_url(resume_id, "experience")
        response = auth_client.post(url, {"title": "Intern", "is_current": True, "end_date": "2024"})
        assert response.status_code == 400
        assert first_error_code(response, "end_date") == "current_with_end_date"

        response = auth_client.post(url, {"description": "no title or company"})
        assert response.status_code == 400

        response = auth_client.post(url, {"title": "Intern", "company": "Acme", "start_date": "Jun 2024", "is_current": True})
        assert response.status_code == 201
        assert response.json()["source"] == "user"

    def test_project_technologies_are_normalised_and_deduplicated(self, auth_client):
        resume_id = upload_resume(auth_client)
        response = auth_client.post(
            section_url(resume_id, "projects"),
            {"name": "Chat", "technologies": ["JS", "javascript", "Redis", "Custom Tool"]},
        )
        assert response.status_code == 201
        assert response.json()["technologies"] == ["JavaScript", "Redis", "Custom Tool"]

    def test_certification_crud(self, auth_client):
        resume_id = upload_resume(auth_client)
        url = section_url(resume_id, "certifications")
        created = auth_client.post(url, {"name": "Example Cert", "issuer": "Example Org", "issue_date": "2024"})
        assert created.status_code == 201
        cert_id = created.json()["id"]
        assert auth_client.get(url).json()[0]["name"] == "Example Cert"
        assert auth_client.patch(section_url(resume_id, "certifications", cert_id), {"name": ""}).status_code == 400
        assert auth_client.delete(section_url(resume_id, "certifications", cert_id)).status_code == 204

    def test_profile_edit_sets_user_edited(self, auth_client):
        resume_id = upload_resume(auth_client)
        url = reverse("resume-profile", kwargs={"resume_pk": resume_id})
        response = auth_client.patch(url, {"location": "Pune, India", "links": ["github.com/alex"]})
        assert response.status_code == 200
        assert response.json()["user_edited"] is True
        assert response.json()["location"] == "Pune, India"
        bad = auth_client.patch(url, {"links": ["not a url with spaces"]})
        assert bad.status_code == 400
        assert auth_client.patch(url, {"email": "not-an-email"}).status_code == 400


class TestReparse:
    def test_reparse_preserves_user_work(self, auth_client):
        resume_id = upload_resume(auth_client)
        auth_client.patch(reverse("resume-profile", kwargs={"resume_pk": resume_id}), {"full_name": "Alex E."})
        auth_client.post(section_url(resume_id, "skills"), {"name": "Kubernetes"})
        python = ResumeSkill.objects.get(resume_id=resume_id, name="Python")
        auth_client.patch(section_url(resume_id, "skills", python.pk), {"is_verified": True})
        skill_count = ResumeSkill.objects.filter(resume_id=resume_id).count()

        response = auth_client.post(reverse("resume-reparse", kwargs={"pk": resume_id}))

        assert response.status_code == 200
        assert response.json()["profile"]["full_name"] == "Alex E."
        names = [s["name"] for s in response.json()["skills"]]
        assert "Kubernetes" in names
        assert names.count("Python") == 1
        assert ResumeSkill.objects.filter(resume_id=resume_id).count() == skill_count
        assert ResumeSkill.objects.get(pk=python.pk).is_verified  # same row kept


# --- Authorization -----------------------------------------------------------------


class TestOwnership:
    def test_other_user_cannot_read_or_edit_structured_data(self, auth_client, other_client):
        resume_id = upload_resume(auth_client)
        skill = ResumeSkill.objects.filter(resume_id=resume_id).first()

        assert extraction(other_client, resume_id).status_code == 404
        assert other_client.get(section_url(resume_id, "skills")).status_code == 404
        assert other_client.post(section_url(resume_id, "skills"), {"name": "Go"}).status_code == 404
        assert other_client.patch(section_url(resume_id, "skills", skill.pk), {"name": "X"}).status_code == 404
        assert other_client.delete(section_url(resume_id, "skills", skill.pk)).status_code == 404
        assert other_client.get(reverse("resume-profile", kwargs={"resume_pk": resume_id})).status_code == 404
        assert other_client.post(reverse("resume-reparse", kwargs={"pk": resume_id})).status_code == 404
        assert ResumeSkill.objects.filter(pk=skill.pk).exists()

    def test_entry_ids_cannot_be_reached_through_another_resume(self, auth_client, other_client):
        victim_resume = upload_resume(auth_client)
        victim_skill = ResumeSkill.objects.filter(resume_id=victim_resume).first()
        own_resume = upload_resume(other_client)
        url = section_url(own_resume, "skills", victim_skill.pk)
        assert other_client.patch(url, {"name": "Hijacked"}).status_code == 404
        assert other_client.delete(url).status_code == 404

    def test_structured_endpoints_require_authentication(self, api_client, auth_client):
        resume_id = upload_resume(auth_client)
        assert extraction(api_client, resume_id).status_code == 403
        assert api_client.get(section_url(resume_id, "skills")).status_code == 403

    def test_deleting_resume_removes_structured_data(self, auth_client):
        resume_id = upload_resume(auth_client)
        auth_client.delete(reverse("resume-detail", kwargs={"pk": resume_id}))
        assert not ResumeSkill.objects.filter(resume_id=resume_id).exists()
        assert not ResumeProfile.objects.filter(resume_id=resume_id).exists()
