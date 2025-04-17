# Troubleshooting Log

This log tracks issues encountered and resolutions applied during development.

## 2025-04-16: Server Startup & Authentication Issues

**Problem:** Initial attempts to start the backend server (`uvicorn virtualstack.main:app`) and test endpoints failed.

**Debugging Steps & Resolutions:**

1.  **`ModuleNotFoundError: No module named 'virtualstack'`:**
    *   **Cause:** The `src` directory containing the `virtualstack` package was not in the Python path when running `uvicorn` from the project root (`backend/`).
    *   **Resolution:** Added `PYTHONPATH=src` prefix to the `uvicorn` command: `PYTHONPATH=src uvicorn ...`

2.  **`[Errno 48] Address already in use` on port 8000:**
    *   **Cause:** Previous background server processes (`uvicorn ... &`) failed to start correctly (due to ModuleNotFound) but didn't exit cleanly, leaving the port occupied.
    *   **Resolution:** Identified the lingering process PID using `lsof -ti tcp:8000` and terminated it using `kill <PID>`.

3.  **`404 Not Found` for `POST /api/v1/token`:**
    *   **Cause:** Incorrect API path used in `curl` requests. The auth router is mounted under `/auth` within the `/api/v1` prefix.
    *   **Resolution:** Corrected the path to `/api/v1/auth/token`.

4.  **`401 Unauthorized` for `POST /api/v1/auth/token`:**
    *   **Cause:** The server is running and the endpoint is found, but authentication fails.
    *   **Diagnosis:** Likely due to the superuser (`admin@virtualstack.example` with password `testpassword123!`) not existing, being inactive, or having the wrong password in the *development* database (the one specified in `.env`, not the test DB).
    *   **Next Steps:** Verify the development DB state. Ensure the DB container is running and accessible. Check the `iam.users` table for the superuser using `docker exec -it <container_name> psql -U <user> -d <db_name> -c "SELECT ... FROM iam.users WHERE email = 'admin@virtualstack.example';"`. Implement a seeding mechanism for the development environment if the user doesn't exist.

