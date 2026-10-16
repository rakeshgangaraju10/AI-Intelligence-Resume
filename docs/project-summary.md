# CareerForge: project summary, resume bullets and interview notes

All figures below come from CI runs on GitHub Actions; see the README status
line for the commit. Update them if later runs change. Live site: https://careerforge-h362.onrender.com (free hosting; may take ~1 minute to wake).

## One-line description

Full-stack resume analysis platform (Django REST Framework + React/TypeScript +
PostgreSQL). It parses PDF resumes into editable structured data and scores
them against job descriptions with an explainable, deterministic skill-matching
algorithm.

## Resume bullets (pick 3–4)

- Built **CareerForge**, a full-stack resume analysis platform using **Django
  REST Framework, React + TypeScript and PostgreSQL**. Users upload PDF resumes,
  correct the extracted data, and compare it against job descriptions.
- Designed a **rule-based NLP parsing pipeline** (PyMuPDF): section detection,
  a 115-skill dictionary with aliases and 19 related-skill groups, and
  extraction of education, experience, projects and certifications. Each skill
  keeps the resume line it was found on as evidence.
- Implemented an **explainable 0–100 matching score** (weighted required and
  preferred coverage). Analyses are stored as snapshots so users can compare
  resume versions skill by skill and export Markdown reports.
- Secured the API with **session auth + CSRF, per-user ownership checks (404
  for other users' data), scoped rate limiting, layered PDF upload validation
  and private file storage**. Added CSP and other security headers at the API
  and nginx layers.
- Wrote **245 backend tests (pytest, 96% coverage), 50 frontend tests (Vitest +
  Testing Library) and a Playwright end-to-end journey**. All run in **GitHub
  Actions**, along with OpenAPI schema validation and a smoke test of the
  production **Docker Compose (nginx + gunicorn + PostgreSQL)** stack.

Shorter version for a one-line project entry:

> CareerForge (https://careerforge-h362.onrender.com) — Django REST Framework, React/TypeScript, PostgreSQL, Docker. PDF
> resume parsing, explainable job-matching score, 290+ automated tests (96%
> backend coverage), Playwright E2E, CI on GitHub Actions.

## Interview talking points

**Why rule-based NLP instead of an LLM?** Predictable results, no cost, no
privacy risk: resumes never leave the server. Every decision can also be
explained ("Docker matched because line X of your Projects section mentions
it"). The trade-off is recall: synonyms outside the dictionary are missed.
Semantic matching is listed as a future, opt-in feature.

**How is the score calculated?**
`score = s × required_coverage + (1 − s) × preferred_coverage`, with `s = 0.8`.
Coverage is the matched weight divided by the total weight (weights 1–5).
Related skills (e.g. MySQL when the job wants PostgreSQL) are shown but never
scored, so the number can't be inflated. The UI says it is not a hiring
probability. See `docs/matching-algorithm.md` for a worked example.

**How do you stop users seeing each other's data?** Every queryset is filtered
by `owner=request.user`, so another user's ID returns 404 (not 403), which
doesn't even confirm the object exists. The API tests and the E2E test both
check this with a second account.

**Upload security?** Checks run in order: extension, content type, size, then
the `%PDF-` signature, then a full parse with page and text limits.
Encrypted, corrupt and scanned (no text layer) PDFs get specific error codes.
Files are stored under server-generated names, outside any served path, and
deleted with the resume or account. There's no OCR, and the app says so.

**Why session cookies instead of JWT?** The SPA and API share one origin (Vite
proxy in development, nginx in production). HttpOnly session cookies keep tokens
out of JavaScript, and CSRF protection covers unsafe requests, including login
and register.

**Why store analyses as snapshots?** History shouldn't change when a resume or
job is edited later. Snapshots also make comparison easy: "what did my edit
change?"

**Testing strategy?**
- Pure-Python unit tests for the parser, matching engine, comparison and report.
- API tests against a real PostgreSQL database.
- Component tests with mocked services.
- One end-to-end journey in a real browser that asserts exact scores
  (60.0 → 80.0) and cross-user isolation.
- CI runs everything on every push, plus a migrations check, OpenAPI
  `--fail-on-warn`, and a production-stack smoke test.

**Bugs CI caught (good stories):**
- Enum-name collisions in the OpenAPI schema.
- A compare endpoint that returned 500 because already-serialized data was
  passed into a nested serializer.
- Pagination warnings because Django ignores model ordering in GROUP BY
  queries.
- E2E flakiness from the Vite dev server reloading the page; the E2E test now
  runs against a production build.

**What would you do next?**
- A shared Redis cache for rate limits.
- A real deployment with HTTPS, monitoring and backups.
- Optional, consented semantic matching with an evaluation dataset.
- OCR for scanned resumes, if that's needed.

## Honest limitations to mention if asked

- Hosted on free plans: the site sleeps when idle, and the first request takes about a minute.
- English-language resumes only; parsing is heuristic and won't handle every layout.
- No OCR: scanned PDFs are rejected with a clear message.
- Rate limits are per worker until a shared cache is added.
