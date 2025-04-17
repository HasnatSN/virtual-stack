# Core Backend Roadmap (IAM Focus)

This document outlines the remaining tasks required to complete the core Identity and Access Management (IAM) functionality of the VirtualStack backend. We will follow a Test-Driven Development (TDD) approach, focusing on writing tests first where feasible, or ensuring robust test coverage after implementation.

**Crucially, solidifying this core domain is the highest priority and must be completed *before* moving on to infrastructure adapters (e.g., vCenter) or Phase 5 (Compute Module), as per Hexagonal Architecture principles.** The core logic must be stable before adapters are built to interact with it.

## Highest Priority: Complete Core IAM Domain

### 1. Fix Test Setup & Basic API Flow (Completed)

*   **Goal:** Resolve database/migration issues, fix basic API endpoints (health, login, list tenants, list users), and ensure core user/tenant association works.
*   **Status:** **DONE.** Extensive debugging of Alembic migrations, database connections, ORM models, and dependency injection corrected numerous issues. The `scripts/test_api_basic.py` script now passes, verifying health check, login, tenant listing, and user listing within a tenant.

### 2. Stabilize Roles and Permissions System (In Progress)

*   **Goal:** Implement and thoroughly test the full RBAC system.
*   **Status:** Basic global role CRUD endpoints work. User-role assignment and Role permission management endpoints/services exist. Real permission checking (`require_permission` etc.) implemented and basic tests pass. However, running `tests/functional/test_roles.py` still reveals errors related to test setup (initially `UndefinedTableError`, now potentially rate limiting or other dependency issues) preventing full verification. Debugging of `conftest.py` fixtures is ongoing.
*   **Current Blocker:** Functional test suite is failing due to test DB authentication errors (InvalidPasswordError for user "testuser").
*   **Action Items:**
    1. Align `TEST_DATABASE_URL` credentials with the test DB (use `virtualstack:virtualstack` as defined in `.env`/Docker-compose).
    2. Adjust `config.py` or set environment variables (`TEST_POSTGRES_USER`, `TEST_POSTGRES_PASSWORD`) before test setup.
    3. Verify migrations run against the correct test DB and re-seed initial data.
*   **Tasks:**
    *   [X] **Run Role Assignment Tests:** `tests/functional/test_role_assignments.py` executed and failures fixed.
    *   [X] **Run Role Permission Tests:** `tests/functional/test_roles.py` executed, but fixture setup errors persist.
    *   [X] **Implement Real Permission Checking (`require_permission`):** Verified `require_permission` correctly checks permissions.
    *   [X] **Implement Real Permission Checking (`require_any_permission`, `require_all_permissions`):** Verified these dependencies work.
    *   [X] **Write/Verify Permission Dependency Tests:** Tests passing.
    *   [ ] **Resolve Test Fixture Issues:** Fix remaining errors (`UndefinedTableError`, `429 Too Many Requests`) in `tests/functional/test_roles.py` by debugging `conftest.py`.
    *   [ ] **Increase Test Coverage:** Increase test coverage for `role.py`, `permission.py`, `permissions.py`, `deps.py` related to RBAC. Aim for >80%.

### 3. Invitation System (Partially Done)

*   **Goal:** Implement the full user invitation workflow, including role assignment upon acceptance.
*   **Status:** Endpoints/Models/Schemas exist. Core service logic implemented. Test isolation issues mostly resolved. Several bugs fixed.
*   **Tasks:**
    *   [X] **Implement Core Service Logic:** Verified core service functions exist.
    *   [X] **Fix Test Isolation:** Adjusted several tests.
    *   [X] **Fix Service/Endpoint Bugs:** Resolved various interaction issues.
    *   [X] **Adjust Failing Test Assertions:** Corrected assertions.
    *   [X] **Remove Obsolete Test:** Removed `test_extract_token_from_link`.
    *   [ ] **Implement Role Assignment on Acceptance:** **PENDING** - Verify `invitation_service.accept_invitation` correctly assigns the `role_id`.
    *   [ ] **Run & Fix Remaining Tests:** Execute `tests/functional/test_invitations.py` again.
    *   [ ] **Increase Test Coverage:** Add tests for role assignment during acceptance.

### 4. Tenant Isolation and Management (Partially Done - Basic List Users Verified)

