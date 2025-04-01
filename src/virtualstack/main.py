from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from virtualstack.api.middleware import setup_middleware
from virtualstack.api.v1.api import api_router
from virtualstack.core.config import settings


# Create the FastAPI application with OpenAPI docs
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
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
