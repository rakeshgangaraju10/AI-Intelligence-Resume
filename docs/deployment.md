# Deployment guide

> **Status:** CareerForge has **not** been deployed anywhere yet. This guide
> describes the production setup in this repository. The containers are
> built, started and smoke-tested together in CI
> (`.github/workflows/production-stack.yml`): HTTP checks through nginx,
> `check --deploy`, and a Chromium page load under the production CSP. That run is
> plain HTTP on a CI runner, not a public deployment.

## What runs in production

```
            HTTPS (443)                       HTTP (8080)
Browser ───────────────► TLS proxy ───────────────────────► frontend (nginx)
                         (Caddy / platform LB)               ├─ /            → built React SPA (index.html, /assets)
                                                             ├─ /static/     → Django admin/Swagger static files (shared volume)
                                                             └─ /api/, /admin/ ─► backend (gunicorn + Django, production settings)
                                                                                    ├─ PostgreSQL 16 (db)
                                                                                    └─ private resume files (volume, never served)
```

| Piece | Where | Notes |
|---|---|---|
| `frontend` | `frontend/Dockerfile`, `frontend/nginx/` | Multi-stage: Node 22 builds the SPA, `nginx:1.28-alpine` serves it. CSP and other security headers for the SPA; 6 MB request-body limit; long-term caching for fingerprinted assets. |
| `backend` | `backend/Dockerfile` | Python 3.12, gunicorn, runs as a non-root user. On start: `migrate`, `collectstatic`, then gunicorn. |
| `db` | `postgres:16-alpine` | Not published on the host; only the backend can reach it. |
| Compose file | `docker-compose.prod.yml` | Only nginx is published (`HTTP_PORT`, default 8080). |
| Config | `.env.production.example` | Copy to `.env.production`, which is git-ignored. |

The SPA and the API share one origin: nginx proxies `/api/`. Session and CSRF
cookies therefore work with `SameSite=Lax` and no CORS configuration.

## Option A: one Linux server with Docker (VPS)

Any small Ubuntu server with 1–2 GB RAM, Docker Engine and the Compose plugin will do.

```bash
# 1. Get the code
git clone https://github.com/rakeshgangaraju10/AI-Intelligence-Resume.git careerforge
cd careerforge

# 2. Configure (edit every "change-me" value; see the table below)
cp .env.production.example .env.production
python3 -c "import secrets; print(secrets.token_urlsafe(50))"   # DJANGO_SECRET_KEY
nano .env.production

# 3. Build and start
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
docker compose -f docker-compose.prod.yml --env-file .env.production ps

# 4. Admin account
docker compose -f docker-compose.prod.yml --env-file .env.production exec backend \
  python manage.py createsuperuser

# 5. Production self-check (expect no errors)
docker compose -f docker-compose.prod.yml --env-file .env.production exec backend \
  python manage.py check --deploy
```

### HTTPS with Caddy on the host

Session and CSRF cookies are `Secure` in production, so **logging in needs
HTTPS**. Caddy gets and renews Let's Encrypt certificates automatically. Point
your domain's DNS A record at the server, install Caddy, then use this
`/etc/caddy/Caddyfile`:

```
careerforge.example.com {
    reverse_proxy localhost:8080
}
```

With Caddy in front of nginx, set `DRF_NUM_PROXIES=2` in `.env.production` so
rate limits use the real client IP. Then restart the stack with the
`up -d` command from step 3. Caddy sends `X-Forwarded-Proto: https`; nginx passes
it on, and Django uses it for HTTPS redirects and secure cookies.

Keep port 8080 closed to the internet (firewall) so all traffic goes through Caddy.

### Updating

```bash
git pull
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```

Migrations run automatically on start. With more than one backend instance,
run them as a separate one-off step instead.

### Backups

