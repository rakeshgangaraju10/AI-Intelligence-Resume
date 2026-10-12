from rest_framework.routers import SimpleRouter

from .views import ResumeViewSet

router = SimpleRouter()
router.register("resumes", ResumeViewSet, basename="resume")

urlpatterns = router.urls
