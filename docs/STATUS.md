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
- [x] API Key model (`models/iam/api_key.py`) - Includes `scope`, timezone-aware timestamps (`created_at`, `updated_at`, `expires_at`, `last_used_at`).
- [x] Role model (`models/iam/role.py`) - Basic model only
- [x] Permission model (`models/iam/permission.py`)
- [x] Invitation model (`models/iam/invitation.py`) - NOTE: `role_id` FK disabled
- [x] `user_tenant_roles` association table defined (`models/iam/user_tenant_role.py`)
- [x] Other Role association models (`tenant_roles_table`, `role_permissions_table`) - Defined in `models/iam/tenant_role.py` & `models/iam/role_permissions.py`

- [x] User Schemas (`schemas/iam/user.py`)
- [x] Tenant Schemas (`schemas/iam/tenant.py`)
- [x] API Key Schemas (`schemas/iam/api_key.py`) - NOTE: Pydantic v2 migration in progress.
- [x] Role Schemas (`schemas/iam/role.py`)
- [x] Invitation Schemas (`schemas/iam/invitation.py`) - NOTE: Pydantic v2 migration in progress.
- [x] Auth Schemas (`schemas/iam/auth.py`)
- [x] Permission Schemas (`schemas/iam/permission.py`) - Added `PermissionAssign`.

- [x] User Service (`services/iam/user.py`) - Implemented `assign_role_to_user_in_tenant` and `remove_role_from_user_in_tenant`.
- [x] Tenant Service (`services/iam/tenant.py`)
- [x] API Key Service (`services/iam/api_key.py`) - Includes validation, scope handling, **timezone-aware expiry handling fixed**. Refresh logic added to `get_multi...` methods.
- [x] Role Service (`services/iam/role.py`) - Added `get_role_permissions`, `add_permission_to_role`, `remove_permission_from_role`.
- [x] Permission Service (`services/iam/permission.py`)
- [ ] Invitation Service (`services/iam/invitation.py`) - NOTE: `role_id` logic affected by missing Role models

- [x] Auth Endpoints (`api/v1/endpoints/auth.py`) - Login works for tests.
- [x] User Endpoints (`api/v1/endpoints/users.py`) - Basic CRUD + /me endpoints functional
- [x] Tenant Endpoints (`api/v1/endpoints/tenants.py`) - Basic CRUD endpoints functional
- [x] API Key Endpoints (`api/v1/endpoints/api_keys.py`) - Endpoints exist. **Persistent validation error on `created_at` during list operations.** Create/Get/Update/Delete endpoints functional.
- [x] Role Endpoints (`api/v1/endpoints/roles.py`) - Basic CRUD working.
- [x] Tenant User Management Endpoints (`api/v1/endpoints/tenant_user_management.py`) - Implemented `POST` (assign role) and `DELETE` (remove role). User-in-tenant check temporarily commented out.
- [x] Role Endpoints (`api/v1/endpoints/roles.py`) - Added permission management endpoints (`GET`, `POST`, `DELETE` /permissions).
- [x] Invitation Endpoints (`api/v1/endpoints/invitations.py`)

### Testing

- [x] Test framework setup (pytest, pytest-asyncio)
- [x] Test database setup (using real DB URI from env vars, requires `RUN_ENV=test`)
- [x] `pytest.ini` configured (`asyncio_mode=strict`, `pythonpath=src`)
- [x] Core test fixtures (`tests/conftest.py`)
    - [x] Session-scoped `setup_database` fixture creates tables and test user (with hashed password) ONCE per session.
    - [x] Session-scoped `app` fixture provides FastAPI app instance with DB dependency override.
    - [x] Function-scoped `async_client` provides basic `httpx.AsyncClient`.
    - [x] Function-scoped `authenticated_async_client` handles login via API and provides authenticated client (superuser).
    - [x] Function-scoped `authenticated_async_client_user2` handles login for regular user.
    - [x] Function-scoped `authenticated_async_client_tenant_admin` fixture implemented (`tests/conftest.py`).
