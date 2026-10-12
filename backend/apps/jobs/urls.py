from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import JobRequirementViewSet, JobViewSet

router = SimpleRouter()
router.register("jobs", JobViewSet, basename="job")

urlpatterns = router.urls + [
    path(
        "jobs/<int:job_pk>/requirements/",
        JobRequirementViewSet.as_view({"get": "list", "post": "create"}),
        name="job-requirement-list",
    ),
    path(
        "jobs/<int:job_pk>/requirements/<int:pk>/",
        JobRequirementViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}),
        name="job-requirement-detail",
    ),
]
