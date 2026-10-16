# CareerForge — AI-Powered Resume Intelligence Platform

CareerForge lets candidates upload a PDF resume, review and correct what was
extracted from it, and compare it with job descriptions using an explainable,
deterministic matching score.

1. **Upload** a text-based PDF. It is validated, stored privately, and parsed into
   skills, education, experience, projects and certifications, each with the
   resume line it came from.
2. **Review**: every parsed item can be confirmed, edited or removed, and the
   app records whether each item came from the parser or from the user.
3. **Match** against a job's required and preferred skills to get a 0–100
   score. Each skill comes back as matched, missing or related, with evidence and
   an explanation. The score measures skill overlap; it is not a hiring prediction.
4. **Track**: every analysis is saved as a snapshot. Compare two versions skill
   by skill, then download a Markdown report or print the page.

The "intelligence" is rule-based NLP: section detection, a skill dictionary with
aliases, and related-skill groups. Scoring is a documented formula. No resume
data is sent to any external AI service.

**🌐 Live site: [careerforge-h362.onrender.com](https://careerforge-h362.onrender.com)**. It's free to use:
create an account, upload a resume, and compare it with a job (paste it, pick a sample job, or import
it from a careers-page link). It's hosted on free plans (Render + Neon); a scheduled ping keeps it
awake, and if it was asleep the app shows "Starting the server…" and waits about a minute.

> **Status:** All stages verified in CI. Latest run, on commit `a660e39`: Backend CI #19
> (254 tests, 96% coverage), Frontend CI #12 (57 tests), E2E #14 (full Playwright journey
> in Chromium), and Production stack #10 (Docker Compose stack, plus the single-container
> image the live site runs). Deployed on Render's free web service with a Neon Postgres
> database ([how](docs/deploy-free-render-neon.md)).

## Screenshots

The end-to-end test takes screenshots of the main screens using synthetic data
only, and uploads them as the `screenshots-and-lockfile` artifact of each E2E run.
They haven't been added to this README yet. Until then, the live site above is the
best way to see the app.

## What's implemented

| Area | Implemented |
|---|---|
| Accounts | Custom email-based `User` model; register / login / logout / me with session cookies + CSRF; rate-limited auth; profile update, password change, account deletion; college name and year of passing out at sign-up; forgot-password emails (signed, expiring one-time links) |
| Resume upload | `POST /api/v1/resumes/` (multipart) with extension, content-type, size and `%PDF-` signature checks |
| Text extraction | PyMuPDF; rejects corrupt, password-protected, scanned (no text layer), too-many-pages and oversized-text PDFs with specific error codes |
| Storage | Private directory, server-generated filenames, no public URL, file removed when the resume or user is deleted |
| Resume API | List (paginated), retrieve, delete — scoped to the owner (other users get 404) |
| Structured parsing (Stage 4) | Rule-based section, contact, skill, education, experience, project and certification extraction; 115-skill dictionary with aliases; evidence for every detected skill |
| Review & editing (Stage 4) | Extraction endpoint, CRUD per section, profile editing, re-parse that preserves user edits, parser vs user provenance |
| Job descriptions (Stage 5) | Save jobs with required/preferred skills and weights; skills suggested from pasted descriptions; full editing; six one-click example jobs (clearly marked as examples); **import from a job link** (reads schema.org `JobPosting` data from career sites, with SSRF protections) |
| Matching (Stage 5) | Deterministic weighted score (0–100) with matched / missing / related skills, resume evidence, per-skill explanations, strengths, improvements and suggestions; results stored as history |
| History & reports (Stage 7) | Compare any two analyses skill by skill (gained / lost / unchanged, score delta, like-for-like warning); Markdown report download; print-friendly results page |
| Platform | Health check, consistent JSON error envelope, OpenAPI schema + Swagger UI, Django Admin |
| Frontend (Stage 6) | React + TypeScript SPA: landing, register/login, dashboard, drag-and-drop upload with progress, resume review/editing, job descriptions with weighted skills, analysis results with evidence, history, settings |
| Security hardening (Stage 7) | Per-user rate limit on running analyses; deny-all CSP and Permissions-Policy on API responses |
| Quality | pytest suite (validation, parsing, API, auth, CSRF, ownership, throttling), Vitest + Testing Library component tests, Playwright end-to-end journey in Chromium, GitHub Actions CI for all three |
| Production setup (Stage 8) | nginx + gunicorn + PostgreSQL via `docker-compose.prod.yml`, SPA security headers (CSP), upload size limit at the proxy, CI smoke test of the running stack |
| Live deployment | One container on Render's free plan (Django serves the API, admin and React app) with Neon Postgres via `render.yaml`; no PDFs kept (text only, `RESUME_STORE_FILES=False`); password-reset email through Brevo's HTTPS API; keep-awake workflow; the frontend wakes a sleeping server and retries uploads once |

