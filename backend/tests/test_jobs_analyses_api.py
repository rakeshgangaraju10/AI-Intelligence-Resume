from unittest import mock

import pytest
from django.urls import reverse
from rest_framework.throttling import ScopedRateThrottle

from apps.analyses.models import Analysis
from apps.jobs.models import JobDescription, JobRequirement
from apps.skills.models import SkillGroup

from .conftest import pdf_upload

pytestmark = pytest.mark.django_db

JOBS = reverse("job-list")
ANALYSES = reverse("analysis-list")

JD_TEXT = """Junior Backend Developer

Requirements
- Python and Django
- PostgreSQL
- Docker is a plus

Nice to have
- AWS
"""


def job_url(pk):
    return reverse("job-detail", kwargs={"pk": pk})


def req_url(job_pk, pk=None):
    if pk is None:
        return reverse("job-requirement-list", kwargs={"job_pk": job_pk})
    return reverse("job-requirement-detail", kwargs={"job_pk": job_pk, "pk": pk})


def analysis_url(pk):
    return reverse("analysis-detail", kwargs={"pk": pk})


def upload_resume(client) -> str:
    response = client.post(reverse("resume-list"), {"file": pdf_upload()}, format="multipart")
    assert response.status_code == 201, response.content
    return response.json()["id"]


def make_job(client, **overrides) -> dict:
    payload = {"title": "Backend Intern", "company": "Acme", "experience_level": "internship",
               "description": "", "auto_extract": False, **overrides}
    response = client.post(JOBS, payload)
    assert response.status_code == 201, response.content
    return response.json()


def field_code(response, field):
    return response.json()["error"]["fields"][field][0]["code"]


# --- Seed data -------------------------------------------------------------------------


def test_related_skill_groups_are_seeded():
    group = SkillGroup.objects.get(name="Relational databases")
    assert {"PostgreSQL", "MySQL"} <= set(group.skills.values_list("name", flat=True))


# --- Jobs ------------------------------------------------------------------------------


