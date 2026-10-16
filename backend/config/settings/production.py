"""Production settings. Expects to run behind an HTTPS-terminating reverse proxy."""
from .base import *  # noqa: F401,F403
from .base import REST_FRAMEWORK, env

DEBUG = False

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = env.int("DJANGO_SECURE_HSTS_SECONDS", default=60 * 60 * 24 * 30)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# If the SPA and API live on different sites, set these to "None" (requires HTTPS).
SESSION_COOKIE_SAMESITE = env("SESSION_COOKIE_SAMESITE", default="Lax")
CSRF_COOKIE_SAMESITE = env("CSRF_COOKIE_SAMESITE", default="Lax")

# Throttling state must be shared across workers in production. Point this at
# Redis/Memcached when running more than one process; LocMem is per-process.
CACHES = {
    "default": env.cache("CACHE_URL", default="locmemcache://"),
}

# Behind nginx every request comes from the proxy's address. Tell DRF how many
# proxies sit in front of Django so rate limits key on the client IP taken
# from X-Forwarded-For (1 = our nginx; 2 = nginx behind a platform load balancer).
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "NUM_PROXIES": env.int("DRF_NUM_PROXIES", default=1),
}

# Never print emails (they contain password-reset links) to production logs.
# Without a configured provider, reset emails are dropped and a warning is logged.
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.dummy.EmailBackend")