Not built: server-side PDF reports (reports are Markdown; use Print → Save as PDF),
OCR for scanned resumes, semantic/embedding-based matching, reading LinkedIn/Indeed job
pages (they forbid automated access; paste the text instead).

## Tech stack

Python 3.12 · Django 5.2 LTS · Django REST Framework 3.16 · PostgreSQL 16 ·
PyMuPDF · drf-spectacular · gunicorn · nginx · pytest · Docker Compose · GitHub Actions.
Frontend: React 19 · TypeScript · Vite · Tailwind CSS 4 · React Router 7 ·
React Hook Form · Axios · Vitest + Testing Library · Playwright (E2E).

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
├── frontend/
│   ├── src/
│   │   ├── components/         # ui/ (buttons, fields, alerts…) and layout/
│   │   ├── pages/              # one component per route
│   │   ├── features/           # auth, resumes, analyses building blocks
│   │   ├── services/           # typed API client (axios, CSRF, error normalisation)
│   │   ├── hooks/ lib/ types/  # data loading, helpers, API types
│   │   └── test/               # Vitest setup + render helpers
│   ├── e2e/                    # Playwright journey test (fixture PDF generated into e2e/.generated/)
│   ├── package.json
│   ├── playwright.config.ts    # starts Django + Vite for E2E
│   ├── Dockerfile, nginx/      # production image: built SPA + reverse proxy
│   └── vite.config.ts          # dev proxy /api -> Django, test config
├── docs/                       # architecture, API, security notes
├── scripts/                    # synthetic PDF generators, API smoke test
├── .github/workflows/          # Backend CI, Frontend CI, E2E, Production stack
├── docker-compose.yml          # development stack
├── docker-compose.prod.yml     # production stack (nginx + gunicorn + Postgres)
├── .env.production.example
├── LICENSE                     # AGPL-3.0
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

### Frontend (Node 20.19+ or 22)

```bash
cd frontend
npm install            # first run creates package-lock.json: commit it
npm run dev            # http://localhost:5173 (proxies /api to http://localhost:8000)
npm test               # Vitest component and unit tests
npm run build          # type check + production build into frontend/dist
```

Run the backend at the same time (Docker Compose or `python manage.py runserver`).
The dev server proxies `/api` to Django, so the browser sees a single origin and
the session/CSRF cookies work without cross-site settings. Keep
`CSRF_TRUSTED_ORIGINS=http://localhost:5173` in `.env`.

### End-to-end tests (Playwright)

Needs PostgreSQL with migrations applied and the backend virtualenv active
(Playwright starts Django and a production build served by `vite preview`, or reuses servers already running):

```bash
python scripts/make_e2e_resume_pdf.py frontend/e2e/.generated/e2e-resume.pdf   # synthetic resume
cd frontend
npx playwright install chromium     # once
npm run e2e
```

The single journey test registers a user, uploads the synthetic PDF, creates a
job, checks the score is exactly 60.0, downloads the report, adds a skill,
checks 80.0, compares the two analyses (+20.0, Kubernetes "Gained"), then logs in
as a second user and confirms both the page and the API return "not found".
Set `E2E_PYTHON` if your Python executable isn't `python`. CI runs it in
`.github/workflows/e2e.yml`.

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

## Production

`docker-compose.prod.yml` runs PostgreSQL, Django under gunicorn, and nginx.
nginx serves the built SPA and proxies `/api/` and `/admin/`. CI builds the
stack, starts it, and checks it through nginx: health, SPA routing, security
headers, cookie flags, static files, the upload size limit and
`check --deploy`. It also loads the built SPA in Chromium to confirm the CSP
doesn't block it. Step-by-step guide, HTTPS setup and pre-launch checklist:
[docs/deployment.md](docs/deployment.md).
**Free public website, no credit card:** Render + Neon via `render.yaml`. See
[docs/deploy-free-render-neon.md](docs/deploy-free-render-neon.md).
Your own server with automatic HTTPS: [docs/deploy-oracle-cloud.md](docs/deploy-oracle-cloud.md).

## License

[GNU AGPL-3.0](LICENSE). CareerForge uses PyMuPDF, which is licensed under
AGPL-3.0 (or commercially), so the project is released under the same license.
If you run a modified version as a network service, the AGPL requires you to
offer its source to the service's users.

## Documentation

- [docs/architecture.md](docs/architecture.md) — components, request flow, design decisions
- [docs/api-documentation.md](docs/api-documentation.md) — every implemented endpoint
- [docs/security.md](docs/security.md) — implemented controls and known gaps
- [docs/matching-algorithm.md](docs/matching-algorithm.md) — scoring formula, worked example, limitations
- [docs/deployment.md](docs/deployment.md) — production stack, HTTPS, backups, checklist
- [docs/project-summary.md](docs/project-summary.md) — resume bullets and interview talking points
