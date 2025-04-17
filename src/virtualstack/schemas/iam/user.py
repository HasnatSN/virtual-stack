from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import UUID4, BaseModel, EmailStr, Field, ConfigDict, field_validator


class UserBase(BaseModel):
    """Base User schema with common attributes."""

    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: Optional[bool] = True


class UserCreate(UserBase):
    """Schema for creating a new user, which includes the password."""

    email: EmailStr
    password: str = Field(min_length=8)
    first_name: str
    last_name: str
    is_superuser: bool = False
    is_active: bool = True

    @field_validator('password')
    @classmethod
    def password_complexity(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v


class UserUpdate(UserBase):
    """Schema for updating a user, where all fields are optional."""

    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    password: Optional[str] = Field(default=None, min_length=8)
    is_active: Optional[bool] = None

    @field_validator('password')
    @classmethod
    def password_complexity(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if len(v) < 8:
                raise ValueError("Password must be at least 8 characters long")
        return v


class UserStatusUpdate(BaseModel):
    """Schema for updating just the active status of a user."""

    is_active: bool

    model_config = ConfigDict(
        json_schema_extra={"examples": [{"is_active": False}]}
    )


class UserInDBBase(UserBase):
    """Properties shared by models stored in DB."""

    id: UUID
    hashed_password: str
    is_superuser: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class User(UserInDBBase):
    """Schema for returning a user, which includes the ID and timestamps."""

    # Exclude sensitive fields by default
    hashed_password: Optional[str] = Field(None, exclude=True)
    # TODO: Add roles specific to the tenant context when returning user lists/details
    roles: Optional[List[str]] = Field(None, description="List of role names assigned to the user within the current tenant context")

    model_config = {
        "from_attributes": True,
        # Exclude hashed_password by default unless explicitly included
        # This is often handled by response_model exclusions too, but belt-and-suspenders
        "fields": {
            "hashed_password": {"exclude": True}
        }
    }


class UserInDB(UserInDBBase):
    pass


# TODO: Consider adding Role info to User schema or UserListResponse items if needed by FE
class UserListResponse(BaseModel):
    """Response schema for paginated list of users."""
    items: List[User]
    total: int
    page: int
    limit: int
