from typing import List, Optional, Union, Dict, Any
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl, PostgresDsn, field_validator


class Settings(BaseSettings):
    """
    Application settings configuration class based on environment variables.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Allow extra fields from .env file
    )

    # Application Settings
    APP_ENV: str = "development"
    DEBUG: bool = False
    SECRET_KEY: str = "dev-secret-key-replace-in-production"
    
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "VirtualStack API"
    VERSION: str = "0.1.0"
    DESCRIPTION: str = "VirtualStack API - Multi-tenant cloud management platform"

    # CORS Settings
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[AnyHttpUrl]:
        if isinstance(v, str) and not v.startswith("["):
            return [item.strip() for item in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Database settings
    DATABASE_URL: Optional[str] = None
    POSTGRES_SERVER: str = "localhost"  # Default value for demo
    POSTGRES_USER: str = "postgres"  # Default value for demo
    POSTGRES_PASSWORD: str = "postgres"  # Default value for demo
    POSTGRES_DB: str = "virtualstack"  # Default value for demo
    POSTGRES_PORT: str = "5432"
    DATABASE_URI: Optional[PostgresDsn] = None

    @field_validator("DATABASE_URI", mode="before")
    def assemble_db_connection(cls, v: Optional[str], info: Dict[str, Any]) -> Any:
        if v:
            return v
            
        # Try to use DATABASE_URL if provided
        if info.data.get("DATABASE_URL"):
            return info.data.get("DATABASE_URL")
        
        # Otherwise build from components
        data = info.data
        
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=data.get("POSTGRES_USER"),
            password=data.get("POSTGRES_PASSWORD"),
            host=data.get("POSTGRES_SERVER"),
            port=int(data.get("POSTGRES_PORT", 5432)),
            path=f"{data.get('POSTGRES_DB') or ''}",
        )

    # JWT Token settings
    JWT_SECRET_KEY: str = "demo-secret-key"  # Default value for demo
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

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
