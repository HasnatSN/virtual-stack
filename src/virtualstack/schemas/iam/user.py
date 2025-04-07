from datetime import datetime
from typing import Optional

from pydantic import UUID4, BaseModel, EmailStr, Field, ConfigDict


class UserBase(BaseModel):
    """Base User schema with common attributes."""

    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False


class UserCreate(UserBase):
    """Schema for creating a new user, which includes the password."""

    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    """Schema for updating a user, where all fields are optional."""

    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    password: Optional[str] = Field(None, min_length=8)
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None


class User(UserBase):
    """Schema for returning a user, which includes the ID and timestamps."""

    id: UUID4
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# TODO: Consider adding Role info to User schema or UserListResponse items if needed by FE
class UserListResponse(BaseModel):
    """Response schema for paginated list of users."""
    items: list[User]
    total: int
    page: int
    limit: int
