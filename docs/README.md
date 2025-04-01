# VirtualStack Backend

A multi-tenant cloud management platform backend service built with FastAPI, following Hexagonal Architecture principles.

## Features

### Current / In Progress:

- Multi-tenant architecture foundation
- Core User and Tenant management (CRUD)
- API Key generation and validation (including **timezone-aware expiry**, scope handling)
- Role definition management (CRUD for global roles)
- Basic Tenant/User role assignment (POST/DELETE)
- Permission assignment to Roles (POST/DELETE)
- Authentication layer (JWT-based, requires integration with real auth provider eventually)
- Async Database interactions (PostgreSQL via SQLAlchemy)
- Configuration via environment variables
- Basic API documentation via Swagger/ReDoc

### Planned:

- Full Role-Based Access Control (RBAC):
    - Permission checking logic implementation and integration
    - Tenant-specific role definitions (if needed)
- User Invitation system
- Audit logging
- Background job processing (e.g., Celery)
- Integration with infrastructure providers (e.g., vCenter)
- Billing and usage tracking
- Support ticket integration hooks

## Project Status (April 2024)

- **Core:** FastAPI app, Config, DB Session, Base Models/Schemas/Services - Implemented and stable.
- **Architecture:** Adopting Hexagonal (Ports & Adapters). See `docs/architecture_approach.md`.
- **Roadmap & Priorities:** Focused on resolving current test failures in IAM Domain. See `docs/STATUS.md`.
- **Auth:** Endpoints/Schemas exist, underlying logic uses basic password hashing but lacks full provider integration.
- **Users & Tenants:** Basic CRUD implemented and tested.
- **API Keys:** CRUD, expiry validation (timezone-aware) implemented. **List endpoint currently failing `created_at` validation.**
- **Roles:** Basic CRUD for global Role definitions implemented.
- **Role Permissions:** Endpoints for assigning/removing permissions from roles added.
- **Tenant/User Role Assignment:** Endpoints (POST/DELETE) added.
- **Permission Checking:** Initial `require_permission` dependency implemented but needs refinement and thorough testing, especially regarding tenant context. **Likely involved in role assignment test failures.**
- **Invitations:** Models/Endpoints exist but are **blocked** by the incomplete permission checking and role assignment logic.
- **Testing:** Pytest framework setup with fixtures for DB and authenticated clients (superuser, regular user, tenant admin). Basic tests passing for Health, Auth, Users, Tenants. API Key expiry test passing. **API Key list tests, Role Permission tests, and Role Assignment tests currently failing.** Overall coverage target >80%.

## Prerequisites

- Python 3.10+
- Poetry for dependency management
- PostgreSQL 13+
- Redis 6+
- Docker and Docker Compose (for local development database/Redis)

## Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd virtualstack-backend
   ```

2. Install dependencies:
   ```bash
   poetry install
   ```

3. Copy environment variables:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` with your configuration.

4. Start development services (PostgreSQL and Redis):
   ```bash
   docker-compose up -d postgres redis
   ```

5. Run database migrations:
   ```bash
   # Ensure your .env file points to the Docker PostgreSQL instance
   python3 -m alembic upgrade head
   ```

6. Start the development server:
   ```bash
   python3 -m uvicorn src.virtualstack.main:app --reload --host 0.0.0.0 --port 8000
   ```

## Development

- Run tests: `python3 -m pytest`
- Check for issues (linting, formatting, etc.): `python3 -m ruff check .`
- Fix fixable issues: `python3 -m ruff check . --fix`
- Format code: `python3 -m ruff format .`
- Type checking: `python3 -m mypy src/`

## Code Quality

See `docs/code_quality.md` for details on `ruff` and `pytest-cov` usage.

## Architecture

See `docs/architecture_approach.md` for details on the Hexagonal Architecture approach.

## Roadmap

See `docs/core_roadmap.md` for the current development plan and priorities.

## Database Migrations

See `docs/database_migrations.md` (TODO: Create this file) for details on using Alembic.

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
virtualstack-backend/
├── alembic/              # Alembic migration configuration and scripts
├── docs/                 # Project documentation
├── src/
│   └── virtualstack/     # Main application source code
│       ├── __init__.py
│       ├── api/            # API layer (endpoints, dependencies, middleware)
│       │   ├── __init__.py
│       │   ├── deps.py
│       │   ├── middleware.py
│       │   └── v1/
│       │       ├── __init__.py
│       │       └── endpoints/ # Specific API endpoints (e.g., users.py)
│       ├── core/           # Core application settings, security, exceptions
│       ├── db/             # Database session, base class (SQLAlchemy)
│       ├── models/         # SQLAlchemy ORM models (data structure)
│       ├── schemas/        # Pydantic schemas (data validation & serialization)
│       ├── services/       # Business logic layer
│       ├── adapters/       # External service integrations (e.g., vCenter)
│       ├── workers/        # Background tasks (Celery)
│       └── main.py         # FastAPI application entrypoint
├── tests/                 # Automated tests (pytest)
│   ├── conftest.py
│   ├── functional/
│   └── unit/
├── .env.example           # Example environment variables
├── .gitignore
├── alembic.ini            # Alembic configuration file
├── docker-compose.yml     # Docker Compose setup for dev services
├── pyproject.toml         # Project metadata and dependencies (Poetry)
├── poetry.lock
├── pytest.ini             # Pytest configuration
└── README.md              # This file
```

## License

[Specify License - e.g., MIT, Apache 2.0] 