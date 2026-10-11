# Production Deployment Guide

This guide covers deploying the Academy Management System using Docker and Docker Compose.

> Note: Docker is one supported deployment option. The live VPS deployment uses
> Gunicorn behind system Nginx under systemd instead — see
> [VPS Deployment](VPS_DEPLOYMENT.md) for the general architecture and workflow.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose v2+
- Git

## Quick Start

```bash
# 1. Clone the repository
git clone <repo-url>
cd SchoolManager

# 2. Configure environment variables
cp .env.example .env
# Edit .env with your production secrets (SECRET_KEY, POSTGRES_PASSWORD, etc.)

# 3. Start all services
docker-compose up -d

# 4. Verify the deployment
curl http://localhost/health
# Should return: {"status":"ok"}
```

## Services

| Service | Description | Port |
|---------|-------------|------|
| `db` | PostgreSQL 15 database | 5432 (internal) |
| `web` | Flask app via Gunicorn | 8000 (internal) |
| `nginx` | Reverse proxy + static files | 80 |

## Default Credentials

After seeding (SEED_MODE=demo):

| Username | Password | Role |
|----------|----------|------|
| admin | admin123 | Administrator |
| teacher1 | teacher123 | Teacher |
| student1 | student123 | Student |
| parent1 | parent123 | Parent |

## Environment Variables

### Required

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Flask secret key (change in production!) |
| `POSTGRES_PASSWORD` | PostgreSQL password |

### Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `SEED_MODE` | (empty) | `demo` for rich demo data, `basic` for roles/admin only, empty to skip |
| `NGINX_PORT` | `80` | External port for Nginx |
| `GUNICORN_WORKERS` | `CPU*2+1` | Number of Gunicorn worker processes |
| `GUNICORN_TIMEOUT` | `120` | Request timeout in seconds |

## Common Operations

### View logs

```bash
docker-compose logs -f web       # App logs
docker-compose logs -f db        # Database logs
docker-compose logs -f nginx     # Nginx logs
```

### Restart services

```bash
docker-compose restart web       # Restart app only
docker-compose restart           # Restart all services
```

### Run database migrations manually

```bash
docker-compose exec web flask db upgrade
```

### Access PostgreSQL

```bash
docker-compose exec db psql -U school_user -d school_manager
```

### Stop the stack

```bash
docker-compose down              # Stop containers
docker-compose down -v           # Stop and remove volumes (WARNING: deletes data)
```

## Rebuilding

After code changes:

```bash
docker-compose build web
docker-compose up -d web
```

## Backup

### Database backup

```bash
docker-compose exec db pg_dump -U school_user school_manager > backup.sql
```

### Database restore

```bash
cat backup.sql | docker-compose exec -T db psql -U school_user -d school_manager
```

## Production Notes

### Scheduler

The application includes an in-process background scheduler that runs as a daemon thread. **The scheduler is disabled by default** and only starts when the `ENABLE_SCHEDULER=True` environment variable is set.

- **Docker / VPS**: Set `ENABLE_SCHEDULER=True` in your `.env` file to enable the background scheduler.
- **cPanel shared hosting**: Do NOT set this variable. Use Cron Jobs instead (see cPanel section below).

With multiple Gunicorn workers, multiple scheduler instances may run concurrently when enabled. The scheduler is idempotent, so duplicate execution is safe. For strict single-instance scheduling, set `GUNICORN_WORKERS=1` or consider a dedicated scheduler process in a future phase.

### Static Files

Nginx serves static files (`/static/`) directly for better performance. Uploads are stored in a Docker volume and shared between the web and nginx containers.

### Security Checklist

- [ ] Change `SECRET_KEY` to a strong random value
- [ ] Change `POSTGRES_PASSWORD` to a strong random value
- [ ] Set `FLASK_DEBUG=0` (default in production)
- [ ] Set `FLASK_ENV=production`
- [ ] Set `SEED_MODE=` (empty) for real production use
- [ ] Configure SSL/TLS (e.g., via Nginx with Let's Encrypt)
- [ ] Restrict PostgreSQL access to internal network only

---

## cPanel Shared Hosting Deployment

cPanel shared hosting uses Phusion Passenger as the WSGI server instead of Gunicorn. Background daemon threads are killed by the host, so scheduled tasks must use Cron Jobs.

### Setup

1. **Upload the project** to your cPanel home directory (e.g., `~/school_manager/`).

2. **Configure the Python app** in cPanel > Setup Python App:
   - Python version: 3.12
   - App root: `school_manager`
   - WSGI file: `passenger_wsgi.py`
   - Application startup: `passenger_wsgi.py`

3. **Install dependencies** via cPanel Terminal or SSH:
   ```bash
   cd ~/school_manager
   pip install -r requirements.txt
   ```

4. **Configure environment variables** in cPanel > Setup Python App > Environment Variables:
   - `SECRET_KEY` = (generate a strong random value)
   - `DATABASE_URL` = (your PostgreSQL or MySQL connection string)
   - `FLASK_APP` = `passenger_wsgi.py`
   - `FLASK_ENV` = `production`
   - Do NOT set `ENABLE_SCHEDULER` — the scheduler must remain disabled on shared hosting.

5. **Run migrations and seed**:
   ```bash
   cd ~/school_manager
   flask db upgrade
   flask seed-demo  # or flask seed for basic data
   ```

### Scheduler (Cron Job)

Background daemon threads are killed on shared hosting. The scheduler must run via Cron instead.

**Important**: The `ENABLE_SCHEDULER` environment variable must NOT be set to `True` on cPanel. The background scheduler is disabled by default, making the app safe for shared hosting.

In cPanel > Cron Jobs, add a new cron job:

```
Minute: 0
Hour: */1
Command: cd ~/school_manager && python -m flask run-jobs
```

This runs `flask run-jobs` every hour. The command is idempotent — running it multiple times per day is safe.

### Important Notes

- `passenger_wsgi.py` is the WSGI entry point for Passenger (equivalent to `wsgi.py` for Gunicorn). It includes a fallback mechanism to load environment variables from `.env` if cPanel env vars are not configured.
- The scheduler daemon thread is **disabled by default** and will NOT start unless `ENABLE_SCHEDULER=True` is set. On cPanel, use the Cron Job instead.
- `flask run-jobs` runs both the daily class reminder and weekly payment reminder in one invocation.
- If your host only supports MySQL, set `DATABASE_URL` to a `mysql+pymysql://` connection string. The application automatically configures `utf8mb4` charset for MySQL connections.
- MySQL migrations automatically use `utf8mb4` charset and collation for full Persian character support.