class TestJobs:
    def test_create_with_description_suggests_requirements(self, auth_client):
        response = auth_client.post(JOBS, {"title": "Junior Backend Developer", "description": JD_TEXT})
        assert response.status_code == 201, response.content
        reqs = {r["name"]: r for r in response.json()["requirements"]}
        assert reqs["Python"]["kind"] == "required"
        assert reqs["Django"]["kind"] == "required"
        assert reqs["PostgreSQL"]["kind"] == "required"
        assert reqs["Docker"]["kind"] == "preferred"
        assert reqs["AWS"]["kind"] == "preferred"
        assert reqs["Python"]["source"] == "extracted"
        assert reqs["Python"]["canonical"] is True
        assert reqs["PostgreSQL"]["evidence"] == "- PostgreSQL"

    def test_explicit_lists_are_canonicalised_weighted_and_deduplicated(self, auth_client):
        job = make_job(
            auth_client,
            required_skills=["JS", {"name": "Docker", "weight": 3}, "python"],
            preferred_skills=["javascript", "Custom Tool"],
        )
        reqs = {r["name"]: r for r in job["requirements"]}
        assert reqs["JavaScript"]["kind"] == "required"  # required wins over the preferred duplicate
        assert reqs["Docker"]["weight"] == 3
        assert reqs["Python"]["source"] == "user"
        assert reqs["Custom Tool"]["canonical"] is False
        assert len(job["requirements"]) == 4
        assert [r["kind"] for r in job["requirements"]][:3] == ["required"] * 3  # required listed first

    def test_empty_job_is_rejected(self, auth_client):
        response = auth_client.post(JOBS, {"title": "Empty", "description": "   "})
        assert response.status_code == 400
        assert field_code(response, "non_field_errors") == "empty_job"

    @pytest.mark.parametrize("item", [{"name": "Docker", "weight": 6}, {"name": "Docker", "weight": 0}, {"weight": 2}, 42])
    def test_invalid_skill_items_are_rejected(self, auth_client, item):
        response = auth_client.post(JOBS, {"title": "x", "required_skills": [item]})
        assert response.status_code == 400

    def test_description_length_limit(self, auth_client):
        response = auth_client.post(JOBS, {"title": "x", "description": "a" * 20_001})
        assert response.status_code == 400
        assert field_code(response, "description") == "too_long"

    def test_update_job_fields(self, auth_client):
        job = make_job(auth_client, required_skills=["Python"])
        response = auth_client.patch(job_url(job["id"]), {"title": "Backend Engineer I", "experience_level": "entry"})
        assert response.status_code == 200
        assert response.json()["title"] == "Backend Engineer I"
        assert auth_client.patch(job_url(job["id"]), {"experience_level": "wizard"}).status_code == 400

    def test_list_counts_and_search(self, auth_client, django_assert_max_num_queries):
        make_job(auth_client, title="Python Developer", required_skills=["Python", "Django"], preferred_skills=["AWS"])
        make_job(auth_client, title="Data Analyst", company="Numbers Inc", required_skills=["SQL"])
        with django_assert_max_num_queries(5):
            body = auth_client.get(JOBS).json()
        assert body["count"] == 2
        python_job = next(j for j in body["results"] if j["title"] == "Python Developer")
        assert (python_job["required_count"], python_job["preferred_count"]) == (2, 1)
        assert auth_client.get(JOBS, {"search": "numbers"}).json()["count"] == 1

    def test_requirement_crud(self, auth_client):
        job = make_job(auth_client, required_skills=["Python"])
        created = auth_client.post(req_url(job["id"]), {"name": "k8s", "kind": "preferred", "weight": 2})
        assert created.status_code == 201
        assert created.json()["name"] == "Kubernetes"
        assert created.json()["source"] == "user"
        duplicate = auth_client.post(req_url(job["id"]), {"name": "PYTHON"})
        assert field_code(duplicate, "name") == "duplicate_skill"
        assert auth_client.post(req_url(job["id"]), {"name": "Go", "weight": 0}).status_code == 400
        req_id = created.json()["id"]
        assert auth_client.patch(req_url(job["id"], req_id), {"weight": 5}).json()["weight"] == 5
        assert auth_client.delete(req_url(job["id"], req_id)).status_code == 204

    def test_suggest_requirements_only_adds_new_skills(self, auth_client):
        job = make_job(auth_client, description=JD_TEXT, required_skills=[{"name": "Python", "weight": 4}])
        response = auth_client.post(reverse("job-suggest-requirements", kwargs={"pk": job["id"]}))
        assert response.status_code == 200
        assert response.json()["added"] == 4  # Django, PostgreSQL, Docker, AWS
        python = JobRequirement.objects.get(job_id=job["id"], name="Python")
        assert python.weight == 4 and python.source == "user"  # untouched
        again = auth_client.post(reverse("job-suggest-requirements", kwargs={"pk": job["id"]}))
        assert again.json()["added"] == 0

    def test_other_users_cannot_access_jobs(self, auth_client, other_client):
        job = make_job(auth_client, required_skills=["Python"])
        req_id = job["requirements"][0]["id"]
        assert other_client.get(job_url(job["id"])).status_code == 404
        assert other_client.patch(job_url(job["id"]), {"title": "x"}).status_code == 404
        assert other_client.delete(job_url(job["id"])).status_code == 404
        assert other_client.get(req_url(job["id"])).status_code == 404
        assert other_client.patch(req_url(job["id"], req_id), {"weight": 5}).status_code == 404
        assert other_client.get(JOBS).json()["count"] == 0
        assert JobDescription.objects.filter(pk=job["id"]).exists()


# --- Analyses ----------------------------------------------------------------------------


def analysis_job(client) -> dict:
    # Resume (test PDF): Python, DRF, PostgreSQL, React, TypeScript in Skills;
    # Django/PostgreSQL/React in project "Inventory Tracker".
    return make_job(
        client,
        title="Backend Intern",
        required_skills=[{"name": "Python", "weight": 2}, "Django", "Docker", "MySQL"],
        preferred_skills=["AWS", "React"],
    )


