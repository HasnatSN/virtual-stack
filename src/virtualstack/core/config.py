from typing import Any, Optional, Union

from pydantic import (
    AnyHttpUrl,
    PostgresDsn,
    ValidationInfo,
    field_validator,
    model_validator,
    Field
)
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings configuration class based on environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Allow extra fields from .env file
    )

    # Environment Configuration
    RUN_ENV: str = Field("development", description="Runtime environment (development, test, production)")
    APP_ENV: str = Field("development", description="Application environment (deprecated, use RUN_ENV)") # Marked as deprecated
    DEBUG: bool = Field(False, description="Debug mode flag")

    # Application Settings
    SECRET_KEY: str = "dev-secret-key-replace-in-production"

    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "VirtualStack API"
    VERSION: str = "0.1.0"
    DESCRIPTION: str = "VirtualStack API - Multi-tenant cloud management platform"

    # CORS Settings
    BACKEND_CORS_ORIGINS: list[AnyHttpUrl] = []

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, list[str]]) -> list[AnyHttpUrl]:
        if isinstance(v, str) and not v.startswith("["):
            return [item.strip() for item in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Database settings
    # Main DB
    DATABASE_URL: Optional[PostgresDsn] = None
    POSTGRES_SERVER: str = Field("db", description="Default DB host if DATABASE_URL not set")
    POSTGRES_USER: str = Field("postgres", description="Default DB user if DATABASE_URL not set")
    POSTGRES_PASSWORD: str = Field("postgres", description="Default DB password if DATABASE_URL not set")
    POSTGRES_DB: str = Field("virtualstack", description="Default DB name if DATABASE_URL not set")
    POSTGRES_PORT: str = Field("5432", description="Default DB port if DATABASE_URL not set")

    # Test DB
    TEST_DATABASE_URL: Optional[PostgresDsn] = None
    TEST_POSTGRES_SERVER: str = Field("localhost", description="Default Test DB host if TEST_DATABASE_URL not set")
    TEST_POSTGRES_USER: str = Field("testuser", description="Default Test DB user if TEST_DATABASE_URL not set")
    TEST_POSTGRES_PASSWORD: str = Field("testpassword", description="Default Test DB password if TEST_DATABASE_URL not set")
    TEST_POSTGRES_DB: str = Field("virtualstack_test", description="Default Test DB name if TEST_DATABASE_URL not set")
    TEST_POSTGRES_PORT: str = Field("5433", description="Default Test DB port if TEST_DATABASE_URL not set")

    @model_validator(mode='before')
    @classmethod
    def build_test_database_url(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Build TEST_DATABASE_URL from components if not explicitly set in env."""
        # Check if TEST_DATABASE_URL is already set (e.g., from .env)
        if values.get('TEST_DATABASE_URL') is not None:
            return values # Use the value from .env

        # If not set, build it from components
        scheme = "postgresql+asyncpg"
        user = values.get('TEST_POSTGRES_USER')
        password = values.get('TEST_POSTGRES_PASSWORD')
        host = values.get('TEST_POSTGRES_SERVER')
        port = values.get('TEST_POSTGRES_PORT')
        db = values.get('TEST_POSTGRES_DB')

        if all([user, password, host, port, db]): # Ensure all components are present
            # Directly assign the built URL string to the dictionary Pydantic will use
            # Pydantic will then validate this string against the PostgresDsn type hint later
            values['TEST_DATABASE_URL'] = (
                f"{scheme}://{user}:{password}@{host}:{port}/{db}"
            )
        else:
            # Handle cases where components might be missing if defaults weren't set properly
            # For now, we rely on the defaults being defined via Field()
            pass 

        return values

    # JWT Token settings
    def assemble_test_db_connection(cls, v: Optional[str], info: ValidationInfo) -> Any:
        """Build TEST_DATABASE_URL from components if not set explicitly."""
        if isinstance(v, str):
            # If TEST_DATABASE_URL is explicitly set (as str), validate and return
            return PostgresDsn(v)
        elif v is not None:
            # If it's already a PostgresDsn (e.g., from default), return it
            return v
        
        # If v is None, assemble from components
        values = info.data
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=values.get("TEST_POSTGRES_USER"),
            password=values.get("TEST_POSTGRES_PASSWORD"),
            host=values.get("TEST_POSTGRES_SERVER"),
            # Use the port from .env if provided, otherwise default
            port=int(values.get("TEST_POSTGRES_PORT", 5433)), 
            path=f"{values.get('TEST_POSTGRES_DB') or ''}",
        )

    # JWT Token settings
    JWT_SECRET_KEY: str = "demo-secret-key"  # Keep simple for tests, but change for prod
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Test User Settings
    TEST_USER_EMAIL: str = "admin@virtualstack.example"
    TEST_USER_PASSWORD: str = "testpassword123!"
    TEST_TENANT_SLUG: str = "test-tenant"
    DEFAULT_TEST_TENANT_NAME: str = "Default Test Tenant"

    # Redis settings
    REDIS_URL: Optional[str] = None
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None

    # Celery settings
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # Security
    API_KEY_SECRET: str = "dev-api-key-secret-replace-in-production"

    # Logging
    LOG_LEVEL: str = "INFO"


settings = Settings()
