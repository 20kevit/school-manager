# Architecture

## Overview

Academy Management System uses a **modular monolith** architecture. The codebase is organized into four layers with strictly enforced dependency direction.

## Layers

```
Interface (routes, templates, API endpoints)
    |
    v
Application (use cases, orchestration, DTOs)
    |
    v
Domain (entities, value objects, domain services, repository interfaces)

Infrastructure (database, external services, email, payment gateways)
    |
    v
Domain / Application contracts (repository interfaces, service interfaces)
```

### Domain Layer

- Contains business entities and rules.
- Framework-agnostic: no Flask, no SQLAlchemy imports.
- Repository interfaces are defined here; implementations live in Infrastructure.

### Application Layer

- Orchestrates use cases.
- Calls domain services and infrastructure.
- Never imports from Interface.

### Infrastructure Layer

- Implements repository interfaces from Domain.
- Contains database models (SQLAlchemy), external service integrations, email, SMS, payment gateways.
- Implements ports defined by Application/Domain.

### Interface Layer

- Flask blueprints, routes, templates, API views.
- Thin controllers: parse input, call Application layer, return response.
- No business logic here.

## Application Factory

`app/__init__.py` exposes `create_app(config_name)` which:

1. Loads configuration.
2. Initializes extensions (SQLAlchemy, Migrate).
3. Registers blueprints.
4. Registers error handlers.

## Configuration

Separate configs per environment (development, testing, production) in `config/__init__.py`. Secrets come from environment variables via `.env`.

## Database

- PostgreSQL in production.
- SQLAlchemy ORM for models.
- Flask-Migrate (Alembic) for schema migrations.
- Migration workflow: Model change -> Migration -> Test -> Commit.

## Frontend

- Jinja2 templates with a base layout.
- Vanilla CSS/JS, mobile-first responsive design.
- RTL-ready: HTML `dir` attribute and CSS logical properties when Persian is added.

## API Strategy

- REST/JSON API at `/api/v1/`.
- Separate blueprint (`api_bp`) for API routes.
- Same backend serves web and future mobile clients.

## Adding New Modules

1. Create domain entities in `app/domain/<module>/`.
2. Create repository interfaces in domain.
3. Implement repositories in `app/infrastructure/`.
4. Create application services in `app/application/<module>/`.
5. Create interface (blueprint) in `app/interface/web/` or `app/interface/api/`.
6. Register blueprint in `app/__init__.py`.

## Payment Integration (Future)

```
Application
    |
    v
Payment Service
    |
    v
Gateway Interface (abstract)
    +-- ZarinPal
    +-- Other Iranian Gateway
    +-- Future Gateway
```

The domain defines the payment port; infrastructure implements each gateway.

## Notification Integration (Future)

External communication providers (SMS, Telegram, Bale, Email) belong in `app/infrastructure/`. The domain defines notification interfaces; infrastructure implements them per provider.
