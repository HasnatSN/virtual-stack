from collections.abc import AsyncGenerator
import os

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from virtualstack.core.config import settings


# Determine which database URI to use
# Use TEST_DATABASE_URI if RUN_ENV is 'test', otherwise use DATABASE_URI
RUN_ENV = os.getenv("RUN_ENV", "development")  # Default to development

# Primary Database URI
# Use DATABASE_URL which is now directly loaded and validated by pydantic-settings
DATABASE_CONNECTION_URI = settings.DATABASE_URL
if not DATABASE_CONNECTION_URI:
    raise RuntimeError("Primary DATABASE_URL not configured.")

# Explicitly print the URI being used to create the engine
print(f"DEBUG [db/session.py]: Creating engine with URI: {DATABASE_CONNECTION_URI}")
engine = create_async_engine(
    str(DATABASE_CONNECTION_URI), 
    pool_pre_ping=True,
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",  # Control with SQL_ECHO env var
    echo_pool=False  # Disable pool logging as it rarely adds value
)
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Remove Test Database setup from here
# TEST_DATABASE_CONNECTION_URI = settings.TEST_DATABASE_URI
# if not TEST_DATABASE_CONNECTION_URI:
#     raise RuntimeError("Test TEST_DATABASE_URI not configured.")
# test_engine = create_async_engine(str(TEST_DATABASE_CONNECTION_URI), pool_pre_ping=True)
# TestingSessionLocal = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides an async database session.
    
    Uses SessionLocal by default. Tests should override this dependency.
    """
    # SessionFactory = TestingSessionLocal if RUN_ENV == "test" else SessionLocal # Removed check
    print("Opening a new database session")
    async with SessionLocal() as session: # Use primary SessionLocal
        try:
            yield session
            # Optionally commit here if you want auto-commit behavior for endpoints
            # await session.commit()
        except Exception as e:
            print(f"Error in session, rolling back: {e}")
            await session.rollback()
            raise
        finally:
            print("Closing database session")
            await session.close()
