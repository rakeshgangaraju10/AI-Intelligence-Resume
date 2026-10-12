FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# psycopg[binary] and PyMuPDF ship manylinux wheels, so no compiler or libpq is needed.
COPY requirements.txt requirements-dev.txt ./
ARG INSTALL_DEV=false
RUN if [ "$INSTALL_DEV" = "true" ]; then pip install -r requirements-dev.txt; \
    else pip install -r requirements.txt; fi

COPY . .

# Run as an unprivileged user; uploads go to a directory only this user can read.
RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/private_media \
    && chown -R appuser:appuser /app \
    && chmod 700 /app/private_media
USER appuser

EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-"]
