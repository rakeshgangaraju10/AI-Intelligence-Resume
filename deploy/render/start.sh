#!/bin/sh
# Container start: apply migrations, optionally create the admin account, run gunicorn.
set -e
python manage.py migrate --noinput

# Optional: set DJANGO_SUPERUSER_EMAIL, DJANGO_SUPERUSER_PASSWORD and
# DJANGO_SUPERUSER_FULL_NAME to create an admin on first start (no shell needed).
if [ -n "${DJANGO_SUPERUSER_EMAIL:-}" ] && [ -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]; then
  python manage.py createsuperuser --noinput >/dev/null 2>&1 \
    && echo "Admin account created." || echo "Admin account already exists (or could not be created)."
fi

# Render provides PORT; default 8000 elsewhere.
exec gunicorn config.wsgi:application \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers "${GUNICORN_WORKERS:-2}" \
  --timeout 60 \
  --access-logfile - \
  --forwarded-allow-ips '*'
