from collections.abc import AsyncGenerator
import os

from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy.sql import text

from src.virtualstack.api.deps import get_db # Import the dependency

# Ensure models are imported so Base.metadata is populated
import src.virtualstack.models

# Set environment variable to indicate test mode *before* importing settings or app
# This ensures settings loads the correct .env file if logic depends on RUN_ENV
os.environ["RUN_ENV"] = "test"

from virtualstack.core.config import settings
from virtualstack.db.base import Base

if not settings.TEST_DATABASE_URL:
    raise RuntimeError("Test database URL (TEST_DATABASE_URL) not set in environment or .env file.")

test_engine = create_async_engine(str(settings.TEST_DATABASE_URL), echo=False) # Corrected: Use URL
TestingSessionLocal = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

from virtualstack.main import app as fastapi_app  # Import your FastAPI app
from virtualstack.schemas.iam.user import UserCreate  # Import UserCreate schema
from virtualstack.services.iam import user_service, tenant_service, role_service, permission_service # Import services
from virtualstack.models.iam import User, Tenant, Role, Permission # Added Role, Permission
from virtualstack.schemas.iam.tenant import TenantCreate # Add TenantCreate
from virtualstack.schemas.iam.role import RoleCreate
from virtualstack.schemas.iam.permission import PermissionCreate # Add PermissionCreate
from virtualstack.core import permissions as core_permissions # Import the enum definition


# --- Database Fixtures ---

