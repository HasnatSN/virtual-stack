from typing import AsyncGenerator
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from virtualstack.core.config import settings

# Determine which database URI to use
# Use TEST_DATABASE_URI if RUN_ENV is 'test', otherwise use DATABASE_URI
RUN_ENV = os.getenv("RUN_ENV", "development") # Default to development
DATABASE_CONNECTION_URI = settings.TEST_DATABASE_URI if RUN_ENV == "test" else settings.DATABASE_URI

if not DATABASE_CONNECTION_URI:
    raise RuntimeError("Database URI not configured. Set DATABASE_URI or TEST_DATABASE_URI.")

engine = create_async_engine(str(DATABASE_CONNECTION_URI), pool_pre_ping=True)

#expire_on_commit=False is important for async sessions
AsyncSessionFactory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that provides an async database session.
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
            # Optionally commit here if you want auto-commit behavior for endpoints
            # await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