*   **Goal:** Ensure strict data isolation between tenants and implement necessary tenant-user management features.
*   **Status:** Tenant ID validation occurs in permission dependencies. Basic user listing within a tenant (`GET /tenants/{tenant_id}/users/`) confirmed working via `test_api_basic.py`. Dedicated review across all services and specific isolation tests are still needed.
*   **Tasks:**
    *   [ ] **Review Service Methods:** Systematically review all service methods (especially list/get operations) for consistent `tenant_id` filtering.
    *   [ ] **Add Tenant Isolation Tests:** Create specific integration tests.
    *   [X] **Implement/Test Tenant User Listing:** Endpoint `GET /tenants/{tenant_id}/users/` verified.
    *   [ ] **Implement/Test Other Tenant User Management:** Verify other user management endpoints within tenant context (if any).

## Secondary Priorities / Paused

### 5. API Key Functionality

*   **Goal:** Resolve previous issues and enhance test coverage.
*   **Status:** **PAUSED.** Basic CRUD endpoints exist. Listing previously failed due to `created_at=None` validation error (Low priority, might be resolved by other fixes).
*   **Tasks (If/When Resumed):**
    *   [ ] Verify if the `created_at=None` issue during API key listing persists; fix if necessary.
    *   [ ] Add more tests to `tests/functional/test_api_keys.py` covering edge cases, permissions, and scopes.

### 6. Address Technical Debt

*   **Goal:** Clean up warnings and improve code quality.
*   **Status:** **PAUSED.**
*   **Tasks:**
    *   [ ] Address Pydantic V2 migration warnings.
    *   [ ] Address `httpx` `DeprecationWarning`.
    *   [ ] Fix any persistent database or migration warnings (e.g., `passlib` bcrypt warning in logs).
    *   [ ] Address `pytest-asyncio` deprecation warnings.
    *   [ ] Generate necessary Alembic migrations once schema stabilizes.

## Conclusion

Significant progress has been made, resolving core database, migration, and basic API endpoint issues. The basic flow for login, tenant access, and user listing is functional. Permission dependency checking is implemented and tested. The immediate priorities are now:

1.  **Fix Role Tests:** Resolve the persistent test setup errors (`UndefinedTableError`/`429 Too Many Requests`) in `tests/functional/test_roles.py` by debugging `conftest.py` fixtures.
2.  **Complete Invitation System:** Finalize service logic (verify role assignment) and fix any remaining tests in `test_invitations.py`.
3.  **Verify Tenant Isolation:** Conduct the service review and add dedicated isolation tests.
4.  **Increase RBAC Test Coverage:** Improve test coverage for roles, permissions, and related dependencies once tests are stable.

Work on API Keys, Technical Debt, or infrastructure adapters will commence only after these core IAM functionalities are complete, tested, and stable.

## Immediate Next Step

1.  **Fix Role Tests:** Continue debugging `tests/functional/test_roles.py` and `conftest.py` to resolve the `UndefinedTableError` and `429 Too Many Requests` errors.

## Immediate Next Steps Checklist

- [ ] Align TEST DB credentials (`TEST_DATABASE_URL`) with actual test DB credentials (`virtualstack:virtualstack` on port 5434)
- [ ] Override `TEST_POSTGRES_USER` and `TEST_POSTGRES_PASSWORD` in `src/virtualstack/core/config.py` or via environment variables before tests
- [ ] Confirm `scripts/run_dev.sh` works and remove references to deprecated scripts (e.g., `run-without-reload.sh`)
- [ ] Rerun Alembic migrations against the test DB (via `create_test_schema` fixture)
- [ ] Verify `seed_initial_data` executes without errors
- [ ] Functional Test: Health check (`GET /health`)
- [ ] Functional Test: Authentication token (`POST /api/v1/auth/token`)
- [ ] Functional Test: Current user info (`GET /api/v1/users/me`)
- [ ] Functional Test: List tenants (`GET /api/v1/tenants`)
- [ ] Functional Test: List users in tenant (`GET /api/v1/tenants/{tenant_id}/users`)
- [ ] Update API reference documentation with confirmed endpoints and examples

---

# Required MVP Endpoints (FE)

This section outlines the *minimum* necessary backend API endpoints identified by the Frontend team to support the core MVP/Alpha functionality focusing on Login, Tenant Selection, User/Role Management (core), and VM Management.

**Assumptions:**

*   Base Path: `/api/v1`
*   Authentication: Handled via Authorization header (e.g., Bearer Token).
*   Tenant Scoping: All resource endpoints are automatically scoped to the user's active tenant based on their authentication context unless otherwise specified.
*   Standard List Responses: List endpoints (`GET` collections) support pagination (`?page=1&limit=20`).
*   Error Handling: Consistent error response format (e.g., `{ "detail": "Error message" }`).

---

## 1. Authentication & User Session

### 1.1. Login (Get Token)