@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_database():
    """Sets up the test database, seeds initial data, and tears down afterwards.

    Scope is FUNCTION to ensure isolation between tests.
    Autouse=True ensures this runs for every test function.
    Uses engine connection for DDL and a separate session for seeding.
    """
    print("Setting up database and test users for function...")

    # --- DDL Operations --- 
    print("Performing DDL operations using engine connection...")
    async with test_engine.begin() as conn:
        print("Dropping existing 'iam' schema (if exists)...")
        await conn.execute(text("DROP SCHEMA IF EXISTS iam CASCADE;"))
        print("Creating 'iam' schema...")
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS iam;"))
        print("Creating tables...")
        # Pass the connection to run_sync for create_all
        # Explicitly pass the schema name to create_all
        print("Creating tables for schema 'iam'...")
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                bind=sync_conn, 
                tables=None, # Explicitly None to create all tables in metadata
                checkfirst=False, # Try creating without checking first 
                schemas=['iam'] # Explicitly target the 'iam' schema
            )
        )
        try:
            await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'))
            print("Ensured uuid-ossp extension exists.")
        except Exception as e:
            if "already exists" not in str(e):
                 print(f"Could not create uuid-ossp extension (might require DB superuser or already exist): {e}")
            else:
                 print("uuid-ossp extension already exists.")
        # Explicitly set search path for the transaction
        print("Setting search_path to iam, public...")
        await conn.execute(text("SET search_path TO iam, public;"))
        print("DDL operations committed and search_path set.")
        # Transaction commits automatically here upon exiting `async with test_engine.begin()`

    # --- Seeding Operations --- 
    print("Performing seeding operations using session...")
    async with TestingSessionLocal() as db:
        try:
            # --- DIAGNOSTIC CHECK --- 
            print("Executing diagnostic raw SQL check for iam.tenants...")
            try:
                await db.execute(text("SELECT 1 FROM iam.tenants LIMIT 1;"))
                print("Diagnostic check SUCCESS: iam.tenants is visible.")
            except Exception as diag_error:
                print(f"Diagnostic check FAILED: iam.tenants not visible. Error: {diag_error}")
                # Optionally re-raise if we want the setup to fail here
                raise diag_error # Re-raise to see the error clearly
            # --- END DIAGNOSTIC CHECK --- 

            # Ensure tenant exists
            existing_tenant = await tenant_service.get_by_slug(db, slug=settings.TEST_TENANT_SLUG)
            tenant_id = None
            if not existing_tenant:
                tenant_in = TenantCreate(name="Test Tenant", slug=settings.TEST_TENANT_SLUG)
                created_tenant = await tenant_service.create(db, obj_in=tenant_in)
                tenant_id = created_tenant.id
                print(f"Created test tenant: {created_tenant.name}, ID: {tenant_id}")
            else:
                tenant_id = existing_tenant.id
                print(f"Test tenant already exists: {existing_tenant.name}, ID: {tenant_id}")
            pytest.tenant_id = tenant_id

            # Create first test user (admin)
            user1_email = settings.TEST_USER_EMAIL
            user1_password = settings.TEST_USER_PASSWORD
            user1 = await user_service.get_by_email(db, email=user1_email)
            if not user1:
                user1_in = UserCreate(
                    email=user1_email,
                    password=user1_password,
                    first_name="Test",
                    last_name="Admin",
                    is_superuser=True, 
                    is_active=True,
                )
                user1 = await user_service.create(db, obj_in=user1_in)
                print(f"Created test admin user: {user1.email}, ID: {user1.id}")
            else:
                if not user1.is_superuser or not user1.is_active:
                     user1.is_superuser = True
                     user1.is_active = True
                     db.add(user1)
                     print(f"Updated existing test admin user to be superuser and active: {user1.email}")
                else:
                    print(f"Test admin user already exists and is configured correctly: {user1.email}, ID: {user1.id}")
            pytest.user_id = user1.id

            # Create second test user (regular)
            user2_email = "user2@virtualstack.example"
            user2_password = "testpassword456!"
            user2 = await user_service.get_by_email(db, email=user2_email)
            if not user2:
                user2_in = UserCreate(
                    email=user2_email,
                    password=user2_password,
                    first_name="Regular",
                    last_name="User",
                    is_superuser=False,
                    is_active=True,
                )
                user2 = await user_service.create(db, obj_in=user2_in)
                print(f"Created second test user: {user2.email}, ID: {user2.id}")
            else:
                if user2.is_superuser or not user2.is_active:
                    user2.is_superuser = False
                    user2.is_active = True
                    db.add(user2)
                    print(f"Updated existing second test user to be non-superuser and active: {user2.email}")
                else:
                    print(f"Second test user already exists and is configured correctly: {user2.email}, ID: {user2.id}")
            pytest.user2_email = user2_email
            pytest.user2_password = user2_password
            pytest.user2_id = user2.id

            # --- Seed Permissions --- 
            seeded_permissions = {}
            print("Seeding core permissions...")
            for perm_enum in core_permissions.Permission:
                perm = await permission_service.get_by_name(db, name=perm_enum.value)
                if not perm:
                    perm_in = PermissionCreate(
                        name=perm_enum.value, 
                        code=perm_enum.value,
                        description=f"System permission: {perm_enum.value}"
                    )
                    perm = await permission_service.create(db, obj_in=perm_in)
                    print(f"  Created permission: {perm.name}, ID: {perm.id}")
                else:
                    pass 
                seeded_permissions[perm_enum.value] = perm
            if core_permissions.Permission.VM_READ.value in seeded_permissions:
                 pytest.seeded_permission_id_vm_read = seeded_permissions[core_permissions.Permission.VM_READ.value].id
            else:
                 print(f"WARNING: Could not find/seed {core_permissions.Permission.VM_READ.value} permission for tests!")
                 pytest.seeded_permission_id_vm_read = None

            # --- Tenant Admin Role and User Setup ---
            tenant_admin_role_name = "Tenant Admin"
            tenant_admin_role = await role_service.get_by_name(db, name=tenant_admin_role_name, tenant_id=tenant_id)
            tenant_admin_role_id = None
            if not tenant_admin_role:
                role_in = RoleCreate(
                    name=tenant_admin_role_name, 
                    description="Tenant Administrator Role",
                    tenant_id=tenant_id,
                    is_system_role=True
                )
                tenant_admin_role = await role_service.create(db, obj_in=role_in)
                tenant_admin_role_id = tenant_admin_role.id
                print(f"Created role: {tenant_admin_role.name}, ID: {tenant_admin_role_id}")
                permissions_to_assign = [
                    core_permissions.Permission.TENANT_MANAGE_USER_ROLES,
                    core_permissions.Permission.TENANT_VIEW_USERS,
                    core_permissions.Permission.TENANT_MANAGE_INVITATIONS
                ]
                for perm_to_assign_enum in permissions_to_assign:
                    perm_to_assign = seeded_permissions.get(perm_to_assign_enum.value)
                    if perm_to_assign:
                        print(f"Assigning permission '{perm_to_assign.name}' (ID: {perm_to_assign.id}) to role '{tenant_admin_role.name}' (ID: {tenant_admin_role.id})")
                        try:
                            await role_service.add_permission_to_role(
                                db=db,
                                role_id=tenant_admin_role.id,
                                permission_id=perm_to_assign.id
                            )
                        except Exception as perm_error:
                            print(f"ERROR assigning permission '{perm_to_assign.name}' to role '{tenant_admin_role.name}': {perm_error}")
                    else:
                        print(f"ERROR: Could not find seeded permission '{perm_to_assign_enum.value}' to assign to Tenant Admin role.")
            else:
                tenant_admin_role_id = tenant_admin_role.id
                print(f"Tenant Admin role '{tenant_admin_role.name}' already exists: ID {tenant_admin_role_id}")
            pytest.tenant_admin_role_id = tenant_admin_role_id

            # Create third test user (tenant admin)
            tenant_admin_email = "tenantadmin@virtualstack.example"
            tenant_admin_password = "testpassword789!"
            tenant_admin_user = await user_service.get_by_email(db, email=tenant_admin_email)
            if not tenant_admin_user:
                tenant_admin_in = UserCreate(
                    email=tenant_admin_email,
                    password=tenant_admin_password,
                    first_name="Tenant",
                    last_name="AdminUser",
                    is_superuser=False,
                    is_active=True,
                )
                tenant_admin_user = await user_service.create(db, obj_in=tenant_admin_in)
                print(f"Created third test user (tenant admin): {tenant_admin_user.email}, ID: {tenant_admin_user.id}")
            else:
                print(f"Third test user (tenant admin) already exists: {tenant_admin_user.email}, ID: {tenant_admin_user.id}")

            if tenant_admin_role_id:
                 try:
                    await user_service.assign_role_to_user_in_tenant(
                        db=db,
                        user_id=tenant_admin_user.id,
                        role_id=tenant_admin_role_id,
                        tenant_id=tenant_id
                    )
                    print(f"Assigned role '{tenant_admin_role_name}' to user '{tenant_admin_email}' in tenant ID '{tenant_id}'")
                 except ValueError as assign_error:
                    print(f"Info assigning role '{tenant_admin_role_name}' to user '{tenant_admin_email}': {assign_error}")
                 except Exception as e:
                    print(f"ERROR assigning role '{tenant_admin_role_name}' to user '{tenant_admin_email}': {e}")
                    raise RuntimeError(f"Failed to assign Tenant Admin role during setup: {e}") from e
            else:
                print("ERROR: Cannot assign Tenant Admin role, role ID not found.")

            pytest.tenant_admin_user_email = tenant_admin_email
            pytest.tenant_admin_user_password = tenant_admin_password
            pytest.tenant_admin_user_id = tenant_admin_user.id

            # Explicitly commit all seeding changes within this session block
            await db.commit()
            print("Seeding operations committed.")

        except Exception as seeding_error:
            print(f"ERROR during seeding: {seeding_error}")
            await db.rollback() # Rollback seeding session on error
            raise # Re-raise the exception to fail the setup
        finally:
             print("Seeding session finished.") # Helps track flow

    print("Database and test user setup complete.")

    yield # Test runs here

    # Teardown: Dispose engine after test function completes
    print("\n--- Test Function Teardown --- ")
    print("Disposing database engine for function...")
    await test_engine.dispose()
    print("Database engine disposed.")


