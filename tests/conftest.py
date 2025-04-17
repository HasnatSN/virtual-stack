import sys
import os
import pytest
from typing import Generator, Any, AsyncGenerator
import logging
import asyncio
from uuid import UUID
import alembic

# Add project root to sys.path to allow absolute imports from 'src'
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, AsyncEngine, AsyncConnection
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy import text
from sqlalchemy.schema import CreateTable, CreateSchema, DropSchema
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import ProgrammingError

from src.virtualstack.api.deps import get_db # Import the dependency
# Remove the problematic import
# from src.virtualstack.api.v1.endpoints.auth import login_rate_limiter 

# Import the rate_limit function to create our own rate limiter for testing
from src.virtualstack.core.rate_limiter import rate_limit

# Ensure models are imported so Base.metadata is populated
import src.virtualstack.models

# Set environment variable to indicate test mode *before* importing settings or app
# This ensures settings loads the correct .env file if logic depends on RUN_ENV
os.environ["RUN_ENV"] = "test"

# Explicit override: ensure TEST_DATABASE_URL matches the Docker test container
os.environ["TEST_DATABASE_URL"] = "postgresql+asyncpg://testuser:testpassword@localhost:5434/virtualstack_test"

from virtualstack.core.config import settings
from virtualstack.db.base import Base
from virtualstack.core.security import create_access_token # Import token creation function

# Force settings.TEST_DATABASE_URL to match the test container DSN (override pydantic default)
settings.TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

if not settings.TEST_DATABASE_URL:
    raise RuntimeError("Test database URL (TEST_DATABASE_URL) not set in environment or .env file.")

test_engine = create_async_engine(str(settings.TEST_DATABASE_URL), echo=False) # Corrected: Use URL
TestingSessionLocal = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

from virtualstack.main import app as fastapi_app # Import the app instance directly
from virtualstack.schemas.iam.user import UserCreate  # Import UserCreate schema
from virtualstack.services.iam import user_service, tenant_service, role_service, permission_service # Import services
from virtualstack.models.iam import User, Tenant, Role, Permission # Added Role, Permission
from virtualstack.schemas.iam.tenant import TenantCreate # Add TenantCreate
from virtualstack.schemas.iam.role import RoleCreate
from virtualstack.schemas.iam.permission import PermissionCreate # Add PermissionCreate
from virtualstack.core import permissions as core_permissions # Import the enum definition

# Create our own login_rate_limiter for testing - a simple pass-through function
# that doesn't actually rate limit but satisfies the dependency
async def login_rate_limiter():
    """No-op rate limiter for testing."""
    return None

# Hardcode the schema name used by the models
DB_SCHEMA_NAME = "iam"

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Alembic imports
from alembic.config import Config as AlembicConfig
from alembic import command as alembic_command
# Remove dynamic loading imports if they exist
# import importlib.util
# import importlib.machinery
import asyncio # Ensure asyncio is imported
import os
import alembic

# Ensure project root is defined (needed for script_location)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# --- Database Fixtures ---

