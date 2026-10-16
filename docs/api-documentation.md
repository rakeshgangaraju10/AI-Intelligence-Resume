# API documentation (Stages 1–6)

Base path: `/api/v1/`. Only endpoints listed here exist. The live OpenAPI schema
is served at `/api/v1/schema/` and Swagger UI at `/api/v1/docs/`.

## Authentication model

Session cookies (`sessionid`, HttpOnly) + CSRF. Clients:

1. `GET /auth/csrf/` to receive the `csrftoken` cookie.
2. Send `X-CSRFToken: <csrftoken>` on every `POST`/`PATCH`/`DELETE`.
3. Send cookies on every request (`credentials: "include"` / `withCredentials: true`).

Unauthenticated requests to protected endpoints return **403** with code `not_authenticated`.

## Error format

```json
{
  "error": {
    "code": "validation_error",
    "message": "The PDF is password-protected. Remove the password and upload it again.",
    "fields": { "file": [{ "code": "pdf_encrypted", "message": "..." }] }
  }
}
```

`fields` appears only on validation errors. Other codes: `not_authenticated`,
`permission_denied`, `not_found`, `method_not_allowed`, `throttled`, `server_error`.

## Endpoints

### Health
| Method | Path | Auth | Response |
|---|---|---|---|
| GET | `/health/` | none | `200 {"status":"ok","database":"ok"}` or `503` |

### Auth
| Method | Path | Body | Success |
|---|---|---|---|
| GET | `/auth/csrf/` | — | `204`, sets `csrftoken` cookie |
| POST | `/auth/register/` | `{full_name, email, password}` | `201` user; session started |
| POST | `/auth/login/` | `{email, password}` | `200` user; session started |
| POST | `/auth/logout/` | — | `204` |
| GET | `/auth/me/` | — | `200 {id, email, full_name, date_joined}` |
| PATCH | `/auth/me/` | `{full_name}` | `200` user (email is not editable) |
| DELETE | `/auth/me/` | `{password}` | `204`; deletes the account and everything it owns (resumes + files, jobs, analyses) and logs out. Wrong password → `wrong_password`. |
| POST | `/auth/change-password/` | `{current_password, new_password}` | `204`; the current session stays valid, other sessions are invalidated. Codes: `wrong_password`, `password_unchanged`, password-validator messages. Throttled like login. |

Register/login are throttled (`THROTTLE_AUTH_RATE`, default `10/minute` per IP).
Validation codes: `email_taken`, password-validator messages, `invalid_credentials`.

### Resumes
| Method | Path | Notes |
|---|---|---|
| POST | `/resumes/` | `multipart/form-data`: `file` (PDF, required), `title` (optional, ≤150). `201` → detail object. Throttled (`THROTTLE_UPLOAD_RATE`). |
| GET | `/resumes/` | Paginated list of **your** resumes (`?page=`, `?page_size=` ≤100). No `extracted_text`. |
| GET | `/resumes/{id}/` | Detail incl. `extracted_text`, `char_count`. `404` if not yours. |
| PATCH | `/resumes/{id}/` | `{"title": "..."}` — only the title is editable. `PUT` is not allowed. |
| DELETE | `/resumes/{id}/` | `204`. Deletes the row, structured data and the stored file. `404` if not yours. |
| GET | `/resumes/{id}/extraction/` | Profile + skills + education + experience + projects + certifications + `parse_warnings` in one response. |
| POST | `/resumes/{id}/reparse/` | Re-run the parser (throttled like uploads). Keeps user-added rows, verified rows and an edited profile; replaces unverified parser rows. |

Detail object:

```json
{
  "id": "4f0c…-uuid",
  "title": "Alex Resume",
  "original_filename": "Alex Resume.pdf",
  "file_size": 1834,
  "page_count": 1,
  "status": "parsed",
  "created_at": "2026-10-12T06:00:00Z",
  "updated_at": "2026-10-12T06:00:00Z",
  "error_code": "",
  "parse_warnings": ["section_not_found:experience"],
  "parsed_at": "2026-10-12T06:00:01Z",
  "char_count": 412,
  "extracted_text": "…"
}
```

Upload rejection codes (`fields.file[].code`, HTTP 400):

| Code | Meaning |
|---|---|
| `required` | No `file` part sent |
| `invalid_extension` | Name does not end in `.pdf` |
| `invalid_content_type` | Browser-declared type is clearly not PDF |
| `empty_file` | Zero bytes |
| `file_too_large` | Exceeds `RESUME_MAX_UPLOAD_BYTES` |
| `invalid_signature` | Bytes lack the `%PDF-` header |
| `pdf_corrupt` | PyMuPDF cannot open/read it, or it has 0 pages |
| `pdf_encrypted` | Password required to open |
| `pdf_too_many_pages` | More than `RESUME_MAX_PAGES` |
| `pdf_no_text` | Fewer than `RESUME_MIN_TEXT_CHARS` non-space characters — likely scanned; OCR is not implemented |
| `pdf_text_too_long` | More than `RESUME_MAX_TEXT_CHARS` characters |