@pytest_asyncio.fixture(scope="function")
async def setup_invitation_dependencies(setup_database): # Depends on main setup
    """Fixture to ensure necessary dependencies for invitation tests are available."""
    # Retrieve IDs stored by setup_database
    tenant_id = getattr(pytest, 'tenant_id', None)
    tenant_admin_role_id = getattr(pytest, 'tenant_admin_role_id', None)
    
    if not tenant_id or not tenant_admin_role_id:
        raise RuntimeError("Required tenant_id or tenant_admin_role_id not found in pytest attributes after setup_database.")
        
    print(f"setup_invitation_dependencies: tenant_id={tenant_id}, tenant_admin_role_id={tenant_admin_role_id}")
    return {
        "tenant_id": tenant_id,
        "tenant_admin_role_id": tenant_admin_role_id
    }


# --- Application Fixtures ---


@pytest.fixture(scope="function")
def app(setup_database) -> FastAPI:
    """Return FastAPI app instance for testing, overriding the DB dependency.
    
    Scope is function because it depends on setup_database which is function-scoped.
    """
    # Define the override function for get_db
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with TestingSessionLocal() as session:
            yield session
    # Apply the override to the FastAPI app instance
    fastapi_app.dependency_overrides[get_db] = override_get_db
    return fastapi_app