@pytest.fixture(scope="session")
def event_loop(request):
    """Create an instance of the default event loop for each test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="function")
async def engine() -> AsyncGenerator[AsyncEngine, None]:
    """Creates an isolated async engine for each test with NullPool."""
    # Access the TEST_DATABASE_URL attribute directly
    test_db_dsn = settings.TEST_DATABASE_URL
    if not test_db_dsn:
        pytest.fail("TEST_DATABASE_URL could not be determined from settings. Ensure environment variables (e.g., TEST_POSTGRES_*) are set or TEST_DATABASE_URL is explicitly defined.")

    # Convert the DSN object to a string for create_async_engine
    test_db_url_str = str(test_db_dsn)

    logger.info(f"[Test Setup] Creating engine for test with URL: {test_db_url_str}")
    # Use NullPool to ensure no connections are carried over between tests
    e = create_async_engine(test_db_url_str, poolclass=NullPool, echo=False)
    try:
        yield e
    finally:
        # Ensure engine disposal happens even if yield raises exception
        if e is not None:
            await e.dispose()
            logger.info("[Test Teardown] Engine disposed.")

@pytest_asyncio.fixture(scope="function")
async def create_test_schema(engine: AsyncEngine) -> AsyncGenerator[AsyncConnection, None]:
    """Fixture to drop/recreate schema using raw SQL + Alembic commands in a thread."""
    schema_name = "iam" # Assuming 'iam' is the primary schema managed by Alembic
    unique_id = id(create_test_schema)
    logger.info(f"[Test Setup - {unique_id}] Acquiring connection and setting up schema '{schema_name}'.")
    alembic_cfg = None # Initialize alembic_cfg
    test_db_url_str = str(engine.url) # Get URL for env var

    conn = await engine.connect()

    try:
        # 1. Drop/Create schema within a transaction
        async with conn.begin():
             logger.info(f"[Test Setup - {unique_id}] Dropping schema '{schema_name}' if exists (cascade).")
             await conn.execute(DropSchema(schema_name, if_exists=True, cascade=True))
             logger.info(f"[Test Setup - {unique_id}] Creating schema '{schema_name}'.")
             await conn.execute(CreateSchema(schema_name, if_not_exists=True))
             logger.info(f"[Test Setup - {unique_id}] Schema drop/create transaction committed.")

        # 2. Use Alembic commands via asyncio.to_thread
        logger.info(f"[Test Setup - {unique_id}] Configuring Alembic for upgrade command.")
        alembic_cfg = AlembicConfig("alembic.ini")
        # Point Alembic at our test DB URL directly (override ini)
        alembic_cfg.set_main_option("sqlalchemy.url", test_db_url_str)
        script_location = os.path.join(PROJECT_ROOT, "alembic")
        alembic_cfg.set_main_option("script_location", script_location)

        logger.info(f"[Test Setup - {unique_id}] Setting VIRTUALSTACK_TEST_DB_URL for Alembic thread: {test_db_url_str}")
        os.environ["VIRTUALSTACK_TEST_DB_URL"] = test_db_url_str # Set env var

        logger.info(f"[Test Setup - {unique_id}] Running Alembic upgrade command in thread...")
        try:
            # Run the synchronous Alembic command in a separate thread
            await asyncio.to_thread(alembic.command.upgrade, alembic_cfg, "head")
            logger.info(f"[Test Setup - {unique_id}] Alembic upgrade command thread finished.")
        except Exception as e:
             logger.error(f"[Test Setup - {unique_id}] Alembic upgrade command failed: {e}", exc_info=True)
             raise
        finally:
             # Ensure env var is unset even if upgrade fails
             if "VIRTUALSTACK_TEST_DB_URL" in os.environ:
                 logger.info(f"[Test Setup - {unique_id}] Unsetting VIRTUALSTACK_TEST_DB_URL.")
                 del os.environ["VIRTUALSTACK_TEST_DB_URL"]

        # 3. Verify table existence *after* Alembic command thread completes
        try:
            # Use the connection established at the start of the fixture
            await conn.execute(text(f"SELECT 1 FROM {schema_name}.tenants LIMIT 1"))
            logger.info(f"[Test Setup - {unique_id}] Verified '{schema_name}.tenants' table exists post-Alembic command.")
        except Exception as e:
            logger.error(f"[Test Setup - {unique_id}] '{schema_name}.tenants' table not found after Alembic command: {e}", exc_info=True)
            raise

        logger.info(f"[Test Setup - {unique_id}] Schema setup complete. Yielding connection.")
        yield conn # Yield the connection

    except Exception as e:
        logger.error(f"[Test Setup - {unique_id}] Error during schema setup phase: {e}", exc_info=True)
        if conn and not conn.closed:
            # Rollback might not be needed if error occurred before yielding
            # await conn.rollback()
            await conn.close()
            logger.info(f"[Test Teardown - {unique_id}] Connection closed after setup error.")
        raise
    finally:
        # Cleanup: Downgrade and drop schema (optional, but good practice)
        # For now, focus on upgrade working. Add downgrade later if needed.
        # if alembic_cfg: # Ensure config was created
        #     try:
        #         logger.info(f"[Test Teardown - {unique_id}] Running Alembic downgrade to base.")
        #         alembic.command.downgrade(alembic_cfg, "base")
        #         logger.info(f"[Test Teardown - {unique_id}] Alembic downgrade finished.")
        #     except Exception as e:
        #         logger.error(f"[Test Teardown - {unique_id}] Error during Alembic downgrade: {e}", exc_info=True)

        # Ensure connection is closed even if downgrade fails
        if conn and not conn.closed:
             logger.info(f"[Test Teardown - {unique_id}] Closing connection yielded by create_test_schema.")
             await conn.close()

@pytest_asyncio.fixture(scope="function")
async def db_session(create_test_schema: AsyncConnection) -> AsyncGenerator[AsyncSession, None]: # Changed return type hint
    """Yields an AsyncSession backed by the connection from create_test_schema."""
    conn = create_test_schema # The yielded connection
    # Create a session bound to this connection
    TestSession = sessionmaker(conn, class_=AsyncSession, expire_on_commit=False)
    async with TestSession() as session:
         logger.info(f"[Test Setup - {id(session)}] Yielding DB Session based on connection {id(conn)}.")
         yield session
         # Session is automatically closed by async context manager
    logger.info(f"[Test Teardown - {id(session)}] db_session finished.")

@pytest_asyncio.fixture(scope="function")
async def seed_data(db_session: AsyncSession): # Now depends on the AsyncSession
    """Seeds initial data like the default tenant, superuser, and core permissions."""
    # Dependency on create_test_schema is now implicit via db_session
    from src.virtualstack.services.iam.tenant import tenant_service
    from src.virtualstack.services.iam.user import user_service
    from src.virtualstack.schemas.iam.tenant import TenantCreate
    from src.virtualstack.schemas.iam.user import UserCreate
    from src.virtualstack.core.config import settings

    unique_id = id(seed_data)
    logger.info(f"[Test Setup - {unique_id}] Seeding initial data (tenant, superuser).")

    try:
        # Ensure default tenant exists - Use the new specific setting
        tenant = await tenant_service.get_by_name(db_session, name=settings.DEFAULT_TEST_TENANT_NAME)
        if not tenant:
            logger.info(f"[Test Setup - {unique_id}] Default test tenant '{settings.DEFAULT_TEST_TENANT_NAME}' not found, creating.")
            tenant_in = TenantCreate(name=settings.DEFAULT_TEST_TENANT_NAME)
            tenant = await tenant_service.create(db_session, obj_in=tenant_in)
            logger.info(f"[Test Setup - {unique_id}] Default test tenant created with ID: {tenant.id}.")
        else:
            logger.info(f"[Test Setup - {unique_id}] Default test tenant '{settings.DEFAULT_TEST_TENANT_NAME}' already exists with ID: {tenant.id}.")

        # Ensure superuser exists
        superuser = await user_service.get_by_email(db_session, email=settings.SUPERUSER_EMAIL)
        if not superuser:
            logger.info(f"[Test Setup - {unique_id}] Superuser '{settings.SUPERUSER_EMAIL}' not found, creating.")
            user_in = UserCreate(
                email=settings.SUPERUSER_EMAIL,
                password=settings.SUPERUSER_PASSWORD,
                first_name="Default",  # Add first_name to match the current schema
                last_name="Superuser", # Add last_name to match the current schema
                is_superuser=True # Explicitly set
            )
            # Update to use create instead of create_user and match parameter names
            superuser = await user_service.create(db_session, obj_in=user_in, tenant_id=tenant.id)
            logger.info(f"[Test Setup - {unique_id}] Superuser created with ID: {superuser.id}.")
        else:
            logger.info(f"[Test Setup - {unique_id}] Superuser '{settings.SUPERUSER_EMAIL}' already exists with ID: {superuser.id}.")

        logger.info(f"[Test Setup - {unique_id}] Data seeding completed successfully.")
        return {"tenant": tenant, "superuser": superuser} # Return seeded objects if needed

    except Exception as e:
        logger.error(f"[Test Setup - {unique_id}] Error during data seeding: {e}", exc_info=True)
        raise

# --- Application Fixtures ---

@pytest.fixture(scope="function")
def app(db_session: AsyncSession) -> FastAPI: # Depends on AsyncSession
    """Overrides dependencies for the FastAPI app for testing, depends on schema being ready."""
    # Create a no-op rate limiter for tests
    async def fake_rate_limiter():
        """No-op rate limiter for testing."""
        return None

    # Override get_db to use the single connection provided by db_session fixture
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]: # Yield AsyncSession
         logger.debug(f"[Dependency Override] Yielding session {id(db_session)} for get_db")
         yield db_session
         # Session lifecycle managed by db_session fixture

    # More explicit dependency override setup
    fastapi_app.dependency_overrides[login_rate_limiter] = fake_rate_limiter
    fastapi_app.dependency_overrides[get_db] = override_get_db # Use the session override
    logger.info(f"[Test Setup] FastAPI app configured with overridden dependencies (rate_limiter, get_db using session {id(db_session)}).")

    yield fastapi_app

    # Clean up overrides after test
    fastapi_app.dependency_overrides = {}
    logger.info("[Test Teardown] FastAPI dependency overrides cleared.")

@pytest_asyncio.fixture(scope="function")
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Provides an AsyncClient for making requests to the test app."""
    # Use ASGITransport directly for FastAPI lifespan events
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        logger.info("[Test Setup] AsyncClient created.")
        yield c
    logger.info("[Test Teardown] AsyncClient closed.")

