from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import UUID4, BaseModel, Field, ConfigDict


class APIKeyScope(str, Enum):
    """Enum for API key scope types."""

    GLOBAL = "GLOBAL"
    TENANT = "TENANT"


class APIKeyBase(BaseModel):
    """Base schema for API Key data."""

    name: str = Field(..., description="Name of the API key")
    description: Optional[str] = Field(None, description="Optional description")
    is_active: bool = Field(True, description="Whether the API key is active")
    expires_at: Optional[datetime] = Field(
        None, description="Expiration date (null for no expiration)"
    )
    scope: APIKeyScope = Field(APIKeyScope.TENANT, description="Scope of the API key")
    tenant_id: Optional[UUID4] = Field(None, description="Tenant ID if scope is tenant-specific")

    # @validator('tenant_id') # TODO: Removed problematic Pydantic v1 validator. Re-evaluate need/implementation with Pydantic v2.
    # def validate_tenant_id(cls, v, values):
    #     """Validate that tenant_id is set if scope is TENANT."""
    #     if values.get('scope') == APIKeyScope.TENANT and v is None:
    #         raise ValueError('tenant_id must be provided when scope is TENANT')
    #     return v


class APIKeyCreate(APIKeyBase):
    """Schema for creating a new API key."""


class APIKeyUpdate(BaseModel):
    """Schema for updating an API key."""

    name: Optional[str] = Field(None, description="Name of the API key")
    description: Optional[str] = Field(None, description="Optional description")
    is_active: Optional[bool] = Field(None, description="Whether the API key is active")
    expires_at: Optional[datetime] = Field(
        None, description="Expiration date (null for no expiration)"
    )


class APIKeyInDB(APIKeyBase):
    """Schema for API key as stored in the database."""

    id: UUID4
    key_prefix: str = Field(..., description="First few characters of the key")
    user_id: UUID4 = Field(..., description="ID of the user who created the key")
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None

    # Use ConfigDict for Pydantic V2 compatibility
    model_config = ConfigDict(from_attributes=True)


class APIKeyWithValue(APIKeyInDB):
    """Schema for returning a newly created API key with its full value.
    This is returned only once when the key is created.
    """

    key: str = Field(..., description="The full API key value (only returned on creation)")

    # Inherits model_config from APIKeyInDB, but we can redefine if needed
    # model_config = ConfigDict(from_attributes=True)


class APIKey(APIKeyInDB):
    """Schema for returning an API key (without the key value)."""
