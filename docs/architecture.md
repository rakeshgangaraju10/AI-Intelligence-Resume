# Architecture (Stage 1)

## Components

```
Browser / SPA (Stage 6)
   │  HTTPS, session cookie + X-CSRFToken
   ▼
Django + DRF  (/api/v1/)
   ├── core       health check, error envelope, pagination
   ├── accounts   User model, session auth endpoints
   └── resumes    ResumeViewSet ──► ResumeUploadSerializer
                                     └─► services/resume_ingestion.py
                                          ├─ pdf_validation.py  (name, type, size, signature)
                                          ├─ pdf_parser.py      (PyMuPDF → normalised text)
                                          └─ persist Resume + file (private storage)
   │
   ├── PostgreSQL     users, sessions, resumes (+ extracted text)
   └── PRIVATE_MEDIA_ROOT   PDFs at resumes/<user_id>/<random>.pdf (never served)
```

## Upload request flow

1. `POST /api/v1/resumes/` (multipart). DRF authenticates the session, checks CSRF,
   applies the `uploads` throttle.
2. `ResumeUploadSerializer.validate_file` calls `inspect_resume_upload`, which runs
   validation and text extraction **before** anything is written. Any rejection
   becomes a field error with a stable code.
3. `create_resume` saves the file under a random name, then inserts the row in a
   transaction; if the insert fails, the file is deleted.
4. The response is the detail representation including extracted text.

## Key decisions

| Decision | Reason |
|---|---|
| Custom `User` model from day one, email login | Swapping the user model after the first migration is very costly in Django. |
| Session-cookie auth instead of JWT in localStorage | Keeps credentials out of JavaScript-readable storage; Django already provides CSRF, rotation and server-side logout. |
| Synchronous extraction in the request | Resumes are small (page/size limits); avoids a task queue in early stages. The `status` field leaves room for async processing later. |
| Reject bad files instead of storing failed records | Unusable files hold personal data with no benefit. |
| One `Resume` row per upload | Natural version history; structured data (Stage 4) will hang off each version. |
| Services layer under `apps/resumes/services/` | Parsing code is reusable, unit-testable without HTTP, and swappable (e.g. a non-AGPL PDF library). |
| UUID primary key for `Resume` | Non-guessable ids as defence in depth; ownership checks remain the real control. |
| Settings split base / development / production / test | Production hardening can't leak into dev, and tests run fast with predictable limits. |

## Data model (current)

`accounts.User` — `id`, `email` (unique), `full_name`, Django auth fields.

`resumes.Resume` — `id` (UUID), `owner` → User (CASCADE), `title`,
`original_filename`, `file`, `file_size` (>0), `sha256`, `page_count` (>0),
`status`, `error_code`, `extracted_text`, `created_at`, `updated_at`.
Indexes: `(owner, -created_at)` for listing, `(owner, sha256)` for duplicate detection later.