### Structured resume data (Stage 4)

All routes are nested under a resume you own; anything else returns `404`.
Section lists are not paginated (a resume has few entries per section).

| Method | Path | Notes |
|---|---|---|
| GET / PATCH | `/resumes/{id}/profile/` | `full_name, email, phone, location, links[≤10], summary`. PATCH sets `user_edited=true`, after which re-parsing never overwrites it. |
| GET / POST | `/resumes/{id}/skills/` | POST `{"name": "JS"}` → stored as canonical `"JavaScript"` when the name is a known alias. Duplicates (case-insensitive, after normalisation) → `duplicate_skill`. |
| GET / PATCH / DELETE | `/resumes/{id}/skills/{skill_id}/` | |
| GET / POST | `/resumes/{id}/education/` | Needs `institution` or `degree` (`incomplete_entry`). |
| GET / PATCH / DELETE | `/resumes/{id}/education/{entry_id}/` | |
| GET / POST | `/resumes/{id}/experience/` | Needs `title` or `company`; `is_current=true` requires empty `end_date` (`current_with_end_date`). |
| GET / PATCH / DELETE | `/resumes/{id}/experience/{entry_id}/` | |
| GET / POST | `/resumes/{id}/projects/` | `technologies[≤30]` normalised to canonical names and de-duplicated. |
| GET / PATCH / DELETE | `/resumes/{id}/projects/{entry_id}/` | |
| GET / POST | `/resumes/{id}/certifications/` | `name` required. |
| GET / PATCH / DELETE | `/resumes/{id}/certifications/{entry_id}/` | |

Provenance fields on every entry (read-only unless noted):

| Field | Meaning |
|---|---|
| `source` | `parser` (extracted) or `user` (added by the user). Clients cannot set it. |
| `is_verified` | Writable. User-created and user-edited entries are verified; a PATCH may send `false` explicitly. |
| `section`, `evidence` | Skills only: where the parser found it and the exact resume line. Empty for user-added skills. |
| `canonical` | Skills only: `true` when the name is in the skills dictionary. |

Dates are free text (`"Jun 2024"`, `"2025"`) because resumes are inconsistent;
the parser never invents a day or month.

`parse_warnings` codes: `section_not_found:<skills|education|experience|projects>`,
`no_skills_detected`, `experience_unstructured`, `education_unstructured`,
`projects_unstructured`, `email_not_found`, `name_not_found`.
If the parser itself fails, the upload still succeeds with
`status="text_extracted"` and `error_code="parse_failed"`.

### Job descriptions (Stage 5)

| Method | Path | Notes |
|---|---|---|
| POST | `/jobs/` | `title` (required), `company`, `experience_level` (`unspecified`, `internship`, `entry`, `mid`, `senior`), `description` (≤20,000 chars), `required_skills[]`, `preferred_skills[]`, `auto_extract` (default `true`). Needs a description or at least one skill (`empty_job`). |
| GET | `/jobs/` | Paginated; includes `required_count`, `preferred_count`. `?search=` filters title/company. |
| GET / PATCH / DELETE | `/jobs/{id}/` | Detail includes `requirements`. Deleting a job deletes its analyses. |
| POST | `/jobs/{id}/suggest-requirements/` | Adds skills found in the description that aren't listed yet; never removes or edits existing ones. Returns `{added, job}`. |
| GET / POST | `/jobs/{id}/requirements/` | `{name, kind, weight}`; names are canonicalised (`k8s` → `Kubernetes`); duplicates → `duplicate_skill`. |
| GET / PATCH / DELETE | `/jobs/{id}/requirements/{req_id}/` | |

Skill list items are either a string (`"Docker"`) or `{"name": "Docker", "weight": 3}`;
weights are integers 1–5 (`invalid_weight`). A skill given as both required and
preferred is stored as required. Suggested requirements have `source="extracted"`
and `evidence` (the description line).

### Analyses (Stage 5)

| Method | Path | Notes |
|---|---|---|
| POST | `/analyses/` | `{"resume": "<uuid>", "job": <id>}`. Both must be yours (`does_not_exist` otherwise). A job with no skills → `no_requirements`. `201` → detail. |
| GET | `/analyses/` | Paginated history: `score`, coverages, `matched_count`, `missing_count`, snapshot titles. Filters: `?resume=<uuid>`, `?job=<id>`. |
| GET / DELETE | `/analyses/{id}/` | |

Detail object (abridged):

