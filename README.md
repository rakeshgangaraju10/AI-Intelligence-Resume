# CareerForge — AI-Powered Resume Intelligence Platform

CareerForge lets candidates upload a PDF resume, review the information extracted
from it, and compare it against job descriptions with an explainable,
deterministic matching score.

> **Status: backend Stages 1–5 built. Stages 1–4 verified in CI (127 tests, 96% coverage); Stage 5 awaiting its first CI run.** What exists today is listed
> below. Nothing in later stages is implemented yet, and nothing has been deployed.

## What works in Stage 1

| Area | Implemented |
|---|---|
| Accounts | Custom email-based `User` model; register / login / logout / me with session cookies + CSRF; rate-limited auth |
| Resume upload | `POST /api/v1/resumes/` (multipart) with extension, content-type, size and `%PDF-` signature checks |
| Text extraction | PyMuPDF; rejects corrupt, password-protected, scanned (no text layer), too-many-pages and oversized-text PDFs with specific error codes |
| Storage | Private directory, server-generated filenames, no public URL, file removed when the resume or user is deleted |
| Resume API | List (paginated), retrieve, delete — scoped to the owner (other users get 404) |
| Structured parsing (Stage 4) | Rule-based section, contact, skill, education, experience, project and certification extraction; 115-skill dictionary with aliases; evidence for every detected skill |
| Review & editing (Stage 4) | Extraction endpoint, CRUD per section, profile editing, re-parse that preserves user edits, parser vs user provenance |
| Job descriptions (Stage 5) | Save jobs with required/preferred skills and weights; skills suggested from pasted descriptions; full editing |
| Matching (Stage 5) | Deterministic weighted score (0–100) with matched / missing / related skills, resume evidence, per-skill explanations, strengths, improvements and suggestions; results stored as history |
| Platform | Health check, consistent JSON error envelope, OpenAPI schema + Swagger UI, Django Admin |
| Quality | pytest suite (validation, parsing, API, auth, CSRF, ownership, throttling), GitHub Actions CI on PostgreSQL |

Not yet built: React frontend (Stage 6), analysis comparison/report export
(Stage 7), production deploy (Stage 8), optional semantic matching.

## Tech stack

Python 3.12 · Django 5.2 LTS · Django REST Framework 3.16 · PostgreSQL 16 ·
PyMuPDF · drf-spectacular · pytest · Docker Compose · GitHub Actions.
Frontend (React + TypeScript + Vite + Tailwind) arrives in Stage 6.

## Repository layout

```
careerforge/
├── backend/
│   ├── config/                 # settings (base/development/production/test), urls, wsgi
│   ├── apps/
│   │   ├── core/               # health check, error envelope, pagination
│   │   ├── accounts/           # custom User + session auth endpoints
│   │   ├── skills/             # skill dictionary, aliases, related-skill groups
│   │   ├── jobs/               # job descriptions, requirements, JD skill suggestions
│   │   ├── analyses/           # matching engine + stored analyses
│   │   └── resumes/            # Resume model, private storage, upload API
│   │       └── services/       # pdf_validation.py, pdf_parser.py, resume_ingestion.py,
│   │           │               # resume_parsing.py
│   │           └── parsing/    # section/contact/skill/education/experience/project/certification extractors
│   ├── tests/                  # pytest suite + synthetic PDF factory
│   ├── requirements.txt / requirements-dev.txt
│   └── Dockerfile
├── docs/                       # architecture, API, security notes
├── scripts/                    # sample PDF generator, API smoke test
├── .github/workflows/          # CI
├── docker-compose.yml
└── .env.example
```

## Getting started

### Prerequisites

- Python 3.12 (3.10–3.13 are supported by Django 5.2)
- PostgreSQL 16 (local install **or** Docker)
- Git; Docker Desktop if you use the Compose route

### Option A — Docker Compose (recommended)

```bash
cp .env.example .env
# edit .env: set DJANGO_SECRET_KEY to a random value
docker compose up --build              # starts Postgres, runs migrations, serves :8000
docker compose exec backend pytest     # run the test-suite inside the container
docker compose exec backend python manage.py createsuperuser
```

### Option B — Local virtualenv

```bash
# 1. Database (psql as a Postgres superuser). CREATEDB lets pytest create its test DB.
psql -U postgres -c "CREATE ROLE careerforge LOGIN PASSWORD 'careerforge' CREATEDB;"
psql -U postgres -c "CREATE DATABASE careerforge OWNER careerforge;"

# 2. Python environment
cd backend
python -m venv .venv
source .venv/bin/activate              # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
pip freeze > requirements.lock         # record the exact versions that installed

# 3. Configuration
cp ../.env.example ../.env             # set DJANGO_SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(50))"

# 4. Database schema + checks
python manage.py migrate
python manage.py check
python manage.py makemigrations --check --dry-run   # expect: "No changes detected"

# 5. Tests and server
pytest
python manage.py runserver
```

### One-command verification (Docker)

```bash
bash scripts/verify_backend.sh      # macOS/Linux, or Git Bash / WSL on Windows
```

This builds the image, starts PostgreSQL, and runs: package listing,
`pip freeze > backend/requirements.lock`, `manage.py check`, the production
`check --deploy`, `makemigrations --check`, `migrate`, OpenAPI generation with
`--fail-on-warn`, the full pytest suite with coverage, and (if `curl` and
`python3` exist on the host) the API smoke test. Everything is written to
`verify-report.txt` with a PASS/FAIL summary at the end.

### Verify the milestone manually

```bash
python ../scripts/make_sample_pdf.py sample_resume.pdf
../scripts/smoke_test_api.sh sample_resume.pdf
```

Expected: health `ok`, a `201` registration, a `201` upload whose
`extracted_text` contains the sample skills, a list with one resume, `HTTP 204`
on delete and `HTTP 404` afterwards.

Interactive API docs: <http://localhost:8000/api/v1/docs/> · Admin: <http://localhost:8000/admin/>

## Licensing note (decide before publishing)

PyMuPDF is dual-licensed **AGPL-3.0 / commercial**. If this project uses PyMuPDF
and is published or run as a network service, the AGPL obligations apply to the
combined work. The simplest options are (a) license CareerForge under AGPL-3.0,
or (b) swap the extractor in `pdf_parser.py` for an MIT/BSD library such as
`pypdf` or `pdfminer.six` (the parser is isolated behind one function for this
reason). No `LICENSE` file is committed until you choose.

## Documentation

- [docs/architecture.md](docs/architecture.md) — components, request flow, design decisions
- [docs/api-documentation.md](docs/api-documentation.md) — every implemented endpoint
- [docs/security.md](docs/security.md) — implemented controls and known gaps
- [docs/matching-algorithm.md](docs/matching-algorithm.md) — scoring formula, worked example, limitations
