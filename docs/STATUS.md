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
- [x] Test client setup (`TestClient`)
- [x] Core test fixtures (`tests/conftest.py`) - Working
- [x] Basic functional tests (`tests/functional/test_health.py`, `tests/functional/test_auth.py`) - Passing
- [ ] Port remaining functional tests (Tenants, Users, API Keys, Roles, Invitations)
- [ ] Create authentication fixtures for tests
- [ ] Achieve >80% test coverage

## Key TODOs / Next Steps

1.  **Port functional tests** from old script to `tests/functional/` (Tenants, Users, API Keys, Roles, Invitations).
2.  **Create authentication fixtures** for tests (e.g., authenticated client, test user/token).
3.  **Enable and run** ported tests, fixing failures against the real DB.
4.  **Implement missing Role models** (`TenantRole`, `UserTenantRole`, `TenantRolePermission`).
5.  **Uncomment related code** in `Invitation` model and `Role` service, fix any issues.
6.  **Implement real authentication logic** (user lookup, password verification) in auth endpoints/dependencies.
7.  **Write tests** for Role/Permission assignment and Tenant/User management.
8.  **Achieve target test coverage** (>80%).
9.  **Review and update** `docs/instructions.md` based on this detailed status.
10. **Address warnings** from `pytest` run (Pydantic, asyncio event loop). 