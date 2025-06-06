from datetime import datetime
from typing import Optional

from pydantic import UUID4, BaseModel, constr, ConfigDict


class TenantBase(BaseModel):
    """Base Tenant schema with common attributes."""

    name: str
    slug: constr(min_length=3, max_length=50, pattern="^[a-z0-9-]+$")
    description: Optional[str] = None
    is_active: Optional[bool] = True


class TenantCreate(TenantBase):
    """Schema for creating a new tenant."""


class TenantUpdate(BaseModel):
    """Schema for updating a tenant, where all fields are optional."""

    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class Tenant(TenantBase):
    """Schema for returning a tenant, which includes the ID and timestamps."""

    id: UUID4
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
