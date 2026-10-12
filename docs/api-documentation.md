# API documentation (Stages 1–4)

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
