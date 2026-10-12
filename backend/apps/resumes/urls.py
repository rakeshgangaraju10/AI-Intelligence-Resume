from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import (
    ResumeCertificationViewSet,
    ResumeEducationViewSet,
    ResumeExperienceViewSet,
    ResumeProfileView,
    ResumeProjectViewSet,
    ResumeSkillViewSet,
    ResumeViewSet,
)

router = SimpleRouter()
router.register("resumes", ResumeViewSet, basename="resume")

# Nested section endpoints: /resumes/<uuid>/<section>/ and /resumes/<uuid>/<section>/<id>/
SECTION_VIEWSETS = {
    "skills": ResumeSkillViewSet,
    "education": ResumeEducationViewSet,
    "experience": ResumeExperienceViewSet,
    "projects": ResumeProjectViewSet,
    "certifications": ResumeCertificationViewSet,
}

nested = [path("resumes/<uuid:resume_pk>/profile/", ResumeProfileView.as_view(), name="resume-profile")]
for section, viewset in SECTION_VIEWSETS.items():
    nested += [
        path(
            f"resumes/<uuid:resume_pk>/{section}/",
            viewset.as_view({"get": "list", "post": "create"}),
            name=f"resume-{section}-list",
        ),
        path(
            f"resumes/<uuid:resume_pk>/{section}/<int:pk>/",
            viewset.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}),
            name=f"resume-{section}-detail",
        ),
    ]

urlpatterns = router.urls + nested
