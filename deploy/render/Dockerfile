# One container for free hosting (Render): builds the React app, then runs
# Django + gunicorn, which serve the API, the admin and the SPA.
# Build context is the repository root (see render.yaml).

FROM node:22-alpine AS frontend
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN if [ -f package-lock.json ]; then npm ci --no-audit --no-fund; \
    else npm install --no-audit --no-fund; fi
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DJANGO_SETTINGS_MODULE=config.settings.single_service \
    SPA_DIST_DIR=/app/spa
WORKDIR /app

COPY backend/requirements.txt ./
RUN pip install -r requirements.txt

COPY backend/ ./
COPY --from=frontend /app/dist /app/spa
COPY deploy/render/start.sh /app/start.sh

# Collect admin/Swagger static files at build time. Settings need these two
# variables to import; the values are placeholders used only for this step.
RUN DJANGO_SECRET_KEY=build-only DATABASE_URL=postgres://build:build@localhost:5432/build \
    python manage.py collectstatic --noinput

RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/private_media \
    && chown -R appuser:appuser /app \
    && chmod 700 /app/private_media \
    && chmod +x /app/start.sh
USER appuser

EXPOSE 8000
CMD ["/app/start.sh"]