class TestAnalyses:
    def test_analysis_scores_explains_and_saves(self, auth_client):
        resume_id = upload_resume(auth_client)
        job = analysis_job(auth_client)

        response = auth_client.post(ANALYSES, {"resume": resume_id, "job": job["id"]})

        assert response.status_code == 201, response.content
        body = response.json()
        # required: Python(2)+Django(1) matched of 5 -> 60.0; preferred: React of 2 -> 50.0
        assert body["required_coverage"] == 60.0
        assert body["preferred_coverage"] == 50.0
        assert body["score"] == 58.0  # 0.8*60 + 0.2*50
        assert isinstance(body["score"], float)
        assert "not a probability of being hired" in body["score_label"]
        assert body["algorithm_version"] == "baseline-v1"
        assert body["breakdown"]["related_skills_count_toward_score"] is False

        results = {r["skill_name"]: r for r in body["skill_results"]}
        assert results["Python"]["status"] == "matched"
        assert results["Django"]["status"] == "matched"
        assert results["Django"]["evidence"][0]["location"] == "Project: Inventory Tracker"
        assert results["Docker"]["status"] == "missing"
        assert results["MySQL"]["status"] == "related"
        assert results["MySQL"]["related_to"] == ["PostgreSQL"]
        assert results["MySQL"]["related_reason"] == "relational SQL databases"
        assert results["AWS"]["status"] == "missing"
        assert all(r["explanation"] for r in body["skill_results"])
        assert any("Django: demonstrated in Project: Inventory Tracker" in s for s in body["strengths"])
        assert "Missing required skill: Docker" in body["improvements"]

        assert Analysis.objects.get(pk=body["id"]).resume_title == "resume"

    def test_job_without_requirements_cannot_be_analysed(self, auth_client):
        resume_id = upload_resume(auth_client)
        job = make_job(auth_client, description="We want a kind, curious teammate.", auto_extract=True)
        assert job["requirements"] == []
        response = auth_client.post(ANALYSES, {"resume": resume_id, "job": job["id"]})
        assert response.status_code == 400
        assert field_code(response, "job") == "no_requirements"
        assert Analysis.objects.count() == 0

    def test_history_is_a_snapshot(self, auth_client):
        resume_id = upload_resume(auth_client)
        job = analysis_job(auth_client)
        first = auth_client.post(ANALYSES, {"resume": resume_id, "job": job["id"]}).json()

        auth_client.patch(job_url(job["id"]), {"title": "Renamed"})
        auth_client.post(reverse("resume-skills-list", kwargs={"resume_pk": resume_id}), {"name": "Docker"})
        second = auth_client.post(ANALYSES, {"resume": resume_id, "job": job["id"]}).json()

        old = auth_client.get(analysis_url(first["id"])).json()
        assert old["score"] == 58.0 and old["job_title"] == "Backend Intern @ Acme"
        assert second["score"] == 74.0  # Docker now matched: 0.8*80 + 0.2*50
        assert second["job_title"] == "Renamed @ Acme"

    def test_list_filter_and_counts(self, auth_client, django_assert_max_num_queries):
        resume_id = upload_resume(auth_client)
        job = analysis_job(auth_client)
        for _ in range(3):
            auth_client.post(ANALYSES, {"resume": resume_id, "job": job["id"]})
        with django_assert_max_num_queries(5):
            body = auth_client.get(ANALYSES).json()
        assert body["count"] == 3
        assert (body["results"][0]["matched_count"], body["results"][0]["missing_count"]) == (3, 3)
        assert auth_client.get(ANALYSES, {"resume": resume_id}).json()["count"] == 3
        assert auth_client.get(ANALYSES, {"job": job["id"] + 999}).json()["count"] == 0
        assert auth_client.get(ANALYSES, {"resume": "not-a-uuid"}).status_code == 400

    def test_cannot_use_or_see_other_users_objects(self, auth_client, other_client):
        resume_id = upload_resume(auth_client)
        job = analysis_job(auth_client)
        analysis = auth_client.post(ANALYSES, {"resume": resume_id, "job": job["id"]}).json()

        own_resume = upload_resume(other_client)
        own_job = analysis_job(other_client)
        response = other_client.post(ANALYSES, {"resume": resume_id, "job": own_job["id"]})
        assert response.status_code == 400 and field_code(response, "resume") == "does_not_exist"
        response = other_client.post(ANALYSES, {"resume": own_resume, "job": job["id"]})
        assert response.status_code == 400 and field_code(response, "job") == "does_not_exist"

        assert other_client.get(analysis_url(analysis["id"])).status_code == 404
        assert other_client.delete(analysis_url(analysis["id"])).status_code == 404
        assert other_client.get(ANALYSES).json()["count"] == 0
        assert Analysis.objects.filter(pk=analysis["id"]).exists()

    def test_malformed_ids_are_validation_errors(self, auth_client):
        response = auth_client.post(ANALYSES, {"resume": "nope", "job": "x"})
        assert response.status_code == 400
        assert set(response.json()["error"]["fields"]) == {"resume", "job"}

    def test_delete_and_cascade(self, auth_client):
        resume_id = upload_resume(auth_client)
        job = analysis_job(auth_client)
        a1 = auth_client.post(ANALYSES, {"resume": resume_id, "job": job["id"]}).json()
        a2 = auth_client.post(ANALYSES, {"resume": resume_id, "job": job["id"]}).json()
        assert auth_client.delete(analysis_url(a1["id"])).status_code == 204
        auth_client.delete(reverse("resume-detail", kwargs={"pk": resume_id}))
        assert not Analysis.objects.filter(pk__in=[a1["id"], a2["id"]]).exists()

    def test_requires_authentication(self, api_client):
        assert api_client.get(ANALYSES).status_code == 403
        assert api_client.get(JOBS).status_code == 403


