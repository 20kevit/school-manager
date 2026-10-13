# Clean Installation (supported path)

This is the supported way to install school-manager on a fresh host or
alongside an existing installation. It mirrors the production layout
(system Nginx + Gunicorn + systemd + local PostgreSQL, no Docker). Docker
and cPanel paths are documented separately in `docs/DEPLOYMENT.md`.

No real secrets appear below — copy values from your own password manager.

## 1. Supported versions

- Python **3.12** (`python:3.12-slim` in Docker, venv 3.12.3 in production)
- PostgreSQL **15/16** (production runs 16)
- SQLAlchemy `>=2.1,<2.2` with `psycopg2-binary`; database URLs MUST use the
  explicit `postgresql+psycopg2://` scheme (bare `postgresql://` is rejected
  at startup)

## 2. System packages (Debian/Ubuntu)

```bash
sudo apt update
sudo apt install -y python3.12 python3.12-venv postgresql-16 git nginx certbot
```

## 3. Service user and checkout

```bash
sudo useradd -r -m -s /usr/sbin/nologin school-manager
sudo -u school-manager git clone <repo-url> /opt/projects/school-manager
cd /opt/projects/school-manager
git checkout <release-SHA>   # exact SHA from the release report, never a branch
```

## 4. Virtual environment and dependencies

```bash
sudo -u school-manager python3.12 -m venv .venv
sudo -u school-manager .venv/bin/pip install -r requirements.txt
sudo -u school-manager .venv/bin/python -c "from wsgi import app; print('import-ok')"
```

## 5. Database and role

```bash
sudo -u postgres psql -c "CREATE ROLE school_manager WITH LOGIN PASSWORD '<strong-generated-password>';"
sudo -u postgres psql -c "CREATE DATABASE school_manager OWNER school_manager;"
```

This host connects over TCP (`127.0.0.1:5432`) with scram-sha-256, so the
role needs a strong generated password. The password lives ONLY in the
640 root-owned environment file (§6) — never in the repo, logs, or shell
history (type it via a password manager, don't `echo` it into files).
Peer-socket auth (no password) is possible only when the role name equals
the OS user; the TCP+password layout above matches the existing
production setup.

## 6. Environment file

```bash
sudo mkdir -p /etc/school-manager
sudo cp .env.example /etc/school-manager/school-manager.env
sudo chown root:school-manager /etc/school-manager/school-manager.env
sudo chmod 640 /etc/school-manager/school-manager.env
```

Edit the file and set (names only — values are yours):

- `FLASK_ENV=production`
- `SECRET_KEY` — strong random, ≥32 chars (startup refuses known defaults)
- `DATABASE_URL=postgresql+psycopg2://school_manager:<password>@127.0.0.1:5432/school_manager`
- `FILE_STORAGE_BACKEND=local`
- `FILE_STORAGE_PATH=/opt/projects/school-manager/data/uploads`
- `ZARINPAL_MERCHANT_ID` — leave empty until payments are activated
- `ZARINPAL_SANDBOX=true`

## 7. Migrate to head

```bash
su -s /bin/bash school-manager -c 'set -a; . /etc/school-manager/school-manager.env; set +a; cd /opt/projects/school-manager && .venv/bin/flask --app wsgi db current'
# Expect the repo head (see CHANGELOG / release report for the current value).
su -s /bin/bash school-manager -c 'set -a; . /etc/school-manager/school-manager.env; set +a; cd /opt/projects/school-manager && .venv/bin/flask --app wsgi db upgrade'
```

There is no non-mutating dry run — `upgrade` mutates. On a clean install the
database is empty, so this is safe. For upgrades of live data, follow the
deployment runbook (`DEPLOYMENT.local.md` on the VPS).

## 8. Initial administrator (secure)

```bash
su -s /bin/bash school-manager -c 'set -a; . /etc/school-manager/school-manager.env; set +a; cd /opt/projects/school-manager && .venv/bin/flask --app wsgi create-admin --login admin'
# Password is prompted without echo; ≥10 chars, not a known default.
```

Never run `flask seed` / `flask seed-demo` on a real installation — they
create documented weak credentials and refuse `FLASK_ENV=production`.

## 9. First academy configuration (via UI, logged in as admin)

1. Academic year + semesters (`/admin/years`).
2. Courses (`/academy/courses`), then classes with schedules and teachers.
3. Teacher accounts (admin creates them; each sets their own password).
4. Tuition charges post automatically on enrollment approval.

## 10. Service, TLS, health

Install the systemd unit and Nginx vhost from `deploy/` examples (adapt
paths), `systemctl daemon-reload`, enable + start the service, issue the
Let's Encrypt certificate, then verify:

```bash
curl -s http://127.0.0.1:8100/health   # {"status":"ok","database":"ok"}
curl -sSI https://<your-domain>/ | head -3   # HTTP 200
```

`/health` returns HTTP 503 `{"status":"degraded"}` when the process is
alive but PostgreSQL is unreachable — use it for monitoring.

## 11. Backups

Enable the backup timer and verify the first run plus a restore drill
before opening to users. Details live in `DEPLOYMENT.local.md` (VPS-only).
Local backups do not survive host loss — arrange encrypted off-host copies
(see `docs/VPS_DEPLOYMENT.md`) before trusting the installation.

## 12. Future upgrades

Code: fetch + checkout exact SHA + restart (see runbook). Database: back up
first, run `flask --app wsgi db upgrade`, verify `db current` equals the
repo head. Downgrades are destructive and unsupported — recover forward.
