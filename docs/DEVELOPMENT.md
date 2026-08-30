# Development Guide

## Requirements

- Python 3.14+
- PostgreSQL
- Git

## Setup

```bash
# Clone
git clone <repo-url>
cd SchoolManager

# Virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Linux/macOS

# Dependencies
pip install -r requirements-dev.txt

# Environment
cp .env.example .env
# Edit .env with your database credentials
```

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `SECRET_KEY` | Flask secret key | `change-me` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://localhost:5432/school_manager_dev` |
| `FLASK_ENV` | Environment name | `development` |
| `FLASK_DEBUG` | Debug mode | `1` |

## Running

```bash
python run.py
```

The app runs at `http://127.0.0.1:5000` by default.

## Testing

```bash
pytest
```

With coverage:

```bash
pytest --cov=app --cov-report=term-missing
```

## Linting & Formatting

```bash
# Check
ruff check .

# Fix
ruff check --fix .

# Format
ruff format .
```

## Database

### Create database

```bash
# In PostgreSQL
createdb school_manager_dev
```

### Initialize migrations

```bash
flask db init
```

### Create migration

```bash
flask db migrate -m "description"
```

### Apply migration

```bash
flask db upgrade
```

## Git Workflow

1. Create a feature branch from `main`.
2. Make changes in logical commits.
3. Run tests and lint before committing.
4. Commit with clear messages.
5. Open a PR for review.

## Conventions

- All source code and documentation in English.
- Persian/RTL support in UI only (not in code comments or variable names).
- Type hints on public APIs.
- One logical change per commit.
- Tests required for new features.