@pytest_asyncio.fixture(scope="function")
async def async_client(app: FastAPI) -> AsyncClient:
    """Provides a basic async client for unauthenticated requests."""
    # Use httpx.AsyncClient with ASGITransport for async FastAPI testing
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


# --- Authentication Fixtures ---


@pytest.fixture(scope="session")
def test_password() -> str:
    """Provides the default test password."""
    return settings.TEST_USER_PASSWORD


@pytest_asyncio.fixture(scope="function")
async def test_user() -> str:  # Return type changed to str (email)
    """Provide the email of the default test admin user (function scope)."""
    # This fixture no longer interacts with the DB.
    # It relies on setup_database having created the user.
    return settings.TEST_USER_EMAIL


@pytest_asyncio.fixture(scope="function")
async def authenticated_async_client_tenant_admin(
    async_client: AsyncClient, # Use the base unauthenticated client
    setup_database # Depend on setup_database
) -> AsyncClient:
    """Provides an authenticated async client logged in as the tenant admin user."""
    # Ensure the necessary attributes were set during setup
    if not hasattr(pytest, 'tenant_admin_user_email') or not hasattr(pytest, 'tenant_admin_user_password'):
        raise RuntimeError("Tenant admin user credentials not found in pytest attributes. Setup failed?")

    login_data = {
        "username": pytest.tenant_admin_user_email,
        "password": pytest.tenant_admin_user_password,
    }
    print(f"Attempting login for tenant admin user: {pytest.tenant_admin_user_email}")
    # Use the base async_client to perform login
    response = await async_client.post(
        "/api/v1/auth/login/access-token",
        data=login_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if response.status_code != 200:
        print(f"Login failed for tenant admin: {response.text}")
        response.raise_for_status()

    token_data = response.json()
    access_token = token_data["access_token"]
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    # Add tenant header, likely required for tenant admin operations
    if hasattr(pytest, 'tenant_id'):
       headers["X-Tenant-ID"] = str(pytest.tenant_id)
       print(f"Adding X-Tenant-ID header: {pytest.tenant_id} for tenant admin client")

    # Create a NEW client instance for the tenant admin user
    app_instance = async_client._transport.app # type: ignore
    transport = ASGITransport(app=app_instance) # Create transport

    tenant_admin_client = AsyncClient(
        transport=transport, # Use transport instead
        base_url=async_client.base_url,
        headers=headers
    )
    print(f"Login successful for {pytest.tenant_admin_user_email}. NEW Client authenticated.")
    # Yield the new client instance within its own context manager
    async with tenant_admin_client:
        yield tenant_admin_client


# --- Test Clients ---

@pytest.fixture(scope="session")
def app() -> FastAPI:
    """Returns the FastAPI app instance."""
    return fastapi_app


# Use httpx.AsyncClient for async tests
@pytest_asyncio.fixture(scope="function") # Keep function scope for override
async def async_client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]: # Removed db_session injection
    """Provides an asynchronous test client with db dependency override."""
    # Define the override function to use TestingSessionLocal directly
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with TestingSessionLocal() as session:
             yield session
             # No rollback needed here, request handler transactions are managed by get_db

    # Apply the override
    app.dependency_overrides[get_db] = override_get_db
    print("Applied get_db dependency override using TestingSessionLocal.")

    # Use ASGITransport for direct ASGI interaction
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

    # Clean up the override after the test
    del app.dependency_overrides[get_db]
    print("Removed get_db dependency override.")


# --- Authentication Helpers ---

