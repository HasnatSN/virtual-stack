from typing import Any, Optional, Union

from pydantic import (
    AnyHttpUrl,
    PostgresDsn,
    ValidationInfo,
    field_validator,
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
    DATABASE_URL: Optional[str] = None
    POSTGRES_SERVER: str = "db"  # Changed default to match docker-compose service name
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "virtualstack"
    POSTGRES_PORT: str = "5432"
    DATABASE_URI: Optional[PostgresDsn] = None

    # Test DB
    TEST_DATABASE_URL: Optional[str] = None
    TEST_POSTGRES_SERVER: str = "localhost"  # Default for local test runs without docker
    TEST_POSTGRES_USER: str = "testuser"
    TEST_POSTGRES_PASSWORD: str = "testpassword"
    TEST_POSTGRES_DB: str = "virtualstack_test"
    TEST_POSTGRES_PORT: str = "5433"  # Default for local test runs without docker
    TEST_DATABASE_URI: Optional[PostgresDsn] = None

    @field_validator("DATABASE_URI", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Optional[str], values: ValidationInfo) -> Any:
        if isinstance(v, str):
            return v
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=values.data.get("POSTGRES_USER"),
            password=values.data.get("POSTGRES_PASSWORD"),
            host=values.data.get("POSTGRES_SERVER"),
            port=int(values.data.get("POSTGRES_PORT")),
            path=f"{values.data.get('POSTGRES_DB') or ''}",
        )

    @field_validator("TEST_DATABASE_URI", mode="before")
    @classmethod
    def assemble_test_db_connection(cls, v: Optional[str], values: ValidationInfo) -> Any:
        if isinstance(v, str):
            return v
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=values.data.get("TEST_POSTGRES_USER"),
            password=values.data.get("TEST_POSTGRES_PASSWORD"),
            host=values.data.get("TEST_POSTGRES_SERVER"),
            port=int(values.data.get("TEST_POSTGRES_PORT")),
            path=f"{values.data.get('TEST_POSTGRES_DB') or values.data.get('POSTGRES_DB') or ''}",
        )

    # JWT Token settings
    JWT_SECRET_KEY: str = "demo-secret-key"  # Keep simple for tests, but change for prod
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Test User Settings
    TEST_USER_EMAIL: str = "admin@virtualstack.example"
    TEST_USER_PASSWORD: str = "testpassword123!"

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