*   **Method:** `POST`
*   **Path:** `/auth/token`
*   **Description:** Authenticates a user, returns access token.
*   **Request:** `application/x-www-form-urlencoded` or JSON `{ "username": "user@email.com", "password": "user_password" }`
*   **Response:** `{ "access_token": "xxx.yyy.zzz", "token_type": "bearer" }`
*   **Permissions:** Public

### 1.2. Get Current User Info

*   **Method:** `GET`
*   **Path:** `/users/me`
*   **Description:** Retrieves details of the authenticated user (needed for UI display, permissions context).
*   **Request:** None (Auth token required)
*   **Response:** `{ "id": "user-1", "email": "admin@example.com", "first_name": "Admin", "last_name": "User", "is_active": true }`
*   **Permissions:** Authenticated User

---

## 2. Tenant Management

### 2.1. List Accessible Tenants

*   **Method:** `GET`
*   **Path:** `/tenants`
*   **Description:** Retrieves tenants accessible to the user (for Tenant Selector).
*   **Request:** None (Auth token required)
*   **Response:** `[ { "id": "tenant-abc", "name": "Huemer Demo Tenant" }, ... ]`
*   **Permissions:** Authenticated User

*   **Note:** Tenant selection is handled client-side for MVP. Backend scopes requests based on user's token and permissions within the target tenant context.

---

## 3. Users & Roles (/users/* - Core)

### 3.1. Users (/users/users)

#### 3.1.1. List Users in Tenant

*   **Method:** `GET`
*   **Path:** `/users`
*   **Description:** Retrieves users within the current tenant for display and role assignment. Supports pagination.
*   **Request:** Query Params: `?page=...`, `?limit=...`, `?search=...` (optional search)
*   **Response:** `{ "items": [ { "id": "user-1", "email": "...", "first_name": "...", "last_name": "...", "is_active": true, "roles": ["Tenant Admin"] }, ... ], "total": ..., "page": ..., "limit": ... }`
*   **Permissions:** `user:read`

#### 3.1.2. [MVP Optional] Update User (Activate/Deactivate)

*   **Method:** `PATCH`
*   **Path:** `/users/{user_id}`
*   **Description:** Allows activating/deactivating a user. May be deferrable if user management outside the app is acceptable for MVP.
*   **Request:** `{ "is_active": boolean }`
*   **Response:** Updated User Object
*   **Permissions:** `user:update`

#### 3.1.3. [MVP Optional] Delete User (or Deactivate)

*   **Method:** `DELETE`
*   **Path:** `/users/{user_id}`
*   **Description:** Removes/deactivates a user. Complex implications, likely deferrable for MVP.
*   **Request:** None
*   **Response:** Status 204 No Content
*   **Permissions:** `user:delete`

### 3.2. Roles & Permissions (/users/roles)

#### 3.2.1. List Roles in Tenant

*   **Method:** `GET`
*   **Path:** `/roles`
*   **Description:** Retrieves roles (system & custom) in the tenant.
*   **Request:** None
*   **Response:** `[ { "id": "role-1", "name": "Tenant Admin", ..., "is_system_role": true, "user_count": 2 }, ... ]`
*   **Permissions:** `role:read`

#### 3.2.2. Get Role Details (incl. Permissions)

*   **Method:** `GET`
*   **Path:** `/roles/{role_id}`
*   **Description:** Retrieves details and assigned permissions for a specific role (for "View Permissions" modal).
*   **Request:** None
*   **Response:** `{ "id": "role-1", ..., "permissions": [ { "id": "vm:read", ... }, ... ] }`
*   **Permissions:** `role:read`

#### 3.2.3. List Available Permissions

*   **Method:** `GET`
*   **Path:** `/permissions`
*   **Description:** Retrieves all possible permissions (for "Create/Edit Custom Role" dialogs).
*   **Request:** None
*   **Response:** `[ { "id": "vm:read", "name": "View VMs", "module": "VMs" }, ... ]`
*   **Permissions:** `role:read` (or dedicated permission)

#### 3.2.4. Create Custom Role

*   **Method:** `POST`
*   **Path:** `/roles`
*   **Description:** Creates a new custom role.
*   **Request:** `{ "name": "...", "description": "...", "permission_ids": ["vm:read", ...] }`
*   **Response:** `{ "id": "role-new-xyz", ... }`
*   **Permissions:** `role:create`

#### 3.2.5. Update Custom Role

*   **Method:** `PATCH`
*   **Path:** `/roles/{role_id}`
*   **Description:** Updates a custom role's name, description, and permissions.
*   **Request:** `{ "name": "...", "description": "...", "permission_ids": [...] }` (Partial updates allowed)
*   **Response:** Updated Role Object `{ "id": "...", ... }`
*   **Permissions:** `role:update`