# --- Authentication Fixtures ---

# Remove test_password, test_user fixtures as they are superseded by seed_data
# Remove authenticated_async_client_tenant_admin (use seed_data + test_user_client if needed)

# --- Authentication Helpers ---

# Remove _get_token and get_user_token helpers
# async def _get_token(...)
# async def get_user_token(...)

# --- Authenticated Clients ---

# Update authenticated clients to use tokens from seed_data
@pytest_asyncio.fixture(scope="function")
async def authenticated_async_client(client: AsyncClient, seed_data: dict) -> AsyncClient:
    """Provides an authenticated async client (using the seeded superuser's token)."""
    superuser = seed_data.get("superuser")
    tenant = seed_data.get("tenant")
    if not superuser or not tenant:
        pytest.fail("Seeding failed to provide superuser or tenant objects.")

    logger.info("[Test Setup] Getting token for authenticated_async_client (superuser)...")
    login_data = {
        "username": settings.SUPERUSER_EMAIL,
        "password": settings.SUPERUSER_PASSWORD,
    }
    token_url = "/api/v1/auth/token"
    response = None
    try:
        response = await client.post(
            token_url,
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        token_data = response.json()
        access_token = token_data["access_token"]
        
        # Set headers on the client instance
        client.headers["Authorization"] = f"Bearer {access_token}"
        # Set tenant header for superuser tests, using the seeded tenant ID
        client.headers["X-Tenant-ID"] = str(tenant.id)
        logger.info(f"[Test Setup] authenticated_async_client ready (Superuser, Tenant: {tenant.id}).")
        return client # Return the configured client
    except Exception as e:
        logger.error(f"[Test Setup] Failed to authenticate client: {e}", exc_info=True)
        if response is not None:
             logger.error(f"Login response status: {response.status_code}")
             try:
                 logger.error(f"Login response body: {response.json()}")
             except Exception:
                 logger.error(f"Login response body (non-JSON): {response.text}")
        pytest.fail(f"Failed to authenticate client: {e}")

@pytest_asyncio.fixture(scope="function")
async def authenticated_async_client_user2(async_client: AsyncClient, seed_data: dict) -> AsyncClient:
    """Provides an authenticated async client (using the second test user's token from seed_data)."""
    token = seed_data["test_user_token"]
    tenant = seed_data["tenant"]
    async_client.headers["Authorization"] = f"Bearer {token}"
    async_client.headers["X-Tenant-ID"] = str(tenant.id)
    logging.info(f"Authenticated client created for test user 2 using seeded token.")
    return async_client

# --- Specific Test Dependencies ---
# Keep setup_invitation_dependencies for now, but it might need review later
@pytest.fixture(scope="function")
def setup_invitation_dependencies(seed_data: dict) -> dict:
    """Provides necessary dependencies (tenant_id, role_id) for invitation tests."""
    tenant = seed_data["tenant"]
    tenant_admin_role = seed_data["tenant_admin_role"]
    return {
        "tenant_id": tenant.id,
        "role_id": tenant_admin_role.id
    }

# Remove old Test Clients fixtures (admin_client, test_user_client)
# They are effectively replaced by authenticated_async_client and authenticated_async_client_user2
# @pytest_asyncio.fixture(scope="function")
# async def admin_client(...)
# @pytest_asyncio.fixture(scope="function")
# async def test_user_client(...)

# Fixture to get authentication token for the superuser
@pytest_asyncio.fixture(scope="function")
async def superuser_token_headers(client: AsyncClient, seed_data: dict) -> dict[str, str]:
    """Generates authentication token headers for the seeded superuser by logging in."""
    logger.info("[Test Setup] Getting token for superuser_token_headers...")
    login_data = {
        "username": settings.SUPERUSER_EMAIL,
        "password": settings.SUPERUSER_PASSWORD,
    }
    token_url = "/api/v1/auth/token"
    response = None
    try:
        # Use the *base* client fixture which doesn't have preset headers
        async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test") as temp_client:
            response = await temp_client.post(
                token_url,
                data=login_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            token_data = response.json()
            access_token = token_data["access_token"]

            headers = {
                "Authorization": f"Bearer {access_token}",
                "X-Tenant-ID": str(seed_data["tenant"].id)
            }
            logger.info(f"[Test Setup] superuser_token_headers generated (Tenant: {seed_data['tenant'].id}).")
            return headers
    except Exception as e:
        logger.error(f"[Test Setup] Failed to get token for superuser_token_headers: {e}", exc_info=True)
        if response is not None:
             logger.error(f"Login response status: {response.status_code}")
             try:
                 logger.error(f"Login response body: {response.json()}")
             except Exception:
                 logger.error(f"Login response body (non-JSON): {response.text}")
        pytest.fail(f"Failed to get token for superuser_token_headers: {e}")
