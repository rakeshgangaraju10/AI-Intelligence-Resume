from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

api_v1 = [
    path("", include("apps.core.urls")),
    path("auth/", include("apps.accounts.urls")),
    path("", include("apps.resumes.urls")),  # routers register their own prefixes
    path("", include("apps.jobs.urls")),
    path("", include("apps.analyses.urls")),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include(api_v1)),
]
# NOTE: there is intentionally no static()/MEDIA_URL route. Uploaded resumes are
# private and are only ever read by server-side code after an ownership check.