# --- Stage 7: compare, report, rate limit ------------------------------------------------

COMPARE = reverse("analysis-compare")


def report_url(pk):
    return reverse("analysis-report", kwargs={"pk": pk})


def two_versions(client):
    """Same job analysed before and after adding Docker to the resume."""
    resume_id = upload_resume(client)
    job = analysis_job(client)
    first = client.post(ANALYSES, {"resume": resume_id, "job": job["id"]}).json()
    client.post(reverse("resume-skills-list", kwargs={"resume_pk": resume_id}), {"name": "Docker"})
    second = client.post(ANALYSES, {"resume": resume_id, "job": job["id"]}).json()
    return first, second


class TestCompareAndReport:
    def test_compare_two_versions_of_a_resume(self, auth_client, django_assert_max_num_queries):
        first, second = two_versions(auth_client)
        with django_assert_max_num_queries(6):
            response = auth_client.get(COMPARE, {"a": first["id"], "b": second["id"]})
        assert response.status_code == 200, response.content
        body = response.json()
        assert body["a"]["id"] == first["id"] and body["b"]["id"] == second["id"]
        assert body["score_delta"] == 16.0  # 58.0 -> 74.0
        assert body["basis"] == "same_resume_and_job"
        assert body["skills"][0] == {
            "skill_name": "Docker", "kind_a": "required", "kind_b": "required",
            "status_a": "missing", "status_b": "matched", "change": "gained",
        }
        changes = {s["skill_name"]: s["change"] for s in body["skills"]}
        assert changes["Python"] == "unchanged" and changes["AWS"] == "unchanged"

    def test_compare_across_jobs_reports_basis(self, auth_client):
        resume_id = upload_resume(auth_client)
        job_a = analysis_job(auth_client)
        job_b = make_job(auth_client, title="Frontend", required_skills=["React", "TypeScript"])
        a = auth_client.post(ANALYSES, {"resume": resume_id, "job": job_a["id"]}).json()
        b = auth_client.post(ANALYSES, {"resume": resume_id, "job": job_b["id"]}).json()
        body = auth_client.get(COMPARE, {"a": a["id"], "b": b["id"]}).json()
        assert body["basis"] == "same_resume"
        changes = {s["skill_name"]: s["change"] for s in body["skills"]}
        assert changes["TypeScript"] == "only_in_b" and changes["Docker"] == "only_in_a"

    def test_compare_validation(self, auth_client):
        first, _ = two_versions(auth_client)
        response = auth_client.get(COMPARE, {"a": first["id"]})
        assert response.status_code == 400 and field_code(response, "b") == "required"
        response = auth_client.get(COMPARE, {"a": "x", "b": first["id"]})
        assert response.status_code == 400 and field_code(response, "a") == "invalid"
        response = auth_client.get(COMPARE, {"a": first["id"], "b": first["id"]})
        assert response.status_code == 400 and field_code(response, "b") == "same_analysis"
        assert auth_client.get(COMPARE, {"a": first["id"], "b": first["id"] + 999}).status_code == 404

    def test_compare_and_report_are_owner_only(self, auth_client, other_client):
        first, second = two_versions(auth_client)
        mine = two_versions(other_client)[0]
        assert other_client.get(COMPARE, {"a": first["id"], "b": second["id"]}).status_code == 404
        assert other_client.get(COMPARE, {"a": mine["id"], "b": first["id"]}).status_code == 404
        assert other_client.get(report_url(first["id"])).status_code == 404

    def test_markdown_report_download(self, auth_client):
        first, _ = two_versions(auth_client)
        response = auth_client.get(report_url(first["id"]))
        assert response.status_code == 200
        assert response["Content-Type"] == "text/markdown; charset=utf-8"
        assert response["Content-Disposition"] == f'attachment; filename="careerforge-analysis-{first["id"]}.md"'
        assert response["Cache-Control"] == "no-store"
        text = response.content.decode()
        assert "## Matching score: 58.0 / 100" in text
        assert "not a probability of being hired" in text
        assert "| Docker | required | 1 | Missing |" in text
        assert "| MySQL | required | 1 | Related skill found |" in text

    def test_report_and_compare_require_authentication(self, api_client):
        assert api_client.get(report_url(1)).status_code == 403
        assert api_client.get(COMPARE, {"a": 1, "b": 2}).status_code == 403

    def test_running_analyses_is_rate_limited(self, auth_client, monkeypatch):
        monkeypatch.setattr(
            ScopedRateThrottle, "THROTTLE_RATES",
            {"auth": "1000/minute", "uploads": "1000/minute", "analyses": "2/minute"},
        )
        resume_id = upload_resume(auth_client)
        job = analysis_job(auth_client)
        for _ in range(2):
            assert auth_client.post(ANALYSES, {"resume": resume_id, "job": job["id"]}).status_code == 201
        response = auth_client.post(ANALYSES, {"resume": resume_id, "job": job["id"]})
        assert response.status_code == 429
        assert response.json()["error"]["code"] == "throttled"
        # reading history is not throttled
        assert auth_client.get(ANALYSES).status_code == 200


