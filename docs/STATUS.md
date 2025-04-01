## Current Implementation Status

### Core Features

- [x] Basic FastAPI setup (`main.py`)
- [x] Configuration management (`core/config.py`)
- [x] CORS Middleware
- [x] Basic health check endpoints (`/`, `/health`)
- [x] Database setup (SQLAlchemy, asyncpg)
- [x] Base model class (`db/base_class.py`)
- [x] Async database session management (`db/session.py`) - Using REAL DB based on RUN_ENV
- [x] Base CRUD service (`services/base.py`)
- [x] Basic API dependency setup (`api/deps.py`)

### IAM Features

- [x] User model (`models/iam/user.py`)
- [x] Tenant model (`models/iam/tenant.py`)
- [x] API Key model (`models/iam/api_key.py`) - Includes `scope` ENUM field.
- [x] Role model (`models/iam/role.py`) - Basic model only
- [x] Permission model (`models/iam/permission.py`)
- [x] Invitation model (`models/iam/invitation.py`) - NOTE: `role_id` FK disabled
- [ ] Role association models (`TenantRole`, `UserTenantRole`, `TenantRolePermission`) - **MISSING**

- [x] User Schemas (`schemas/iam/user.py`)
- [x] Tenant Schemas (`schemas/iam/tenant.py`)
- [x] API Key Schemas (`schemas/iam/api_key.py`) - NOTE: Pydantic v2 migration in progress.
- [x] Role Schemas (`schemas/iam/role.py`)
- [x] Invitation Schemas (`schemas/iam/invitation.py`) - NOTE: Pydantic v2 migration in progress.
- [x] Auth Schemas (`schemas/iam/auth.py`)

- [x] User Service (`services/iam/user.py`)
- [x] Tenant Service (`services/iam/tenant.py`)
- [x] API Key Service (`services/iam/api_key.py`) - Includes validation and scope handling.
- [ ] Role Service (`services/iam/role.py`) - NOTE: Depends on missing models, related code commented out
- [x] Permission Service (`services/iam/permission.py`)
- [ ] Invitation Service (`services/iam/invitation.py`) - NOTE: `role_id` logic affected by missing Role models

- [x] Auth Endpoints (`api/v1/endpoints/auth.py`) - NOTE: Auth logic is **mocked** (but login works for tests)
- [x] User Endpoints (`api/v1/endpoints/users.py`) - Basic CRUD + /me endpoints functional
- [x] Tenant Endpoints (`api/v1/endpoints/tenants.py`) - Basic CRUD endpoints functional
- [x] API Key Endpoints (`api/v1/endpoints/api_keys.py`) - Endpoints exist. Testing needed.
- [x] Role Endpoints (`api/v1/endpoints/roles.py`) - NOTE: Permission assignment logic is disabled
- [x] Invitation Endpoints (`api/v1/endpoints/invitations.py`)

### Testing

- [x] Test framework setup (pytest, pytest-asyncio)
- [x] Test database setup (using real DB URI from env vars, requires `RUN_ENV=test`)
- [x] `pytest.ini` configured (`asyncio_mode=strict`, `pythonpath=src`)
- [x] Core test fixtures (`tests/conftest.py`)
    - [x] Session-scoped `setup_database` fixture creates tables and test user (with hashed password) ONCE per session.
    - [x] Session-scoped `app` fixture provides FastAPI app instance with DB dependency override.
    - [x] Function-scoped `async_client` provides basic `httpx.AsyncClient`.
    - [x] Function-scoped `authenticated_async_client` handles login via API and provides authenticated client.
- [x] Basic functional tests (`tests/functional/test_health.py`) - Passing
- [x] Auth functional tests (`tests/functional/test_auth.py`) - Passing (Confirms `authenticated_async_client` works)
- [x] Tenant functional tests (`tests/functional/test_tenants.py`) - **Passing** (Basic CRUD)
- [x] User functional tests (`tests/functional/test_users.py`) - **Passing** (Basic CRUD + /me)
- [ ] API Key functional tests (`tests/functional/test_api_keys.py`) - **NEEDS RE-RUN** (Previously failed due to ENUM drop issue during teardown, migration/model fixes applied).
- [ ] Role functional tests (`tests/functional/test_roles.py`) - Not ported/run
- [ ] Invitation functional tests (`tests/functional/test_invitations.py`) - Not ported/run
- [ ] Achieve >80% test coverage

**Testing Issues & History:**

*   **Alembic Migration Generation Issues:** Encountered significant issues with `autogenerate` when adding the `scope` ENUM column to `api_keys`. Required a manually created migration (`manual_add_scope_column.py`) that explicitly creates/drops the ENUM type. SQLAlchemy model also requires `create_type=False` for the ENUM to prevent test teardown failures (`metadata.drop_all`). See `docs/database_migrations.md` (TODO: Create this file) for details.
*   **Pydantic V2 Migration:** Ongoing process. Core settings validators (`config.py`) and some schema validators (`invitation.py`) updated. More V1 validators likely exist.
*   **Previous Test Failures:** Historical issues related to user object access (`TypeError`/`AttributeError`), API key validation (`ValidationError`), assertion errors (`scope` value), tenant/user CRUD tests, and Alembic execution errors (DB connection, missing functions/schemas, duplicate tables, `uuid-ossp` extension) have been addressed through various fixes and manual migration steps.

## Key TODOs / Next Steps

1.  **Verify Test Suite:** Run `pytest` to confirm all tests pass after recent Pydantic V2 and Alembic/ENUM fixes. Address any remaining failures (especially API Key tests).
2.  **Complete Pydantic V2 Migration:** Identify and update remaining Pydantic V1 validators/configs across schemas and models.
3.  **Port/Enable Role & Invitation Tests:** Refactor and run tests for Roles and Invitations. This likely requires implementing missing Role association models first.
4.  **Implement Missing Role Models:** Create `TenantRole`, `UserTenantRole`, `TenantRolePermission` models (`models/iam/`).
5.  **Implement Missing Logic:** Uncomment/Implement Role/Permission assignment logic in services/endpoints, fix Invitation service dependencies. Update corresponding tests.
6.  **Achieve Target Test Coverage:** Write necessary unit/integration tests to reach >80%.
7.  **Create Missing Docs:** Add `database_migrations.md`, `testing.md`, `api_documentation.md`.
8.  **Review `docs/instructions.md`:** Update the checklist based on the final working state. 