async def get_user_token(async_client: AsyncClient, email: str, password: str) -> str:
    """Helper function to authenticate a user and get a token."""
    login_data = {"username": email, "password": password}
    # Use headers for form data
    headers = {"content-type": "application/x-www-form-urlencoded"}
    r = await async_client.post("/api/v1/auth/login/access-token", data=login_data, headers=headers)
    r.raise_for_status() # Raise exception for bad status codes
    response = r.json()
    assert "access_token" in response
    return response["access_token"]


# --- Authenticated Clients ---

@pytest_asyncio.fixture(scope="function")
async def authenticated_async_client(async_client: AsyncClient) -> AsyncClient:
    """Provides an authenticated async client (using the default test admin user)."""
    print(f"Attempting login for user: {settings.TEST_USER_EMAIL}")
    token = await get_user_token(
        async_client,
        settings.TEST_USER_EMAIL,
        settings.TEST_USER_PASSWORD
    )
    async_client.headers = {"Authorization": f"Bearer {token}"}
    # Add tenant header for default superuser client
    if hasattr(pytest, "tenant_id") and pytest.tenant_id:
        async_client.headers["X-Tenant-ID"] = str(pytest.tenant_id)
        print(f"Adding X-Tenant-ID header: {pytest.tenant_id}")
    else:
        print("Warning: Tenant ID not available to set X-Tenant-ID header for superuser client.")
    print(f"Login successful for {settings.TEST_USER_EMAIL}. Client authenticated.")
    return async_client

@pytest_asyncio.fixture(scope="function")
async def authenticated_async_client_user2(async_client: AsyncClient) -> AsyncClient:
    """Provides an authenticated async client (using the second test user)."""
    assert hasattr(pytest, "user2_email"), "user2_email not set by setup_database"
    assert hasattr(pytest, "user2_password"), "user2_password not set by setup_database"
    email = pytest.user2_email
    password = pytest.user2_password
    print(f"Attempting login for user: {email}")
    token = await get_user_token(async_client, email, password)
    # Create a *new* client instance to avoid header conflicts
    async with AsyncClient(transport=async_client._transport, base_url=async_client.base_url) as client:
        client.headers = {"Authorization": f"Bearer {token}"}
        if hasattr(pytest, "tenant_id") and pytest.tenant_id:
            client.headers["X-Tenant-ID"] = str(pytest.tenant_id)
            print(f"Adding X-Tenant-ID header: {pytest.tenant_id} for user2 client")
        print(f"Login successful for {email}. NEW Client authenticated.")
        yield client


@pytest_asyncio.fixture(scope="function")
async def authenticated_async_client_tenant_admin(async_client: AsyncClient) -> AsyncClient:
    """Provides an authenticated async client (using the tenant admin user)."""
    email = "tenantadmin@virtualstack.example"
    password = "testpassword789!"
    print(f"Attempting login for user: {email}")
    token = await get_user_token(async_client, email, password)
    async with AsyncClient(transport=async_client._transport, base_url=async_client.base_url) as client:
        client.headers = {"Authorization": f"Bearer {token}"}
        if hasattr(pytest, "tenant_id") and pytest.tenant_id:
            client.headers["X-Tenant-ID"] = str(pytest.tenant_id)
            print(f"Adding X-Tenant-ID header: {pytest.tenant_id} for tenant admin client")
        print(f"Login successful for {email}. NEW Client authenticated.")
        yield client

# --- Specific Test Dependencies ---

@pytest.fixture(scope="function")
def setup_invitation_dependencies() -> dict:
    """Provides necessary dependencies (tenant_id, role_id) for invitation tests."""
    assert hasattr(pytest, "tenant_id"), "tenant_id not set by setup_database fixture"
    assert hasattr(pytest, "tenant_admin_role_id"), "tenant_admin_role_id not set by setup_database fixture"

    return {
        "tenant_id": pytest.tenant_id,
        "role_id": pytest.tenant_admin_role_id # Use the Tenant Admin role created in setup
    }


# Make sure setup_database runs automatically before other fixtures if needed
@pytest_asyncio.fixture(autouse=True)
async def ensure_db_setup(setup_database):
    # This fixture doesn't do anything itself,
    # but ensures setup_database runs because of autouse=True
    pass

# Teardown logic (already handled by setup_database fixture)
# No explicit teardown fixture needed here as setup_database handles drop/create
