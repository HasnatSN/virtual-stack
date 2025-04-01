from collections.abc import AsyncGenerator
import os

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy.sql import text


# Set environment variable to indicate test mode *before* importing settings or app
os.environ["RUN_ENV"] = "test"

from virtualstack.core.config import settings
from virtualstack.db.base_class import Base  # Corrected import path
from virtualstack.db.session import get_db  # Added import for get_db
from virtualstack.main import app as fastapi_app  # Import your FastAPI app
from virtualstack.schemas.iam.user import UserCreate  # Import UserCreate schema
from virtualstack.services.iam import user_service  # Import user service


# --- Database Fixtures ---

# Create a new engine instance for testing, using NullPool to avoid connection hanging issues
engine = create_async_engine(str(settings.TEST_DATABASE_URI), echo=False, poolclass=NullPool)

# Create a new sessionmaker instance for testing
TestingSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def create_test_tables_and_user():
    """Drops/Creates the iam schema and tables, and ensures the test user exists."""
    async with engine.begin() as conn:
        # Use raw SQL to drop the schema and handle dependencies correctly
        print("Dropping existing 'iam' schema (if exists)...")  # Debug print
        await conn.execute(text("DROP SCHEMA IF EXISTS iam CASCADE;"))
        print("Creating 'iam' schema...")  # Debug print
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS iam;"))
        # Now create tables within the schema
        print("Creating tables...")  # Debug print
        await conn.run_sync(Base.metadata.create_all)
        print("Tables created.")  # Debug print

    # Create the user in a separate session to mimic real-world separation
    async with TestingSessionLocal() as session:
        user = await user_service.get_by_email(session, email=settings.TEST_USER_EMAIL)
        if not user:
            user_in = UserCreate(
                email=settings.TEST_USER_EMAIL,
                password=settings.TEST_USER_PASSWORD,  # Use the password from settings
                full_name="Test Admin User",
                is_superuser=True,
                is_active=True,
            )
            print(f"Creating test user: {settings.TEST_USER_EMAIL}")  # Debug print
            user = await user_service.create(session, obj_in=user_in)
            await session.commit()
            await session.refresh(user)
            print(f"Test user created: {user.email}, ID: {user.id}")  # Debug print
        else:
            print(f"Test user already exists: {user.email}, ID: {user.id}")  # Debug print


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    """Creates database tables and test user before test session and drops schema after."""
    print("Setting up database and test user for session...")  # Debug print
    await create_test_tables_and_user()
    print("Database and test user setup complete.")  # Debug print
    yield
    # Teardown: Drop the schema using raw SQL
    print("Dropping 'iam' schema...")  # Debug print
    async with engine.begin() as conn:
        # Explicitly drop the schema cascade
        await conn.execute(text("DROP SCHEMA IF EXISTS iam CASCADE;"))
    print("'iam' schema dropped.")  # Debug print

    print("Disposing database engine for session...")  # Debug print
    await engine.dispose()
    print("Database engine disposed.")  # Debug print


# --- Application Fixtures ---


@pytest.fixture(scope="session")
def app() -> FastAPI:
    """Return the FastAPI application instance."""

    # Ensure the override is set for the app instance used by httpx
    async def override_get_db_for_httpx() -> AsyncGenerator[AsyncSession, None]:
        async with TestingSessionLocal() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = override_get_db_for_httpx
    yield fastapi_app
    # Clean up override after session
    del fastapi_app.dependency_overrides[get_db]


@pytest_asyncio.fixture(scope="function")
async def async_client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Yield an httpx.AsyncClient configured for the test app (function scope)."""
    # Use ASGITransport with the app instance
    # Use base_url="http://testserver" for making requests
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
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
async def authenticated_async_client(
    async_client: AsyncClient,
    test_user: str,  # Expecting email (str) now
    test_password: str,
) -> AsyncClient:
    """Authenticate test user via API and return httpx.AsyncClient with header set."""
    login_data = {
        "username": test_user,  # Use the email directly
        "password": test_password,
    }
    print(f"Attempting login for user: {test_user}")  # Debug print
    # Use await for the async client call
    response = await async_client.post(
        f"{settings.API_V1_STR}/auth/login/access-token", data=login_data
    )
    try:
        response.raise_for_status()  # Raise exception for 4xx/5xx errors
    except Exception:
        print(f"Login failed: {response.text}")
        raise

    tokens = response.json()
    access_token = tokens["access_token"]

    # Set header on the async_client instance
    async_client.headers["Authorization"] = f"Bearer {access_token}"

    # Return the client ready for use in tests
    return async_client