```json
{
  "id": 12, "resume": "4f0c…", "job": 7,
  "resume_title": "Backend v2", "job_title": "Backend Intern @ Acme",
  "score": 58.0,
  "score_label": "Resume-to-job matching score: … It is not a probability of being hired.",
  "required_coverage": 60.0, "preferred_coverage": 50.0, "required_share": 0.8,
  "algorithm_version": "baseline-v1",
  "breakdown": {"formula": "0.80 × required coverage (60.0) + 0.20 × preferred coverage (50.0)",
                "required": {"matched_weight": 3, "total_weight": 5, "coverage": 60.0},
                "preferred": {"matched_weight": 1, "total_weight": 2, "coverage": 50.0},
                "required_share": 0.8, "related_skills_count_toward_score": false},
  "strengths": ["Django: demonstrated in Project: Inventory Tracker — \"built a Django API…\""],
  "improvements": ["Missing required skill: Docker"],
  "suggestions": ["Docker: if you have real experience with it, add it …"],
  "skill_results": [
    {"skill_name": "MySQL", "kind": "required", "weight": 1, "status": "related",
     "evidence": [{"location": "Skills section", "text": "Python, …, PostgreSQL, …"}],
     "related_to": ["PostgreSQL"], "related_reason": "relational SQL databases",
     "explanation": "Required skill 'MySQL' was not found. Your resume lists PostgreSQL (relational SQL databases). Related skills are shown for context and do not add to the score."}
  ],
  "created_at": "2026-10-12T07:00:00Z"
}
```

`status` is `matched`, `missing` or `related`. The algorithm is documented in
[matching-algorithm.md](matching-algorithm.md).

### Comparison and reports (Stage 7)

| Method | Path | Notes |
|---|---|---|
| GET | `/analyses/compare/?a=<id>&b=<id>` | Both ids must be yours (otherwise `404`). Missing/non-integer ids → `required`/`invalid`; `a == b` → `same_analysis`. |
| GET | `/analyses/{id}/report/` | Markdown file: `Content-Type: text/markdown; charset=utf-8`, `Content-Disposition: attachment; filename="careerforge-analysis-<id>.md"`, `Cache-Control: no-store`. Same content as the detail view. |

Comparison response:

```json
{
  "a": { "...": "analysis detail" },
  "b": { "...": "analysis detail" },
  "score_delta": 16.0,
  "basis": "same_resume_and_job",
  "skills": [
    {"skill_name": "Docker", "kind_a": "required", "kind_b": "required",
     "status_a": "missing", "status_b": "matched", "change": "gained"}
  ]
}
```

- `score_delta` is `b.score − a.score` in score points.
- `basis` is `same_resume_and_job`, `same_job`, `same_resume` or `different`.
  Only comparisons against the same job are like-for-like; the UI warns otherwise.
- `change` is `gained` (not matched → matched; a *related* skill counts as not
  matched), `lost`, `only_in_a`, `only_in_b` or `unchanged`. Skills are matched
  by name case-insensitively; changed rows come first.

Rate limit: `POST /analyses/` uses the `analyses` scope
(`THROTTLE_ANALYSIS_RATE`, default `60/hour` per user). Reading history, comparing
and downloading reports are not throttled.

### Password reset (forgot password)

| Method | Path | Notes |
|---|---|---|
| POST | `/auth/password-reset/` | `{email}`. Always `200` with the same message, whether or not the account exists. Emails a link `/reset-password/<uid>/<token>` (expires after `PASSWORD_RESET_TIMEOUT`, default 1 hour). CSRF required; throttle scope `password_reset` (`THROTTLE_PASSWORD_RESET_RATE`, default 5/hour per IP). |
| POST | `/auth/password-reset/confirm/` | `{uid, token, new_password}`. `invalid_token` for a wrong, used or expired link; password validators apply. A successful reset logs out existing sessions, and the link stops working. |

Email delivery: `EMAIL_BACKEND` (console in development, dummy in production unless
configured; `apps.core.email_backends.BrevoAPIBackend` on Render).

### Import a job from a link

| Method | Path | Notes |
|---|---|---|
| POST | `/jobs/import-url/` | `{url}` → `{title, company, description, source_url, method, warnings}`. Nothing is saved; the frontend fills the Add-job form for review. `method` is `structured` (schema.org `JobPosting` JSON-LD) or `page_text` (visible text, with a warning). Errors on `url`: `invalid_url`, `unsupported_site` (LinkedIn, Indeed, Glassdoor), `blocked_address`, `fetch_failed`, `not_html`, `too_large`, `no_content`. Throttle scope `job_import` (`THROTTLE_JOB_IMPORT_RATE`, default 30/hour per user). |

### Sign-up profile fields

`POST /auth/register/` also requires `college_name` (2–200 characters, whitespace
collapsed) and `graduation_year` (integer from 1980 to the current year + 6). Errors use
codes `blank` and `invalid_year`. Both fields appear in the user object (`/auth/me/`)
and can be changed with `PATCH /auth/me/`. They're blank/`null` for admin accounts and
accounts created before the fields existed; the dashboard asks those users to add them.
