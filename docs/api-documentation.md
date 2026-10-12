# API documentation (Stage 1)

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
| DELETE | `/resumes/{id}/` | `204`. Deletes the row and the stored file. `404` if not yours. |

Detail object:

```json
{
  "id": "4f0c…-uuid",
  "title": "Alex Resume",
  "original_filename": "Alex Resume.pdf",
  "file_size": 1834,
  "page_count": 1,
  "status": "text_extracted",
  "created_at": "2026-10-12T06:00:00Z",
  "updated_at": "2026-10-12T06:00:00Z",
  "error_code": "",
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
