# Security notes

Status of each control as of Stage 7. "Tested" means a pytest test exercises it.

## Implemented

| Control | Where | Tested |
|---|---|---|
| Passwords hashed by Django (PBKDF2 default); validators: length ≥10, common, numeric, similarity | `accounts` | ✓ |
| Session id in HttpOnly cookie; no tokens in localStorage | settings | ✓ |
| CSRF on all unsafe requests, including anonymous login/register (login-CSRF) | `accounts/views.py` | ✓ |
| Generic login error (no account enumeration) | `LoginSerializer` | ✓ |
| Privilege fields (`is_staff`, `is_superuser`) ignored on register | `RegisterSerializer` | ✓ |
| Rate limits: auth by IP, uploads by user | DRF `ScopedRateThrottle` | ✓ |
| Upload checks: extension, content-type, size, `%PDF-` signature, then full parse | `services/pdf_validation.py`, `pdf_parser.py` | ✓ |
| Bounded read of uploads; page and text-length limits (PDF-bomb mitigation) | same | ✓ |
| Server-generated storage names → no path traversal; sanitised display name | `storage.py` | ✓ |
| Private storage: outside any served path, `url()` refuses, files 0600 / dirs 0700 | `storage.py` | ✓ |
| Object-level ownership via queryset scoping; other users' ids → 404 | `ResumeViewSet.get_queryset` | ✓ |
| Non-sequential UUID primary keys for resumes | `Resume.id` | — |
| File removed on resume delete and on user delete (cascade) | `signals.py` | ✓ |
| No stack traces to clients; generic 500 envelope | `core/exceptions.py` | ✓ |
| Logs contain ids and sizes only — no resume text, filenames, passwords | `resume_ingestion.py` | review |
| Secrets only via environment variables | settings, `.env.example` | review |
| CORS limited to `CORS_ALLOWED_ORIGINS` | settings | — |
| Production: HTTPS redirect, HSTS, secure cookies, nosniff, `X-Frame-Options: DENY` | `settings/production.py` | — |

## Frontend and account controls (Stage 6)

| Control | Where |
|---|---|
| No auth tokens in localStorage/sessionStorage; session id stays in an HttpOnly cookie | `frontend/src/services/api.ts` |
| CSRF header on every unsafe request; CSRF cookie fetched first when missing | `api.ts` interceptor |
| Protected routes redirect to login; the API still enforces auth and ownership on every call | `RouteGuards.tsx` |
| Errors shown to users come from the API's safe error envelope; raw/HTML error bodies are never rendered | `toApiError()` (tested) |
| Password change keeps the current session and invalidates others (`update_session_auth_hash`) | `ChangePasswordView` (tested) |
| Account deletion requires the current password and removes all owned data and files | `MeView.delete` (tested) |

## History, reports and headers (Stage 7)

| Control | Where | Tested |
|---|---|---|
| Compare and report endpoints use the owner-scoped queryset; another user's id → 404 (never 403, so ids aren't confirmed) | `AnalysisViewSet` | ✓ (API + E2E) |
| Running analyses is rate-limited per user (`analyses` scope) | `AnalysisViewSet.get_throttles` | ✓ |
| Report downloads are `Cache-Control: no-store` attachments; user text is Markdown-escaped | `report` action, `services/report.py` | ✓ |
| `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'` on every non-HTML response (JSON, Markdown) | `core/middleware.py` | ✓ |
| `Permissions-Policy` disables camera, microphone, geolocation and payment | same | ✓ |
| Report download goes through axios (cookies + same origin), not a public link | `frontend/src/services/analyses.ts` | ✓ |
| Full journey including cross-user isolation checked in a real browser | `frontend/e2e/careerforge.spec.ts` | E2E |

The HTML pages served by Django (admin, Swagger UI) don't get the deny-all CSP
because they need their own scripts; the SPA's CSP is set by whatever serves the
built frontend (Stage 8).

## Known gaps (tracked for later stages)

- **Throttle storage**: LocMem cache is per process. Production with several
  workers needs a shared cache (`CACHE_URL=redis://…`).
- **Proxy body limit**: configure `client_max_body_size` (nginx) or equivalent so
  oversized uploads are rejected before reaching Django.
- **Malware scanning** of uploads is not performed. PDFs are only parsed, never
  rendered to users or executed.
- **Extracted text retention**: raw text is stored to support parsing and editing.
  Users can delete a resume (file + text) or their whole account; there is no
  automatic expiry yet.
- **Account lockout** beyond rate limiting is not implemented.
- Admin access should be restricted by network/IP in production.
