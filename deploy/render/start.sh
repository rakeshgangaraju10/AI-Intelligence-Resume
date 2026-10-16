#!/bin/sh
# Container start: apply migrations, optionally create the admin account, run gunicorn.
set -e
python manage.py migrate --noinput

# Optional: set DJANGO_SUPERUSER_EMAIL and DJANGO_SUPERUSER_PASSWORD (and
# DJANGO_SUPERUSER_FULL_NAME) to create the admin account, or to reset its
# password, on start. Remove the password variable again after logging in.
# A rejected (too weak) password is reported but doesn't stop the site.
python manage.py ensure_admin || echo "Admin account not changed (see message above)."

# Render provides PORT; default 8000 elsewhere.
exec gunicorn config.wsgi:application \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers "${GUNICORN_WORKERS:-2}" \
  --timeout 60 \
  --access-logfile - \
  --forwarded-allow-ips '*'
