# Academy Management System

A modular monolith for managing academy operations: students, teachers, courses, classes, enrollment, attendance, and finance.

## Quick Start

```bash
# Clone and setup
git clone <repo-url>
cd SchoolManager
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements-dev.txt
cp .env.example .env

# Run
python run.py

# Test
pytest
```

## Production Deployment

Docker-based deployment:

```bash
cp .env.example .env
# Edit .env with production secrets
docker-compose up -d
# App is now running on http://localhost
```

See [Deployment Guide](docs/DEPLOYMENT.md) for full instructions.

> Note: the live VPS deployment does not use Docker. It runs Gunicorn behind
> system Nginx under systemd; see [VPS Deployment](docs/VPS_DEPLOYMENT.md) for
> the general architecture and workflow. Machine-specific instructions live in
> `DEPLOYMENT.local.md` on the VPS only (never committed).

## Tech Stack

- Python 3.14+
- Flask
- SQLAlchemy + Flask-Migrate
- PostgreSQL
- Jinja2 + vanilla JS

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Development Guide](docs/DEVELOPMENT.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [Project Status](docs/PROJECT_STATUS.md)
- [Roadmap](docs/TODO.md)
- [Changelog](docs/CHANGELOG.md)

## License

Proprietary.
