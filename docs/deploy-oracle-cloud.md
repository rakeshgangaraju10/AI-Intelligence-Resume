# Put CareerForge on the internet: Oracle Cloud free server + free domain + HTTPS

The result is a public HTTPS address like `https://careerforge-rakesh.duckdns.org`
that anyone can use to register, upload a resume and run analyses.

Cost: ₹0 on Oracle Cloud's Always Free tier. Oracle asks for a card to verify
your identity. Free-tier terms can change, so check Oracle's free-tier page
when you sign up.

You'll use: a free Oracle Cloud Ubuntu server, a free DuckDNS subdomain,
Docker, and this repository's `docker-compose.prod.yml` + `docker-compose.caddy.yml`.
Caddy gets and renews the HTTPS certificate automatically.

Time: about 45–60 minutes the first time.

---

## Step 1: Create the server (Oracle Cloud console)

1. Sign up at oracle.com/cloud/free and pick a **home region** close to your
   users (e.g. India West (Mumbai) or India South (Hyderabad)). The home region
   can't be changed later.
2. Menu → **Compute → Instances → Create instance**.
3. **Image:** Canonical Ubuntu 24.04.
   **Shape:** Ampere → `VM.Standard.A1.Flex`, **2 OCPU, 12 GB memory**. Check that
   it says *Always Free-eligible*.
4. **Networking:** keep the default VCN and **assign a public IPv4 address**.
5. **SSH keys:** choose *Generate a key pair* and **download the private key**
   (e.g. `ssh-key.key`). You can't download it again later.
6. Create. When it's running, copy the **Public IP address**.

If you get "Out of capacity", try again later or pick another availability domain.

## Step 2: Open ports 80 and 443 in Oracle's firewall

1. Instance page → the **subnet** link → **Security Lists** → *Default Security List*.
2. **Add Ingress Rules** (two rules):
   - Source CIDR `0.0.0.0/0`, IP protocol TCP, destination port **80**
   - Source CIDR `0.0.0.0/0`, IP protocol TCP, destination port **443**

## Step 3: Free domain name (DuckDNS)

1. Go to duckdns.org and sign in (GitHub or Google).
2. Add a subdomain, e.g. `careerforge-rakesh`, which gives `careerforge-rakesh.duckdns.org`.
3. Put your server's **public IP** in the *current ip* box and click **update ip**.

You can use your own domain instead: add an **A record** pointing at the server IP.

## Step 4: Log in to the server (Git Bash on Windows)

```bash
chmod 600 ~/Downloads/ssh-key.key
ssh -i ~/Downloads/ssh-key.key ubuntu@YOUR_SERVER_IP
```

Type `yes` the first time. Every command below runs **on the server**.

## Step 5: Server setup (one time)

```bash
# Updates
sudo apt update && sudo apt -y upgrade

# Oracle's Ubuntu image blocks incoming web traffic in its own firewall too; allow 80/443
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save

# Docker (official install script) and permission to run it without sudo
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
exit
```

Log in again (the `ssh` command from Step 4) so the docker permission applies, then check:

```bash
docker --version
docker compose version
```

## Step 6: Get the code and configure it

```bash
git clone https://github.com/rakeshgangaraju10/AI-Intelligence-Resume.git careerforge
cd careerforge
cp .env.production.example .env.production

# Generate two random secrets; you'll paste them into the file
python3 -c "import secrets; print('DJANGO_SECRET_KEY=' + secrets.token_urlsafe(50))"
python3 -c "import secrets; print('POSTGRES_PASSWORD=' + secrets.token_urlsafe(24))"

nano .env.production
```

In `nano`, set these lines (use your own domain), then save with **Ctrl+O, Enter**
and exit with **Ctrl+X**:

```
DJANGO_SECRET_KEY=<the generated value>
DJANGO_ALLOWED_HOSTS=careerforge-rakesh.duckdns.org
CSRF_TRUSTED_ORIGINS=https://careerforge-rakesh.duckdns.org
DJANGO_SECURE_SSL_REDIRECT=True
DRF_NUM_PROXIES=2
POSTGRES_PASSWORD=<the generated value>
DOMAIN=careerforge-rakesh.duckdns.org
VITE_DEMO_MODE=false
```

`DRF_NUM_PROXIES=2` because requests pass through Caddy and then nginx, so the
rate limits need to look two proxies back to find the visitor's real IP.

## Step 7: Start it

```bash
docker compose -f docker-compose.prod.yml -f docker-compose.caddy.yml \
  --env-file .env.production up -d --build
```

The first build takes several minutes. Then:

```bash
docker compose -f docker-compose.prod.yml -f docker-compose.caddy.yml --env-file .env.production ps
docker compose -f docker-compose.prod.yml -f docker-compose.caddy.yml --env-file .env.production logs --tail=50 caddy
```

All four services (`db`, `backend`, `frontend`, `caddy`) should be *running*.
Caddy's log should mention obtaining a certificate for your domain.

Open **https://careerforge-rakesh.duckdns.org** in your browser. 🎉

## Step 8: Admin account and production check

```bash
docker compose -f docker-compose.prod.yml -f docker-compose.caddy.yml --env-file .env.production exec backend \
  python manage.py createsuperuser
docker compose -f docker-compose.prod.yml -f docker-compose.caddy.yml --env-file .env.production exec backend \
  python manage.py check --deploy
```

Admin: `https://<your-domain>/admin/`

## Step 9: Test it like a user (from your laptop)

1. Register, upload a resume, create a job, run an analysis, compare, download a report.
2. Open a private window, register a second account, and paste a URL from the
   first account (e.g. `/analyses/1`). It must say *not found*.
3. Try it on your phone.

## Step 10: Backups (real users' data)

```bash
mkdir -p ~/backups
crontab -e
```

Add this line, which takes a database backup every night at 02:30 and keeps the
last 14 days:

```
30 2 * * * cd ~/careerforge && docker compose -f docker-compose.prod.yml --env-file .env.production exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' | gzip > ~/backups/db-$(date +\%F).sql.gz && find ~/backups -name 'db-*.sql.gz' -mtime +14 -delete
```

Uploaded resume files are in the Docker volume `careerforge-prod_resume_files`.
Back them up too, and keep backups private: they contain personal data.

## Updating to a new version

```bash
cd ~/careerforge
git pull
docker compose -f docker-compose.prod.yml -f docker-compose.caddy.yml --env-file .env.production up -d --build
```

## If something goes wrong

| Symptom | Check |
|---|---|
| Browser can't connect | Step 2 ingress rules and Step 5 iptables; DuckDNS IP matches the server's public IP |
| Certificate error | `logs caddy`. DNS must point at the server and port 80 must be open for Let's Encrypt |
| "Bad Request (400)" | `DJANGO_ALLOWED_HOSTS` must be exactly your domain |
| Login fails with a CSRF error | `CSRF_TRUSTED_ORIGINS` must be `https://your-domain` |
| Build fails | send the last 40 lines of the `up --build` output |
| Anything else | `docker compose ... logs --tail=100 backend` |

## Running a real public service: your responsibilities

People will upload real resumes, which contain personal data. Before you share the link widely:

- Add a short privacy notice: what is stored, why, that nothing goes to
  external AI services, and how to delete it (Settings → Delete account removes
  everything).
- Keep the server updated (`sudo apt upgrade`) and keep backups private.
- Watch for abuse. Rate limits are on, and you can deactivate users in `/admin/`.
- Read India's Digital Personal Data Protection Act basics if you expect real
  users. This isn't legal advice.