- [x] Basic functional tests (`tests/functional/test_health.py`) - Passing
- [x] Auth functional tests (`tests/functional/test_auth.py`) - Passing (Confirms `authenticated_async_client` works)
- [x] Tenant functional tests (`tests/functional/test_tenants.py`) - Passing (Basic CRUD)
- [x] User functional tests (`tests/functional/test_users.py`) - Passing (Basic CRUD + /me)
- [x] API Key functional tests (`tests/functional/test_api_keys.py`) - **API Key list tests failing due to `created_at` validation error.** Expiry test (`test_api_key_expiry`) now passing after timezone fixes.
- [x] Role functional tests (`tests/functional/test_roles.py`) - Basic CRUD passing. **Permission management tests still failing.**
- [x] Role assignment tests (`tests/functional/test_role_assignments.py`) - **Still failing** due to `ForeignKeyViolationError` (role not found) or `400 Bad Request` (permission dependency/tenant context issue).
- [ ] Invitation functional tests (`tests/functional/test_invitations.py`) - Not ported/run
- [ ] Achieve >80% test coverage
- [x] Write tests for Role Permission Management endpoints. **DONE** (but failing, see above)

**Testing Issues & History:**

*   **Mocked Permissions:** Tests involving permission checks (like `test_assign_role_to_user_permission_denied`) are passing against the *mocked* implementation in `api/deps.py`. These tests will need to be re-verified once real permission checking logic is implemented.
*   **Alembic Migration Generation Issues:** Encountered issues with `autogenerate`. Manually created migration (`XXXXXXXXXXXX_...`) for `tenant_roles` and `role_permissions` tables - **needs final revision IDs**. Previous issues with `api_keys` `scope` also required manual migration. Manual migration needed for `last_used_at` timezone change.
*   **Pydantic V2 Migration:** Ongoing process.
*   **Previous Test Failures:** Historical issues related to user object access (`TypeError`/`AttributeError`), API key validation (`ValidationError`), assertion errors (`scope` value), tenant/user CRUD tests, and Alembic execution errors (DB connection, missing functions/schemas, duplicate tables, `uuid-ossp` extension) have been addressed through various fixes and manual migration steps.
*   **Current Test Failures (Post-April 1st ~10:00 PM Debugging):**
    *   **API Key `created_at` Validation:** `GET /api/v1/api-keys/` fails with `ResponseValidationError` because `created_at` is `None` during Pydantic serialization for some keys. Explicit `db.refresh()` calls in service did not resolve this. Keys created by test fixtures seem okay, suggesting a session/loading issue with older/setup-created keys. **(High Priority)**
    *   **Role Assignment/Permission Failures:** Tests in `test_role_assignments.py` (e.g., `test_assign_role_to_user`, `test_remove_role_from_user_success`) fail with `404`, `400`, or `ForeignKeyViolationError`, indicating issues with role/permission creation/lookup potentially related to test fixture scope, transaction management, or permission dependency logic. **(High Priority)**

## Key TODOs / Next Steps

1.  **Resolve `created_at` Validation Error (Highest Priority):**
    *   Investigate SQLAlchemy session behavior, object loading, and potential interactions with `server_default` or `expire_on_commit=False` causing `created_at` to be `None` when listing multiple API keys.
2.  **Fix Role Assignment/Permission Test Failures (High Priority):**
    *   Debug `ForeignKeyViolationError`: Ensure roles created in fixtures/setup are available within the transaction scope of the test execution. Check `setup_database` in `conftest.py`.
    *   Debug `400 Bad Request` / "Tenant context required": Review `require_permission` dependency and tenant context propagation in role assignment endpoints.
3.  **Complete Core IAM Domain:**
    *   Re-verify permission-based tests after fixing `require_permission`.
    *   Complete Invitation System (blocked by role/permission stability).
    *   Review/Implement Tenant Isolation logic and add tests.
4.  **Database Migrations:**
    *   Generate and apply an Alembic migration for the `last_used_at` timezone change in the `APIKey` model.
5.  **Address Secondary Priorities & Test Coverage:**
    *   Enhance API Key Test Coverage (CRUD edge cases).
    *   Address Technical Debt (Pydantic V2, warnings, etc.).
    *   Increase overall test coverage (>80%).
6.  **Documentation:**
    *   Create missing docs (`database_migrations.md`, etc.).
    *   Update `instructions.md` checklist (lower priority). 