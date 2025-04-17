import logging
import os  # Import os for environment variables
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from virtualstack.api.middleware import setup_middleware
from virtualstack.api.v1.api import api_router
from virtualstack.core.config import settings
from virtualstack.db.session import SessionLocal
from virtualstack.db.init_db import seed_initial_data

logger = logging.getLogger(__name__)


# Startup/Shutdown Events using asynccontextmanager (preferred for FastAPI)
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting application lifespan...")
    logger.info("Attempting initial data seeding...")
    # Log the DATABASE_URL for debugging
    logger.info(f"Using DATABASE_URL: {os.getenv('DATABASE_URL')}")
    
    async with SessionLocal() as db_session:
        try:
            await seed_initial_data(db_session) # Pass the session
            logger.info("About to flush and commit seeding transaction...")
            await db_session.flush()  # Ensure PKs are assigned even when later parts of the seed need them
            
            # Debug information about session state
            logger.info(f"Session state before commit - dirty: {len(db_session.dirty)}, new: {len(db_session.new)}")
            
            try:
                await db_session.commit() # Explicitly commit the transaction
                logger.info("Seeding transaction successfully committed")
            except Exception as e:
                logger.error(f"Commit failed: {e}")
                raise
        except Exception as e:
            logger.error(f"Initial data seeding failed: {e}. Rolling back...", exc_info=True)
            await db_session.rollback() # Rollback on error
            # Decide if we should raise to halt startup
            # raise e
    yield
    logger.info("Shutting down application lifespan...")
    # Add cleanup logic here if needed


# Create the FastAPI application with OpenAPI docs and lifespan manager
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup custom middleware
setup_middleware(app)


@app.get("/")
async def root():
    """Root endpoint for health checks."""
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "name": settings.PROJECT_NAME,
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.VERSION,
    }


# Import and include API routers
app.include_router(api_router, prefix=settings.API_V1_STR)