# --- Import a job from a link --------------------------------------------------------------

IMPORT_URL = reverse("job-import-url")


class TestJobImport:
    def test_returns_fields_for_the_form_without_saving(self, auth_client):
        from apps.jobs.services.job_import import ImportedJob

        imported = ImportedJob(title="Junior Backend Developer", company="Acme Example",
                               description="Source: https://jobs.example.com/1\n\nRequirements\n- Python",
                               source_url="https://jobs.example.com/1", method="structured")
        with mock.patch("apps.jobs.views.import_job_from_url", return_value=imported) as importer:
            response = auth_client.post(IMPORT_URL, {"url": "https://jobs.example.com/1"})
        assert response.status_code == 200, response.content
        body = response.json()
        assert body["title"] == "Junior Backend Developer" and body["company"] == "Acme Example"
        assert body["method"] == "structured" and body["warnings"] == []
        importer.assert_called_once_with("https://jobs.example.com/1")
        assert JobDescription.objects.count() == 0

    def test_import_errors_are_field_errors(self, auth_client):
        from apps.jobs.services.job_import import JobImportError

        error = JobImportError("unsupported_site", "LinkedIn doesn't allow job pages to be read automatically.")
        with mock.patch("apps.jobs.views.import_job_from_url", side_effect=error):
            response = auth_client.post(IMPORT_URL, {"url": "https://www.linkedin.com/jobs/view/1"})
        assert response.status_code == 400
        assert field_code(response, "url") == "unsupported_site"
        assert "LinkedIn" in response.json()["error"]["fields"]["url"][0]["message"]

    def test_private_addresses_are_refused_end_to_end(self, auth_client):
        response = auth_client.post(IMPORT_URL, {"url": "http://127.0.0.1/admin/"})
        assert response.status_code == 400
        assert field_code(response, "url") == "blocked_address"

    def test_requires_login_and_url(self, api_client, auth_client):
        assert api_client.post(IMPORT_URL, {"url": "https://example.com"}).status_code == 403
        assert auth_client.post(IMPORT_URL, {}).status_code == 400

    def test_rate_limited(self, auth_client, monkeypatch):
        from apps.jobs.services.job_import import ImportedJob

        monkeypatch.setattr(ScopedRateThrottle, "THROTTLE_RATES", {"job_import": "1/hour", "uploads": "1000/minute"})
        ok = ImportedJob(title="T", company="", description="d", source_url="u", method="page_text")
        with mock.patch("apps.jobs.views.import_job_from_url", return_value=ok):
            assert auth_client.post(IMPORT_URL, {"url": "https://a.example"}).status_code == 200
            assert auth_client.post(IMPORT_URL, {"url": "https://a.example"}).status_code == 429
        # other job endpoints are not throttled by this scope
        assert auth_client.get(JOBS).status_code == 200