5.  **`SyntaxError: unexpected character after line continuation character` in `init_db.py`:**
    *   **Cause:** Error introduced during previous edit (stray `\`).
    *   **Resolution:** Corrected syntax near docstring definition.

6.  **`ValidationError: ... slug Field required` during seeding:**
    *   **Cause:** `TenantCreate` schema requires `slug`, but it wasn't provided.
    *   **Resolution:** Added `slugify` helper and provided `slug` in `TenantCreate` call in `init_db.py`.

7.  **`ValidationError: ... first_name Field required, last_name Field required` during seeding:**
    *   **Cause:** `UserCreate` schema requires `first_name`, `last_name`.
    *   **Resolution:** Added `first_name`, `last_name` to `UserCreate` call in `init_db.py`, removed `full_name`.

8.  **`AttributeError: 'UserService' object has no attribute 'create_user'` during seeding:**
    *   **Cause:** Incorrect method name used. Should be `create`.
    *   **Resolution:** Changed `user_service.create_user` to `user_service.create` in `init_db.py`. Added `db.refresh()`.

9.  **`TypeError: create() missing 1 required keyword-only argument: 'tenant_id'` during seeding:**
    *   **Cause:** The `user_service.create` method requires `tenant_id` explicitly.
    *   **Resolution:** Added `tenant_id=tenant.id` to the `user_service.create` call in `init_db.py`.

10. **`TypeError: 'AsyncSession' object is not callable'` during startup:**
    *   **Cause:** Incorrect modification in `main.py` lifespan function when adding explicit commit/rollback.
    *   **Resolution:** Reverted session creation logic in `main.py`.

11. **Internal Commits in Services:**
    *   **Cause:** `CRUDBase`, `UserService`, and `TenantService` `create` methods contained internal `db.commit()` calls, interfering with transaction management in `main.py`'s `lifespan`.
    *   **Resolution:** Removed internal commits from these service methods, replaced with `db.flush()` where needed.

12. **`AttributeError: 'UserCreate' object has no attribute 'is_superuser'` during seeding:**
    *   **Cause:** `UserCreate` schema missing `is_superuser` field.
    *   **Resolution:** Added `is_superuser: bool = False` to `UserCreate` schema.

13. **`TypeError: 'first_name' is an invalid keyword argument for User` during seeding:**
    *   **Cause:** `UserService.create` passed `first_name`/`last_name` to `User` model constructor.
    *   **Resolution:** Updated `UserService.create` to construct and pass `full_name` instead.

14. **`ModuleNotFoundError: No module named 'redis'` during startup:**
    *   **Cause:** `redis` added to requirements but not installed.
    *   **Resolution:** User ran `pip install -r requirements.txt`.

15. **`ValueError: no signature found for builtin type <class 'bool'>` during startup (without reload):**
    *   **Cause:** `/auth/token` endpoint incorrectly used `bool` type hint for rate limiter dependency.
    *   **Resolution:** Moved rate limiter to decorator's `dependencies` list.

16. **`AssertionError: A parameter-less dependency must have a callable dependency` during startup (without reload):**
    *   **Cause:** Passed the `rate_limit` factory to `Depends()` instead of the function it returned.
    *   **Resolution:** Called the factory immediately, used the result in `Depends()`.

17. **`sqlalchemy.exc.IntegrityError: null value in column "id" of relation "user_tenant_roles" violates not-null constraint` during seeding:**
    *   **Cause:** The `UserTenantRole` model was being created in `UserService.create` without providing a value for its `id` primary key column, which is non-nullable.
    *   **Resolution (Next Step):** Check `UserTenantRole` model definition and add a default UUID generator (`default=uuid.uuid4`) to its `id` column.

18. **`TypeError: ValidationError() takes no keyword arguments` during seeding error handling:**
    *   **Cause:** The `except IntegrityError` block in `UserService.create` tried to raise `ValidationError(..., error_type="...")`, but the custom `ValidationError` class doesn't accept `error_type`.
    *   **Resolution (Next Step):** Check `ValidationError` definition and adjust the `raise` statement in `UserService.create`.

**Other Noted Issues:**
*   **bcrypt Warning:** Persists. (Deferred)

**Current Status:** Seeding fails due to the `IntegrityError` on the `user_tenant_roles` table, followed by a `TypeError` in the exception handling.

**Next Step:** Fix the `UserTenantRole` model and the `ValidationError` instantiation.

## 2025-05-XX: Functional Test Authentication Failures

**Problem:** All functional tests now fail with `asyncpg.exceptions.InvalidPasswordError: password authentication failed for user "testuser"`.

**Diagnosis:** The generated `TEST_DATABASE_URL` uses default `testuser:testpassword` credentials, but the test database container credentials defined in `.env` and Docker Compose are `virtualstack:virtualstack` (on port 5434), causing an authentication mismatch.

**Resolution Plan:**
1. Update the Test DB credentials in `config.py` or via environment variables so `TEST_DATABASE_URL` matches the actual test DB user/password.
2. Modify `tests/conftest.py` to explicitly set `TEST_POSTGRES_USER`, `TEST_POSTGRES_PASSWORD`, and/or override `TEST_DATABASE_URL` before engine creation.
3. Re-run the Alembic migrations and functional test suite to confirm that database connections and data seeding succeed without authentication errors.

## 2025-05-YY: Missing Run Script

**Problem:** Attempting to start the server with `bash scripts/run-without-reload.sh` fails with "No such file or directory" because that script doesn't exist.

**Resolution:** Use the provided `scripts/run_dev.sh` instead, which correctly sets `PYTHONPATH` and starts Uvicorn (e.g., `bash scripts/run_dev.sh`).

## 2025-05-ZZ: Persistent Test DB Volume Mismatch

**Problem:** Despite updating credentials, the test container is still using stale data (old volume), causing authentication errors.

**Diagnosis:** The named volume `postgres_test_data` persists between restarts, so switching to `tmpfs` did not remove the old data directory. A stale `postgresql.conf` and user setup remains.

**Resolution
1. Run `docker-compose down -v` to remove all named volumes, including `postgres_test_data`.
2. Then `docker-compose up -d db_test` (or full stack) to recreate an ephemeral test DB with correct credentials.

```bash
# Stop and remove containers + volumes
docker-compose down -v
# Start fresh test DB container
docker-compose up -d db_test
``` 