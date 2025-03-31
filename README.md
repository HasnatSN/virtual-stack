# VirtualStack Backend

A multi-tenant cloud management platform backend service built with FastAPI.

## Features

- Multi-tenant architecture
- Role-based access control (RBAC)
- vCenter integration for VM management
- Background job processing with Celery
- API key authentication
- Audit logging
- Support ticket integration
- Billing and usage tracking

## Project Status (as of last review)

- **Core:** FastAPI app, Config, DB Session (real DB), Base Models/Schemas/Services - Implemented.
- **Auth:** Endpoints/Schemas exist, logic is **mocked**.
- **Users:** Basic CRUD implemented.
- **Tenants:** Basic CRUD implemented.
- **API Keys:** Implemented and includes validation logic.
- **Roles:** Basic Role model/endpoints exist. Tenant/User/Permission association models **missing**, related service code **commented out**.
- **Invitations:** Mostly implemented. `role_id` FK/relationship **commented out** pending Role model completion.
- **Testing:** Refactored to pytest, Docker test DB, TestClient. Initial health/auth tests written. Test setup requires fixes.

## Prerequisites

- Python 3.10+
- Poetry for dependency management
- PostgreSQL 13+
- Redis 6+
- Docker and Docker Compose (for development)

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

4. Start development services:
   ```bash
   docker-compose up -d
   ```

5. Run database migrations:
   ```bash
   poetry run alembic upgrade head
   ```

6. Start the development server:
   ```bash
   poetry run uvicorn virtualstack.main:app --reload
   ```

## Development

- Run tests: `poetry run pytest`
- Format code: `poetry run black .`
- Sort imports: `poetry run isort .`
- Type checking: `poetry run mypy .`
- Lint code: `poetry run flake8`

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
virtualstack-backend/
├── src/
│   └── virtualstack/
│       ├── api/            # API endpoints
│       ├── core/           # Core functionality
│       ├── models/         # Database models
│       ├── services/       # Business logic
│       ├── repositories/   # Data access layer
│       ├── adapters/       # External service adapters
│       └── workers/        # Celery tasks
├── config/                 # Configuration files
├── scripts/               # Utility scripts
├── tests/                 # Test files
└── alembic/              # Database migrations
```

## License

[Your License] 