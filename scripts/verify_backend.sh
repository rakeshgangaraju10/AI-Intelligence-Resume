#!/usr/bin/env bash
# Stage 2 verification: builds the stack, runs every backend check, and writes
# all output to verify-report.txt (send this file back for review).
#
#   Usage (from the repository root):  bash scripts/verify_backend.sh
#   Needs: Docker with Compose v2. The optional smoke test also needs curl + python3 on the host.
set -uo pipefail

cd "$(dirname "$0")/.."
REPORT="verify-report.txt"
: > "$REPORT"
declare -a SUMMARY=()

log() { echo -e "$*" | tee -a "$REPORT"; }

run_step() {
  local name="$1"; shift
  log "\n================ $name ================"
  log "\$ $*"
  "$@" 2>&1 | tee -a "$REPORT"
  local code=${PIPESTATUS[0]}
  SUMMARY+=("$( [ "$code" -eq 0 ] && echo PASS || echo "FAIL($code)" )  $name")
  return "$code"
}

in_backend() { docker compose run --rm --no-deps backend sh -c "$1"; }

log "CareerForge Stage 2 verification - $(date -u +%Y-%m-%dT%H:%M:%SZ)"
log "Host: $(uname -a 2>/dev/null || echo unknown)"

if [ ! -f .env ]; then
  log "No .env found - creating one from .env.example with a random secret key."
  cp .env.example .env
  SECRET="$(LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom | head -c 50)"
  sed -i.bak "s|^DJANGO_SECRET_KEY=.*|DJANGO_SECRET_KEY=${SECRET}|" .env && rm -f .env.bak
fi

run_step "Docker versions"            sh -c "docker --version && docker compose version"
run_step "Build backend image"        docker compose build backend || { log "Build failed - stopping."; exit 1; }
run_step "Start PostgreSQL"           docker compose up -d --wait db
run_step "Python + key packages"      in_backend "python --version && pip list 2>/dev/null | grep -iE '^(django|djangorestframework|drf-spectacular|django-cors-headers|django-environ|psycopg|pymupdf|pytest|pytest-django|gunicorn) '"
run_step "Freeze requirements.lock"   in_backend "pip freeze > requirements.lock && wc -l requirements.lock"
run_step "Django system check"        in_backend "python manage.py check"
run_step "Deploy check (production)"  in_backend "DJANGO_SETTINGS_MODULE=config.settings.production python manage.py check --deploy"
run_step "Migrations up to date"      in_backend "python manage.py makemigrations --check --dry-run"
run_step "Apply migrations"           in_backend "python manage.py migrate --noinput"
run_step "Show migrations"            in_backend "python manage.py showmigrations accounts resumes"
run_step "OpenAPI schema (no warnings)"   in_backend "python manage.py spectacular --fail-on-warn --file /tmp/schema.yml && echo schema-ok"
run_step "pytest"                     in_backend "pytest --cov=apps --cov-report=term-missing"

# Optional end-to-end smoke test against the running dev server.
if command -v curl >/dev/null && command -v python3 >/dev/null; then
  run_step "Start backend server" docker compose up -d --wait backend || true
  for _ in $(seq 1 30); do curl -sf http://localhost:8000/api/v1/health/ >/dev/null && break; sleep 2; done
  run_step "Generate sample PDF"  in_backend "python /scripts/make_sample_pdf.py /app/sample_resume.pdf"
  run_step "API smoke test"       bash scripts/smoke_test_api.sh backend/sample_resume.pdf
else
  SUMMARY+=("SKIP  API smoke test (needs curl and python3 on the host)")
fi

log "\n================ SUMMARY ================"
for line in "${SUMMARY[@]}"; do log "$line"; done
log "\nFull output saved to $REPORT. requirements.lock was written to backend/."
log "Stop the stack with: docker compose down"
