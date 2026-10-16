"""
One-container production settings (e.g. Render's free web service).

Django + gunicorn serve everything: the API, the admin, and the built React app
(WhiteNoise serves its files; core.views.spa_index serves index.html for
client-side routes). TLS is terminated by the platform's proxy.
"""
from .production import *  # noqa: F401,F403
from .production import MIDDLEWARE, env

# WhiteNoise right after the security middlewares, as its docs recommend.
MIDDLEWARE = [*MIDDLEWARE]
MIDDLEWARE.insert(MIDDLEWARE.index("apps.core.middleware.SecurityHeadersMiddleware") + 1,
                  "whitenoise.middleware.WhiteNoiseMiddleware")

SPA_DIST_DIR = env("SPA_DIST_DIR", default="/app/spa")
# Serve the SPA's files (favicon, /assets/*) from the site root.
WHITENOISE_ROOT = SPA_DIST_DIR
# Vite fingerprints /assets/* file names, so those can be cached forever.
WHITENOISE_IMMUTABLE_FILE_TEST = r"^/?assets/"

# Free hosts usually have no persistent disk: keep extracted text, not the PDF.
RESUME_STORE_FILES = env.bool("RESUME_STORE_FILES", default=False)
