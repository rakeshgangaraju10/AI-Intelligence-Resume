# Free public website: Render + Neon (no credit card)

> CareerForge is deployed this way at https://careerforge-h362.onrender.com.

At the end, CareerForge runs at a public address like **https://careerforge.onrender.com**.
Anyone can register, upload a resume and get their analysis.

| Piece | Service | Cost |
|---|---|---|
| Website + API (one container) | Render free web service | ₹0, no card |
| Database | Neon free Postgres (does not expire) | ₹0, no card |

**Free-tier trade-offs (good to know):**

- **Sleeping.** After 15 minutes without visitors the server goes to sleep. The
  next visitor waits about a minute while it wakes up; after that it's fast.
- **No PDFs kept.** The free server has no permanent disk, so the uploaded PDF
  is not kept. Its extracted text and everything parsed from it are saved in the
  database, and the app works the same.
- **Limits** (free Postgres ~1 GB, monthly compute hours) are plenty for a
  portfolio site. Check each service's pricing page if you expect heavy use.

Time: about 30 minutes, mostly waiting for the first build.

---

## Step 1: Free database on Neon (about 5 minutes)

1. Go to **neon.com** → **Sign up** → **Continue with GitHub** (your `iamrxkiiiii` account).
2. Create a project:
   - **Name:** `careerforge`
   - **Region:** **AWS Asia Pacific (Singapore)**, closest to India and to the Render server
   - Postgres version: the default is fine
3. On the project dashboard click **Connect**.
   - Turn **Connection pooling** **off**, so you get the *direct* connection string.
   - Copy the connection string. It looks like:
     `postgresql://neondb_owner:abc123...@ep-cool-name-123456.ap-southeast-1.aws.neon.tech/neondb?sslmode=require`
4. Keep it somewhere private: it contains the database password. Never commit it to GitHub.

## Step 2: Deploy on Render (about 5 minutes, then the build)

1. Go to **render.com** → **Get Started** → **GitHub**, and sign up with your GitHub account.
2. In the dashboard: **New +** → **Blueprint**.
3. **Connect a repository.** Allow Render to access
   `rakeshgangaraju10/AI-Intelligence-Resume`, then select it.
   Render finds `render.yaml` in the repo and shows one service: **careerforge (free)**.
4. Fill in the values Render asks for:

   | Key | What to enter |
   |---|---|
   | `DATABASE_URL` | the Neon connection string from Step 1 |
   | `DJANGO_SUPERUSER_EMAIL` | your email (for the admin login) |
   | `DJANGO_SUPERUSER_PASSWORD` | a strong password for the admin login |
   | `DJANGO_SUPERUSER_FULL_NAME` | `Rakesh G` |

   Everything else is already set by `render.yaml`. The secret key is generated
   automatically.
5. Click **Apply** (or **Deploy Blueprint**).
6. Open the **careerforge** service → **Logs**. The first build takes 5–10 minutes.
   It's done when you see lines like:
   ```
   Admin account created.
   [INFO] Listening at: http://0.0.0.0:10000
   ```
7. Your address is at the top of the service page, e.g.
   **https://careerforge.onrender.com**. If that name was taken, Render adds a short
   suffix, e.g. `careerforge-ab12.onrender.com`.

If Render asks for a card at any point, stop and tell me; there's another way to do this step.

## Step 3: Check it works

1. Open your address. The CareerForge home page should load. The first load
   after sleeping can take about a minute.
2. **Create account** → upload a resume → **Jobs** → add a job → **Run analysis**.
3. Run a second analysis and **Compare** them, then **Download report**.
4. Admin: `https://<your-address>/admin/`, logging in with the email and password from Step 2.
5. Privacy check: register a second account in a private window and paste a URL
   from the first account (e.g. `/analyses/1`). It must say *not found*.

## Step 4: Tidy up

- Render → careerforge → **Environment**: delete `DJANGO_SUPERUSER_PASSWORD`. The
  admin account already exists, and the password shouldn't sit in settings.
- Send Claude your address, so the README and your resume bullets can link to the live site.

## Turn on "Forgot password?" emails (Brevo, free, no card)

Render's free plan blocks normal email (SMTP), so CareerForge sends through
Brevo's web API instead. The free plan allows 300 emails/day.

1. Go to **brevo.com** → **Sign up free** and create an account. No card is needed.
2. Verify a sender address: **Settings** (or your name, top right) →
   **Senders, Domains & Dedicated IPs** → **Senders** → **Add a sender**.
   Use your Gmail address, then enter the code Brevo emails you.
   Brevo sends from Gmail addresses through its own compliant address; that's
   normal, and the email still shows "CareerForge" as the sender name.
3. Create an API key: **SMTP & API** → **API Keys** → **Generate a new API key**,
   named `careerforge`. **Copy it straight into Render. Don't paste it anywhere else.**
4. Render → careerforge → **Environment** (add the variables if they're missing):
   - `BREVO_API_KEY` = the key
   - `DEFAULT_FROM_EMAIL` = `CareerForge <your-verified-sender@gmail.com>`
   - `EMAIL_BACKEND` = `apps.core.email_backends.BrevoAPIBackend` (already set by `render.yaml`)

   Then **Save, rebuild, and deploy**.
5. Test it: log out → **Log in** → **Forgot password?** → enter your email → open
   the email (check spam) → set a new password.

Reset links expire after 1 hour and work once. The page always says "If an
account exists…", so nobody can use it to find out who has an account. It's
limited to 5 requests per hour per visitor.

## Forgot the admin password?

- Use **Forgot password?** on the login page with the admin email (once Brevo is set up), or:
- Render → careerforge → **Environment** → set `DJANGO_SUPERUSER_EMAIL` and a new
  `DJANGO_SUPERUSER_PASSWORD` (10+ characters, not common, not only numbers) →
  **Save, rebuild, and deploy** → logs show `Admin account password updated.` →
  log in at `/admin/` → delete `DJANGO_SUPERUSER_PASSWORD` again.

## Updating the site

Every push to `main` on GitHub redeploys automatically (`autoDeploy: true`).
Watch progress in Render → careerforge → **Events**/**Logs**.

## If something goes wrong

| What you see | What to do |
|---|---|
| Build failed | Render → Logs: copy the last 40 lines and send them |
| "Bad Request (400)" | The address must end in `.onrender.com`. For a custom domain, add it to `DJANGO_ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` |
| Logs show `could not connect` / SSL error | Re-copy the Neon string with pooling **off** and `?sslmode=require` at the end |
| Page loads but login fails | Use the `https://` address; cookies are HTTPS-only |
| Slow first load | Normal on the free plan (waking up from sleep) |

## How this differs from the Docker Compose setup

`render.yaml` builds `deploy/render/Dockerfile`: one container in which Django
serves the API, the admin and the built React app (via WhiteNoise, with the same
Content-Security-Policy nginx uses). Settings: `config/settings/single_service.py`.
CI builds and runs this exact image on every push (`Production stack` workflow,
`single-service-image` job). The nginx + Docker Compose setup in
[deployment.md](deployment.md) is still the option for your own server.
