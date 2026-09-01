# Production Deployment Guide

This guide covers deploying the Academy Management System using Docker and Docker Compose.

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

The application includes an in-process background scheduler that runs as a daemon thread. With multiple Gunicorn workers, multiple scheduler instances may run concurrently. The scheduler is idempotent, so duplicate execution is safe. For strict single-instance scheduling, set `GUNICORN_WORKERS=1` or consider a dedicated scheduler process in a future phase.

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
