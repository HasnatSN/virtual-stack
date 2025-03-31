import asyncio
import os
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Set environment variable to indicate test mode *before* importing settings or app
os.environ["RUN_ENV"] = "test"

from virtualstack.core.config import settings
from virtualstack.db.base_class import Base # Corrected import path
from virtualstack.db.session import get_db # Added import for get_db
from virtualstack.main import app as fastapi_app # Import your FastAPI app

# --- Database Fixtures ---

# Create a new engine instance for testing
engine = create_async_engine(str(settings.TEST_DATABASE_URI), echo=False) # echo=False for cleaner test output

# Create a new sessionmaker instance for testing
TestingSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def create_test_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all) # Drop existing tables first
        await conn.run_sync(Base.metadata.create_all)

@pytest_asyncio.fixture(scope="session")
def event_loop(request) -> Generator:
    """Create an instance of the default event loop for each test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    # Set the event loop for the current context
    # This is important for pytest-asyncio with session-scoped fixtures
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="session", autouse=True) # Autouse ensures this runs for the session
async def setup_database():
    """Creates database tables before test session and disposes engine after."""
    await create_test_tables()
    yield engine
    await engine.dispose()

@pytest_asyncio.fixture(scope="function")
async def db_session(setup_database) -> AsyncGenerator[AsyncSession, None]: # Depends on setup_database
    """Yield a database session for a single test function."""
    async with TestingSessionLocal() as session:
        # Optional: Start a transaction
        # await session.begin()
        yield session
        # Optional: Rollback transaction after test
        # await session.rollback()


# --- Application Fixtures ---

@pytest.fixture(scope="session")
def app() -> FastAPI:
    """Return the FastAPI application instance."""
    return fastapi_app

@pytest_asyncio.fixture(scope="function")
async def async_client(app: FastAPI, db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]: # Added db_session dependency
    """Yield an HTTPX client for making requests to the test app.
       Overrides the get_db dependency to use the test session.
    """
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    # Use httpx.AsyncClient with base_url against the test server provided by pytest
    async with AsyncClient(base_url="http://testserver") as client: # Removed app=app
        yield client
    del app.dependency_overrides[get_db] # Clean up override
