from django.contrib import admin
from django.urls import include, path, re_path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.core.views import spa_index

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
    # Last: client-side routes of the React app (only when SPA_DIST_DIR is set).
    # api/, admin/ and static/ never fall through to the SPA.
    re_path(r"^(?!api(?:/|$)|admin(?:/|$)|static(?:/|$)).*$", spa_index, name="spa"),
]
# NOTE: there is intentionally no static()/MEDIA_URL route. Uploaded resumes are
# private and are only ever read by server-side code after an ownership check.
