# Security notes

Status of each control as of Stage 8. "Tested" means a pytest test exercises it.

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
built frontend: nginx in production (see below).

## Production web tier (Stage 8)

| Control | Where | Checked in CI |
|---|---|---|
| SPA served with CSP `default-src 'self'` (no inline scripts, no third-party origins), `frame-ancestors 'none'`, nosniff, `X-Frame-Options: DENY`, Referrer-Policy, Permissions-Policy, COOP | `frontend/nginx/spa-headers.conf` | ✓ (CSP, X-Frame-Options) |
| nginx version hidden (`server_tokens off`) | `frontend/nginx/default.conf.template` | ✓ |
| Request bodies over 6 MB rejected by nginx before reaching Django | same | ✓ |
| Resume files live on a volume mounted only into the backend container; nginx has no route to them | `docker-compose.prod.yml` | review |
| Database not published on the host | same | review |
| Session/CSRF cookies `Secure` + `SameSite=Lax` in production | `settings/production.py` | ✓ (CSRF cookie) |
| Rate limits key on the real client IP behind proxies (`DRF_NUM_PROXIES`) | same | — |
| `manage.py check --deploy` has no errors | CI | ✓ |
| Backend container runs as a non-root user | `backend/Dockerfile` | review |

The SPA CSP doesn't cover `/admin/` or `/api/v1/docs/`: Django serves those
pages and Swagger UI loads its assets from a CDN. Restrict admin/docs access by
network in production if possible.

## Password reset (forgot password)

| Control | Where | Tested |
|---|---|---|
| Same response for known and unknown emails (no account enumeration); inactive users get nothing | `accounts/password_reset.py` | ✓ |
| Django's signed, expiring tokens (1 hour); a link stops working once the password changes | `default_token_generator` | ✓ |
| Password validators on the new password; other sessions logged out after reset | `PasswordResetConfirmSerializer` | ✓ |
| CSRF required; 5 requests/hour per IP | views, `password_reset` throttle | ✓ |
| Reset links never logged; production never prints emails (dummy backend unless a provider is set) | `settings/production.py` | ✓ |

## Job import from a link (server-side fetch: SSRF controls)

| Control | Where | Tested |
|---|---|---|
| Only `http`/`https`, default ports, no credentials in the URL | `jobs/services/job_import.py` `validate_url` | ✓ |
| Hostname resolved; **every** address must be public (no loopback, private, link-local/cloud metadata, CGNAT, multicast, IPv4-mapped tricks) | `resolve_public_ip`, `is_public_ip` | ✓ |
| Connection made to the already-checked IP (TLS still verifies the real hostname), so DNS rebinding has no window | `_PinnedHTTPSConnection` | review |
| Redirects followed manually (max 3), each hop re-validated | `fetch_html` | ✓ |
| 8 s timeout, 2 MB limit, HTML only, nothing executed; JSON-LD parsed as data | same | ✓ |
| Login-walled / no-automation sites refused with a "paste instead" message | `BLOCKED_SITES` | ✓ |
| Logged-in users only, 30 imports/hour per user; nothing saved without review | `JobViewSet.import_url` | ✓ |

## Single-service / free hosting

`RESUME_STORE_FILES=False` (the default in `config/settings/single_service.py`)
stores no PDF at all, only the extracted text needed for parsing and analysis.
This means less personal data at rest. The SPA's `index.html` gets the same CSP
from Django (`core.views.spa_index`) as nginx sends in the Compose setup. Both
are tested (`test_core.py`, `test_resumes_api.py`) and smoke-tested on the built
image in CI.

## Known gaps (tracked for later stages)

- **Throttle storage**: LocMem cache is per process. Production with several
  workers needs a shared cache (`CACHE_URL=redis://…` plus the `redis` package).
- **Malware scanning** of uploads is not performed. PDFs are only parsed, never
  rendered to users or executed.
- **Extracted text retention**: raw text is stored to support parsing and editing.
  Users can delete a resume (file + text) or their whole account; there is no
  automatic expiry yet.
- **Account lockout** beyond rate limiting is not implemented.
- Admin access should be restricted by network/IP in production.
