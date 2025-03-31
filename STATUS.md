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
- [x] API Key model (`models/iam/api_key.py`)
- [x] Role model (`models/iam/role.py`) - Basic model only
- [x] Permission model (`models/iam/permission.py`)
- [x] Invitation model (`models/iam/invitation.py`) - NOTE: `role_id` FK disabled
- [ ] Role association models (`TenantRole`, `UserTenantRole`, `TenantRolePermission`) - **MISSING**

- [x] User Schemas (`schemas/iam/user.py`)
- [x] Tenant Schemas (`schemas/iam/tenant.py`)
- [x] API Key Schemas (`schemas/iam/api_key.py`)
- [x] Role Schemas (`schemas/iam/role.py`)
- [x] Invitation Schemas (`schemas/iam/invitation.py`)
- [x] Auth Schemas (`schemas/iam/auth.py`)

- [x] User Service (`services/iam/user.py`)
- [x] Tenant Service (`services/iam/tenant.py`)
- [x] API Key Service (`services/iam/api_key.py`) - Includes validation
- [ ] Role Service (`services/iam/role.py`) - NOTE: Depends on missing models, related code commented out
- [x] Permission Service (`services/iam/permission.py`)
- [ ] Invitation Service (`services/iam/invitation.py`) - NOTE: `role_id` logic affected by missing Role models

- [x] Auth Endpoints (`api/v1/endpoints/auth.py`) - NOTE: Auth logic is **mocked**
- [x] User Endpoints (`api/v1/endpoints/users.py`)
- [x] Tenant Endpoints (`api/v1/endpoints/tenants.py`)
- [x] API Key Endpoints (`api/v1/endpoints/api_keys.py`)
- [x] Role Endpoints (`api/v1/endpoints/roles.py`) - NOTE: Permission assignment logic is disabled
- [x] Invitation Endpoints (`api/v1/endpoints/invitations.py`)

### Testing

- [x] Test framework setup (pytest, pytest-asyncio)
- [x] Test database setup (Docker Compose, PostgreSQL)
- [x] Test client setup (`TestClient` via `httpx`)
- [x] Core test fixtures (`tests/conftest.py`) - Needs fixes (`async_client`)
- [x] Basic functional tests (`tests/functional/test_health.py`, `tests/functional/test_auth.py`)
- [ ] Port remaining functional tests
- [ ] Achieve >80% test coverage

## Key TODOs / Next Steps

1.  **Fix `async_client` fixture** in `tests/conftest.py` (`TypeError`).
2.  **Run basic tests** (`test_health`, `test_auth`) successfully against the real test DB.
3.  **Port functional tests** from old script to `tests/functional/` using new fixtures.
4.  **Run full test suite** and fix failures encountered against the real DB.
5.  **Implement missing Role models** (`TenantRole`, `UserTenantRole`, `TenantRolePermission`).
6.  **Uncomment related code** in `Invitation` model and `Role` service, fix any issues.
7.  **Implement real authentication logic** (user lookup, password verification) in auth endpoints/dependencies.
8.  **Write tests** for Role/Permission assignment and Tenant/User management.
9.  **Achieve target test coverage** (>80%).
10. **Review and update** `instructions.md` based on this detailed status. 