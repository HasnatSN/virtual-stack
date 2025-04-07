## Current Implementation Status

### Core Features

- [x] Basic FastAPI setup (`main.py`)
- [x] Configuration management (`core/config.py`) - Reads `.env`.
- [x] CORS Middleware
- [x] Basic health check endpoints (`/`, `/health`)
- [x] Database setup (SQLAlchemy, asyncpg, greenlet)
- [x] Base model class (`db/base_class.py`)
- [x] Async database session management (`db/session.py`)
- [x] Base CRUD service (`services/base.py`)
- [x] Basic API dependency setup (`api/deps.py`) - Includes JWT/API Key handling. `require_permission` updated to read `tenant_id` from path params.

### IAM Features

- [x] User model (`models/iam/user.py`) - Schema defined
- [x] Tenant model (`models/iam/tenant.py`) - Schema defined
- [x] API Key model (`models/iam/api_key.py`) - Schema defined. Includes `scope`, timezone-aware timestamps.
- [x] Role model (`models/iam/role.py`) - Schema defined.
- [x] Permission model (`models/iam/permission.py`) - Schema defined. Added `TENANT_VIEW_USERS`.
- [ ] Invitation model (`models/iam/invitation.py`) - **PAUSED** (Code commented out). Schema defined.
- [x] `user_tenant_roles` association table defined (`models/iam/user_tenant_role.py`) - **ORM Class `UserTenantRole` added.**
- [x] `role_permissions` association table defined (`models/iam/role_permissions.py`)

- [x] User Schemas (`schemas/iam/user.py`) - `UserResponse` import corrected to use `User`.
- [x] Tenant Schemas (`schemas/iam/tenant.py`)
- [x] API Key Schemas (`schemas/iam/api_key.py`)
- [x] Role Schemas (`schemas/iam/role.py`)
- [ ] Invitation Schemas (`schemas/iam/invitation.py`) - **PAUSED** (Code commented out).
- [x] Auth Schemas (`schemas/iam/auth.py`)
- [x] Permission Schemas (`schemas/iam/permission.py`)

- [x] User Service (`services/iam/user.py`) - Includes `assign_role_to_user_in_tenant` and `remove_role_from_user_in_tenant`. Added `get_users_by_tenant`. Fixed `AuthorizationError` import.
- [x] Tenant Service (`services/iam/tenant.py`)
- [x] API Key Service (`services/iam/api_key.py`) - Implemented. Validation logic added. Refresh logic added but effectiveness TBD.
- [x] Role Service (`services/iam/role.py`) - Includes permission management methods.
- [x] Permission Service (`services/iam/permission.py`)
- [ ] Invitation Service (`services/iam/invitation.py`) - **PAUSED** (Code commented out).

- [x] Auth Endpoints (`api/v1/endpoints/auth.py`) - Functional for tests.
- [x] User Endpoints (`api/v1/endpoints/users.py`) - Basic CRUD + /me functional
- [x] Tenant Endpoints (`api/v1/endpoints/tenants.py`) - Basic CRUD functional
- [x] API Key Endpoints (`api/v1/endpoints/api_keys.py`) - Endpoints exist. **Functionality PAUSED due to focus shift.**
- [x] Role Endpoints (`api/v1/endpoints/roles.py`) - Basic CRUD working. Includes permission management endpoints.
- [x] Tenant User Management Endpoints (`api/v1/endpoints/tenant_user_management.py`) - Implemented `POST` (assign role), `DELETE` (remove role), `GET /` (list users), `GET /{user_id}` (get user). Routing prefix issue resolved. Schema import corrected.
- [x] Role Permission Endpoints (`api/v1/endpoints/roles.py`) - Endpoints exist (`/roles/{role_id}/permissions`).
- [ ] Invitation Endpoints (`api/v1/endpoints/invitations.py`) - **PAUSED** (Code commented out, router inclusion commented out).

### Testing

- [x] Test framework setup (pytest, pytest-asyncio)
- [x] Test database setup (using real DB URI, creating/dropping `iam` schema per session)
- [x] `pytest.ini` configured
- [x] Core test fixtures (`tests/conftest.py`)
    - [x] Session-scoped `setup_database` fixture (creates tables, seeds users, permissions, base tenant, base role). FK violation resolved. **Added `TENANT_MANAGE_USER_ROLES` and `TENANT_VIEW_USERS` permission assignment to Tenant Admin role.**
    - [x] Various authenticated client fixtures (superuser, regular user, tenant admin).
- [x] Basic functional tests (`tests/functional/test_health.py`) - Passing (assumed, not run recently)
- [x] Auth functional tests (`tests/functional/test_auth.py`) - Passing (assumed, not run recently)
- [x] Tenant functional tests (`tests/functional/test_tenants.py`) - Passing (assumed, not run recently)
- [x] User functional tests (`tests/functional/test_users.py`) - Passing (assumed, not run recently)
- [x] API Key functional tests (`tests/functional/test_api_keys.py`) - **PAUSED**.
- [x] Role functional tests (`tests/functional/test_roles.py`) - Basic CRUD passing. Permission management tests need verification.
- [ ] Role assignment tests (`tests/functional/test_role_assignments.py`) - **BLOCKED/FAILING** during setup (`conftest.py`) due to `OSError: [Errno 61] Connection refused` when trying to connect to the test database (`localhost:5434`). Previous issues (FK violation, routing, permissions, imports) resolved.
- [ ] Invitation functional tests (`tests/functional/test_invitations.py`) - **PAUSED** (Module commented out).
- [ ] Achieve >80% test coverage

**Current Blocker (Highest Priority):**

*   **RESOLVED:** The `db_test` container was not running. Started it using `docker-compose up -d`. Connection should now work.

**Other Issues (Lower Priority / Paused):**

*   **API Key `created_at` Validation:** Paused investigation.
*   **Permission Checking Thoroughness:** Comprehensive testing of all permission scenarios is needed once tests can run.
*   **Alembic Migrations:** Need to be generated/updated once the schema stabilizes.

## Key TODOs / Next Steps (Refocused)

1.  **Run and Verify Tests (High Priority):**
    *   Execute `test_role_assignments.py` and resolve any remaining failures (e.g., logic errors now that connection/setup issues are fixed).
    *   Add and run tests for the new list/get user endpoints.
    *   Verify role permission management tests (`test_roles.py`).
    *   Re-verify all permission-denied tests across modules.
2.  **Re-enable/Complete Invitation System:**
    *   Uncomment code in `invitations.py` and `api.py`.
    *   Implement remaining Invitation service logic.
    *   Write/Enable invitation tests.
3.  **Address Secondary Priorities:**
    *   Investigate/resolve API Key `created_at` issue (Lower Priority).
    *   Address Technical Debt (Pydantic V2, warnings, etc.).
    *   Increase overall test coverage (>80%).
    *   Generate necessary Alembic migrations.
4.  **Documentation:**
    *   Create missing docs (`database_migrations.md`, etc.).
    *   Keep other docs updated as features stabilize. 