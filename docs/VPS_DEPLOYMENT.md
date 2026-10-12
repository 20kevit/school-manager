# VPS Deployment (general)

This document describes **how** the application is deployed on the production VPS
at a general level. It intentionally contains **no secrets, no host-specific
paths, no credentials, and no internal addresses**.

Machine-specific facts (exact paths, ports, service names, database names) live in
`DEPLOYMENT.local.md` at the project root **on the VPS only**. That file is
excluded from Git and must never be committed or pushed.

## Architecture

```
Internet → Cloudflare Edge (TLS + proxy) → system Nginx → Gunicorn (loopback) → Flask (WSGI)
                                                              ↳ PostgreSQL (local)
```

- **Cloudflare** terminates public TLS and proxies to the origin. The origin also
  serves TLS; plain HTTP is redirected to HTTPS.
- **System Nginx** (not the `nginx/` container config in this repo) is the reverse
  proxy. It serves `/static/` directly and forwards application traffic to
  Gunicorn over a loopback port. Unknown hostnames are rejected by a catch-all
  server block.
- **Gunicorn** runs the Flask app (`wsgi:app`) from a project virtualenv under a
  dedicated service user, supervised by **systemd** with automatic restart and a
  dependency on PostgreSQL.
- **PostgreSQL** runs locally. Schema is managed with Flask-Migrate/Alembic
  (`migrations/`); the database must be at the repo migration head.
- **Uploads** use the local filesystem backend under the project data directory.

The `docker-compose.yml` / `nginx/nginx.conf` files in this repo describe a
**Docker-based deployment option**, not the live VPS deployment. Do not assume
they describe production. The cPanel/Passenger path in `docs/DEPLOYMENT.md` is a
third, separate option.

## Development vs production

| Concern | Development | Production (VPS) |
|---|---|---|
| Runner | `python run.py` (Flask dev server) | Gunicorn via systemd |
| Config | `.env` from `.env.example` | service environment file (VPS-only) |
| Database | local PostgreSQL / SQLite | local PostgreSQL, migrated to head |
| TLS | none | Cloudflare + origin certificates |
| Scheduler | off by default | see `docs/DEPLOYMENT.md` scheduler notes |

## Standard deployment workflow (summary)

Full machine-specific steps are in `DEPLOYMENT.local.md`. The general order is:

1. Verify a clean tree and fetch the canonical branch (`main`).
2. Back up the database and uploads **before** any migration.
3. Check out the target revision; ensure file ownership matches the service user.
4. Sync dependencies only if requirements changed.
5. Apply migrations only if the database is behind the repo head.
6. Restart the backend service; confirm the loopback listener responds.
7. Reload Nginx **only** if its configuration actually changed.
8. Smoke-test the public HTTPS endpoint and inspect logs for new errors.

Rollback is Git-based: check out the previous revision (restoring the
pre-deploy database backup if migrations ran forward), restart, verify.

Automated daily backups (database plus uploads) run on the VPS with retention;
details and the restore procedure are in `DEPLOYMENT.local.md`.

## Discovering deployment details (for future agents)

- Start with `DEPLOYMENT.local.md` on the VPS (project root, Git-ignored).
- Verify every claim against the live system: service status, listeners,
  migration revision (`flask db current` vs repo heads), Nginx validity
  (`nginx -t`), and the public HTTPS endpoint — never trust docs blindly.
- The canonical branch is `main`; deployment SHAs are recorded in
  `DEPLOYMENT.local.md` after each release.

## Files that must never enter Git

- `DEPLOYMENT.local.md` (enforced by `/DEPLOYMENT.local.md` in `.gitignore`)
- `.env`, `.env.*` (except `.env.example`), any file containing secret values
- Database files/dumps (`*.db`, `*.sqlite3`, `*.sql`, `backup*`)
- Uploads and media (`uploads/`, `data/uploads/`, `test_storage/`)
- Virtualenvs (`.venv/`), logs (`*.log`, `logs/`), caches (`.config/`, `.ruff_cache/`)
- Private SSH keys and TLS private keys

Before every push, inspect `git status`, staged files, and confirm none of the
above are included.