#### 3.2.6. Delete Custom Role

*   **Method:** `DELETE`
*   **Path:** `/roles/{role_id}`
*   **Description:** Deletes a custom role. Should fail if users are assigned.
*   **Request:** None
*   **Response:** Status 204 No Content
*   **Permissions:** `role:delete`

#### 3.2.7. Get Assigned Users for a Role

*   **Method:** `GET`
*   **Path:** `/roles/{role_id}/users`
*   **Description:** Retrieves user IDs assigned to a role (for "Manage Users" dialog).
*   **Request:** None
*   **Response:** `{ "user_ids": ["user-1", ...] }`
*   **Permissions:** `user:read`, `role:read`

#### 3.2.8. Update Assigned Users for a Role

*   **Method:** `PUT`
*   **Path:** `/roles/{role_id}/users`
*   **Description:** Sets the complete list of users assigned to a role.
*   **Request:** `{ "user_ids": ["user-1", "user-5"] }`
*   **Response:** Status 200 OK or 204 No Content.
*   **Permissions:** `role:assign_users`

---

## 4. Virtual Machines (hSERVER) (/virtual-machines/vms)

### 4.1. List VMs

*   **Method:** `GET`
*   **Path:** `/vms`
*   **Description:** Retrieves VMs in the tenant. Supports pagination.
*   **Request:** Query Params: `?page=...`, `?limit=...`, `?search=...` (optional)
*   **Response:** `{ "items": [ { "id": "vm-123", "name": "...", "status": "RUNNING" | "STOPPED" | "PROVISIONING" | "ERROR", "cpu": ..., "memory_gb": ..., "disk_gb": ..., "ip_address": "...", "created_at": "...", "template_name": "..." }, ... ], "total": ..., ... }`
*   **Permissions:** `vm:read`

### 4.2. Get VM Details

*   **Method:** `GET`
*   **Path:** `/vms/{vm_id}`
*   **Description:** Retrieves details for a specific VM (primarily for Edit form pre-fill).
*   **Request:** None
*   **Response:** `{ "id": "vm-123", "name": "...", "status": "...", ... }`
*   **Permissions:** `vm:read`

### 4.3. Create VM

*   **Method:** `POST`
*   **Path:** `/vms`
*   **Description:** Creates a new VM.
*   **Request:** `{ "name": "...", "source_type": "template" | "iso", "template_id": "...", "iso_url": "...", "cpu": ..., "memory_gb": ..., "disk_gb": ... }` (Need config details if not template-defined)
*   **Response:** `{ "id": "vm-new-abc", "status": "PROVISIONING", ... }`
*   **Permissions:** `vm:create`

### 4.4. Update VM Name

*   **Method:** `PATCH`
*   **Path:** `/vms/{vm_id}`
*   **Description:** Updates the VM's name.
*   **Request:** `{ "name": "new-name" }`
*   **Response:** `{ "id": "vm-123", "name": "new-name", ... }`
*   **Permissions:** `vm:update`

### 4.5. Delete VM

*   **Method:** `DELETE`
*   **Path:** `/vms/{vm_id}`
*   **Description:** Deletes a VM.
*   **Request:** None
*   **Response:** Status 204 No Content (or async job ID)
*   **Permissions:** `vm:delete`

### 4.6. Get VM Logs

*   **Method:** `GET`
*   **Path:** `/vms/{vm_id}/logs`
*   **Description:** Retrieves activity/event logs for a VM (for the "View Logs" modal).
*   **Request:** Query Params: `?limit=...` (optional)
*   **Response:** `[ { "timestamp": "...", "level": "INFO", "message": "..." }, ... ]`
*   **Permissions:** `vm:read` (or `vm:read_logs`)

### 4.7. List VM Templates

*   **Method:** `GET`
*   **Path:** `/vm-templates`
*   **Description:** Retrieves available templates for VM creation dropdown.
*   **Request:** None
*   **Response:** `[ { "id": "tmpl-...", "name": "...", ... }, ... ]`
*   **Permissions:** `vm:create` (or `template:read`)

### 4.8. Perform VM Power Action

*   **Method:** `POST`
*   **Path:** `/vms/{vm_id}/actions`
*   **Description:** Starts, stops, or restarts a VM.
*   **Request:** `{ "action": "start" | "stop" | "restart" }`
*   **Response:** Status 202 Accepted or 200 OK + updated VM status.
*   **Permissions:** `vm:power_manage`

---