```bash
# Database
docker compose -f docker-compose.prod.yml --env-file .env.production exec -T db \
  sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > careerforge-$(date +%F).sql
# Uploaded resumes (personal data: store the archive encrypted)
docker run --rm -v careerforge-prod_resume_files:/data -v "$PWD":/backup alpine \
  tar czf /backup/resume-files-$(date +%F).tar.gz -C /data .
```

Never commit database dumps or resume files. `.gitignore` already excludes
`*.dump`, `*.sql.gz` and `private_media/`.

## Option B: a container platform

Any platform that runs Dockerfiles and offers managed PostgreSQL can host the
two images:

1. Create a managed PostgreSQL 16 database.
2. Deploy `backend/` as a web service from its Dockerfile. Set the variables
   below, and set `DATABASE_URL` to the platform's connection string. The start
   command is the same `migrate && collectstatic && gunicorn …` sequence as in
   `docker-compose.prod.yml`. Attach a persistent disk at `/app/private_media`.
   Without one, uploaded resumes are lost on every restart.
3. Deploy `frontend/` from its Dockerfile. Set `BACKEND_UPSTREAM` to the
   backend's internal `host:port`. The nginx image puts it into the config at
   start-up.
4. Admin/Swagger static files are collected inside the backend container, but
   nginx serves `/static/` from a shared volume. Platforms rarely share volumes
   between services, so either proxy `/static/` to the backend and add a static
   file server there, or skip the admin's CSS. This is the one part of Option B
   that needs extra work.
5. Platform load balancers terminate TLS. Set `DRF_NUM_PROXIES=2`.

## Configuration reference

| Variable | Required | Meaning |
|---|---|---|
| `DJANGO_SECRET_KEY` | yes | Long random string; never reuse the development one. |
| `DJANGO_ALLOWED_HOSTS` | yes | Public hostname(s), comma-separated. |
| `CSRF_TRUSTED_ORIGINS` | yes | Full HTTPS origin(s), e.g. `https://careerforge.example.com`. |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | yes | Database credentials (compose builds `DATABASE_URL` from these). |
| `DJANGO_SECURE_SSL_REDIRECT` | default `True` | Set `False` only for an HTTP-only local trial. |
| `DJANGO_SECURE_HSTS_SECONDS` | default 30 days | Raise once HTTPS is known to work. |
| `DRF_NUM_PROXIES` | default `1` | Number of proxies in front of Django. |
| `HTTP_PORT` | default `8080` | Host port nginx is published on. |
| `GUNICORN_WORKERS` | default `3` | gunicorn worker processes. |
| `THROTTLE_*_RATE` | optional | Rate limits (see `.env.example`). |
| `CACHE_URL` | optional | Shared cache for rate limits (see below). |
| `BACKEND_UPSTREAM` | frontend only | `host:port` of the backend (default `backend:8000`). |

## Known limitations before a real launch

- **Rate limits per worker.** The default cache is in-memory per gunicorn
  worker, so with 3 workers each limit is effectively up to 3× higher. A shared
  cache (`CACHE_URL=redis://…`) fixes this, but it needs a Redis service and the
  `redis` Python package, and neither is included yet.
- **Single instance.** Migrations run on container start, and uploaded files
  live on a local volume. Running several backend instances needs shared
  storage and a separate migration step.
- **No monitoring/alerting** is configured. gunicorn and nginx log to stdout
  (`docker compose logs`); logs never contain resume text.
- **Malware scanning** of uploads is not performed (see `docs/security.md`).

## Pre-launch checklist

- [ ] `.env.production` filled in; secret generated fresh; file not committed
- [ ] DNS points at the server; Caddy (or the platform) serves HTTPS
- [ ] `manage.py check --deploy` shows no errors
- [ ] Register, upload the synthetic sample PDF (`scripts/make_sample_pdf.py`), analyse, compare and download a report over HTTPS
- [ ] A second account cannot open the first account's resume or analysis URLs (404)
- [ ] Backups scheduled for the database and the resume-files volume
- [ ] Port 8080 not reachable from the internet
- [ ] Only then call the project "deployed", and link the URL in the README
